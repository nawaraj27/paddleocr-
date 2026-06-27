"use strict";
/* Analytics charts using Chart.js. Replaces Three.js 3D scenes. */
(function () {
  let trendChart, productsChart, vendorsChart;

  const GREEN = ["#3D4A3A","#5A6A4A","#A8C898","#C8D9A8","#D4E4B4","#E8EAB4","#88AA78","#6B8A5A"];

  function setText(id, v) {
    const e = document.getElementById(id);
    if (e) e.textContent = v;
  }
  function fmt(v) {
    return v == null ? "—" : Number(v).toLocaleString(undefined, {maximumFractionDigits: 0});
  }

  function mkCanvas(wrapperId) {
    const wrap = document.getElementById(wrapperId);
    if (!wrap) return null;
    wrap.innerHTML = "";
    const canvas = document.createElement("canvas");
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    wrap.appendChild(canvas);
    return canvas;
  }

  function buildTrend(data) {
    const canvas = mkCanvas("viz-trend");
    if (!canvas) return;
    if (trendChart) trendChart.destroy();
    const labels = data.map(d => d.period || "");
    const values = data.map(d => d.revenue || 0);
    trendChart = new Chart(canvas, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Revenue",
          data: values,
          borderColor: "#3D4A3A",
          backgroundColor: "rgba(168,200,152,0.3)",
          borderWidth: 2,
          pointRadius: 5,
          pointBackgroundColor: "#3D4A3A",
          fill: true,
          tension: 0.4,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#6B6B6B" }, grid: { color: "#E8E5E0" } },
          y: { ticks: { color: "#6B6B6B" }, grid: { color: "#E8E5E0" } }
        }
      }
    });
  }

  function buildProducts(data) {
    const canvas = mkCanvas("viz-products");
    if (!canvas) return;
    if (productsChart) productsChart.destroy();
    const labels = data.map(d => d.name || "");
    const values = data.map(d => d.revenue || 0);
    productsChart = new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label: "Revenue",
          data: values,
          backgroundColor: GREEN,
          borderRadius: 6,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#6B6B6B", maxRotation: 35 }, grid: { display: false } },
          y: { ticks: { color: "#6B6B6B" }, grid: { color: "#E8E5E0" } }
        }
      }
    });
  }

  function buildVendors(data) {
    const canvas = mkCanvas("viz-vendors");
    if (!canvas) return;
    if (vendorsChart) vendorsChart.destroy();
    const labels = data.map(d => d.vendor || "Unknown");
    const values = data.map(d => d.revenue || 0);
    vendorsChart = new Chart(canvas, {
      type: "doughnut",
      data: {
        labels,
        datasets: [{
          data: values,
          backgroundColor: GREEN,
          borderWidth: 2,
          borderColor: "#fff",
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: "bottom", labels: { color: "#4A4A4A", padding: 12 } }
        }
      }
    });
  }

  function qs() {
    const p = new URLSearchParams();
    const g = id => { const el = document.getElementById(id); return el ? el.value : ""; };
    if (g("a-granularity")) p.set("granularity", g("a-granularity"));
    if (g("a-vendor")) p.set("vendor", g("a-vendor"));
    if (g("a-category")) p.set("category", g("a-category"));
    if (g("a-from")) p.set("date_from", g("a-from"));
    if (g("a-to")) p.set("date_to", g("a-to"));
    return p.toString();
  }

  async function refresh() {
    let d;
    try { d = await window.DF.api("/api/analytics/?" + qs()); }
    catch (e) {
      console.error("Analytics API error:", e);
      d = { totals: {}, trend: [], vendors: [], top_products: [] };
    }
    const t = d.totals || {};
    setText("m-docs", t.total_documents ?? 0);
    setText("m-rev", fmt(t.total_revenue));
    setText("m-aov", fmt(t.avg_order_value));
    buildTrend(d.trend || []);
    buildProducts(d.top_products || []);
    buildVendors(d.vendors || []);
  }

  function init() {
    const btn = document.getElementById("a-apply");
    if (btn) btn.addEventListener("click", refresh);
    refresh();
  }

  if (document.readyState !== "loading") init();
  else document.addEventListener("DOMContentLoaded", init);
})();
