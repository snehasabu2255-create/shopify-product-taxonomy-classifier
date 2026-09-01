from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from apps.taxonomy.models import Product, ClassificationResult, BatchJob, ShopifyCategory

class DashboardView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        total_products = Product.objects.count()
        classifications = ClassificationResult.objects.all()
        processed_count = classifications.exclude(status=ClassificationResult.STATUS_UNPROCESSED).count()
        pending_count = total_products - processed_count
        requires_review_count = classifications.filter(status=ClassificationResult.STATUS_REQUIRES_REVIEW).count()
        approved_count = classifications.filter(
            status__in=[ClassificationResult.STATUS_APPROVED, ClassificationResult.STATUS_MANUALLY_OVERRIDDEN]
        ).count()

        batch_job = BatchJob.objects.filter(job_id='default_job').first()
        categories = ShopifyCategory.objects.all()[:50]

        context.update({
            'total_products': total_products,
            'processed_count': processed_count,
            'pending_count': pending_count,
            'requires_review_count': requires_review_count,
            'approved_count': approved_count,
            'batch_job': batch_job,
            'categories': categories,
        })
        return context


class ReviewQueueView(TemplateView):
    template_name = 'review.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Products that need review or are low confidence
        review_products = Product.objects.filter(
            classification__status=ClassificationResult.STATUS_REQUIRES_REVIEW
        ).select_related('classification', 'classification__predicted_category')[:100]

        total_review_count = Product.objects.filter(
            classification__status=ClassificationResult.STATUS_REQUIRES_REVIEW
        ).count()

        context.update({
            'review_products': review_products,
            'total_review_count': total_review_count,
        })
        return context
