from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render
from django.views import View

from .models import Product


class InventoryListView(LoginRequiredMixin, View):
    def get(self, request):
        store = getattr(request, "store", None)
        products = (Product.objects.filter(store=store).select_related("category")
                    if store else Product.objects.none())
        return render(request, "inventory/list.html",
                      {"products": products[:500]})
