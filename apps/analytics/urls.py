from django.urls import path
from .views import AnalyticsView

app_name = "analytics"
urlpatterns = [path("", AnalyticsView.as_view(), name="index")]
