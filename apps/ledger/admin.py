from django.contrib import admin

from .models import Party, Transaction, TransactionLine, DocumentMapping


class LineInline(admin.TabularInline):
    model = TransactionLine
    extra = 0


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "store", "kind", "status", "date", "total")
    list_filter = ("store", "kind", "status")
    search_fields = ("number", "party__name")
    inlines = [LineInline]


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "store", "phone")
    list_filter = ("store", "kind")
    search_fields = ("name",)


@admin.register(DocumentMapping)
class DocumentMappingAdmin(admin.ModelAdmin):
    list_display = ("document", "store", "detected_kind", "status",
                    "transaction", "mapped_at")
    list_filter = ("store", "status", "detected_kind")
