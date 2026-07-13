"""Template context for user roles."""
from __future__ import annotations

from dashboard.permissions import is_super_admin


def user_access(request):
    return {
        "is_super_admin": is_super_admin(request.user),
    }
