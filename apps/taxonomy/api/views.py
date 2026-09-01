from rest_framework import status, views, viewsets
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q, Avg, Count
from django.utils import timezone
from django.shortcuts import get_object_or_404

from apps.taxonomy.models import Product, ClassificationResult, ShopifyCategory, BatchJob
from apps.taxonomy.api.serializers import (
    ProductSerializer,
    ClassificationResultSerializer,
    ShopifyCategorySerializer,
    BatchJobSerializer,
    ReviewActionSerializer
)
from apps.taxonomy.services.ai_matcher import TaxonomyMatcher
from apps.taxonomy.services.attribute_extractor import extract_attributes_for_product
from apps.taxonomy.services.batch_processor import (
    start_batch_job,
    pause_batch_job,
    resume_batch_job,
    reset_batch_job,
    get_batch_job_status
)

class StandardProductPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100


class MetricsAPIView(views.APIView):
    """
    Returns executive-level KPI metrics summary for Dashboard.
    """
    def get(self, request):
        total_products = Product.objects.count()
        
        # Classification stats
        classifications = ClassificationResult.objects.all()
        processed_count = classifications.exclude(status=ClassificationResult.STATUS_UNPROCESSED).count()
        pending_count = total_products - processed_count
        requires_review_count = classifications.filter(status=ClassificationResult.STATUS_REQUIRES_REVIEW).count()
        approved_count = classifications.filter(
            status__in=[ClassificationResult.STATUS_APPROVED, ClassificationResult.STATUS_MANUALLY_OVERRIDDEN]
        ).count()
        
        avg_confidence = classifications.exclude(status=ClassificationResult.STATUS_UNPROCESSED).aggregate(
            avg=Avg('confidence_score')
        )['avg'] or 0.0

        high_confidence = classifications.filter(confidence_score__gte=70.0).count()
        medium_confidence = classifications.filter(confidence_score__gte=60.0, confidence_score__lt=70.0).count()
        low_confidence = classifications.exclude(status=ClassificationResult.STATUS_UNPROCESSED).filter(confidence_score__lt=60.0).count()

        # Job progress
        job = BatchJob.objects.filter(job_id='default_job').first()
        job_data = BatchJobSerializer(job).data if job else None

        return Response({
            'total_products': total_products,
            'processed_count': processed_count,
            'pending_count': pending_count,
            'requires_review_count': requires_review_count,
            'approved_count': approved_count,
            'average_confidence': round(avg_confidence, 1),
            'confidence_distribution': {
                'high': high_confidence,
                'medium': medium_confidence,
                'low': low_confidence
            },
            'batch_job': job_data
        })


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Paginated Product List with search, filtering, and classification details.
    """
    queryset = Product.objects.select_related('classification', 'classification__predicted_category').all()
    serializer_class = ProductSerializer
    pagination_class = StandardProductPagination

    def get_queryset(self):
        qs = super().get_queryset()
        
        search = self.request.query_params.get('search', '').strip()
        status_filter = self.request.query_params.get('status', '').strip().upper()
        category = self.request.query_params.get('category', '').strip()
        ordering = self.request.query_params.get('ordering', 'id')

        if search:
            qs = qs.filter(
                Q(product_number__icontains=search) |
                Q(product_name__icontains=search) |
                Q(model_number__icontains=search) |
                Q(product_category__icontains=search) |
                Q(product_sub_category__icontains=search) |
                Q(classification__predicted_category_name__icontains=search)
            )

        if status_filter:
            if status_filter in ('REVIEW_NEEDED', 'REQUIRES_REVIEW'):
                qs = qs.filter(classification__status=ClassificationResult.STATUS_REQUIRES_REVIEW)
            elif status_filter in ('COMPLETED', 'CLASSIFIED'):
                qs = qs.filter(classification__status__in=[
                    ClassificationResult.STATUS_CLASSIFIED,
                    ClassificationResult.STATUS_APPROVED,
                    ClassificationResult.STATUS_MANUALLY_OVERRIDDEN
                ])
            elif status_filter == 'APPROVED':
                qs = qs.filter(classification__status__in=[
                    ClassificationResult.STATUS_APPROVED,
                    ClassificationResult.STATUS_MANUALLY_OVERRIDDEN
                ])
            elif status_filter == 'UNPROCESSED':
                qs = qs.filter(Q(classification__isnull=True) | Q(classification__status=ClassificationResult.STATUS_UNPROCESSED))

        if category:
            qs = qs.filter(product_category__iexact=category)

        # Ordering
        allowed_orderings = ['id', '-id', 'product_number', '-product_number', 'product_name', '-product_name', 'classification__confidence_score', '-classification__confidence_score']
        if ordering in allowed_orderings:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by('id')

        return qs


class ProductReviewAPIView(views.APIView):
    """
    One-click Review, Manual Override & Save endpoint.
    """
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        serializer = ReviewActionSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        cat_id = data.get('category_id')
        cat_gid = data.get('category_gid')
        cat_name = data.get('category_name')
        extracted_attrs = data.get('extracted_attributes')
        review_notes = data.get('review_notes', '')
        new_status = data.get('status', ClassificationResult.STATUS_APPROVED)

        category = None
        if cat_id:
            category = ShopifyCategory.objects.filter(id=cat_id).first()
        elif cat_gid:
            category = ShopifyCategory.objects.filter(category_gid=cat_gid).first()

        if category:
            cat_name = category.full_name
        elif not cat_name and category is None:
            cat_name = getattr(product.classification, 'predicted_category_name', '')

        # Get or create classification
        clf, created = ClassificationResult.objects.get_or_create(
            product=product,
            defaults={'confidence_score': 100.0}
        )

        clf.predicted_category = category
        if cat_name:
            clf.predicted_category_name = cat_name
        if extracted_attrs is not None:
            clf.extracted_attributes = extracted_attrs
        clf.status = new_status
        clf.is_reviewed = True
        clf.reviewed_by = request.user.username if request.user.is_authenticated else 'Admin'
        clf.review_notes = review_notes
        clf.reviewed_at = timezone.now()
        clf.confidence_score = 100.0 if new_status in (ClassificationResult.STATUS_APPROVED, ClassificationResult.STATUS_MANUALLY_OVERRIDDEN) else clf.confidence_score
        clf.save()

        return Response({
            'message': 'Product classification approved and saved successfully.',
            'product_id': product.id,
            'status': clf.status,
            'category_name': clf.predicted_category_name,
            'classification': ClassificationResultSerializer(clf).data
        }, status=status.HTTP_200_OK)


class SingleProductClassifyAPIView(views.APIView):
    """
    Trigger instant on-demand AI classification for a single product.
    """
    def post(self, request, product_id):
        product = get_object_or_404(Product, id=product_id)
        matcher = TaxonomyMatcher.get_instance()
        matcher.initialize()

        extracted_attrs = extract_attributes_for_product(product)
        best_cat, cat_name, confidence, st, alternatives = matcher.classify_product(product)

        clf, created = ClassificationResult.objects.update_or_create(
            product=product,
            defaults={
                'predicted_category': best_cat,
                'predicted_category_name': cat_name,
                'confidence_score': confidence,
                'status': st,
                'extracted_attributes': extracted_attrs,
                'alternative_categories': alternatives,
                'classified_at': timezone.now()
            }
        )

        return Response({
            'message': 'Classification completed.',
            'product_id': product.id,
            'classification': ClassificationResultSerializer(clf).data
        })


class BatchControlAPIView(views.APIView):
    """
    Control endpoints for background batch processing (Start, Pause, Resume, Reset, Status).
    """
    def get(self, request):
        job = get_batch_job_status()
        return Response(BatchJobSerializer(job).data)

    def post(self, request):
        action = request.data.get('action', 'start').lower()
        chunk_size = int(request.data.get('chunk_size', 50))

        if action == 'start':
            res = start_batch_job(chunk_size=chunk_size)
        elif action == 'pause':
            res = pause_batch_job()
        elif action == 'resume':
            res = resume_batch_job(chunk_size=chunk_size)
        elif action == 'reset':
            res = reset_batch_job()
        else:
            return Response({'error': f"Unknown action '{action}'"}, status=status.HTTP_400_BAD_REQUEST)

        job_data = BatchJobSerializer(res.get('job')).data if 'job' in res else None
        return Response({
            'action': action,
            'result': res.get('status'),
            'job': job_data
        })


class TaxonomySearchAPIView(views.APIView):
    """
    Fast autocomplete lookup for official Shopify categories.
    """
    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if not q:
            categories = ShopifyCategory.objects.all()[:25]
        else:
            categories = ShopifyCategory.objects.filter(
                Q(full_name__icontains=q) |
                Q(name__icontains=q) |
                Q(vertical_name__icontains=q)
            )[:30]

        serializer = ShopifyCategorySerializer(categories, many=True)
        return Response(serializer.data)
