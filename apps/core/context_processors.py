def app_context(request):
    """Expose nav + role flags to all templates."""
    user = getattr(request, "user", None)
    role = getattr(user, "role", None) if user and user.is_authenticated else None
    return {
        "APP_NAME": "Mero Dokan",
        "current_role": role,
        "is_admin_role": role == "admin" if role else False,
        "can_upload": user.can_upload() if user and user.is_authenticated else False,
        "can_view_analytics": user.can_view_analytics() if user and user.is_authenticated else False,
    }
