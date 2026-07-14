/**
 * Main dashboard — KPIs, overview charts, section charts, geographic map.
 */
let geoLoaded = false;
let currentParams = null;
let overviewChartsCache = null;
let allKpisCache = [];

const OVERVIEW_CHARTS = [
  ["chartOverviewMothers", "mothers_by_district", "District Wise Total Mothers Registered"],
  ["chartOverviewAnc", "anc_by_district", "District Wise Total ANC"],
  ["chartOverviewChildren", "children_under_five_by_district", "District Wise Children Under Five Registered"],
  ["chartOverviewPnc", "pnc_records_by_district", "District Wise Total PNC Records"],
  ["chartOverviewFpCounsel", "fp_counsel_by_district", "District Wise Family Planning Counseling"],
  ["chartOverviewFpCommodity", "fp_commodity_by_district", "District Wise FP Commodity Distribution"],
];

const RANKING_OPTIONS = [
  ["mothers_by_district", "Total Mothers Registered"],
  ["anc_by_district", "Total ANC"],
  ["children_under_five_by_district", "Children Under Five Registered"],
  ["pnc_records_by_district", "Total PNC Records"],
  ["fp_counsel_by_district", "Family Planning Counseling"],
  ["fp_commodity_by_district", "FP Commodity Distribution"],
];

const MODULE_KPI_KEYS = {
  tabAnc: ["total_anc", "total_mothers", "diabetes_cases"],
  tabMi: ["minimum_protected", "fully_immunized_mothers"],
  tabCn: ["children_under_five", "sam_cases", "mam_cases"],
  tabCi: ["fully_immunized_children", "due_children", "defaulters"],
  tabPnc: ["pnc_visits", "early_breastfeeding"],
  tabFp: ["fp_counseling", "fp_commodity"],
};

const PUNJAB_CENTER = [31.1471, 75.3412];
const DISTRICT_COORDS = {
  Lahore: [31.5497, 74.3436],
  Faisalabad: [31.418, 73.079],
  Rawalpindi: [33.5651, 73.0169],
  Multan: [30.1575, 71.5249],
  Gujranwala: [32.1877, 74.1945],
  Sialkot: [32.4945, 74.5229],
  Sargodha: [32.0836, 72.6711],
  Bahawalpur: [29.3956, 71.6833],
  Sheikhupura: [31.7131, 73.9783],
  Jhang: [31.2682, 72.3181],
  Gujrat: [32.5742, 74.0754],
  Kasur: [31.1156, 74.4469],
  Sahiwal: [30.6682, 73.1114],
  Okara: [30.808, 73.4458],
  Mianwali: [32.5839, 71.5269],
  Attock: [33.7667, 72.3598],
  Vehari: [30.0445, 72.361],
  "Rahim Yar Khan": [28.4202, 70.2952],
  Muzaffargarh: [30.1575, 71.199],
  Khanewal: [30.3017, 71.9321],
};

const MEDALS = ["🥇", "🥈", "🥉", "4", "5"];

function ensureModuleKpiStrip(tabId) {
  const pane = document.getElementById(tabId);
  if (!pane || pane.querySelector(".module-kpi-strip")) return;
  const strip = document.createElement("div");
  strip.className = "module-kpi-strip row g-2 mb-3";
  strip.id = `${tabId}Kpis`;
  pane.insertBefore(strip, pane.firstChild);
}

function renderModuleKpis(tabId, keys) {
  ensureModuleKpiStrip(tabId);
  const strip = document.getElementById(`${tabId}Kpis`);
  if (!strip || !allKpisCache.length) return;
  const items = allKpisCache.filter((k) => keys.includes(k.key));
  strip.innerHTML = items.map((k) => {
    const label = HAD.KPI_LABELS[k.key] || k.label;
    const change = k.change_pct || {};
    const changeText = change.available === false || change.value == null
      ? "—"
      : `${change.direction === "up" ? "↑" : change.direction === "down" ? "↓" : "→"} ${change.value}%`;
    return `
      <div class="col-md-4 col-sm-6">
        <div class="module-kpi-mini card h-100">
          <div class="card-body py-2 px-3">
            <div class="small text-muted">${label}</div>
            <div class="fw-bold">${Number(k.value).toLocaleString()}</div>
            <div class="small text-muted">${changeText}</div>
          </div>
        </div>
      </div>`;
  }).join("");
}

