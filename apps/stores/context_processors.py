def store_context(request):
    """Expose the active store + the user's stores to templates."""
    store = getattr(request, "store", None)
    stores = []
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from .models import Store
        stores = list(Store.objects.filter(
            memberships__user=user, memberships__is_active=True,
            is_active=True).distinct())
    return {"active_store": store, "user_stores": stores}
