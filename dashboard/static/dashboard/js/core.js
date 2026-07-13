/**
 * Core utilities: theme, filters, AJAX helpers, responsive Plotly wrappers.
 */
const HAD = {
  chartIds: new Set(),

  PLOT_CONFIG: {
    responsive: true,
    displayModeBar: false,
    useResizeHandler: true,
  },

  showSpinner() { document.getElementById("globalSpinner")?.classList.remove("d-none"); },
  hideSpinner() { document.getElementById("globalSpinner")?.classList.add("d-none"); },

  isDarkTheme() {
    return document.documentElement.getAttribute("data-bs-theme") === "dark";
  },

  baseLayout(title, extra = {}) {
    const textColor = this.isDarkTheme() ? "#ffffff" : "#000000";
    return {
      title: { text: title, font: { size: 14, color: textColor } },
      autosize: true,
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      font: { color: textColor, size: 11 },
      margin: { t: 44, b: 56, l: 56, r: 24, autoexpand: true },
      legend: { orientation: "h", yanchor: "top", y: -0.2, x: 0, font: { color: textColor } },
      xaxis: { tickfont: { color: textColor }, titlefont: { color: textColor } },
      yaxis: { tickfont: { color: textColor }, titlefont: { color: textColor } },
      ...extra,
    };
  },

  chartThemeLayout() {
    const textColor = this.isDarkTheme() ? "#ffffff" : "#000000";
    const gridColor = this.isDarkTheme() ? "rgba(255,255,255,0.15)" : "rgba(128,128,128,0.2)";
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
    const textColor = this.isDarkTheme() ? "#ffffff" : "#000000";
    const gridColor = this.isDarkTheme() ? "rgba(255,255,255,0.15)" : "rgba(128,128,128,0.2)";
    layout.xaxis = {
      ...(layout.xaxis || {}),
      tickfont: { color: textColor, ...(layout.xaxis?.tickfont || {}) },
      titlefont: { color: textColor, ...(layout.xaxis?.titlefont || {}) },
      gridcolor: layout.xaxis?.gridcolor || gridColor,
    };
    layout.yaxis = {
      ...(layout.yaxis || {}),
      tickfont: { color: textColor, ...(layout.yaxis?.tickfont || {}) },
      titlefont: { color: textColor, ...(layout.yaxis?.titlefont || {}) },
      gridcolor: layout.yaxis?.gridcolor || gridColor,
    };
    return layout;
  },

  updateChartTheme() {
    const layout = this.chartThemeLayout();
    this.chartIds.forEach((id) => {
      const el = document.getElementById(id);
      if (!el) return;
      Plotly.relayout(el, layout);
      Plotly.restyle(el, { "textfont.color": layout["font.color"] });
    });
  },

  async plotChart(elId, data, layout = {}) {
    const el = document.getElementById(elId);
    if (!el) {
      console.warn(`Chart element not found: ${elId}`);
      return;
    }
    if (typeof Plotly === "undefined") {
      console.error("Plotly is not loaded");
      return;
    }

    if (el.querySelector(".plotly")) {
      Plotly.purge(el);
    }

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
    requestAnimationFrame(() => this.resizeChart(elId));
  },

  resizeChart(elId) {
    const el = document.getElementById(elId);
    if (el && el.querySelector(".plotly")) {
      Plotly.Plots.resize(el);
    }
  },

  resizeAllCharts() {
    this.chartIds.forEach((id) => this.resizeChart(id));
  },

  resizeChartsIn(container) {
    if (!container) return;
    container.querySelectorAll(".chart-box").forEach((el) => {
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
          setTimeout(() => this.resizeChartsIn(pane), 80);
        });
      });
    });

    if (window.ResizeObserver) {
      const observer = new ResizeObserver(() => this.resizeAllCharts());
      const observeCharts = () => {
        document.querySelectorAll(".chart-box").forEach((el) => observer.observe(el));
      };
      observeCharts();
      this._observeCharts = observeCharts;
    }
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
  },

  async fetchJSON(url, params) {
    const qs = params ? `?${params.toString()}` : "";
    const resp = await fetch(`${url}${qs}`, { headers: { "X-Requested-With": "XMLHttpRequest" } });
    if (!resp.ok) throw new Error(`Request failed: ${resp.status}`);
    return resp.json();
  },

  plotPie(elId, labels, values, title, donut = false) {
    const textColor = this.isDarkTheme() ? "#ffffff" : "#000000";
    const data = [{
      labels,
      values,
      type: "pie",
      hole: donut ? 0.45 : 0,
      textinfo: "label+percent",
      automargin: true,
      textfont: { color: textColor },
    }];
    return this.plotChart(elId, data, {
      title,
      showlegend: true,
      margin: { t: 44, b: 20, l: 20, r: 20, autoexpand: true },
    });
  },

  plotBar(elId, labels, values, title, horizontal = false) {
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

    const trace = horizontal
      ? { y: chartLabels, x: chartValues, type: "bar", orientation: "h", marker: { color: "#0d6efd" } }
      : { x: chartLabels, y: chartValues, type: "bar", marker: { color: "#0d6efd" } };
    const axisLayout = horizontal
      ? { yaxis: { automargin: true }, xaxis: { automargin: true, gridcolor: "rgba(128,128,128,0.2)" }, margin: { l: 10, r: 24, t: 44, b: 40 } }
      : { xaxis: { automargin: true }, yaxis: { automargin: true, gridcolor: "rgba(128,128,128,0.2)" } };
    return this.plotChart(elId, [trace], { title, ...axisLayout });
  },

  plotLine(elId, labels, values, title) {
    return this.plotChart(elId, [{
      x: labels,
      y: values,
      type: "scatter",
      mode: "lines+markers",
      line: { color: "#6610f2", width: 2 },
    }], {
      title,
      xaxis: { automargin: true },
      yaxis: { automargin: true },
    });
  },

  plotMultiLine(elId, labels, series, title) {
    const traces = Object.entries(series).map(([name, values]) => ({
      x: labels,
      y: values,
      name,
      type: "scatter",
      mode: "lines+markers",
      line: { width: 2 },
    }));
    return this.plotChart(elId, traces, {
      title,
      xaxis: { automargin: true },
      yaxis: { automargin: true },
      showlegend: true,
    });
  },

  renderKpis(containerId, kpis) {
    const grid = document.getElementById(containerId);
    if (!grid) return;
    grid.innerHTML = kpis.map((k, i) => {
      const dir = k.change_pct.direction;
      const icon = dir === "up" ? "bi-arrow-up-short" : dir === "down" ? "bi-arrow-down-short" : "bi-dash";
      return `
        <div class="col-xl-3 col-md-4 col-sm-6">
          <div class="card kpi-card h-100" style="animation-delay:${i * 0.05}s">
            <div class="card-body d-flex gap-3">
              <div class="kpi-icon bg-primary bg-opacity-10 text-primary"><i class="bi ${k.icon}"></i></div>
              <div>
                <div class="text-muted small">${k.label}</div>
                <div class="fs-4 fw-bold">${Number(k.value).toLocaleString()}</div>
                <div class="kpi-change ${dir} small"><i class="bi ${icon}"></i> ${Math.abs(k.change_pct.value)}%</div>
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
});
