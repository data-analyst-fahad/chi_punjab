"""
Global date and district filter parsing for dashboard queries.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from django.db.models import Q, QuerySet, Max, Min
from django.utils import timezone

from dashboard.models import FactDailyHealthSummary


DATE_PRESETS = {
    "all_time": "All Time",
    "today": "Today",
    "yesterday": "Yesterday",
    "last_7_days": "Last 7 Days",
    "last_30_days": "Last 30 Days",
    "this_month": "This Month",
    "last_month": "Last Month",
    "custom": "Custom Date Range",
}


@dataclass(frozen=True)
class DateRange:
    start: date
    end: date
    preset: str

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1

    def previous(self) -> DateRange:
        span = self.days
        prev_end = self.start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=span - 1)
        return DateRange(prev_start, prev_end, self.preset)


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _month_end(d: date) -> date:
    if d.month == 12:
        return date(d.year, 12, 31)
    return date(d.year, d.month + 1, 1) - timedelta(days=1)


def resolve_date_range(params: dict[str, Any]) -> DateRange:
    """Resolve start/end dates from query parameters."""
    preset = (params.get("preset") or params.get("date_preset") or "all_time").strip()
    today = timezone.localdate()

    if preset == "all_time":
        bounds = FactDailyHealthSummary.objects.aggregate(
            min_date=Min("date"), max_date=Max("date")
        )
        start = bounds["min_date"] or today
        end = bounds["max_date"] or today
        return DateRange(start, end, preset)

    if preset == "today":
        return DateRange(today, today, preset)
    if preset == "yesterday":
        y = today - timedelta(days=1)
        return DateRange(y, y, preset)
    if preset == "last_7_days":
        return DateRange(today - timedelta(days=6), today, preset)
    if preset == "last_30_days":
        return DateRange(today - timedelta(days=29), today, preset)
    if preset == "this_month":
        return DateRange(_month_start(today), today, preset)
    if preset == "last_month":
        first_this = _month_start(today)
        last_prev = first_this - timedelta(days=1)
        return DateRange(_month_start(last_prev), last_prev, preset)

    start_raw = params.get("start_date") or params.get("start")
    end_raw = params.get("end_date") or params.get("end")
    if start_raw and end_raw:
        start = datetime.strptime(str(start_raw)[:10], "%Y-%m-%d").date()
        end = datetime.strptime(str(end_raw)[:10], "%Y-%m-%d").date()
        if start > end:
            start, end = end, start
        return DateRange(start, end, "custom")

    return DateRange(today - timedelta(days=29), today, "last_30_days")


class DashboardFilterService:
    """Apply global filters to FactDailyHealthSummary queryset."""

    SUM_FIELDS = [
        "anc_df_total_records",
        "anc_df_unique_mothers",
        "anc_df_total_anc",
        "anc_df_diabetes_count",
        "anc_df_trimester_1st_trimester",
        "anc_df_trimester_2nd_trimester",
        "anc_df_trimester_3rd_trimester",
        "anc_df_bmi_normal",
        "anc_df_bmi_obese",
        "anc_df_bmi_overweight",
        "anc_df_bmi_underweight",
        "anc_df_bmi_nan",
        "anc_df_htn_elevated_unknown",
        "anc_df_htn_hypertension",
        "anc_df_htn_normal",
        "anc_df_htn_severe_hypertension",
        "mi_patient_total_records",
        "mi_patient_has_mi",
        "mi_patient_minimum_protected",
        "mi_patient_fully_immunized_mother",
        "child_patient_total_records",
        "child_patient_has_cn",
        "child_patient_children_under_5",
        "child_patient_sam",
        "child_patient_mam",
        "ci_patient_total_records",
        "ci_patient_has_ci",
        "ci_patient_fully_immunized",
        "ci_patient_due",
        "ci_patient_defaulter",
        "pnc_patient_total_records",
        "pnc_patient_has_pnc",
        "pnc_patient_early_breastfeeding_initiation",
        "pnc_patient_breastfeeding_counseling",
        "pnc_patient_hypertension",
        "fp_patient_total_records",
        "fp_patient_has_fp_counsel",
        "fp_patient_commodity_received",
        "fp_patient_method_condom",
        "fp_patient_method_iud",
        "fp_patient_method_implant",
        "fp_patient_method_injectable",
        "fp_patient_method_none",
        "fp_patient_method_oral_pills",
        "fp_patient_method_other_unknown",
    ]

    def __init__(self, params: dict[str, Any] | None = None):
        self.params = params or {}
        self.date_range = resolve_date_range(self.params)
        self.district = (self.params.get("district") or "").strip()

    def cache_key(self, prefix: str) -> str:
        raw = f"{prefix}|{self.date_range.start}|{self.date_range.end}|{self.district}|{self.date_range.preset}"
        return f"had:{prefix}:{hashlib.md5(raw.encode()).hexdigest()[:16]}"

    def base_queryset(self) -> QuerySet:
        qs = FactDailyHealthSummary.objects.filter(
            date__gte=self.date_range.start,
            date__lte=self.date_range.end,
        )
        if self.district:
            qs = qs.filter(districtname__iexact=self.district)
        return qs

    def previous_queryset(self) -> QuerySet:
        prev = self.date_range.previous()
        qs = FactDailyHealthSummary.objects.filter(
            date__gte=prev.start,
            date__lte=prev.end,
        )
        if self.district:
            qs = qs.filter(districtname__iexact=self.district)
        return qs

    @classmethod
    def district_options(cls) -> list[str]:
        return list(
            FactDailyHealthSummary.objects.exclude(
                Q(districtname__isnull=True) | Q(districtname="")
            )
            .values_list("districtname", flat=True)
            .distinct()
            .order_by("districtname")
        )

    @classmethod
    def filter_metadata(cls) -> dict[str, Any]:
        return {
            "presets": [{"value": k, "label": v} for k, v in DATE_PRESETS.items()],
            "districts": cls.district_options(),
        }

    def filter_payload(self) -> dict[str, Any]:
        return {
            "preset": self.date_range.preset,
            "start_date": self.date_range.start.isoformat(),
            "end_date": self.date_range.end.isoformat(),
            "district": self.district,
        }
