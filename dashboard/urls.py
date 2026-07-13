from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard_view, name="dashboard"),
    path("reports/", views.reports_view, name="reports"),
    path("settings/", views.settings_view, name="settings"),
    path("api/dashboard/", views.api_dashboard, name="api_dashboard"),
    path("api/bundle/", views.api_bundle, name="api_bundle"),
    path("api/anc/", views.api_anc, name="api_anc"),
    path("api/immunization/", views.api_immunization, name="api_immunization"),
    path("api/child-immunization/", views.api_child_immunization, name="api_child_immunization"),
    path("api/nutrition/", views.api_nutrition, name="api_nutrition"),
    path("api/pnc/", views.api_pnc, name="api_pnc"),
    path("api/family-planning/", views.api_family_planning, name="api_family_planning"),
    path("api/geographic/", views.api_geographic, name="api_geographic"),
    path("api/reports/", views.api_reports, name="api_reports"),
    path("api/export/csv/", views.export_csv, name="export_csv"),
    path("api/export/excel/", views.export_excel, name="export_excel"),
    path("api/export/pdf/", views.export_pdf, name="export_pdf"),
]
