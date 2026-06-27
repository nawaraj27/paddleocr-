from rest_framework.routers import DefaultRouter
from .api_views import UploadedFileViewSet

router = DefaultRouter()
router.register("files", UploadedFileViewSet, basename="uploadedfile")
urlpatterns = router.urls
