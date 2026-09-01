from django.urls import path, include
from apps.taxonomy.views import DashboardView, ReviewQueueView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('review/', ReviewQueueView.as_view(), name='review-queue'),
    path('api/', include('apps.taxonomy.api.urls')),
]
