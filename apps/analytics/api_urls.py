from django.urls import path
from .api_views import AnalyticsAPIView

urlpatterns = [path("", AnalyticsAPIView.as_view(), name="analytics-data")]
