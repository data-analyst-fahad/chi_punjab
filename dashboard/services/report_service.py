"""
Paginated reports and export (CSV, Excel, PDF).
"""
from __future__ import annotations

import csv
import io
from typing import Any

from django.http import HttpResponse
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from dashboard.models import FactDailyHealthSummary
from dashboard.services.filter_service import DashboardFilterService

REPORT_COLUMNS = [
    ("districtname", "District"),
    ("date", "Date"),
    ("anc_df_total_anc", "Total ANC"),
    ("anc_df_diabetes_count", "Diabetes"),
    ("mi_patient_minimum_protected", "Min Protected"),
    ("mi_patient_fully_immunized_mother", "Fully Immunized Mothers"),
    ("child_patient_children_under_5", "Children U5"),
    ("child_patient_sam", "SAM"),
    ("child_patient_mam", "MAM"),
    ("ci_patient_fully_immunized", "Fully Immunized Children"),
    ("ci_patient_due", "Due"),
    ("ci_patient_defaulter", "Defaulters"),
    ("pnc_patient_has_pnc", "PNC Visits"),
    ("fp_patient_has_fp_counsel", "FP Counseling"),
    ("fp_patient_commodity_received", "FP Commodity"),
]


class ReportService:
    """Server-side report queries with search, sort, pagination."""

    def __init__(self, params: dict[str, Any] | None = None):
        self.params = params or {}
        self.filters = DashboardFilterService(self.params)
        self.page = max(int(self.params.get("page", 1)), 1)
        self.page_size = min(max(int(self.params.get("page_size", 25)), 1), 500)
        self.search = (self.params.get("search") or "").strip()
        self.sort_field = self.params.get("sort") or "date"
        self.sort_dir = self.params.get("dir") or "desc"

    def _queryset(self):
        qs = self.filters.base_queryset()
        if self.search:
            qs = qs.filter(districtname__icontains=self.search)
        allowed = {c[0] for c in REPORT_COLUMNS}
        sort_field = self.sort_field if self.sort_field in allowed else "date"
        prefix = "-" if self.sort_dir == "desc" else ""
        return qs.order_by(f"{prefix}{sort_field}", "districtname")

    def paginated_rows(self) -> dict[str, Any]:
        qs = self._queryset()
        total = qs.count()
        start = (self.page - 1) * self.page_size
        end = start + self.page_size
        rows = list(qs.values(*[c[0] for c in REPORT_COLUMNS])[start:end])

        for row in rows:
            if row.get("date"):
                row["date"] = row["date"].isoformat()

        return {
            "rows": rows,
            "total": total,
            "page": self.page,
            "page_size": self.page_size,
            "total_pages": max(1, (total + self.page_size - 1) // self.page_size),
            "columns": [{"field": f, "label": l} for f, l in REPORT_COLUMNS],
            "filters": self.filters.filter_payload(),
        }

    def all_rows(self) -> list[dict[str, Any]]:
        qs = self._queryset()
        rows = list(qs.values(*[c[0] for c in REPORT_COLUMNS]))
        for row in rows:
            if row.get("date"):
                row["date"] = row["date"].isoformat()
        return rows

    def export_csv(self) -> HttpResponse:
        rows = self.all_rows()
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="health_summary_report.csv"'
        writer = csv.writer(response)
        writer.writerow([label for _, label in REPORT_COLUMNS])
        for row in rows:
            writer.writerow([row.get(field, "") for field, _ in REPORT_COLUMNS])
        return response

    def export_excel(self) -> HttpResponse:
        rows = self.all_rows()
        wb = Workbook()
        ws = wb.active
        ws.title = "Health Summary"
        ws.append([label for _, label in REPORT_COLUMNS])
        for row in rows:
            ws.append([row.get(field, "") for field, _ in REPORT_COLUMNS])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        response["Content-Disposition"] = 'attachment; filename="health_summary_report.xlsx"'
        return response

    def export_pdf(self) -> HttpResponse:
        rows = self.all_rows()[:500]
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
        styles = getSampleStyleSheet()
        elements = [
            Paragraph("Community Health Inspector Analytics Report", styles["Title"]),
            Spacer(1, 12),
        ]

        table_data = [[label for _, label in REPORT_COLUMNS]]
        for row in rows:
            table_data.append([str(row.get(field, "")) for field, _ in REPORT_COLUMNS])

        table = Table(table_data, repeatRows=1)
        table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ])
        )
        elements.append(table)
        doc.build(elements)
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = 'attachment; filename="health_summary_report.pdf"'
        return response
