/**
 * Core utilities: theme, filters, Plotly chart wrappers, KPI rendering, exports.
 */
const HAD = {
  chartIds: new Set(),
  chartMeta: {},

  MODULE_COLORS: {
    overview: "#4169E1",
    anc: "#0d6efd",
    maternal: "#198754",
    nutrition: "#fd7e14",
    child_immunization: "#6f42c1",
    pnc: "#20c997",
    fp: "#e83e8c",
    geographic: "#003366",
  },

  PLOT_CONFIG: {
    responsive: true,
    displayModeBar: false,
    useResizeHandler: true,
  },

  OVERVIEW_KPI_KEYS: new Set([
    "total_mothers",
    "total_anc",
    "children_under_five",
    "pnc_visits",
    "fp_counseling",
    "fp_commodity",
    "fully_immunized_children",
    "diabetes_cases",
  ]),

  KPI_LABELS: {
    pnc_visits: "Total PNC",
    fp_counseling: "Family Planning Counseling",
    fp_commodity: "FP Commodity Distribution",
  },

  showSpinner() { document.getElementById("globalSpinner")?.classList.remove("d-none"); },
  hideSpinner() { document.getElementById("globalSpinner")?.classList.add("d-none"); },

  isDarkTheme() {
    return document.documentElement.getAttribute("data-bs-theme") === "dark";
  },

  moduleColor(elId) {
    const card = document.getElementById(elId)?.closest("[data-module]");
    const mod = card?.dataset.module || "overview";
    return this.MODULE_COLORS[mod] || this.MODULE_COLORS.overview;
  },

  baseLayout(title, extra = {}) {
    const textColor = this.isDarkTheme() ? "#f8f9fa" : "#212529";
    return {
      title: { text: title, font: { size: 16, color: textColor, family: "Segoe UI, system-ui, sans-serif" }, x: 0.02, xanchor: "left" },
      autosize: true,
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      font: { color: textColor, size: 12, family: "Segoe UI, system-ui, sans-serif" },
      margin: { t: 56, b: 64, l: 64, r: 32, autoexpand: true },
      legend: { orientation: "h", yanchor: "top", y: -0.18, x: 0, font: { color: textColor } },
      hovermode: "closest",
      ...extra,
    };
  },

  chartThemeLayout() {
    const textColor = this.isDarkTheme() ? "#f8f9fa" : "#212529";
    const gridColor = this.isDarkTheme() ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.08)";
    return {
      "font.color": textColor,
      "title.font.color": textColor,
      "legend.font.color": textColor,
      "xaxis.tickfont.color": textColor,
      "yaxis.tickfont.color": textColor,
      "xaxis.titlefont.color": textColor,
      "yaxis.titlefont.color": textColor,
      "xaxis.gridcolor": gridColor,
      "yaxis.gridcolor": gridColor,
    };
  },

  applyAxisTheme(layout) {
    const textColor = this.isDarkTheme() ? "#f8f9fa" : "#212529";
    const gridColor = this.isDarkTheme() ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.08)";
    ["xaxis", "yaxis"].forEach((axis) => {
      layout[axis] = {
        ...(layout[axis] || {}),
        tickfont: { color: textColor, ...(layout[axis]?.tickfont || {}) },
        titlefont: { color: textColor, ...(layout[axis]?.titlefont || {}) },
        gridcolor: layout[axis]?.gridcolor || gridColor,
        zerolinecolor: gridColor,
      };
    });
    return layout;
  },

  updateChartTheme() {
    const layout = this.chartThemeLayout();
    this.chartIds.forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      Plotly.relayout(el, layout);
    });
  },

  showEmptyChart(elId, message = "No Data Available") {
    const el = document.getElementById(elId);
    if (!el) return;
    if (el.querySelector(".plotly")) Plotly.purge(el);
    el.innerHTML = `<div class="chart-empty-state"><i class="bi bi-bar-chart-line"></i><p>${message}</p></div>`;
    this.chartIds.delete(elId);
  },

  hasChartData(labels, values) {
    if (!labels?.length) return false;
    return values.some((v) => Number(v) > 0);
  },

  ensureChartToolbar(elId, title) {
    const el = document.getElementById(elId);
    const cardBody = el?.closest(".card-body");
    if (!cardBody || cardBody.querySelector(".chart-toolbar")) return;

    const toolbar = document.createElement("div");
    toolbar.className = "chart-toolbar d-flex justify-content-end gap-1 mb-2";
    toolbar.innerHTML = `
      <button type="button" class="btn btn-sm btn-outline-secondary" data-export="png" data-chart="${elId}" title="Download PNG"><i class="bi bi-image"></i></button>
      <button type="button" class="btn btn-sm btn-outline-secondary" data-export="csv" data-chart="${elId}" title="Download CSV"><i class="bi bi-filetype-csv"></i></button>
      <button type="button" class="btn btn-sm btn-outline-secondary" data-export="print" data-chart="${elId}" title="Print Chart"><i class="bi bi-printer"></i></button>`;
    cardBody.prepend(toolbar);

    toolbar.querySelectorAll("[data-export]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const action = btn.dataset.export;
        if (action === "png") this.exportPNG(elId, title);
        else if (action === "csv") this.exportCSV(elId);
        else if (action === "print") this.printChart(elId);
      });
    });
  },

  exportPNG(elId, title) {
    const el = document.getElementById(elId);
    if (!el?.querySelector(".plotly")) return;
    Plotly.downloadImage(el, {
      format: "png",
      width: 1200,
      height: 700,
      filename: (title || elId).replace(/\s+/g, "_").toLowerCase(),
    });
  },

  exportCSV(elId) {
    const meta = this.chartMeta[elId];
    if (!meta) return;
    let rows = [["Label", "Value"]];
    if (meta.type === "bar" || meta.type === "line") {
      rows = [["Label", ...(meta.seriesNames || ["Value"])]];
      meta.labels.forEach((label, i) => {
        if (meta.seriesNames) {
          rows.push([label, ...meta.seriesNames.map((n) => meta.series[n][i])]);
        } else {
          rows.push([label, meta.values[i]]);
        }
      });
    } else if (meta.type === "pie") {
      rows = [["Category", "Value", "Percent"]];
      const total = meta.values.reduce((a, b) => a + Number(b), 0) || 1;
      meta.labels.forEach((label, i) => {
        const val = Number(meta.values[i]);
        rows.push([label, val, ((val / total) * 100).toFixed(1) + "%"]);
      });
    }
    const csv = rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${elId}.csv`;
    link.click();
    URL.revokeObjectURL(link.href);
  },

  printChart(elId) {
    const el = document.getElementById(elId);
    const card = el?.closest(".chart-card");
    if (!card) return;
    const w = window.open("", "_blank");
    w.document.write(`<html><head><title>Chart</title><style>body{margin:0;padding:20px;font-family:Segoe UI,sans-serif}</style></head><body>${card.outerHTML}</body></html>`);
    w.document.close();
    w.focus();
    w.print();
    w.close();
  },

  async plotChart(elId, data, layout = {}, meta = {}) {
    const el = document.getElementById(elId);
    if (!el) return;
    if (typeof Plotly === "undefined") return;

    if (el.querySelector(".plotly")) Plotly.purge(el);
    el.innerHTML = "";

    const { title, ...rest } = layout;
    const height = el.clientHeight || parseInt(getComputedStyle(el).height, 10) || 400;
    const mergedLayout = this.applyAxisTheme({
      ...this.baseLayout(title || ""),
      height,
      autosize: true,
      ...rest,
    });

    await Plotly.newPlot(el, data, mergedLayout, this.PLOT_CONFIG);
    this.chartIds.add(elId);
    this.chartMeta[elId] = { ...meta, title: title || "" };
    this.ensureChartToolbar(elId, title);
    requestAnimationFrame(() => this.resizeChart(elId));
  },

  resizeChart(elId) {
    const el = document.getElementById(elId);
    if (el?.querySelector(".plotly")) Plotly.Plots.resize(el);
  },

  resizeAllCharts() {
    this.chartIds.forEach((id) => this.resizeChart(id));
  },

  resizeChartsIn(container) {
    container?.querySelectorAll(".chart-box").forEach((el) => {
      if (el.id) this.resizeChart(el.id);
    });
  },

  initChartResize() {
    let timer;
    window.addEventListener("resize", () => {
      clearTimeout(timer);
      timer = setTimeout(() => this.resizeAllCharts(), 120);
    });

    document.querySelectorAll('[data-bs-toggle="tab"]').forEach((tab) => {
      tab.addEventListener("shown.bs.tab", (event) => {
        const pane = document.querySelector(event.target.getAttribute("data-bs-target"));
        requestAnimationFrame(() => {
          this.resizeChartsIn(pane);
          setTimeout(() => this.resizeChartsIn(pane), 100);
        });
      });
    });

    if (window.ResizeObserver) {
      const observer = new ResizeObserver(() => this.resizeAllCharts());
      document.querySelectorAll(".chart-box").forEach((el) => observer.observe(el));
    }
  },

  initHeaderClock() {
    const clockEl = document.getElementById("headerClock");
    const update = () => {
      const now = new Date();
      if (clockEl) {
        clockEl.textContent = now.toLocaleString("en-PK", {
          weekday: "short", year: "numeric", month: "short", day: "numeric",
          hour: "2-digit", minute: "2-digit", second: "2-digit",
        });
      }
    };
    update();
    setInterval(update, 1000);
  },

  setLastUpdated(isoDate) {
    const el = document.getElementById("headerLastUpdated");
    if (!el) return;
    if (!isoDate) {
      el.textContent = "Last updated: —";
      return;
    }
    const d = new Date(isoDate);
    el.textContent = `Last updated: ${d.toLocaleDateString("en-PK", { year: "numeric", month: "short", day: "numeric" })}`;
  },

  initTheme() {
    const saved = localStorage.getItem("had-theme") || "light";
    document.documentElement.setAttribute("data-bs-theme", saved);
    const toggle = document.getElementById("themeToggle");
    const settingsToggle = document.getElementById("settingsDarkMode");
    if (settingsToggle) settingsToggle.checked = saved === "dark";
    if (toggle) {
      toggle.querySelector("i").className = saved === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
      toggle.addEventListener("click", () => {
        const next = this.isDarkTheme() ? "light" : "dark";
        document.documentElement.setAttribute("data-bs-theme", next);
        localStorage.setItem("had-theme", next);
        toggle.querySelector("i").className = next === "dark" ? "bi bi-sun" : "bi bi-moon-stars";
        if (settingsToggle) settingsToggle.checked = next === "dark";
        this.updateChartTheme();
        this.resizeAllCharts();
      });
    }
    settingsToggle?.addEventListener("change", (e) => {
      const next = e.target.checked ? "dark" : "light";
      document.documentElement.setAttribute("data-bs-theme", next);
      localStorage.setItem("had-theme", next);
      this.updateChartTheme();
      this.resizeAllCharts();
    });
  },

  initSidebar() {
    document.getElementById("sidebarToggle")?.addEventListener("click", () => {
      document.getElementById("sidebar")?.classList.toggle("show");
      setTimeout(() => this.resizeAllCharts(), 300);
    });
  },

  getFilterParams() {
    const preset = document.getElementById("datePreset")?.value || "all_time";
    const params = new URLSearchParams();
    params.set("preset", preset);
    if (preset === "custom") {
      params.set("start_date", document.getElementById("startDate")?.value || "");
      params.set("end_date", document.getElementById("endDate")?.value || "");
    }
    const district = document.getElementById("districtFilter")?.value;
    if (district) params.set("district", district);
    return params;
  },

  resetFilters(onApply) {
    const presetEl = document.getElementById("datePreset");
    const districtEl = document.getElementById("districtFilter");
    if (presetEl) presetEl.value = "all_time";
    if (districtEl) districtEl.value = "";
    document.getElementById("startDate").value = "";
    document.getElementById("endDate").value = "";
    document.querySelectorAll(".custom-date").forEach((el) => el.classList.add("d-none"));
    onApply?.();
  },

  initFilters(onApply) {
    const presetEl = document.getElementById("datePreset");
    const toggleCustom = () => {
      document.querySelectorAll(".custom-date").forEach((el) => {
        el.classList.toggle("d-none", presetEl.value !== "custom");
      });
    };
    presetEl?.addEventListener("change", toggleCustom);
    toggleCustom();
    document.getElementById("applyFilters")?.addEventListener("click", onApply);
    document.getElementById("resetFilters")?.addEventListener("click", () => this.resetFilters(onApply));
  },

  async fetchJSON(url, params) {
    const qs = params ? `?${params.toString()}` : "";
    const resp = await fetch(`${url}${qs}`, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!resp.ok) throw new Error(`Request failed: ${resp.status}`);
    return resp.json();
  },

  groupPieSmallSlices(labels, values, threshold = 3) {
    const total = values.reduce((a, b) => a + Number(b || 0), 0) || 1;
    const grouped = [];
    let other = 0;
    labels.forEach((label, i) => {
      const val = Number(values[i] || 0);
      const pct = (val / total) * 100;
      if (pct < threshold && label !== "Other") other += val;
      else grouped.push({ label: label || "Unknown", value: val });
    });
    if (other > 0) grouped.push({ label: "Other", value: other });
    return {
      labels: grouped.map((g) => g.label),
      values: grouped.map((g) => g.value),
    };
  },

  plotPie(elId, labels, values, title, donut = false) {
    if (!this.hasChartData(labels, values)) {
      this.showEmptyChart(elId);
      return Promise.resolve();
    }
    const grouped = this.groupPieSmallSlices(labels, values);
    const color = this.moduleColor(elId);
    const textColor = this.isDarkTheme() ? "#f8f9fa" : "#212529";
    const data = [{
      labels: grouped.labels,
      values: grouped.values,
      type: "pie",
      hole: donut ? 0.45 : 0,
      textinfo: "label+percent",
      textposition: "auto",
      automargin: true,
      textfont: { color: textColor, size: 11 },
      marker: { colors: this.pieColorScale(grouped.labels.length, color) },
      hovertemplate: "%{label}<br>%{value:,}<br>%{percent}<extra></extra>",
    }];
    this.chartMeta[elId] = { type: "pie", labels: grouped.labels, values: grouped.values };
    return this.plotChart(elId, data, {
      title,
      showlegend: true,
      margin: { t: 56, b: 24, l: 24, r: 24, autoexpand: true },
    });
  },

  pieColorScale(n, base) {
    const palette = ["#4169E1", "#0d6efd", "#198754", "#fd7e14", "#6f42c1", "#20c997", "#e83e8c", "#6610f2", "#ffc107", "#6c757d"];
    return Array.from({ length: n }, (_, i) => palette[i % palette.length]);
  },

  plotBar(elId, labels, values, title, horizontal = false) {
    if (!this.hasChartData(labels, values)) {
      this.showEmptyChart(elId);
      return Promise.resolve();
    }
    const pairs = labels.map((label, index) => ({
      label: label || "Unknown",
      value: Number(values[index] || 0),
    }));
    pairs.sort((a, b) => b.value - a.value);

    let chartLabels = pairs.map((item) => item.label);
    let chartValues = pairs.map((item) => item.value);
    if (horizontal) {
      chartLabels = chartLabels.reverse();
      chartValues = chartValues.reverse();
    }

    const color = this.moduleColor(elId);
    const textColor = this.isDarkTheme() ? "#f8f9fa" : "#212529";
    const trace = horizontal
      ? {
          y: chartLabels,
          x: chartValues,
          type: "bar",
          orientation: "h",
          marker: { color, line: { width: 0 } },
          text: chartValues.map((v) => v.toLocaleString()),
          textposition: "outside",
          textfont: { color: textColor, size: 10 },
          hovertemplate: "%{y}<br>%{x:,}<extra></extra>",
        }
      : {
          x: chartLabels,
          y: chartValues,
          type: "bar",
          marker: { color, line: { width: 0 } },
          text: chartValues.map((v) => v.toLocaleString()),
          textposition: "outside",
          textfont: { color: textColor, size: 10 },
          hovertemplate: "%{x}<br>%{y:,}<extra></extra>",
        };

    this.chartMeta[elId] = { type: "bar", labels: chartLabels, values: chartValues };
    const axisLayout = horizontal
      ? { yaxis: { automargin: true, gridcolor: "rgba(128,128,128,0.15)" }, xaxis: { automargin: true, gridcolor: "rgba(128,128,128,0.15)" }, margin: { l: 8, r: 48, t: 56, b: 48 } }
      : { xaxis: { automargin: true, gridcolor: "rgba(128,128,128,0.15)" }, yaxis: { automargin: true, gridcolor: "rgba(128,128,128,0.15)" } };
    return this.plotChart(elId, [trace], { title, ...axisLayout });
  },

  plotLine(elId, labels, values, title) {
    if (!this.hasChartData(labels, values)) {
      this.showEmptyChart(elId);
      return Promise.resolve();
    }
    const color = this.moduleColor(elId);
    this.chartMeta[elId] = { type: "line", labels, values, seriesNames: null };
    return this.plotChart(elId, [{
      x: labels,
      y: values,
      type: "scatter",
      mode: "lines+markers",
      name: title,
      line: { color, width: 3, shape: "spline" },
      marker: { size: 7, color },
      hovertemplate: "%{x}<br>%{y:,}<extra></extra>",
    }], {
      title,
      showlegend: false,
      xaxis: { automargin: true, type: "category" },
      yaxis: { automargin: true, gridcolor: "rgba(128,128,128,0.15)" },
    });
  },

  plotMultiLine(elId, labels, series, title) {
    const seriesNames = Object.keys(series);
    const hasData = labels?.length && seriesNames.some((n) => series[n]?.some((v) => Number(v) > 0));
    if (!hasData) {
      this.showEmptyChart(elId);
      return Promise.resolve();
    }
    const palette = ["#4169E1", "#0d6efd", "#198754", "#fd7e14", "#6f42c1", "#20c997", "#e83e8c"];
    const traces = seriesNames.map((name, idx) => ({
      x: labels,
      y: series[name],
      name,
      type: "scatter",
      mode: "lines+markers",
      line: { width: 2.5, shape: "spline", color: palette[idx % palette.length] },
      marker: { size: 6, color: palette[idx % palette.length] },
      hovertemplate: `${name}<br>%{x}<br>%{y:,}<extra></extra>`,
    }));
    this.chartMeta[elId] = { type: "line", labels, series, seriesNames };
    return this.plotChart(elId, traces, {
      title,
      xaxis: { automargin: true, type: "category" },
      yaxis: { automargin: true, gridcolor: "rgba(128,128,128,0.15)" },
      showlegend: true,
      legend: { orientation: "h", y: -0.22 },
    });
  },

  renderKpis(containerId, kpis, overviewOnly = true) {
    const grid = document.getElementById(containerId);
    if (!grid) return;

    const filtered = overviewOnly
      ? kpis.filter((k) => this.OVERVIEW_KPI_KEYS.has(k.key))
      : kpis;

    const kpiStyles = {
      total_mothers: { accent: "#4169E1", icon: "bi-people-fill" },
      total_anc: { accent: "#0d6efd", icon: "bi-heart-pulse-fill" },
      children_under_five: { accent: "#fd7e14", icon: "bi-emoji-smile-fill" },
      pnc_visits: { accent: "#20c997", icon: "bi-hospital-fill" },
      fp_counseling: { accent: "#e83e8c", icon: "bi-chat-dots-fill" },
      fp_commodity: { accent: "#d63384", icon: "bi-box-seam-fill" },
      fully_immunized_children: { accent: "#6f42c1", icon: "bi-shield-fill-check" },
      diabetes_cases: { accent: "#dc3545", icon: "bi-droplet-fill" },
    };

    grid.innerHTML = filtered.map((k, i) => {
      const style = kpiStyles[k.key] || { accent: "#4169E1", icon: k.icon };
      const label = this.KPI_LABELS[k.key] || k.label;
      const change = k.change_pct || {};
      let changeHtml;
      if (change.available === false || change.value == null) {
        changeHtml = `<span class="kpi-change none small text-muted">No comparison available</span>`;
      } else {
        const icon = change.direction === "up" ? "bi-arrow-up-short" : change.direction === "down" ? "bi-arrow-down-short" : "bi-dash";
        const sign = change.direction === "up" ? "↑" : change.direction === "down" ? "↓" : "→";
        changeHtml = `<span class="kpi-change ${change.direction} small">${sign} ${change.value}%</span>`;
      }
      return `
        <div class="col-xl-3 col-lg-4 col-md-6">
          <div class="card kpi-card h-100 fade-in-up" style="animation-delay:${i * 0.06}s; --kpi-accent:${style.accent}">
            <div class="card-body d-flex align-items-start gap-3">
              <div class="kpi-icon"><i class="bi ${style.icon}"></i></div>
              <div class="flex-grow-1 min-w-0">
                <div class="kpi-label text-muted small text-uppercase fw-semibold">${label}</div>
                <div class="kpi-value fw-bold">${Number(k.value).toLocaleString()}</div>
                ${changeHtml}
              </div>
            </div>
          </div>
        </div>`;
    }).join("");
  },
};

document.addEventListener("DOMContentLoaded", () => {
  HAD.initTheme();
  HAD.initSidebar();
  HAD.initChartResize();
  HAD.initHeaderClock();
});
