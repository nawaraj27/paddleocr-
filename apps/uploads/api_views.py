from rest_framework import viewsets, mixins
from rest_framework.throttling import ScopedRateThrottle

from apps.users.permissions import IsApproved
from .models import UploadedFile
from .serializers import UploadedFileSerializer


class UploadedFileViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                          viewsets.GenericViewSet):
    serializer_class = UploadedFileSerializer
    permission_classes = [IsApproved]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "upload"
    filterset_fields = ["status", "content_type"]
    ordering_fields = ["created_at", "processed_at"]

    def get_queryset(self):
        return UploadedFile.objects.filter(uploaded_by=self.request.user)
