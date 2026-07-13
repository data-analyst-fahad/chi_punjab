/**
 * Main dashboard — KPIs load first, charts follow, geographic loads on tab click.
 */
let geoLoaded = false;
let currentParams = null;

const OVERVIEW_CHARTS = [
  ["chartOverviewMothers", "mothers_by_district", "District Wise Total Mothers Registered"],
  ["chartOverviewAnc", "anc_by_district", "District Wise Total ANC"],
  ["chartOverviewChildren", "children_under_five_by_district", "District Wise Total Children Under Five Registered"],
  ["chartOverviewPnc", "pnc_records_by_district", "District Wise Total PNC Records"],
  ["chartOverviewFpCounsel", "fp_counsel_by_district", "District Wise Total Family Planning Counseling"],
  ["chartOverviewFpCommodity", "fp_commodity_by_district", "District Wise Total FP Commodity Received"],
];

async function renderOverviewCharts(charts) {
  if (!charts) return;

  await Promise.allSettled(
    OVERVIEW_CHARTS.map(([id, key, title]) => {
      const data = charts[key] || { labels: [], values: [] };
      return HAD.plotBar(id, data.labels, data.values, title, true);
    }),
  );

  requestAnimationFrame(() => {
    HAD.resizeChartsIn(document.getElementById("tabOverview"));
    setTimeout(() => HAD.resizeChartsIn(document.getElementById("tabOverview")), 150);
  });
}

async function renderSectionCharts(charts) {
  const anc = charts.anc;
  const mi = charts.immunization;
  const cn = charts.nutrition;
  const ci = charts.child_immunization;
  const pnc = charts.pnc;
  const fp = charts.family_planning;
  const ac = anc.charts;

  const diabetesSeries = ac.diabetes_trend?.series || { Total: ac.diabetes_trend?.values || [] };
  const diabetesLabels = ac.diabetes_trend?.labels || [];

  await Promise.allSettled([
    HAD.plotPie("chartTrimester", ac.trimester_distribution.labels, ac.trimester_distribution.values, "Trimester Distribution"),
    HAD.plotPie("chartBmi", ac.bmi_distribution.labels, ac.bmi_distribution.values, "BMI Distribution", true),
    HAD.plotBar("chartHtn", ac.hypertension_distribution.labels, ac.hypertension_distribution.values, "Hypertension Distribution"),
    HAD.plotMultiLine("chartDiabetesTrend", diabetesLabels, diabetesSeries, "Diabetes Trend by District"),
    HAD.plotBar("chartAncDistrict", ac.district_anc.labels, ac.district_anc.values, "District-wise ANC", true),
    HAD.plotBar("chartMiMin", mi.charts.minimum_protected_by_district.labels, mi.charts.minimum_protected_by_district.values, "Minimum Protected by District"),
    HAD.plotBar("chartMiFull", mi.charts.fully_immunized_by_district.labels, mi.charts.fully_immunized_by_district.values, "Fully Immunized by District"),
    HAD.plotLine("chartMiTrend", mi.charts.monthly_trend.labels, mi.charts.monthly_trend.values, "Monthly Trend"),
    HAD.plotBar("chartSam", cn.charts.sam_by_district.labels, cn.charts.sam_by_district.values, "SAM by District"),
    HAD.plotBar("chartMam", cn.charts.mam_by_district.labels, cn.charts.mam_by_district.values, "MAM by District"),
    HAD.plotMultiLine("chartNutritionTrend", cn.charts.nutrition_trend.labels,
      { SAM: cn.charts.nutrition_trend.sam, MAM: cn.charts.nutrition_trend.mam }, "Nutrition Trend"),
    HAD.plotBar("chartCiCoverage", ci.charts.coverage_by_district.labels, ci.charts.coverage_by_district.values, "Coverage by District"),
    HAD.plotLine("chartCiDefaulter", ci.charts.defaulter_trend.labels, ci.charts.defaulter_trend.values, "Defaulter Trend"),
    HAD.plotLine("chartCiTrend", ci.charts.coverage_trend.labels, ci.charts.coverage_trend.values, "Coverage Trend"),
    HAD.plotBar("chartPncEbf", pnc.charts.early_breastfeeding_by_district.labels, pnc.charts.early_breastfeeding_by_district.values, "Early Breastfeeding by District"),
    HAD.plotBar("chartPncCounsel", pnc.charts.counseling_by_district.labels, pnc.charts.counseling_by_district.values, "Counseling by District"),
    HAD.plotLine("chartPncTrend", pnc.charts.monthly_trend.labels, pnc.charts.monthly_trend.values, "Monthly PNC Trend"),
    HAD.plotPie("chartFpMix", fp.charts.method_mix.labels, fp.charts.method_mix.values, "Method Mix"),
    HAD.plotBar("chartFpCommodity", fp.charts.commodity_by_district.labels, fp.charts.commodity_by_district.values, "Commodity Distribution by District"),
  ]);

  requestAnimationFrame(() => {
    HAD._observeCharts?.();
    HAD.resizeAllCharts();
    setTimeout(() => HAD.resizeAllCharts(), 100);
    setTimeout(() => HAD.resizeAllCharts(), 400);
  });
}

