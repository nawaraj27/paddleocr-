"use strict";
// Small animated 3D area chart for the landing demo browser.
(function () {
  const THREE = window.THREE;
  const el = document.getElementById("landing-chart");
  if (!THREE || !el) return;
  let renderer;
  try { renderer = new THREE.WebGLRenderer({canvas: el, antialias: true, alpha: true}); }
  catch (e) { return; }
  function size() { return [el.clientWidth || 480, el.clientHeight || 280]; }
  let [w, h] = size();
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.setSize(w, h, false);
  const scene = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(45, w / h, 0.1, 100);
  cam.position.set(0, 2.4, 7); cam.lookAt(0, 1, 0);
  scene.add(new THREE.AmbientLight(0xffffff, 0.9));
  const dl = new THREE.DirectionalLight(0xffffff, 0.6); dl.position.set(4, 6, 5); scene.add(dl);
  const group = new THREE.Group(); scene.add(group);

  const vals = [0.3, 0.5, 0.42, 0.66, 0.55, 0.78, 0.7, 0.92, 0.85, 1.0];
  const span = 7, x0 = -span / 2, dx = span / (vals.length - 1);
  const pts = vals.map((v, i) => new THREE.Vector3(x0 + i * dx, 0.2 + v * 2.6, 0));
  const curve = new THREE.CatmullRomCurve3(pts);
  group.add(new THREE.Mesh(new THREE.TubeGeometry(curve, 100, 0.06, 8, false),
    new THREE.MeshStandardMaterial({color: 0x2d4a2d})));
  const shape = new THREE.Shape();
  shape.moveTo(pts[0].x, 0);
  pts.forEach(p => shape.lineTo(p.x, p.y));
  shape.lineTo(pts[pts.length - 1].x, 0);
  group.add(new THREE.Mesh(new THREE.ShapeGeometry(shape),
    new THREE.MeshBasicMaterial({color: 0xa8c898, transparent: true, opacity: 0.5,
      side: THREE.DoubleSide})));

  function loop() {
    requestAnimationFrame(loop);
    group.rotation.y = Math.sin(performance.now() * 0.0004) * 0.35;
    const [nw, nh] = size();
    if (nw !== w || nh !== h) { w = nw; h = nh; cam.aspect = w / h;
      cam.updateProjectionMatrix(); renderer.setSize(w, h, false); }
    renderer.render(scene, cam);
  }
  loop();
})();
