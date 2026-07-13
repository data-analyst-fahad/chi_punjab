"""View decorators for role-based access."""
from __future__ import annotations

from functools import wraps

from django.http import JsonResponse
from django.shortcuts import redirect

from dashboard.permissions import is_super_admin


def super_admin_required(view_func):
    """Allow only super admin users (full dashboard, reports, settings, exports)."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if is_super_admin(request.user):
            return view_func(request, *args, **kwargs)

        if request.path.startswith("/api/") or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JsonResponse({"error": "Permission denied. Super admin access required."}, status=403)

        return redirect("dashboard")

    return wrapper
