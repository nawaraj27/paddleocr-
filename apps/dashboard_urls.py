"""Dashboard (HTML) routes — thin module to keep config.urls clean."""
from django.urls import path
from apps.core.views import DashboardView

app_name = "dashboard"
urlpatterns = [
    path("", DashboardView.as_view(), name="index"),
]
