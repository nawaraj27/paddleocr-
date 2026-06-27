from django.contrib import admin
from .models import UploadSession, UploadedFile


@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ("original_name", "uploaded_by", "status", "content_type",
                    "size_bytes", "processed_at")
    list_filter = ("status", "content_type")
    search_fields = ("original_name", "sha256")


admin.site.register(UploadSession)
