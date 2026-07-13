"""Create super admin and H&PD dashboard viewer accounts."""
from __future__ import annotations

import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from dashboard.permissions import DASHBOARD_VIEWER_USERNAME, SUPER_ADMIN_GROUP


class Command(BaseCommand):
    help = "Create super admin (full access) and H&PD (dashboard tabs only) users."

    def handle(self, *args, **options):
        user_model = get_user_model()
        super_admin_group, _ = Group.objects.get_or_create(name=SUPER_ADMIN_GROUP)

        superadmin_username = os.getenv("SUPERADMIN_USERNAME", "superadmin")
        superadmin_password = os.getenv("SUPERADMIN_PASSWORD", "")
        viewer_username = os.getenv("DASHBOARD_VIEWER_USERNAME", DASHBOARD_VIEWER_USERNAME)
        viewer_password = os.getenv("DASHBOARD_VIEWER_PASSWORD", "")

        if os.getenv("RAILWAY_ENVIRONMENT") and (not superadmin_password or not viewer_password):
            self.stdout.write(self.style.WARNING(
                "SUPERADMIN_PASSWORD / DASHBOARD_VIEWER_PASSWORD not set — using built-in defaults. "
                "Set strong values in Railway Variables for production."
            ))
        if not superadmin_password:
            superadmin_password = "SuperAdmin@786"
        if not viewer_password:
            viewer_password = "health@786"

        superadmin, created = user_model.objects.get_or_create(username=superadmin_username)
        superadmin.is_staff = True
        superadmin.is_superuser = True
        superadmin.set_password(superadmin_password)
        superadmin.save()
        superadmin.groups.add(super_admin_group)
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Updated'} {superadmin_username} (full access)"
        ))

        hp_user, created = user_model.objects.get_or_create(username=viewer_username)
        hp_user.is_staff = False
        hp_user.is_superuser = False
        hp_user.set_password(viewer_password)
        hp_user.save()
        hp_user.groups.clear()
        self.stdout.write(self.style.SUCCESS(
            f"{'Created' if created else 'Updated'} {viewer_username} (dashboard tabs only)"
        ))

        usernames = list(user_model.objects.order_by("username").values_list("username", flat=True))
        self.stdout.write(f"Dashboard login accounts: {', '.join(usernames)}")