function renderRankingCards(containerId, rows, isBottom = false) {
  const container = document.getElementById(containerId);
  if (!container) return;
  if (!rows.length) {
    container.innerHTML = `<div class="text-muted small py-3">No Data Available</div>`;
    return;
  }
  container.innerHTML = rows.map((row, i) => {
    const medal = isBottom ? `${i + 1}` : MEDALS[i] || `${i + 1}`;
    return `
      <div class="ranking-card ${isBottom ? "ranking-card-bottom" : ""} fade-in-up" style="animation-delay:${i * 0.05}s">
        <span class="ranking-medal">${medal}</span>
        <div class="flex-grow-1">
          <div class="fw-semibold">${row.district}</div>
          <div class="small text-muted">${Number(row.value).toLocaleString()} records</div>
        </div>
      </div>`;
  }).join("");
}

function initRankingSelector(charts) {
  overviewChartsCache = charts;
  const select = document.getElementById("rankingIndicator");
  if (!select) return;
  if (!select.dataset.initialized) {
    RANKING_OPTIONS.forEach(([key, label]) => {
      const opt = document.createElement("option");
      opt.value = key;
      opt.textContent = label;
      select.appendChild(opt);
    });
    select.addEventListener("change", () => updateOverviewRankings(select.value));
    select.dataset.initialized = "1";
  }
  updateOverviewRankings(select.value || RANKING_OPTIONS[0][0]);
}

function updateOverviewRankings(chartKey) {
  const data = overviewChartsCache?.[chartKey] || { labels: [], values: [] };
  const pairs = (data.labels || []).map((district, i) => ({
    district: district || "Unknown",
    value: Number(data.values?.[i] || 0),
  })).filter((p) => p.value > 0);
  pairs.sort((a, b) => b.value - a.value);
  renderRankingCards("topDistrictsOverview", pairs.slice(0, 5));
  renderRankingCards("bottomDistrictsOverview", [...pairs].reverse().slice(0, 5), true);
}

