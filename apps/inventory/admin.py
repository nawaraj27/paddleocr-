from django.contrib import admin

from .models import Product, ProductCategory, StockMovement


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "store")
    list_filter = ("store",)
    search_fields = ("name",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "sku", "store", "category", "quantity_on_hand",
                    "sale_price", "is_active")
    list_filter = ("store", "is_active", "category")
    search_fields = ("name", "sku")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ("product", "delta", "reason", "store", "created_at")
    list_filter = ("store", "reason")
    search_fields = ("product__name",)
    readonly_fields = ("created_at", "updated_at")
