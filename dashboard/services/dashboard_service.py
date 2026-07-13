"""
Main dashboard KPIs and overview aggregations.
"""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum

from dashboard.services.analytics_service import AnalyticsService
from dashboard.services.filter_service import DashboardFilterService


def _sum_field(qs, field: str) -> int:
    result = qs.aggregate(total=Sum(field))["total"]
    return int(result or 0)


def _pct_change(current: float, previous: float) -> dict[str, Any]:
    if previous == 0:
        change = 100.0 if current > 0 else 0.0
    else:
        change = round((current - previous) / previous * 100, 2)
    direction = "up" if change > 0 else "down" if change < 0 else "flat"
    return {"value": change, "direction": direction}


def _kpi_card(current: int, previous: int, icon: str, label: str) -> dict[str, Any]:
    return {
        "label": label,
        "value": current,
        "previous_value": previous,
        "change_pct": _pct_change(current, previous),
        "icon": icon,
    }


class DashboardService:
    """Overview KPI cards and summary metrics."""

    KPI_DEFINITIONS = [
        ("total_anc", "anc_df_total_anc", "bi-heart-pulse", "Total ANC"),
        ("total_mothers", "anc_df_unique_mothers", "bi-people", "Total Mothers Registered"),
        ("diabetes_cases", "anc_df_diabetes_count", "bi-droplet", "Diabetes Cases"),
        ("minimum_protected", "mi_patient_minimum_protected", "bi-shield-check", "Minimum Protected Mothers"),
        ("fully_immunized_mothers", "mi_patient_fully_immunized_mother", "bi-shield-fill-check", "Fully Immunized Mothers"),
        ("children_under_five", "child_patient_children_under_5", "bi-emoji-smile", "Children Under Five"),
        ("sam_cases", "child_patient_sam", "bi-exclamation-triangle", "SAM Cases"),
        ("mam_cases", "child_patient_mam", "bi-exclamation-circle", "MAM Cases"),
        ("fully_immunized_children", "ci_patient_fully_immunized", "bi-shield-plus", "Fully Immunized Children"),
        ("due_children", "ci_patient_due", "bi-clock-history", "Due Children"),
        ("defaulters", "ci_patient_defaulter", "bi-x-circle", "Defaulters"),
        ("pnc_visits", "pnc_patient_has_pnc", "bi-hospital", "PNC Visits"),
        ("early_breastfeeding", "pnc_patient_early_breastfeeding_initiation", "bi-heart", "Early Breastfeeding"),
        ("fp_counseling", "fp_patient_has_fp_counsel", "bi-chat-dots", "Family Planning Counseling"),
        ("fp_commodity", "fp_patient_commodity_received", "bi-box-seam", "FP Commodity Distribution"),
    ]

    def __init__(self, params: dict[str, Any] | None = None):
        self.filters = DashboardFilterService(params)
        self.cache_ttl = getattr(settings, "DASHBOARD_CACHE_TTL", 300)

    def get_kpis(self) -> list[dict[str, Any]]:
        cache_key = self.filters.cache_key("kpis")
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        qs = self.filters.base_queryset()
        prev_qs = self.filters.previous_queryset()

        fields = [field for _, field, _, _ in self.KPI_DEFINITIONS]
        current_agg = qs.aggregate(**{f"c_{f}": Sum(f) for f in fields})
        previous_agg = prev_qs.aggregate(**{f"p_{f}": Sum(f) for f in fields})

        cards = []
        for key, field, icon, label in self.KPI_DEFINITIONS:
            current = int(current_agg[f"c_{field}"] or 0)
            previous = int(previous_agg[f"p_{field}"] or 0)
            card = _kpi_card(current, previous, icon, label)
            card["key"] = key
            cards.append(card)

        cache.set(cache_key, cards, self.cache_ttl)
        return cards

    def get_overview(self) -> dict[str, Any]:
        cache_key = self.filters.cache_key("overview_v2")
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        payload = {
            "filters": self.filters.filter_payload(),
            "filter_options": DashboardFilterService.filter_metadata(),
            "kpis": self.get_kpis(),
            "charts": AnalyticsService(self.filters.params).overview_dashboard()["charts"],
        }
        cache.set(cache_key, payload, self.cache_ttl)
        return payload
