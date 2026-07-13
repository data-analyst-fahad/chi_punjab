"""
Page views and REST API endpoints.
Business logic lives in services — views only parse requests and return responses.
"""
from __future__ import annotations

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from dashboard.decorators import super_admin_required
from dashboard.services.analytics_service import AnalyticsService
from dashboard.services.dashboard_service import DashboardService
from dashboard.services.filter_service import DashboardFilterService
from dashboard.services.report_service import ReportService


def _params(request) -> dict:
    return request.GET.dict()


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = AuthenticationForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect("dashboard")
    return render(request, "dashboard/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    return redirect("login")


@login_required
def dashboard_view(request):
    return render(
        request,
        "dashboard/dashboard.html",
        {
            "filter_options": DashboardFilterService.filter_metadata(),
            "active_nav": "dashboard",
        },
    )


@login_required
@super_admin_required
def reports_view(request):
    return render(
        request,
        "dashboard/reports.html",
        {
            "filter_options": DashboardFilterService.filter_metadata(),
            "active_nav": "reports",
        },
    )


@login_required
@super_admin_required
def settings_view(request):
    return render(
        request,
        "dashboard/settings.html",
        {"active_nav": "settings"},
    )


@login_required
@require_GET
def api_dashboard(request):
    return JsonResponse(DashboardService(_params(request)).get_overview())


@login_required
@require_GET
def api_anc(request):
    return JsonResponse(AnalyticsService(_params(request)).anc_dashboard())


@login_required
@require_GET
def api_immunization(request):
    return JsonResponse(AnalyticsService(_params(request)).immunization_dashboard())


@login_required
@require_GET
def api_nutrition(request):
    return JsonResponse(AnalyticsService(_params(request)).nutrition_dashboard())


@login_required
@require_GET
def api_child_immunization(request):
    return JsonResponse(AnalyticsService(_params(request)).child_immunization_dashboard())


@login_required
@require_GET
def api_pnc(request):
    return JsonResponse(AnalyticsService(_params(request)).pnc_dashboard())


@login_required
@require_GET
def api_family_planning(request):
    return JsonResponse(AnalyticsService(_params(request)).family_planning_dashboard())


@login_required
@require_GET
def api_bundle(request):
    """Chart sections in one call — KPIs loaded separately for faster first paint."""
    return JsonResponse({"charts": AnalyticsService(_params(request)).get_bundle()})


@login_required
@require_GET
def api_geographic(request):
    return JsonResponse(AnalyticsService(_params(request)).geographic_dashboard())


@login_required
@super_admin_required
@require_GET
def api_reports(request):
    data = ReportService(_params(request)).paginated_rows()
    # DataTables server-side format
    if request.GET.get("draw"):
        return JsonResponse({
            "draw": int(request.GET.get("draw", 1)),
            "recordsTotal": data["total"],
            "recordsFiltered": data["total"],
            "data": data["rows"],
            **data,
        })
    return JsonResponse(data)


@login_required
@super_admin_required
@require_GET
def export_csv(request):
    return ReportService(_params(request)).export_csv()


@login_required
@super_admin_required
@require_GET
def export_excel(request):
    return ReportService(_params(request)).export_excel()


@login_required
@super_admin_required
@require_GET
def export_pdf(request):
    return ReportService(_params(request)).export_pdf()
