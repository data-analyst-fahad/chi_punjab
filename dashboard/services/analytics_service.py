"""
Program-specific analytics: ANC, immunization, nutrition, PNC, FP, geographic.
All aggregations use SQL SUM/GROUP BY via Django ORM — no full-table loads.
"""
from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum
from django.db.models.functions import TruncMonth

from dashboard.services.filter_service import DashboardFilterService


def _district_series(qs, field: str, limit: int = 20) -> dict[str, list]:
    rows = (
        qs.values("districtname")
        .annotate(value=Sum(field))
        .order_by("-value")[:limit]
    )
    return {
        "labels": [r["districtname"] or "Unknown" for r in rows],
        "values": [int(r["value"] or 0) for r in rows],
    }


def _monthly_series(qs, field: str) -> dict[str, list]:
    rows = (
        qs.annotate(month=TruncMonth("date"))
        .values("month")
        .annotate(value=Sum(field))
        .order_by("month")
    )
    return {
        "labels": [r["month"].strftime("%Y-%m") if r["month"] else "" for r in rows],
        "values": [int(r["value"] or 0) for r in rows],
    }


def _district_monthly_series(qs, field: str, district_limit: int = 10) -> dict[str, Any]:
    """Monthly trend with one series per top district."""
    top_districts = [
        r["districtname"] or "Unknown"
        for r in (
            qs.values("districtname")
            .annotate(total=Sum(field))
            .order_by("-total")[:district_limit]
        )
    ]
    if not top_districts:
        return {"labels": [], "series": {}}

    rows = (
        qs.filter(districtname__in=top_districts)
        .annotate(month=TruncMonth("date"))
        .values("month", "districtname")
        .annotate(value=Sum(field))
        .order_by("month", "districtname")
    )

    months = sorted({r["month"] for r in rows if r["month"]})
    labels = [m.strftime("%Y-%m") for m in months]
    lookup = {
        (r["month"], r["districtname"] or "Unknown"): int(r["value"] or 0)
        for r in rows
    }
    series = {
        district: [lookup.get((month, district), 0) for month in months]
        for district in top_districts
    }
    return {"labels": labels, "series": series}


