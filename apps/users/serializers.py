from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "role", "is_approved",
                  "is_active", "approved_at", "created_at")
        read_only_fields = ("is_approved", "is_active", "approved_at", "created_at")


class ApprovalSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=User.Role.choices, required=False)
    action = serializers.ChoiceField(choices=["approve", "reject"])
