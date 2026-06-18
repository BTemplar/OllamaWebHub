from django.conf import settings
from django.http import HttpResponseForbidden
from django_prometheus.exports import ExportToDjangoView


def metrics_view(request):
    if not settings.DEBUG:
        client_ip = request.META.get("REMOTE_ADDR", "")
        allowed = settings.METRICS_ALLOWED_IPS
        if allowed and client_ip not in allowed:
            return HttpResponseForbidden("Metrics access denied")
    return ExportToDjangoView(request)