class AnalyticsService:
    """Section dashboards and chart payloads for Plotly.js."""

    def __init__(self, params: dict[str, Any] | None = None):
        self.filters = DashboardFilterService(params)
        self.cache_ttl = getattr(settings, "DASHBOARD_CACHE_TTL", 300)
        self._totals: dict[str, int] | None = None

    def _qs(self):
        return self.filters.base_queryset()

    def _field_totals(self) -> dict[str, int]:
        """Single-query SUM for all numeric columns."""
        if self._totals is not None:
            return self._totals
        fields = DashboardFilterService.SUM_FIELDS
        agg = self._qs().aggregate(**{f"s_{f}": Sum(f) for f in fields})
        self._totals = {f: int(agg[f"s_{f}"] or 0) for f in fields}
        return self._totals

    def _sum(self, field: str) -> int:
        return self._field_totals().get(field, 0)

    def _cached(self, key: str, builder):
        cache_key = self.filters.cache_key(key)
        cached = cache.get(cache_key)
        if cached is not None:
            return cached
        data = builder()
        cache.set(cache_key, data, self.cache_ttl)
        return data

    def anc_dashboard(self) -> dict[str, Any]:
        def build():
            t = self._field_totals()
            qs = self._qs()
            return {
                "kpis": {
                    "total_anc": t["anc_df_total_anc"],
                    "diabetes": t["anc_df_diabetes_count"],
                    "mothers_registered": t["anc_df_unique_mothers"],
                },
                "charts": {
                    "trimester_distribution": {
                        "labels": ["1st Trimester", "2nd Trimester", "3rd Trimester"],
                        "values": [
                            t["anc_df_trimester_1st_trimester"],
                            t["anc_df_trimester_2nd_trimester"],
                            t["anc_df_trimester_3rd_trimester"],
                        ],
                        "type": "pie",
                    },
                    "bmi_distribution": {
                        "labels": ["Normal", "Obese", "Overweight", "Underweight"],
                        "values": [
                            t["anc_df_bmi_normal"],
                            t["anc_df_bmi_obese"],
                            t["anc_df_bmi_overweight"],
                            t["anc_df_bmi_underweight"],
                        ],
                        "type": "donut",
                    },
                    "hypertension_distribution": {
                        "labels": ["Normal", "Hypertension", "Severe"],
                        "values": [
                            t["anc_df_htn_normal"],
                            t["anc_df_htn_hypertension"],
                            t["anc_df_htn_severe_hypertension"],
                        ],
                        "type": "bar",
                    },
                    "diabetes_trend": {
                        **_district_monthly_series(qs, "anc_df_diabetes_count"),
                        "type": "multi_line",
                    },
                    "district_anc": {**_district_series(qs, "anc_df_total_anc"), "type": "bar_h"},
                },
            }

        return self._cached("anc_v3", build)

    def immunization_dashboard(self) -> dict[str, Any]:
        def build():
            t = self._field_totals()
            qs = self._qs()
            return {
                "kpis": {
                    "minimum_protected": t["mi_patient_minimum_protected"],
                    "fully_immunized": t["mi_patient_fully_immunized_mother"],
                },
                "charts": {
                    "minimum_protected_by_district": _district_series(qs, "mi_patient_minimum_protected"),
                    "fully_immunized_by_district": _district_series(qs, "mi_patient_fully_immunized_mother"),
                    "monthly_trend": _monthly_series(qs, "mi_patient_fully_immunized_mother"),
                },
            }

        return self._cached("immunization", build)

    def nutrition_dashboard(self) -> dict[str, Any]:
        def build():
            t = self._field_totals()
            qs = self._qs()
            monthly = (
                qs.annotate(month=TruncMonth("date"))
                .values("month")
                .annotate(
                    sam=Sum("child_patient_sam"),
                    mam=Sum("child_patient_mam"),
                )
                .order_by("month")
            )
            return {
                "kpis": {
                    "children_under_five": t["child_patient_children_under_5"],
                    "sam": t["child_patient_sam"],
                    "mam": t["child_patient_mam"],
                },
                "charts": {
                    "sam_by_district": _district_series(qs, "child_patient_sam"),
                    "mam_by_district": _district_series(qs, "child_patient_mam"),
                    "nutrition_trend": {
                        "labels": [r["month"].strftime("%Y-%m") if r["month"] else "" for r in monthly],
                        "sam": [int(r["sam"] or 0) for r in monthly],
                        "mam": [int(r["mam"] or 0) for r in monthly],
                    },
                },
            }

        return self._cached("nutrition", build)

    def child_immunization_dashboard(self) -> dict[str, Any]:
        def build():
            t = self._field_totals()
            qs = self._qs()
            return {
                "kpis": {
                    "fully_immunized": t["ci_patient_fully_immunized"],
                    "due": t["ci_patient_due"],
                    "defaulters": t["ci_patient_defaulter"],
                },
                "charts": {
                    "coverage_by_district": _district_series(qs, "ci_patient_fully_immunized"),
                    "defaulter_trend": _monthly_series(qs, "ci_patient_defaulter"),
                    "coverage_trend": _monthly_series(qs, "ci_patient_fully_immunized"),
                },
            }

        return self._cached("ci", build)

    def pnc_dashboard(self) -> dict[str, Any]:
        def build():
            t = self._field_totals()
            qs = self._qs()
            return {
                "kpis": {
                    "total_pnc": t["pnc_patient_has_pnc"],
                    "early_breastfeeding": t["pnc_patient_early_breastfeeding_initiation"],
                    "counseling": t["pnc_patient_breastfeeding_counseling"],
                    "hypertension": t["pnc_patient_hypertension"],
                },
                "charts": {
                    "early_breastfeeding_by_district": _district_series(
                        qs, "pnc_patient_early_breastfeeding_initiation"
                    ),
                    "counseling_by_district": _district_series(
                        qs, "pnc_patient_breastfeeding_counseling"
                    ),
                    "monthly_trend": _monthly_series(qs, "pnc_patient_has_pnc"),
                },
            }

        return self._cached("pnc", build)

    def family_planning_dashboard(self) -> dict[str, Any]:
        def build():
            t = self._field_totals()
            qs = self._qs()
            return {
                "kpis": {
                    "counseling": t["fp_patient_has_fp_counsel"],
                    "commodity_distribution": t["fp_patient_commodity_received"],
                },
                "charts": {
                    "method_mix": {
                        "labels": [
                            "Condom", "IUD", "Implant", "Injectable",
                            "Oral Pills", "Other", "None",
                        ],
                        "values": [
                            t["fp_patient_method_condom"],
                            t["fp_patient_method_iud"],
                            t["fp_patient_method_implant"],
                            t["fp_patient_method_injectable"],
                            t["fp_patient_method_oral_pills"],
                            t["fp_patient_method_other_unknown"],
                            t["fp_patient_method_none"],
                        ],
                        "type": "pie",
                    },
                    "commodity_by_district": _district_series(qs, "fp_patient_commodity_received"),
                },
            }

        return self._cached("fp", build)

    def geographic_dashboard(self) -> dict[str, Any]:
        def build():
            qs = self._qs()
            district_rows = (
                qs.values("districtname")
                .annotate(
                    total_anc=Sum("anc_df_total_anc"),
                    fully_immunized_children=Sum("ci_patient_fully_immunized"),
                    sam_cases=Sum("child_patient_sam"),
                    pnc_visits=Sum("pnc_patient_has_pnc"),
                    fp_counseling=Sum("fp_patient_has_fp_counsel"),
                    mi_fully_immunized=Sum("mi_patient_fully_immunized_mother"),
                )
                .order_by("-total_anc")
            )

            rows = []
            for r in district_rows:
                district = r["districtname"] or "Unknown"
                score = round(
                    (int(r["total_anc"] or 0) * 0.2)
                    + (int(r["mi_fully_immunized"] or 0) * 0.15)
                    + (int(r["fully_immunized_children"] or 0) * 0.2)
                    - (int(r["sam_cases"] or 0) * 0.15)
                    + (int(r["pnc_visits"] or 0) * 0.15)
                    + (int(r["fp_counseling"] or 0) * 0.15),
                    2,
                )
                rows.append({
                    "district": district,
                    "score": score,
                    "total_anc": int(r["total_anc"] or 0),
                    "fully_immunized_children": int(r["fully_immunized_children"] or 0),
                    "sam_cases": int(r["sam_cases"] or 0),
                    "pnc_visits": int(r["pnc_visits"] or 0),
                    "fp_counseling": int(r["fp_counseling"] or 0),
                })

            rows.sort(key=lambda x: x["score"], reverse=True)
            top = rows[:5]
            bottom = list(reversed(rows[-5:])) if len(rows) >= 5 else list(reversed(rows))

            return {
                "ranking_table": rows,
                "top_performing": top,
                "lowest_performing": bottom,
                "district_comparison": {
                    "labels": [r["district"] for r in rows[:15]],
                    "anc": [r["total_anc"] for r in rows[:15]],
                    "immunized": [r["fully_immunized_children"] for r in rows[:15]],
                },
            }

        return self._cached("geo", build)

    def overview_dashboard(self) -> dict[str, Any]:
        def build():
            qs = self._qs()
            return {
                "charts": {
                    "mothers_by_district": _district_series(qs, "anc_df_unique_mothers", limit=40),
                    "anc_by_district": _district_series(qs, "anc_df_total_anc", limit=40),
                    "children_under_five_by_district": _district_series(
                        qs, "child_patient_children_under_5", limit=40
                    ),
                    "pnc_records_by_district": _district_series(qs, "pnc_patient_total_records", limit=40),
                    "fp_counsel_by_district": _district_series(qs, "fp_patient_has_fp_counsel", limit=40),
                    "fp_commodity_by_district": _district_series(
                        qs, "fp_patient_commodity_received", limit=40
                    ),
                },
            }

        return self._cached("overview", build)

    def get_bundle(self) -> dict[str, Any]:
        """All section data in one pass — shared field_totals, minimal DB round-trips."""
        cache_key = self.filters.cache_key("bundle_v2")
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        payload = {
            "overview": self.overview_dashboard(),
            "anc": self.anc_dashboard(),
            "immunization": self.immunization_dashboard(),
            "nutrition": self.nutrition_dashboard(),
            "child_immunization": self.child_immunization_dashboard(),
            "pnc": self.pnc_dashboard(),
            "family_planning": self.family_planning_dashboard(),
        }
        cache.set(cache_key, payload, self.cache_ttl)
        return payload
