// 3D View module: Three.js scene with animated station bars, raycasting, and controls.

import {
  appState, numberValue, getStationId, getStationName,
  getAvailabilityHex, CITY_CONFIG,
} from './utils.js';

let threeState = null;

/**
 * Initialize the Three.js scene.
 * Defers actual canvas creation — call resize3DScene() after the container
 * is visible so clientWidth/clientHeight are non-zero.
 */
function ensureThreeScene() {
  if (threeState || !window.THREE) return;

  const container = document.getElementById('three-view');
  if (!container) return;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x1a1a2e);

  // Use fallback dimensions — resize3DScene() will correct once visible
  const width = container.clientWidth || 800;
  const height = container.clientHeight || 600;

  const camera = new THREE.PerspectiveCamera(42, width / height, 0.1, 2000);
  camera.position.set(0, 55, 72);
  camera.lookAt(0, 0, 0);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio || 1);
  renderer.setSize(width, height, false);
  container.innerHTML = '';
  container.appendChild(renderer.domElement);

  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.06;
  controls.enableZoom = true;
  controls.enablePan = true;
  controls.rotateSpeed = 0.75;
  controls.panSpeed = 0.8;
  controls.target.set(0, 8, 0);
  controls.update();

  const ambient = new THREE.AmbientLight(0xffffff, 0.72);
  scene.add(ambient);

  const light = new THREE.DirectionalLight(0xffffff, 1.2);
  light.position.set(30, 60, 30);
  scene.add(light);

  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(160, 160, 1, 1),
    new THREE.MeshStandardMaterial({ color: 0x0f1b2e, metalness: 0.12, roughness: 0.88 })
  );
  floor.rotation.x = -Math.PI / 2;
  scene.add(floor);

  const grid = new THREE.GridHelper(160, 24, 0x2f4b70, 0x1a2d46);
  grid.position.y = 0.02;
  scene.add(grid);

  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();

  threeState = {
    scene,
    camera,
    renderer,
    controls,
    raycaster,
    pointer,
    bars: new Map(),
    floor,
    grid,
    frame: null,
    tooltipVisible: false,
  };

  // Window resize is handled by the exported resize3DScene()
  window.addEventListener('resize', resize3DScene);
  renderer.domElement.addEventListener('click', handleThreeClick);
}

/**
 * Hide the 3D tooltip.
 */
function hideThreeTooltip() {
  const tooltip = document.getElementById('three-tooltip');
  if (!tooltip) return;
  tooltip.classList.remove('is-visible');
  tooltip.setAttribute('aria-hidden', 'true');
  delete tooltip.dataset.stationId;
  if (threeState) {
    threeState.tooltipVisible = false;
  }
}

/**
 * Show the 3D tooltip with station info.
 */
function showThreeTooltip(stationId, station, bikes) {
  const tooltip = document.getElementById('three-tooltip');
  if (!tooltip || !station) return;
  const name = getStationName(station);
  tooltip.dataset.stationId = stationId;
  tooltip.innerHTML = `
    <div class="three-tooltip-name">${name}</div>
    <div class="three-tooltip-value">${bikes} bicis disponibles</div>
    <div class="three-tooltip-note">num_bikes_available</div>
  `;
  tooltip.classList.add('is-visible');
  tooltip.setAttribute('aria-hidden', 'false');
  if (threeState) {
    threeState.tooltipVisible = true;
  }
}

/**
 * Position the tooltip near a mesh.
 */
function positionThreeTooltip(mesh) {
  if (!threeState) return;
  const tooltip = document.getElementById('three-tooltip');
  const container = document.getElementById('three-view');
  if (!tooltip || !container || !mesh) return;

  const rect = container.getBoundingClientRect();
  const projected = mesh.position.clone();
  projected.project(threeState.camera);
  const x = ((projected.x + 1) / 2) * rect.width;
  const y = ((-projected.y + 1) / 2) * rect.height;
  tooltip.style.left = `${x}px`;
  tooltip.style.top = `${y}px`;
}

/**
 * Handle click on 3D scene (raycasting).
 */
