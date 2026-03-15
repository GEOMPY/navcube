/**
 * Interactive NaviCube demo using Three.js
 * Shows a 3D cube with face labels + a miniature NaviCube in the corner,
 * demonstrating the pyside-navicube concept directly in the browser.
 */
(function () {
  "use strict";

  const container = document.getElementById("demo-canvas");
  if (!container) return;

  const W = container.clientWidth;
  const H = Math.min(420, W * 0.56);
  container.style.height = H + "px";

  // ── Three.js setup ──────────────────────────────────────
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1a1d23);

  const camera = new THREE.PerspectiveCamera(40, W / H, 0.1, 100);
  camera.position.set(3.5, 2.5, 3.5);
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(W, H);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.appendChild(renderer.domElement);

  // ── Lighting ────────────────────────────────────────────
  scene.add(new THREE.AmbientLight(0xffffff, 0.5));
  const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
  dirLight.position.set(5, 8, 5);
  scene.add(dirLight);

  // ── Main cube ───────────────────────────────────────────
  const cubeGeo = new THREE.BoxGeometry(1.6, 1.6, 1.6);
  const faceMaterials = [
    new THREE.MeshStandardMaterial({ color: 0x4a9eff, metalness: 0.1, roughness: 0.5 }), // +X
    new THREE.MeshStandardMaterial({ color: 0x4a9eff, metalness: 0.1, roughness: 0.5 }), // -X
    new THREE.MeshStandardMaterial({ color: 0x5cb85c, metalness: 0.1, roughness: 0.5 }), // +Y
    new THREE.MeshStandardMaterial({ color: 0x5cb85c, metalness: 0.1, roughness: 0.5 }), // -Y
    new THREE.MeshStandardMaterial({ color: 0xd9534f, metalness: 0.1, roughness: 0.5 }), // +Z
    new THREE.MeshStandardMaterial({ color: 0xd9534f, metalness: 0.1, roughness: 0.5 }), // -Z
  ];
  const cube = new THREE.Mesh(cubeGeo, faceMaterials);
  scene.add(cube);

  // Edge wireframe
  const edges = new THREE.EdgesGeometry(cubeGeo);
  const wire = new THREE.LineSegments(edges, new THREE.LineBasicMaterial({ color: 0xffffff, opacity: 0.3, transparent: true }));
  cube.add(wire);

  // Grid
  const grid = new THREE.GridHelper(6, 12, 0x333842, 0x262a33);
  grid.position.y = -0.81;
  scene.add(grid);

  // ── NaviCube (corner mini-cube) ─────────────────────────
  const ncScene = new THREE.Scene();
  ncScene.background = null;

  const ncCamera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);

  const ncSize = 120;
  const ncGeo = new THREE.BoxGeometry(1, 1, 1);

  function makeLabel(text, faceColor, textColor) {
    const canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 128;
    const ctx = canvas.getContext("2d");
    ctx.fillStyle = faceColor;
    ctx.fillRect(0, 0, 128, 128);
    ctx.strokeStyle = "#222";
    ctx.lineWidth = 3;
    ctx.strokeRect(1, 1, 126, 126);
    ctx.fillStyle = textColor;
    ctx.font = "bold 36px Inter, Arial, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(text, 64, 68);
    const tex = new THREE.CanvasTexture(canvas);
    tex.minFilter = THREE.LinearFilter;
    return new THREE.MeshBasicMaterial({ map: tex });
  }

  const ncMats = [
    makeLabel("RIGHT", "#c8ccd4", "#222"),  // +X
    makeLabel("LEFT", "#c8ccd4", "#222"),   // -X
    makeLabel("TOP", "#dce0e8", "#222"),    // +Y (Three.js Y-up)
    makeLabel("BOT", "#b0b4bc", "#222"),    // -Y
    makeLabel("FRONT", "#c8ccd4", "#222"),  // +Z
    makeLabel("BACK", "#c8ccd4", "#222"),   // -Z
  ];
  const ncCube = new THREE.Mesh(ncGeo, ncMats);
  ncScene.add(ncCube);

  const ncEdges = new THREE.EdgesGeometry(ncGeo);
  const ncWire = new THREE.LineSegments(ncEdges, new THREE.LineBasicMaterial({ color: 0x444444 }));
  ncCube.add(ncWire);

  ncScene.add(new THREE.AmbientLight(0xffffff, 1.0));

  // ── Orbit controls (simple drag) ───────────────────────
  let isDragging = false;
  let prevX = 0, prevY = 0;
  let spherical = { theta: Math.PI / 4, phi: Math.PI / 3, radius: 6 };

  function updateCamera() {
    const sinPhi = Math.sin(spherical.phi);
    camera.position.set(
      spherical.radius * sinPhi * Math.sin(spherical.theta),
      spherical.radius * Math.cos(spherical.phi),
      spherical.radius * sinPhi * Math.cos(spherical.theta)
    );
    camera.lookAt(0, 0, 0);

    // Sync NaviCube rotation to match main camera
    ncCamera.position.copy(camera.position).normalize().multiplyScalar(3);
    ncCamera.lookAt(0, 0, 0);
  }

  renderer.domElement.addEventListener("pointerdown", (e) => {
    isDragging = true;
    prevX = e.clientX;
    prevY = e.clientY;
    renderer.domElement.setPointerCapture(e.pointerId);
  });

  renderer.domElement.addEventListener("pointermove", (e) => {
    if (!isDragging) return;
    const dx = e.clientX - prevX;
    const dy = e.clientY - prevY;
    spherical.theta -= dx * 0.008;
    spherical.phi = Math.max(0.2, Math.min(Math.PI - 0.2, spherical.phi + dy * 0.008));
    prevX = e.clientX;
    prevY = e.clientY;
    updateCamera();
  });

  renderer.domElement.addEventListener("pointerup", (e) => {
    isDragging = false;
    renderer.domElement.releasePointerCapture(e.pointerId);
  });

  renderer.domElement.addEventListener("wheel", (e) => {
    e.preventDefault();
    spherical.radius = Math.max(3, Math.min(12, spherical.radius + e.deltaY * 0.005));
    updateCamera();
  }, { passive: false });

  // ── NaviCube click handling ─────────────────────────────
  const raycaster = new THREE.Raycaster();
  const ncMouse = new THREE.Vector2();

  renderer.domElement.addEventListener("click", (e) => {
    const rect = renderer.domElement.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Check if click is in the NaviCube region (top-right corner)
    const ncLeft = W - ncSize - 15;
    const ncTop = 15;
    if (clickX >= ncLeft && clickX <= ncLeft + ncSize && clickY >= ncTop && clickY <= ncTop + ncSize) {
      ncMouse.x = ((clickX - ncLeft) / ncSize) * 2 - 1;
      ncMouse.y = -((clickY - ncTop) / ncSize) * 2 + 1;

      raycaster.setFromCamera(ncMouse, ncCamera);
      const hits = raycaster.intersectObject(ncCube);
      if (hits.length > 0) {
        const normal = hits[0].face.normal.clone();
        ncCube.localToWorld(normal).sub(ncCube.position).normalize();
        animateToView(normal);
      }
    }
  });

  // ── Animate to view ─────────────────────────────────────
  let animating = false;
  let animStart = 0;
  let animFrom = {};
  let animTo = {};
  const ANIM_DURATION = 350;

  function animateToView(normal) {
    const targetTheta = Math.atan2(normal.x, normal.z);
    const targetPhi = Math.acos(Math.max(-1, Math.min(1, normal.y)));

    animFrom = { theta: spherical.theta, phi: spherical.phi };
    animTo = { theta: targetTheta, phi: targetPhi || 0.01 };

    // Handle angle wrapping
    let dTheta = animTo.theta - animFrom.theta;
    if (dTheta > Math.PI) dTheta -= 2 * Math.PI;
    if (dTheta < -Math.PI) dTheta += 2 * Math.PI;
    animTo.theta = animFrom.theta + dTheta;

    animStart = performance.now();
    animating = true;
  }

  function smoothstep(t) {
    t = Math.max(0, Math.min(1, t));
    return t * t * t * (t * (t * 6 - 15) + 10);
  }

  // ── Render loop ─────────────────────────────────────────
  updateCamera();

  function render() {
    requestAnimationFrame(render);

    if (animating) {
      const elapsed = performance.now() - animStart;
      const t = smoothstep(Math.min(1, elapsed / ANIM_DURATION));
      spherical.theta = animFrom.theta + (animTo.theta - animFrom.theta) * t;
      spherical.phi = animFrom.phi + (animTo.phi - animFrom.phi) * t;
      updateCamera();
      if (t >= 1) animating = false;
    }

    // Slow auto-rotate when idle
    if (!isDragging && !animating) {
      spherical.theta += 0.001;
      updateCamera();
    }

    // Main render
    renderer.setViewport(0, 0, W, H);
    renderer.setScissor(0, 0, W, H);
    renderer.setScissorTest(true);
    renderer.render(scene, camera);

    // NaviCube render (top-right corner)
    const ncX = W - ncSize - 15;
    const ncY = H - ncSize - 15;
    renderer.setViewport(ncX, ncY, ncSize, ncSize);
    renderer.setScissor(ncX, ncY, ncSize, ncSize);
    renderer.clearDepth();
    renderer.render(ncScene, ncCamera);

    renderer.setScissorTest(false);
  }

  render();

  // ── Resize ──────────────────────────────────────────────
  window.addEventListener("resize", () => {
    const newW = container.clientWidth;
    const newH = Math.min(420, newW * 0.56);
    container.style.height = newH + "px";
    camera.aspect = newW / newH;
    camera.updateProjectionMatrix();
    renderer.setSize(newW, newH);
  });
})();
