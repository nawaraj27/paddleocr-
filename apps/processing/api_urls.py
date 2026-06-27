from rest_framework.routers import DefaultRouter
from .api_views import ExtractedDocumentViewSet, CategoryViewSet

router = DefaultRouter()
router.register("documents", ExtractedDocumentViewSet, basename="document")
router.register("categories", CategoryViewSet, basename="category")
urlpatterns = router.urls
