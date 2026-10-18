from django.conf import settings
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("members.urls")),
    path("", include("dues.urls")),
    path("", include("teams.urls")),
    path("", include("tournaments.urls")),
    path("", include("comms.urls")),
    path("", include("cashbook.urls")),
    path("", include("core.urls")),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    try:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]
    except ImportError:
        pass
