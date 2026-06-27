"""HTML auth views: register, login (rate-limited), logout, user admin."""
from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.core.cache import cache
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from apps.core.models import AuditLog
from .forms import RegisterForm, LoginForm

User = get_user_model()
LOGIN_MAX_ATTEMPTS = 5
LOGIN_WINDOW_S = 300


class RegisterView(View):
    def get(self, request):
        return render(request, "auth/register.html", {"form": RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            AuditLog.record(request, AuditLog.Action.REGISTER, target=user.username)
            messages.success(
                request, "Account created. An admin must approve it before login.")
            return redirect(reverse("users:login"))
        return render(request, "auth/register.html", {"form": form})


class LoginView(View):
    def get(self, request):
        return render(request, "auth/login.html", {"form": LoginForm()})

    def post(self, request):
        ip = request.META.get("REMOTE_ADDR", "?")
        key = f"login_attempts:{ip}"
        attempts = cache.get(key, 0)
        if attempts >= LOGIN_MAX_ATTEMPTS:
            messages.error(request, "Too many attempts. Try again later.")
            return render(request, "auth/login.html", {"form": LoginForm()}, status=429)

        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(request, username=form.cleaned_data["username"],
                                password=form.cleaned_data["password"])
            if user is None:
                cache.set(key, attempts + 1, LOGIN_WINDOW_S)
                AuditLog.record(request, AuditLog.Action.LOGIN_FAILED,
                                target=form.cleaned_data["username"])
                messages.error(request, "Invalid credentials.")
            elif not user.is_approved or not user.is_active:
                messages.warning(request, "Your account is pending admin approval.")
            else:
                login(request, user)
                cache.delete(key)
                AuditLog.record(request, AuditLog.Action.LOGIN, target=user.username)
                return redirect(reverse("dashboard:index"))
        return render(request, "auth/login.html", {"form": form})


class LogoutView(View):
    def post(self, request):
        if request.user.is_authenticated:
            AuditLog.record(request, AuditLog.Action.LOGOUT, target=request.user.username)
        logout(request)
        return redirect(reverse("landing"))


class UserAdminView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Admin-only page to approve/reject and assign roles."""
    template_name = "users/index.html"
    context_object_name = "users"
    paginate_by = 25

    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin_role

    def get_queryset(self):
        return User.objects.order_by("is_approved", "-created_at")


class UserApprovalActionView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_admin_role

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        action = request.POST.get("action")
        role = request.POST.get("role") or None
        if action == "approve":
            target.approve(by=request.user, role=role)
            AuditLog.record(request, AuditLog.Action.ADMIN_ACTION,
                            target=target.username, op="approve", role=target.role)
            messages.success(request, f"Approved {target.username} as {target.role}.")
        elif action == "reject":
            target.is_active = False
            target.is_approved = False
            target.save(update_fields=["is_active", "is_approved", "updated_at"])
            AuditLog.record(request, AuditLog.Action.ADMIN_ACTION,
                            target=target.username, op="reject")
            messages.info(request, f"Rejected {target.username}.")
        return redirect(reverse("users:admin"))