async function renderOverviewCharts(charts) {
  if (!charts) return;
  await Promise.allSettled(
    OVERVIEW_CHARTS.map(([id, key, title]) => {
      const data = charts[key] || { labels: [], values: [] };
      return HAD.plotBar(id, data.labels, data.values, title, true);
    }),
  );
  initRankingSelector(charts);
  requestAnimationFrame(() => HAD.resizeChartsIn(document.getElementById("tabOverview")));
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

  Object.entries(MODULE_KPI_KEYS).forEach(([tabId, keys]) => renderModuleKpis(tabId, keys));

  await Promise.allSettled([
    HAD.plotPie("chartTrimester", ac.trimester_distribution.labels, ac.trimester_distribution.values, "ANC Trimester Distribution"),
    HAD.plotPie("chartBmi", ac.bmi_distribution.labels, ac.bmi_distribution.values, "ANC BMI Distribution", true),
    HAD.plotBar("chartHtn", ac.hypertension_distribution.labels, ac.hypertension_distribution.values, "ANC Hypertension Distribution"),
    HAD.plotMultiLine("chartDiabetesTrend", diabetesLabels, diabetesSeries, "District Wise Diabetes Trend"),
    HAD.plotBar("chartAncDistrict", ac.district_anc.labels, ac.district_anc.values, "District Wise Total ANC", true),
    HAD.plotBar("chartMiMin", mi.charts.minimum_protected_by_district.labels, mi.charts.minimum_protected_by_district.values, "District Wise Minimum Protected Mothers"),
    HAD.plotBar("chartMiFull", mi.charts.fully_immunized_by_district.labels, mi.charts.fully_immunized_by_district.values, "District Wise Fully Immunized Mothers"),
    HAD.plotLine("chartMiTrend", mi.charts.monthly_trend.labels, mi.charts.monthly_trend.values, "Maternal Immunization Monthly Trend"),
    HAD.plotBar("chartSam", cn.charts.sam_by_district.labels, cn.charts.sam_by_district.values, "District Wise SAM Cases"),
    HAD.plotBar("chartMam", cn.charts.mam_by_district.labels, cn.charts.mam_by_district.values, "District Wise MAM Cases"),
    HAD.plotMultiLine("chartNutritionTrend", cn.charts.nutrition_trend.labels,
      { SAM: cn.charts.nutrition_trend.sam, MAM: cn.charts.nutrition_trend.mam }, "Child Nutrition Monthly Trend"),
    HAD.plotBar("chartCiCoverage", ci.charts.coverage_by_district.labels, ci.charts.coverage_by_district.values, "District Wise Immunization Coverage"),
    HAD.plotLine("chartCiDefaulter", ci.charts.defaulter_trend.labels, ci.charts.defaulter_trend.values, "Child Immunization Defaulter Trend"),
    HAD.plotLine("chartCiTrend", ci.charts.coverage_trend.labels, ci.charts.coverage_trend.values, "Child Immunization Coverage Trend"),
    HAD.plotBar("chartPncEbf", pnc.charts.early_breastfeeding_by_district.labels, pnc.charts.early_breastfeeding_by_district.values, "District Wise Early Breastfeeding"),
    HAD.plotBar("chartPncCounsel", pnc.charts.counseling_by_district.labels, pnc.charts.counseling_by_district.values, "District Wise PNC Counseling"),
    HAD.plotLine("chartPncTrend", pnc.charts.monthly_trend.labels, pnc.charts.monthly_trend.values, "PNC Monthly Trend"),
    HAD.plotPie("chartFpMix", fp.charts.method_mix.labels, fp.charts.method_mix.values, "Family Planning Method Mix"),
    HAD.plotBar("chartFpCommodity", fp.charts.commodity_by_district.labels, fp.charts.commodity_by_district.values, "District Wise FP Commodity Distribution", true),
  ]);

  requestAnimationFrame(() => {
    HAD.resizeAllCharts();
    setTimeout(() => HAD.resizeAllCharts(), 150);
  });
}

function districtCoords(name, index) {
  if (DISTRICT_COORDS[name]) return DISTRICT_COORDS[name];
  const angle = (index / 12) * Math.PI * 2;
  const r = 0.35 + (index % 5) * 0.08;
  return [PUNJAB_CENTER[0] + Math.sin(angle) * r, PUNJAB_CENTER[1] + Math.cos(angle) * r];
}

function showGeoPanel(district, stats) {
  const panel = document.getElementById("geoDistrictPanel");
  const title = document.getElementById("geoPanelTitle");
  const body = document.getElementById("geoPanelStats");
  if (!panel || !title || !body) return;
  title.textContent = district;
  body.innerHTML = `
    <div><strong>Score:</strong> ${stats.score ?? "—"}</div>
    <div><strong>ANC:</strong> ${Number(stats.total_anc || 0).toLocaleString()}</div>
    <div><strong>Immunized:</strong> ${Number(stats.fully_immunized_children || 0).toLocaleString()}</div>
    <div><strong>SAM:</strong> ${Number(stats.sam_cases || 0).toLocaleString()}</div>
    <div><strong>PNC:</strong> ${Number(stats.pnc_visits || 0).toLocaleString()}</div>
    <div><strong>FP Counseling:</strong> ${Number(stats.fp_counseling || 0).toLocaleString()}</div>`;
  panel.classList.remove("d-none");
}

