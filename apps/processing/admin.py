from django.contrib import admin
from .models import ExtractedDocument, InvoiceItem, ProcessingLog


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0


@admin.register(ExtractedDocument)
class ExtractedDocumentAdmin(admin.ModelAdmin):
    list_display = ("invoice_number", "vendor_name", "total_amount",
                    "category", "is_saved", "uploaded_by", "processed_at")
    list_filter = ("is_saved", "status", "category")
    search_fields = ("invoice_number", "vendor_name")
    inlines = [InvoiceItemInline]


admin.site.register(ProcessingLog)