function handleThreeClick(event) {
  if (!threeState) return;
  const container = document.getElementById('three-view');
  if (!container) return;

  const rect = container.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  const y = -(((event.clientY - rect.top) / rect.height) * 2 - 1);
  threeState.pointer.set(x, y);
  threeState.raycaster.setFromCamera(threeState.pointer, threeState.camera);

  const intersects = threeState.raycaster.intersectObjects(
    Array.from(threeState.bars.values()),
    false
  );

  if (!intersects.length) {
    hideThreeTooltip();
    return;
  }

  const mesh = intersects[0].object;
  const station = appState.stationById.get(mesh.userData.id);
  if (!station) {
    hideThreeTooltip();
    return;
  }

  showThreeTooltip(mesh.userData.id, station, numberValue(mesh.userData.bikes, 0));
  positionThreeTooltip(mesh);
}

/**
 * Resize the 3D scene to match its container's current dimensions.
 * EXPORTED so the page coordinator can call it after layout changes
 * (chat toggle, mode switch, window resize).
 */
export function resize3DScene() {
  if (!threeState) return;
  const container = document.getElementById('three-view');
  if (!container) return;

  const width = container.clientWidth || 1;
  const height = container.clientHeight || 1;

  // Avoid unnecessary work if size hasn't changed
  if (width <= 1 || height <= 1) return;

  threeState.camera.aspect = width / height;
  threeState.camera.updateProjectionMatrix();
  threeState.renderer.setSize(width, height, false);
  threeState.controls?.update();

  if (threeState.tooltipVisible) {
    const tooltip = document.getElementById('three-tooltip');
    const tooltipId = tooltip?.dataset.stationId;
    const tooltipMesh = tooltipId ? threeState.bars.get(tooltipId) : null;
    if (tooltipMesh) {
      positionThreeTooltip(tooltipMesh);
    }
  }
}

/**
 * Sync 3D scene with station data.
 */
function syncThreeStations() {
  if (!threeState) return;
  const { scene, bars } = threeState;
  const config = CITY_CONFIG[appState.city] || CITY_CONFIG.acoruna;
  const centerLat = config.center[0];
  const centerLon = config.center[1];
  const scale = 7000;
  const nextIds = new Set();

  appState.stations.forEach((station) => {
    const id = getStationId(station);
    const lat = numberValue(station.lat, centerLat);
    const lon = numberValue(station.lon, centerLon);
    const status = appState.statuses.get(id) || {};
    const bikes = numberValue(status.num_bikes_available, 0);
    const docks = numberValue(status.num_docks_available, 0);
    const capacity = numberValue(station.capacity, 20);
    const targetHeight = Math.max(1.6, (bikes / capacity) * 15);
    const targetColor = getAvailabilityHex(bikes);
    nextIds.add(id);

    let mesh = bars.get(id);
    if (!mesh) {
      const material = new THREE.MeshStandardMaterial({
        color: targetColor,
        emissive: 0x000000,
        emissiveIntensity: 0,
        roughness: 0.45,
        metalness: 0.08,
      });
      mesh = new THREE.Mesh(new THREE.BoxGeometry(1, 1, 1), material);
      mesh.position.set((lon - centerLon) * scale, targetHeight / 2, (lat - centerLat) * -scale);
      mesh.scale.set(2.2, targetHeight, 2.2);
      mesh.userData = {
        id,
        stationName: getStationName(station),
        bikes,
        docks,
        currentHeight: targetHeight,
        targetHeight,
        currentColor: targetColor,
        targetColor,
      };
      scene.add(mesh);
      bars.set(id, mesh);
    }

    mesh.position.x = (lon - centerLon) * scale;
    mesh.position.z = (lat - centerLat) * -scale;
    mesh.userData.stationName = getStationName(station);
    mesh.userData.bikes = bikes;
    mesh.userData.docks = docks;
    mesh.userData.targetHeight = targetHeight;
    mesh.userData.targetColor = targetColor;
    if (mesh.userData.currentHeight == null) {
      mesh.userData.currentHeight = targetHeight;
    }
    if (mesh.userData.currentColor == null) {
      mesh.userData.currentColor = targetColor;
    }
    mesh.scale.x = 2.2;
    mesh.scale.z = 2.2;
    mesh.material.color.setHex(targetColor);
  });

  // Remove bars for stations no longer in list
  for (const [id, mesh] of bars.entries()) {
    if (!nextIds.has(id)) {
      scene.remove(mesh);
      mesh.geometry.dispose();
      mesh.material.dispose();
      bars.delete(id);
    }
  }

  const tooltip = document.getElementById('three-tooltip');
  const tooltipId = tooltip?.dataset.stationId;
  if (tooltipId && !bars.has(tooltipId)) {
    hideThreeTooltip();
  }
}

