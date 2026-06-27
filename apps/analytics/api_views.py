from rest_framework.views import APIView
from rest_framework.response import Response

from apps.users.permissions import CanViewAnalytics
from .services import compute


class AnalyticsAPIView(APIView):
    permission_classes = [CanViewAnalytics]

    def get(self, request):
        filters = {
            "vendor": request.GET.get("vendor") or None,
            "category": request.GET.get("category") or None,
            "date_from": request.GET.get("date_from") or None,
            "date_to": request.GET.get("date_to") or None,
            "granularity": request.GET.get("granularity", "day"),
            "saved_only": request.GET.get("saved_only", "1") == "1",
        }
        return Response(compute(request.user, filters))
