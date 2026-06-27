from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView
from apps.core.models import Category


class AnalyticsView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = "analytics/index.html"
    raise_exception = True

    def test_func(self):
        return self.request.user.can_view_analytics()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = Category.objects.order_by("name")
        return ctx
