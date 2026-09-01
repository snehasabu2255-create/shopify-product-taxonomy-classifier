from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.taxonomy.api.views import (
    MetricsAPIView,
    ProductViewSet,
    ProductReviewAPIView,
    SingleProductClassifyAPIView,
    BatchControlAPIView,
    TaxonomySearchAPIView,
)

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')

urlpatterns = [
    path('metrics/', MetricsAPIView.as_view(), name='api-metrics'),
    path('products/<int:product_id>/review/', ProductReviewAPIView.as_view(), name='api-product-review'),
    path('products/<int:product_id>/classify/', SingleProductClassifyAPIView.as_view(), name='api-product-classify'),
    path('batch/control/', BatchControlAPIView.as_view(), name='api-batch-control'),
    path('batch/status/', BatchControlAPIView.as_view(), name='api-batch-status'),
    path('taxonomy/search/', TaxonomySearchAPIView.as_view(), name='api-taxonomy-search'),
    path('', include(router.urls)),
]
