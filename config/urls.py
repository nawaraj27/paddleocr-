"""Root URL configuration."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from apps.core.views import LandingView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", LandingView.as_view(), name="landing"),
    path("auth/", include("apps.users.urls")),
    path("dashboard/", include("apps.dashboard_urls")),
    path("uploads/", include("apps.uploads.urls")),
    path("processing/", include("apps.processing.urls")),
    path("analytics/", include("apps.analytics.urls")),
    path("app/", include("apps.stores.urls")),
    path("app/", include("apps.inventory.urls")),
    path("app/", include("apps.ledger.urls")),
    # JSON APIs
    path("api/users/", include("apps.users.api_urls")),
    path("api/uploads/", include("apps.uploads.api_urls")),
    path("api/processing/", include("apps.processing.api_urls")),
    path("api/analytics/", include("apps.analytics.api_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
