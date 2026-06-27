"""Store selection / creation / switching for the workspace."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from .forms import StoreForm
from .models import Store, StoreMembership


class StoreSelectView(LoginRequiredMixin, View):
    def get(self, request):
        stores = Store.objects.filter(
            memberships__user=request.user, memberships__is_active=True,
            is_active=True).distinct()
        return render(request, "stores/select.html", {"stores": stores})


class StoreCreateView(LoginRequiredMixin, View):
    def get(self, request):
        return render(request, "stores/create.html", {"form": StoreForm()})

    def post(self, request):
        form = StoreForm(request.POST, request.FILES)
        if form.is_valid():
            store = form.save(commit=False)
            store.owner = request.user
            store.save()
            StoreMembership.objects.create(
                store=store, user=request.user,
                role=StoreMembership.Role.OWNER)
            request.session["active_store_id"] = store.id
            messages.success(request, f"Store '{store.name}' created.")
            return redirect("dashboard:index")
        return render(request, "stores/create.html", {"form": form})


class StoreSwitchView(LoginRequiredMixin, View):
    def post(self, request, pk):
        store = get_object_or_404(
            Store, pk=pk, memberships__user=request.user,
            memberships__is_active=True)
        request.session["active_store_id"] = store.id
        return redirect(request.POST.get("next") or reverse("dashboard:index"))
