/**
 * Reports page: server-side DataTable with export links respecting filters.
 */
let reportTable = null;

function updateExportLinks() {
  const params = HAD.getFilterParams();
  const qs = params.toString();
  document.getElementById("exportCsv").href = `/api/export/csv/?${qs}`;
  document.getElementById("exportExcel").href = `/api/export/excel/?${qs}`;
  document.getElementById("exportPdf").href = `/api/export/pdf/?${qs}`;
}

const REPORT_COLUMNS = [
  { data: "districtname", title: "District" },
  { data: "date", title: "Date" },
  { data: "anc_df_total_anc", title: "Total ANC" },
  { data: "anc_df_diabetes_count", title: "Diabetes" },
  { data: "mi_patient_minimum_protected", title: "Min Protected" },
  { data: "mi_patient_fully_immunized_mother", title: "Fully Immunized Mothers" },
  { data: "child_patient_children_under_5", title: "Children U5" },
  { data: "child_patient_sam", title: "SAM" },
  { data: "child_patient_mam", title: "MAM" },
  { data: "ci_patient_fully_immunized", title: "Fully Immunized Children" },
  { data: "ci_patient_due", title: "Due" },
  { data: "ci_patient_defaulter", title: "Defaulters" },
  { data: "pnc_patient_has_pnc", title: "PNC Visits" },
  { data: "fp_patient_has_fp_counsel", title: "FP Counseling" },
  { data: "fp_patient_commodity_received", title: "FP Commodity" },
];

function initReportTable() {
  if (reportTable) reportTable.destroy();

  reportTable = $("#reportTable").DataTable({
    processing: true,
    serverSide: true,
    columns: REPORT_COLUMNS,
    ajax: {
      url: "/api/reports/",
      data(d) {
        const filters = HAD.getFilterParams();
        return {
          draw: d.draw,
          preset: filters.get("preset"),
          start_date: filters.get("start_date") || "",
          end_date: filters.get("end_date") || "",
          district: filters.get("district") || "",
          page: Math.floor(d.start / d.length) + 1,
          page_size: d.length,
          search: d.search.value,
          sort: REPORT_COLUMNS[d.order[0]?.column]?.data || "date",
          dir: d.order[0]?.dir || "desc",
        };
      },
    },
    pageLength: 25,
    order: [[1, "desc"]],
  });
}

function refreshReports() {
  updateExportLinks();
  if (reportTable) reportTable.ajax.reload();
  else initReportTable();
}

document.addEventListener("DOMContentLoaded", () => {
  HAD.initFilters(refreshReports);
  updateExportLinks();
  initReportTable();
  document.getElementById("printReport")?.addEventListener("click", () => window.print());
});
