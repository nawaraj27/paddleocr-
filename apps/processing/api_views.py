"""APIs for viewing extracted docs, saving to DB, and managing categories."""
from __future__ import annotations

from django.db import transaction
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.models import Category, AuditLog
from apps.users.permissions import IsApproved, CanUpload
from .models import ExtractedDocument
from .serializers import (ExtractedDocumentSerializer, CategorySerializer,
                          SaveDocumentSerializer)


class CategoryViewSet(viewsets.ModelViewSet):
    """List + create categories (the 'add category' option)."""
    serializer_class = CategorySerializer
    queryset = Category.objects.all().order_by("name")

    def get_permissions(self):
        return [IsApproved()] if self.action in ("list", "retrieve") else [CanUpload()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class ExtractedDocumentViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin,
                               viewsets.GenericViewSet):
    serializer_class = ExtractedDocumentSerializer
    permission_classes = [IsApproved]
    filterset_fields = ["status", "is_saved", "category", "vendor_name"]
    search_fields = ["invoice_number", "vendor_name"]
    ordering_fields = ["created_at", "invoice_date", "total_amount"]

    def get_queryset(self):
        return (ExtractedDocument.objects
                .filter(uploaded_by=self.request.user)
                .select_related("category").prefetch_related("items"))

    @action(detail=True, methods=["post"], permission_classes=[CanUpload])
    def save_to_db(self, request, pk=None):
        """Confirm-save a reviewed extraction, optionally (re)categorizing.

        Supports creating a brand new category inline via ``new_category``.
        """
        doc = self.get_object()
        ser = SaveDocumentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        category = None
        new_name = (ser.validated_data.get("new_category") or "").strip()
        with transaction.atomic():
            if new_name:
                category, _ = Category.objects.get_or_create(
                    name=new_name, defaults={"created_by": request.user})
            elif ser.validated_data.get("category_id"):
                category = Category.objects.filter(
                    pk=ser.validated_data["category_id"]).first()
            doc.category = category
            doc.is_saved = True
            doc.save(update_fields=["category", "is_saved", "updated_at"])
        AuditLog.record(request, AuditLog.Action.DATA_ACCESS,
                        target=f"doc:{doc.id}", op="save",
                        category=category.name if category else None)
        return Response(ExtractedDocumentSerializer(doc).data,
                        status=status.HTTP_200_OK)
