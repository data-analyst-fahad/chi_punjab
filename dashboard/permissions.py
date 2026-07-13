"""Role helpers for dashboard access control."""
from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser

SUPER_ADMIN_GROUP = "Super Admin"
DASHBOARD_VIEWER_USERNAME = "H&PD"


def is_super_admin(user: AbstractBaseUser | AnonymousUser) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name=SUPER_ADMIN_GROUP).exists()


def is_dashboard_user(user: AbstractBaseUser | AnonymousUser) -> bool:
    """Any authenticated dashboard user (H&PD, super admin, etc.)."""
    return user.is_authenticated


def is_restricted_dashboard_user(user: AbstractBaseUser | AnonymousUser) -> bool:
    """H&PD — full dashboard tabs, no Reports/Settings/admin."""
    if not user.is_authenticated:
        return False
    if is_super_admin(user):
        return False
    return user.username == DASHBOARD_VIEWER_USERNAME