async function renderGeographic(geo) {
  document.getElementById("topDistricts").innerHTML = geo.top_performing.map(d =>
    `<li class="list-group-item d-flex justify-content-between"><span>${d.district}</span><span class="badge bg-success">${d.score}</span></li>`
  ).join("");
  document.getElementById("bottomDistricts").innerHTML = geo.lowest_performing.map(d =>
    `<li class="list-group-item d-flex justify-content-between"><span>${d.district}</span><span class="badge bg-danger">${d.score}</span></li>`
  ).join("");
  await HAD.plotMultiLine("chartGeoCompare", geo.district_comparison.labels,
    { ANC: geo.district_comparison.anc, Immunized: geo.district_comparison.immunized }, "District Comparison");
  document.querySelector("#geoRankingTable tbody").innerHTML = geo.ranking_table.map((r, i) =>
    `<tr><td>${i + 1}</td><td>${r.district}</td><td>${r.score}</td><td>${r.total_anc}</td><td>${r.fully_immunized_children}</td><td>${r.sam_cases}</td><td>${r.pnc_visits}</td><td>${r.fp_counseling}</td></tr>`
  ).join("");
  HAD.resizeChart("chartGeoCompare");
}

async function loadGeographic(params) {
  if (geoLoaded && params.toString() === currentParams?.toString()) {
    HAD.resizeChart("chartGeoCompare");
    return;
  }
  try {
    const geo = await HAD.fetchJSON("/api/geographic/", params);
    await renderGeographic(geo);
    geoLoaded = true;
  } catch (err) {
    console.error("Geographic load failed:", err);
  }
}

async function refreshDashboard() {
  const params = HAD.getFilterParams();
  currentParams = params;
  geoLoaded = false;
  HAD.chartIds.clear();
  HAD.showSpinner();

  try {
    const overview = await HAD.fetchJSON("/api/dashboard/", params);
    HAD.renderKpis("kpiGrid", overview.kpis);
    HAD.hideSpinner();

    await renderOverviewCharts(overview.charts);

    const bundle = await HAD.fetchJSON("/api/bundle/", params);
    await renderSectionCharts(bundle.charts);
    loadGeographic(params);
  } catch (err) {
    console.error(err);
    HAD.hideSpinner();
    alert("Failed to load dashboard data. Check database connection.");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  HAD.initFilters(refreshDashboard);
  refreshDashboard();

  document.querySelector('[data-bs-target="#tabOverview"]')?.addEventListener("shown.bs.tab", () => {
    HAD.resizeChartsIn(document.getElementById("tabOverview"));
    setTimeout(() => HAD.resizeChartsIn(document.getElementById("tabOverview")), 100);
  });

  document.querySelector('[data-bs-target="#tabGeo"]')?.addEventListener("shown.bs.tab", () => {
    if (currentParams) loadGeographic(currentParams);
  });
});
