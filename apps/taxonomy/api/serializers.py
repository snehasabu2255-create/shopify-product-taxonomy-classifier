from rest_framework import serializers
from apps.taxonomy.models import ShopifyCategory, ShopifyAttribute, Product, ClassificationResult, BatchJob


class ShopifyCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopifyCategory
        fields = ['id', 'category_gid', 'name', 'full_name', 'level', 'parent_gid', 'vertical_name', 'attributes_json']


class ShopifyAttributeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopifyAttribute
        fields = ['id', 'attribute_gid', 'name', 'handle', 'description']


class ClassificationResultSerializer(serializers.ModelSerializer):
    predicted_category = ShopifyCategorySerializer(read_only=True)
    predicted_category_id = serializers.PrimaryKeyRelatedField(
        queryset=ShopifyCategory.objects.all(),
        source='predicted_category',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = ClassificationResult
        fields = [
            'id',
            'product_id',
            'predicted_category',
            'predicted_category_id',
            'predicted_category_name',
            'confidence_score',
            'status',
            'extracted_attributes',
            'alternative_categories',
            'is_reviewed',
            'reviewed_by',
            'review_notes',
            'classified_at',
            'reviewed_at',
        ]


class ProductSerializer(serializers.ModelSerializer):
    classification = ClassificationResultSerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            'id',
            'product_number',
            'model_number',
            'product_category',
            'product_sub_category',
            'collection_name',
            'color_collection',
            'product_color',
            'product_name',
            'product_description',
            'bullets',
            'set_includes',
            'product_weight',
            'materials',
            'product_dimensions',
            'assembly_required',
            'is_set',
            'stackable',
            'country_of_origin',
            'item_cost',
            'map_price',
            'msrp',
            'primary_image_url',
            'image_urls',
            'shipping_method',
            'total_box_count',
            'pallet_count',
            'shipping_weight',
            'total_cbm',
            'package_dimensions',
            'product_url',
            'classification',
            'created_at',
            'updated_at',
        ]


class ReviewActionSerializer(serializers.Serializer):
    category_id = serializers.IntegerField(required=False, allow_null=True)
    category_gid = serializers.CharField(required=False, allow_blank=True)
    category_name = serializers.CharField(required=False, allow_blank=True)
    extracted_attributes = serializers.DictField(required=False)
    review_notes = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=ClassificationResult.STATUS_CHOICES,
        default=ClassificationResult.STATUS_APPROVED
    )


class BatchJobSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.SerializerMethodField()

    class Meta:
        model = BatchJob
        fields = [
            'job_id',
            'status',
            'total_items',
            'processed_items',
            'success_items',
            'review_needed_items',
            'last_processed_product_id',
            'current_index',
            'chunk_size',
            'progress_percentage',
            'started_at',
            'updated_at',
            'completed_at',
            'error_message',
        ]

    def get_progress_percentage(self, obj):
        if obj.total_items > 0:
            return round((obj.processed_items / obj.total_items) * 100.0, 2)
        return 0.0
