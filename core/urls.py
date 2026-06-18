from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from core.views import metrics_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("ollama.urls")),
    path("", include("accounts.urls")),
    path("metrics/", metrics_view, name="prometheus-metrics"),
]

if settings.DEBUG:
    from django.conf.urls.static import static

    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
