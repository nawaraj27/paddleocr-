from rest_framework import serializers
from .models import UploadedFile, UploadSession


class UploadedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = ("id", "original_name", "content_type", "size_bytes",
                  "status", "error", "processed_at", "created_at")
        read_only_fields = fields


class UploadSessionSerializer(serializers.ModelSerializer):
    files = UploadedFileSerializer(many=True, read_only=True)

    class Meta:
        model = UploadSession
        fields = ("id", "note", "created_at", "files")