/**
 * Sync 3D highlight for selected station.
 */
function syncThreeHighlight() {
  if (!threeState) return;
  for (const [id, mesh] of threeState.bars.entries()) {
    mesh.material.emissive.setHex(id === appState.selectedStationId ? 0x1f2937 : 0x000000);
    mesh.material.emissiveIntensity = id === appState.selectedStationId ? 0.8 : 0;
  }
  if (threeState.tooltipVisible) {
    const tooltip = document.getElementById('three-tooltip');
    const tooltipId = tooltip?.dataset.stationId;
    const tooltipMesh = tooltipId ? threeState.bars.get(tooltipId) : null;
    if (tooltipMesh) {
      positionThreeTooltip(tooltipMesh);
    }
  }
}

/**
 * Render the 3D scene with animation loop.
 */
function renderThreeScene() {
  if (!threeState) return;
  syncThreeStations();

  if (!threeState.frame) {
    const tick = () => {
      threeState.frame = window.requestAnimationFrame(tick);
      threeState.controls?.update();

      // Animate bar heights (lerp)
      for (const [id, mesh] of threeState.bars.entries()) {
        const currentHeight = numberValue(mesh.userData.currentHeight, mesh.userData.targetHeight || 1.6);
        const targetHeight = numberValue(mesh.userData.targetHeight, currentHeight);
        const nextHeight = currentHeight + (targetHeight - currentHeight) * 0.05;
        mesh.userData.currentHeight = nextHeight;
        mesh.scale.y = nextHeight;
        mesh.position.y = nextHeight / 2;

        const currentColor = mesh.material.color.getHex();
        const targetColor = numberValue(mesh.userData.targetColor, currentColor);
        if (currentColor !== targetColor) {
          mesh.material.color.setHex(targetColor);
          mesh.userData.currentColor = targetColor;
        }

        const isSelected = id === appState.selectedStationId;
        mesh.material.emissive.setHex(isSelected ? 0x1f2937 : 0x000000);
        mesh.material.emissiveIntensity = isSelected ? 0.8 : 0;
      }

      if (threeState.tooltipVisible) {
        const tooltip = document.getElementById('three-tooltip');
        const tooltipId = tooltip?.dataset.stationId;
        const tooltipMesh = tooltipId ? threeState.bars.get(tooltipId) : null;
        if (tooltipMesh) {
          positionThreeTooltip(tooltipMesh);
        }
      }

      threeState.renderer.render(threeState.scene, threeState.camera);
    };
    tick();
  }
}

/**
 * Initialize the 3D view.
 * Creates the scene if needed and starts the render loop.
 * Call resize3DScene() after calling this when the container becomes visible.
 */
export function init3DView(containerId) {
  ensureThreeScene();
  renderThreeScene();
}

/**
 * Update the 3D scene with new stations.
 */
export function updateStations(stations) {
  appState.stations = stations;
  if (threeState) {
    syncThreeStations();
    syncThreeHighlight();
  }
}

/**
 * Toggle 3D view visibility and start/stop render loop.
 */
export function toggleThreeView(visible) {
  if (!threeState) {
    if (visible) {
      ensureThreeScene();
      renderThreeScene();
    }
    return;
  }

  const container = document.getElementById('three-view');
  if (!container) return;

  if (!visible) {
    if (threeState.frame) {
      cancelAnimationFrame(threeState.frame);
      threeState.frame = null;
    }
  } else {
    renderThreeScene();
    // Defer resize to next frame so the container has layout dimensions
    requestAnimationFrame(() => resize3DScene());
  }
}