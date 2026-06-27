from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.models import AuditLog
from .permissions import IsAdmin, IsApproved
from .serializers import UserSerializer, ApprovalSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("-created_at")
    serializer_class = UserSerializer
    filterset_fields = ["role", "is_approved", "is_active"]
    search_fields = ["username", "email"]

    def get_permissions(self):
        if self.action in ("list", "retrieve", "me"):
            return [IsApproved()]
        return [IsAdmin()]

    @action(detail=False, methods=["get"])
    def me(self, request):
        return Response(UserSerializer(request.user).data)

    @action(detail=True, methods=["post"])
    def approval(self, request, pk=None):
        target = self.get_object()
        ser = ApprovalSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if ser.validated_data["action"] == "approve":
            target.approve(by=request.user, role=ser.validated_data.get("role"))
        else:
            target.is_active = target.is_approved = False
            target.save(update_fields=["is_active", "is_approved", "updated_at"])
        AuditLog.record(request, AuditLog.Action.ADMIN_ACTION,
                        target=target.username, op=ser.validated_data["action"])
        return Response(UserSerializer(target).data, status=status.HTTP_200_OK)
