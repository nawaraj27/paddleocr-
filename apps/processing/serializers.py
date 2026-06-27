from rest_framework import serializers
from apps.core.models import Category
from .models import ExtractedDocument, InvoiceItem


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug", "color")
        read_only_fields = ("slug",)


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = ("id", "name", "quantity", "unit_price", "amount")


class ExtractedDocumentSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = ExtractedDocument
        fields = ("id", "invoice_number", "vendor_name", "invoice_date",
                  "currency", "subtotal", "tax", "total_amount", "category",
                  "confidence", "model_version", "is_saved", "status",
                  "raw_json", "items", "created_at", "processed_at")
        read_only_fields = fields


class SaveDocumentSerializer(serializers.Serializer):
    category_id = serializers.IntegerField(required=False, allow_null=True)
    new_category = serializers.CharField(required=False, allow_blank=True)
