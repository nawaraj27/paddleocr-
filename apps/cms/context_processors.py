def landing_content(request):
    """Inject published CMS content (used by the public landing template)."""
    if request.path != "/":
        return {}
    from .models import (SiteSettings, FeatureBlock, Screenshot,
                         PlatformDownload, NavLink)
    return {
        "site": SiteSettings.get(),
        "features": list(FeatureBlock.objects.filter(is_published=True)),
        "screenshots": list(Screenshot.objects.filter(is_published=True)),
        "downloads": list(PlatformDownload.objects.filter(is_active=True)),
        "nav_links": list(NavLink.objects.filter(group="nav", is_active=True)),
        "footer_links": list(NavLink.objects.filter(group="footer",
                                                    is_active=True)),
    }
