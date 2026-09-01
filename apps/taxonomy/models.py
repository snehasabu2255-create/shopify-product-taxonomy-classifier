from django.db import models
from django.utils import timezone

class ShopifyCategory(models.Model):
    """
    Official Shopify Standard Product Taxonomy Node.
    """
    category_gid = models.CharField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=255, db_index=True)
    full_name = models.CharField(max_length=1000, db_index=True)
    level = models.IntegerField(default=0)
    parent_gid = models.CharField(max_length=255, blank=True, null=True)
    vertical_name = models.CharField(max_length=255, blank=True, null=True)
    attributes_json = models.JSONField(default=list, blank=True)
    search_text = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Shopify Category'
        verbose_name_plural = 'Shopify Categories'
        ordering = ['full_name']

    def __str__(self):
        return self.full_name


class ShopifyAttribute(models.Model):
    """
    Official Shopify Taxonomy Attribute Definition.
    """
    attribute_gid = models.CharField(max_length=255, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    handle = models.CharField(max_length=255, db_index=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Shopify Attribute'
        verbose_name_plural = 'Shopify Attributes'

    def __str__(self):
        return f"{self.name} ({self.handle})"


class Product(models.Model):
    """
    Raw Product Record imported from Product_List.xlsx.
    """
    product_number = models.CharField(max_length=100, unique=True, db_index=True)
    model_number = models.CharField(max_length=100, blank=True, default='')
    product_category = models.CharField(max_length=255, blank=True, default='')
    product_sub_category = models.CharField(max_length=255, blank=True, default='')
    collection_name = models.CharField(max_length=255, blank=True, default='')
    color_collection = models.CharField(max_length=255, blank=True, default='')
    product_color = models.CharField(max_length=255, blank=True, default='')
    product_name = models.CharField(max_length=500, db_index=True)
    product_description = models.TextField(blank=True, default='')
    bullets = models.TextField(blank=True, default='')
    set_includes = models.TextField(blank=True, default='')
    product_weight = models.FloatField(null=True, blank=True)
    materials = models.TextField(blank=True, default='')
    product_dimensions = models.TextField(blank=True, default='')
    assembly_required = models.CharField(max_length=50, blank=True, default='')
    is_set = models.CharField(max_length=50, blank=True, default='')
    stackable = models.CharField(max_length=50, blank=True, default='')
    country_of_origin = models.CharField(max_length=100, blank=True, default='')
    item_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    map_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    msrp = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    primary_image_url = models.CharField(max_length=1000, blank=True, default='')
    image_urls = models.JSONField(default=list, blank=True)
    shipping_method = models.CharField(max_length=100, blank=True, default='')
    total_box_count = models.IntegerField(default=1, null=True, blank=True)
    pallet_count = models.FloatField(null=True, blank=True)
    shipping_weight = models.FloatField(null=True, blank=True)
    total_cbm = models.FloatField(null=True, blank=True)
    package_dimensions = models.TextField(blank=True, default='')
    product_url = models.CharField(max_length=1000, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Product'
        verbose_name_plural = 'Products'
        ordering = ['id']

    def __str__(self):
        return f"{self.product_number} - {self.product_name}"


class ClassificationResult(models.Model):
    """
    Classification & Attribute Extraction Output for a Product.
    """
    STATUS_UNPROCESSED = 'UNPROCESSED'
    STATUS_CLASSIFIED = 'CLASSIFIED'
    STATUS_REQUIRES_REVIEW = 'REQUIRES_REVIEW'
    STATUS_MANUALLY_OVERRIDDEN = 'MANUALLY_OVERRIDDEN'
    STATUS_APPROVED = 'APPROVED'

    STATUS_CHOICES = [
        (STATUS_UNPROCESSED, 'Unprocessed'),
        (STATUS_CLASSIFIED, 'Classified'),
        (STATUS_REQUIRES_REVIEW, 'Requires Review'),
        (STATUS_MANUALLY_OVERRIDDEN, 'Manually Overridden'),
        (STATUS_APPROVED, 'Approved'),
    ]

    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='classification')
    predicted_category = models.ForeignKey(ShopifyCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='classifications')
    predicted_category_name = models.CharField(max_length=1000, blank=True, default='')
    confidence_score = models.FloatField(default=0.0)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=STATUS_UNPROCESSED, db_index=True)
    extracted_attributes = models.JSONField(default=dict, blank=True)
    alternative_categories = models.JSONField(default=list, blank=True)
    is_reviewed = models.BooleanField(default=False)
    reviewed_by = models.CharField(max_length=100, blank=True, default='')
    review_notes = models.TextField(blank=True, default='')
    classified_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Classification Result'
        verbose_name_plural = 'Classification Results'
        ordering = ['product_id']

    def __str__(self):
        return f"{self.product.product_number} -> {self.predicted_category_name} ({self.confidence_score:.1f}%)"


class BatchJob(models.Model):
    """
    Background batch processing state tracker with resume capability.
    """
    STATUS_IDLE = 'IDLE'
    STATUS_RUNNING = 'RUNNING'
    STATUS_PAUSED = 'PAUSED'
    STATUS_COMPLETED = 'COMPLETED'
    STATUS_FAILED = 'FAILED'

    STATUS_CHOICES = [
        (STATUS_IDLE, 'Idle'),
        (STATUS_RUNNING, 'Running'),
        (STATUS_PAUSED, 'Paused'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
    ]

    job_id = models.CharField(max_length=100, unique=True, default='default_job')
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default=STATUS_IDLE)
    total_items = models.IntegerField(default=0)
    processed_items = models.IntegerField(default=0)
    success_items = models.IntegerField(default=0)
    review_needed_items = models.IntegerField(default=0)
    last_processed_product_id = models.BigIntegerField(default=0)
    current_index = models.IntegerField(default=0)
    chunk_size = models.IntegerField(default=50)
    started_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Batch Processing Job'
        verbose_name_plural = 'Batch Processing Jobs'

    def __str__(self):
        return f"Job {self.job_id} [{self.status}]: {self.processed_items}/{self.total_items}"
