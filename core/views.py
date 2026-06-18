from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django_prometheus.exports import ExportToDjangoView


def metrics_view(request: HttpRequest) -> HttpResponse:
    """
    Serve Prometheus metrics, optionally restricted by client IP in production.

    Args:
        request (HttpRequest): Current HTTP request.

    Returns:
        HttpResponse: Prometheus metrics payload or 403 when access is denied.
    """
    if not settings.DEBUG:
        client_ip = request.META.get("REMOTE_ADDR", "")
        allowed = settings.METRICS_ALLOWED_IPS
        if allowed and client_ip not in allowed:
            return HttpResponseForbidden("Metrics access denied")
    return ExportToDjangoView(request)
