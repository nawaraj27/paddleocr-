"use strict";
/* 3D animated analytics (Three.js r128). Three independent scenes:
 *   #viz-trend    -> animated 3D revenue ribbon (line/area over time)
 *   #viz-products -> growing 3D bar chart (top products)
 *   #viz-vendors  -> rotating 3D pie (vendor share)
 * Data comes from /api/analytics/. Each scene is self-contained and resilient
 * (skips quietly if THREE/WebGL is unavailable).
 */
(function () {
  const THREE = window.THREE;
  const GREEN = [0x2d4a2d, 0x3d4a3a, 0xa8c898, 0xc8d9a8, 0xd4e4b4, 0xe8eab4,
                 0x88aa78, 0x6b8a5a];
  const scenes = [];

  function mkScene(elId, camZ = 9) {
    const el = document.getElementById(elId);
    if (!el || !THREE) return null;
    let renderer;
    try { renderer = new THREE.WebGLRenderer({antialias: true, alpha: true}); }
    catch (e) { return null; }
    const w = el.clientWidth || 400, h = el.clientHeight || 300;
    renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    renderer.setSize(w, h);
    el.innerHTML = ""; el.appendChild(renderer.domElement);
    const scene = new THREE.Scene();
    const cam = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
    cam.position.set(0, 3.2, camZ); cam.lookAt(0, 0.5, 0);
    scene.add(new THREE.AmbientLight(0xffffff, 0.85));
    const dl = new THREE.DirectionalLight(0xffffff, 0.7); dl.position.set(5, 8, 6);
    scene.add(dl);
    const group = new THREE.Group(); scene.add(group);
    const ctx = {el, renderer, scene, cam, group, t0: performance.now()};
    scenes.push(ctx);
    new ResizeObserver(() => {
      const W = el.clientWidth, H = el.clientHeight; if (!W || !H) return;
      cam.aspect = W / H; cam.updateProjectionMatrix(); renderer.setSize(W, H);
    }).observe(el);
    return ctx;
  }

  // ---- 3D bars (top products) ----
  function buildBars(ctx, items) {
    clear(ctx.group);
    const n = Math.min(items.length, 8) || 1;
    const max = Math.max(1, ...items.map(i => i.revenue || i.frequency || 0));
    const spacing = 1.3, x0 = -(n - 1) * spacing / 2;
    items.slice(0, 8).forEach((it, i) => {
      const val = (it.revenue || it.frequency || 0) / max;
      const targetH = 0.3 + val * 4;
      const geo = new THREE.BoxGeometry(0.8, 1, 0.8);
      const mat = new THREE.MeshStandardMaterial({color: GREEN[i % GREEN.length],
        roughness: 0.5, metalness: 0.1});
      const bar = new THREE.Mesh(geo, mat);
      bar.position.x = x0 + i * spacing;
      bar.scale.y = 0.01; bar.userData = {targetH};
      bar.position.y = 0;
      ctx.group.add(bar);
      addLabel(ctx.group, (it.name || "").slice(0, 10),
               bar.position.x, -0.4, 0.8);
    });
    addGrid(ctx.group, n * spacing + 1);
  }

  // ---- 3D revenue ribbon (trend) ----
  function buildTrend(ctx, trend) {
    clear(ctx.group);
    const pts = trend.slice(-30);
    if (!pts.length) { addLabel(ctx.group, "no data", 0, 1, 0, 0.6); return; }
    const max = Math.max(1, ...pts.map(p => p.revenue));
    const span = 9, x0 = -span / 2, dx = span / Math.max(1, pts.length - 1);
    const vecs = pts.map((p, i) =>
      new THREE.Vector3(x0 + i * dx, 0.2 + (p.revenue / max) * 3.4,
        Math.sin(i * 0.5) * 0.15));
    const curve = new THREE.CatmullRomCurve3(vecs);
    const tube = new THREE.Mesh(
      new THREE.TubeGeometry(curve, 120, 0.07, 8, false),
      new THREE.MeshStandardMaterial({color: 0x2d4a2d, roughness: 0.4}));
    ctx.group.add(tube);
    // area under curve as translucent ribbon
    const shape = new THREE.Shape();
    const flat = pts.map((p, i) => [x0 + i * dx, 0.2 + (p.revenue / max) * 3.4]);
    shape.moveTo(flat[0][0], 0);
    flat.forEach(([x, y]) => shape.lineTo(x, y));
    shape.lineTo(flat[flat.length - 1][0], 0);
    const ribbon = new THREE.Mesh(new THREE.ShapeGeometry(shape),
      new THREE.MeshBasicMaterial({color: 0xa8c898, transparent: true,
        opacity: 0.45, side: THREE.DoubleSide}));
    ctx.group.add(ribbon);
    vecs.forEach(v => {
      const dot = new THREE.Mesh(new THREE.SphereGeometry(0.08, 12, 12),
        new THREE.MeshStandardMaterial({color: 0x3d4a3a}));
      dot.position.copy(v); ctx.group.add(dot);
    });
    ctx.group.userData.grow = true;
  }

  // ---- 3D pie (vendor share) ----
  function buildPie(ctx, vendors) {
    clear(ctx.group);
    const data = vendors.slice(0, 6);
    const total = data.reduce((a, v) => a + (v.revenue || v.count || 0), 0) || 1;
    let start = 0;
    data.forEach((v, i) => {
      const frac = (v.revenue || v.count || 0) / total;
      const ang = frac * Math.PI * 2;
      const geo = new THREE.CylinderGeometry(2.4, 2.4, 0.6, 48, 1, false,
        start, ang);
      const mat = new THREE.MeshStandardMaterial({color: GREEN[i % GREEN.length],
        roughness: 0.5});
      const slice = new THREE.Mesh(geo, mat);
      slice.rotation.x = -Math.PI / 2.4;
      const mid = start + ang / 2;
      slice.position.x = Math.cos(mid) * 0.12;
      slice.position.z = Math.sin(mid) * 0.12;
      slice.scale.set(0.01, 0.01, 0.01);
      slice.userData = {target: 1};
      ctx.group.add(slice);
      start += ang;
    });
  }

  // ---- helpers ----
  function clear(g) { while (g.children.length) g.remove(g.children[0]); }
  function addGrid(g, size) {
    const grid = new THREE.GridHelper(Math.max(6, size), 8, 0xcfd8c2, 0xe3e8da);
    grid.position.y = 0; g.add(grid);
  }
  function addLabel(g, text, x, y, z, scale = 0.4) {
    const cv = document.createElement("canvas"); cv.width = 160; cv.height = 48;
    const c = cv.getContext("2d");
    c.font = "600 26px Inter,sans-serif"; c.fillStyle = "#2d4a2d";
    c.textAlign = "center"; c.fillText(text, 80, 32);
    const spr = new THREE.Sprite(new THREE.SpriteMaterial(
      {map: new THREE.CanvasTexture(cv), transparent: true}));
    spr.position.set(x, y, z); spr.scale.set(scale * 3.3, scale, 1);
    g.add(spr);
  }

  function animate() {
    requestAnimationFrame(animate);
    const now = performance.now();
    scenes.forEach(ctx => {
      ctx.group.rotation.y = Math.sin((now - ctx.t0) * 0.0002) * 0.5;
      ctx.group.children.forEach(ch => {
        if (ch.userData && ch.userData.targetH !== undefined) {       // bars
          const cur = ch.scale.y, tgt = ch.userData.targetH;
          ch.scale.y += (tgt - cur) * 0.08;
          ch.position.y = ch.scale.y / 2;
        }
        if (ch.userData && ch.userData.target !== undefined) {        // pie grow
          const s = ch.scale.x + (1 - ch.scale.x) * 0.08;
          ch.scale.set(s, s, s);
        }
      });
      ctx.renderer.render(ctx.scene, ctx.cam);
    });
  }

  async function load() {
    const trend = mkScene("viz-trend", 8);
    const products = mkScene("viz-products", 9);
    const vendors = mkScene("viz-vendors", 8);
    function qs() {
      const p = new URLSearchParams();
      const g = v => document.getElementById(v) && document.getElementById(v).value;
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
      catch (e) { d = {totals:{}, trend:[], vendors:[], top_products:[]}; }
      const t = d.totals || {};
      setText("m-docs", t.total_documents ?? 0);
      setText("m-rev", fmt(t.total_revenue));
      setText("m-aov", fmt(t.avg_order_value));
      if (trend) buildTrend(trend, d.trend || []);
      if (products) buildBars(products, d.top_products || []);
      if (vendors) buildPie(vendors, d.vendors || []);
    }
    const applyBtn = document.getElementById("a-apply");
    if (applyBtn) applyBtn.addEventListener("click", refresh);
    await refresh();
    animate();
  }
  function setText(id, v) { const e = document.getElementById(id); if (e) e.textContent = v; }
  function fmt(v) { return v == null ? "—" : Number(v).toLocaleString(undefined,
    {maximumFractionDigits: 0}); }

  if (document.readyState !== "loading") load();
  else document.addEventListener("DOMContentLoaded", load);
})();