function initPunjabMap(geo) {
  const mapEl = document.getElementById("punjabMap");
  if (!mapEl || typeof L === "undefined") return;

  if (HAD.geoMap) {
    HAD.geoMap.remove();
    HAD.geoMap = null;
  }

  const map = L.map("punjabMap", { scrollWheelZoom: false }).setView(PUNJAB_CENTER, 7);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  const statsByDistrict = {};
  (geo.ranking_table || []).forEach((row) => { statsByDistrict[row.district] = row; });

  (geo.ranking_table || []).forEach((row, index) => {
    const [lat, lng] = districtCoords(row.district, index);
    const marker = L.circleMarker([lat, lng], {
      radius: 8,
      color: "#003366",
      fillColor: "#4169E1",
      fillOpacity: 0.75,
      weight: 2,
    }).addTo(map);
    marker.bindTooltip(row.district, { permanent: false, direction: "top" });
    marker.on("click", () => showGeoPanel(row.district, row));
  });

  HAD.geoMap = map;
  setTimeout(() => map.invalidateSize(), 200);
}

async function renderGeographic(geo) {
  document.getElementById("topDistricts").innerHTML = geo.top_performing.map((d) =>
    `<li class="list-group-item d-flex justify-content-between align-items-center">
      <span>${d.district}</span><span class="badge bg-success rounded-pill">${d.score}</span></li>`,
  ).join("") || `<li class="list-group-item text-muted">No Data Available</li>`;

  document.getElementById("bottomDistricts").innerHTML = geo.lowest_performing.map((d) =>
    `<li class="list-group-item d-flex justify-content-between align-items-center">
      <span>${d.district}</span><span class="badge bg-danger rounded-pill">${d.score}</span></li>`,
  ).join("") || `<li class="list-group-item text-muted">No Data Available</li>`;

  await HAD.plotMultiLine("chartGeoCompare", geo.district_comparison.labels,
    { ANC: geo.district_comparison.anc, Immunized: geo.district_comparison.immunized },
    "District Wise Performance Comparison");

  document.querySelector("#geoRankingTable tbody").innerHTML = geo.ranking_table.map((r, i) =>
    `<tr><td>${i + 1}</td><td>${r.district}</td><td>${r.score}</td><td>${r.total_anc}</td><td>${r.fully_immunized_children}</td><td>${r.sam_cases}</td><td>${r.pnc_visits}</td><td>${r.fp_counseling}</td></tr>`,
  ).join("") || `<tr><td colspan="8" class="text-center text-muted">No Data Available</td></tr>`;

  initPunjabMap(geo);
  HAD.resizeChart("chartGeoCompare");
}

async function loadGeographic(params) {
  if (geoLoaded && params.toString() === currentParams?.toString()) {
    HAD.geoMap?.invalidateSize();
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
  HAD.chartMeta = {};
  HAD.showSpinner();

  try {
    const overview = await HAD.fetchJSON("/api/dashboard/", params);
    allKpisCache = overview.kpis || [];
    HAD.renderKpis("kpiGrid", allKpisCache, true);
    HAD.setLastUpdated(overview.filters?.end_date || new Date().toISOString().slice(0, 10));

    await renderOverviewCharts(overview.charts);

    const bundle = await HAD.fetchJSON("/api/bundle/", params);
    await renderSectionCharts(bundle.charts);

    HAD.hideSpinner();
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

  document.getElementById("geoPanelClose")?.addEventListener("click", () => {
    document.getElementById("geoDistrictPanel")?.classList.add("d-none");
  });

  document.querySelector('[data-bs-target="#tabOverview"]')?.addEventListener("shown.bs.tab", () => {
    HAD.resizeChartsIn(document.getElementById("tabOverview"));
  });

  document.querySelector('[data-bs-target="#tabGeo"]')?.addEventListener("shown.bs.tab", () => {
    if (currentParams) loadGeographic(currentParams);
    setTimeout(() => HAD.geoMap?.invalidateSize(), 250);
  });
});
