from django.contrib import admin
from .models import ShopifyCategory, ShopifyAttribute, Product, ClassificationResult, BatchJob

@admin.register(ShopifyCategory)
class ShopifyCategoryAdmin(admin.ModelAdmin):
    list_display = ('category_gid', 'name', 'full_name', 'level', 'vertical_name')
    search_fields = ('name', 'full_name', 'category_gid')
    list_filter = ('vertical_name', 'level')


@admin.register(ShopifyAttribute)
class ShopifyAttributeAdmin(admin.ModelAdmin):
    list_display = ('name', 'handle', 'attribute_gid')
    search_fields = ('name', 'handle')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_number', 'product_name', 'product_category', 'product_sub_category', 'item_cost', 'created_at')
    search_fields = ('product_number', 'product_name', 'model_number')
    list_filter = ('product_category', 'product_sub_category')


@admin.register(ClassificationResult)
class ClassificationResultAdmin(admin.ModelAdmin):
    list_display = ('product', 'predicted_category_name', 'confidence_score', 'status', 'is_reviewed', 'classified_at')
    search_fields = ('product__product_number', 'product__product_name', 'predicted_category_name')
    list_filter = ('status', 'is_reviewed')


@admin.register(BatchJob)
class BatchJobAdmin(admin.ModelAdmin):
    list_display = ('job_id', 'status', 'processed_items', 'total_items', 'last_processed_product_id', 'updated_at')
