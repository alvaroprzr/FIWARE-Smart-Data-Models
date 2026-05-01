// Map module: Leaflet map, stations, markers, heatmap, and station selection.

import {
  appState, requestJSON, numberValue, getStationId, getStationName,
  getAvailabilityColor, relativeTime, escapeHtml, cityLabel, CITY_CONFIG, setConnection,
} from './utils.js';

let map = null;
let markers = new Map();
let heatLayer = null;
let popupListenerAttached = false;

/**
 * Initialize the Leaflet map.
 */
function ensureMap(city = appState.city) {
  if (map || !window.L) return;
  const config = CITY_CONFIG[city] || CITY_CONFIG.acoruna;
  map = L.map(document.getElementById('map-view'), { zoomControl: true })
    .setView(config.center, config.zoom);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map);
}

/**
 * Update map view for a given city.
 */
function panToCity(city) {
  const config = CITY_CONFIG[city] || CITY_CONFIG.acoruna;
  if (map) {
    map.setView(config.center, config.zoom);
  }
}

/**
 * Update all station markers on the map.
 */
function updateMarkers() {
  if (!map) return;
  const visibleIds = new Set();

  appState.stations.forEach((station) => {
    const id = getStationId(station);
    const lat = numberValue(station.lat, NaN);
    const lon = numberValue(station.lon, NaN);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    visibleIds.add(id);

    const status = appState.statuses.get(id) || {};
    const bikes = numberValue(status.num_bikes_available, 0);
    const docks = numberValue(status.num_docks_available, 0);
    const active = id === appState.selectedStationId;
    const color = getAvailabilityColor(bikes);

    let marker = markers.get(id);
    const popupHtml = `
      <div class="min-w-[220px] space-y-3 text-slate-900">
        <div>
          <div class="text-sm font-semibold text-slate-700">${escapeHtml(getStationName(station))}</div>
          <div class="font-mono text-xs text-slate-500">${escapeHtml(id)}</div>
        </div>
        <div class="grid grid-cols-2 gap-2 text-sm">
          <div class="rounded-xl bg-slate-100 px-3 py-2"><span class="block text-slate-500">Bicis</span><span class="font-bold text-slate-900">${bikes}</span></div>
          <div class="rounded-xl bg-slate-100 px-3 py-2"><span class="block text-slate-500">Docks</span><span class="font-bold text-slate-900">${docks}</span></div>
        </div>
        <button class="js-forecast-btn w-full rounded-xl bg-slate-900 px-3 py-2 text-sm font-semibold text-white transition hover:bg-slate-700" data-station-id="${escapeHtml(id)}">Ver predicción</button>
      </div>
    `;

    if (!marker) {
      marker = L.circleMarker([lat, lon], {
        radius: active ? 13 : 11,
        color,
        weight: active ? 4 : 2,
        opacity: 0.95,
        fillColor: color,
        fillOpacity: 0.88,
      }).addTo(map);
      marker.on('click', () => selectStation(id, { openPopup: false, panTo: false }));
      marker.bindPopup(popupHtml, { closeButton: true, autoPanPadding: [24, 24] });
      markers.set(id, marker);
    } else {
      marker.setStyle({
        radius: active ? 13 : 11,
        color,
        weight: active ? 4 : 2,
        fillColor: color,
        fillOpacity: 0.88,
      });
      marker.setPopupContent(popupHtml);
    }
  });

  // Remove markers that are no longer visible
  for (const [id, marker] of markers.entries()) {
    if (!visibleIds.has(id)) {
      map.removeLayer(marker);
      markers.delete(id);
    }
  }

  // Attach popup listener for forecast button
  if (!popupListenerAttached) {
    popupListenerAttached = true;
    map.on('popupopen', (event) => {
      const button = event.popup.getElement()?.querySelector('.js-forecast-btn');
      if (button) {
        button.addEventListener('click', () => {
          const stationId = button.getAttribute('data-station-id');
          if (stationId) {
            selectStation(stationId, { openPopup: false, panTo: true });
          }
        }, { once: true });
      }
    });
  }
}

/**
 * Fetch forecast for a station and cache it.
 */
async function fetchForecast(stationId) {
  if (!stationId) return;
  try {
    const forecast = await requestJSON(`/api/stations/${encodeURIComponent(stationId)}/forecast`);
    appState.forecasts.set(stationId, forecast);
    updateSidebar(appState.stationById.get(stationId));
    setConnection(true, `Conectado · ${cityLabel(appState.city)}`);
  } catch (error) {
    console.warn('Forecast failed for', stationId, error);
    setConnection(false, 'Sin conexión');
  }
}

/**
 * Update the sidebar with station details and forecasts.
 */
function updateSidebar(station) {
  const id = station ? getStationId(station) : null;
  const status = id ? (appState.statuses.get(id) || {}) : {};
  const bikes = numberValue(status.num_bikes_available, 0);
  const docks = numberValue(status.num_docks_available, 0);
  const lastReported = status.last_reported;
  const forecast = id ? appState.forecasts.get(id) : null;

  const t30 = normalizeForecast(forecast?.t30, bikes);
  const t60 = normalizeForecast(forecast?.t60, bikes);

  const stationNameEl = document.getElementById('station-name');
  const stationBikesEl = document.getElementById('station-bikes');
  const stationDocksEl = document.getElementById('station-docks');
  const stationUpdatedEl = document.getElementById('station-updated');
  const forecast30PillEl = document.getElementById('forecast-30-pill');
  const forecast60PillEl = document.getElementById('forecast-60-pill');
  const forecast30BarEl = document.getElementById('forecast-30-bar');
  const forecast60BarEl = document.getElementById('forecast-60-bar');
  const forecast30RangeEl = document.getElementById('forecast-30-range');
  const forecast60RangeEl = document.getElementById('forecast-60-range');

  if (stationNameEl) {
    stationNameEl.textContent = station ? getStationName(station) : 'Sin estación seleccionada';
    stationNameEl.className = `mt-1 text-2xl font-bold ${station ? (bikes > 5 ? 'availability-good' : bikes > 0 ? 'availability-warn' : 'availability-bad') : ''}`;
  }
  if (stationBikesEl) {
    stationBikesEl.textContent = station ? String(bikes) : '--';
    stationBikesEl.className = `mt-1 text-4xl font-bold ${station ? (bikes > 5 ? 'availability-good' : bikes > 0 ? 'availability-warn' : 'availability-bad') : ''}`;
  }
  if (stationDocksEl) stationDocksEl.textContent = station ? String(docks) : '--';
  if (stationUpdatedEl) stationUpdatedEl.textContent = station ? relativeTime(lastReported) : '--';

  if (forecast30PillEl) forecast30PillEl.textContent = `${t30.value.toFixed(1)} bicis`;
  if (forecast60PillEl) forecast60PillEl.textContent = `${t60.value.toFixed(1)} bicis`;
  if (forecast30RangeEl) forecast30RangeEl.textContent = `Intervalo: ${formatForecastRange(t30)}`;
  if (forecast60RangeEl) forecast60RangeEl.textContent = `Intervalo: ${formatForecastRange(t60)}`;

  if (forecast30BarEl) forecast30BarEl.style.width = `${Math.max(4, Math.min(100, (t30.value / 25) * 100))}%`;
  if (forecast60BarEl) forecast60BarEl.style.width = `${Math.max(4, Math.min(100, (t60.value / 25) * 100))}%`;
}

/**
 * Normalize a forecast entry with fallback values.
 */
function normalizeForecast(entry, fallbackValue = 0) {
  const value = numberValue(entry?.value, fallbackValue);
  const low = numberValue(entry?.low, Math.max(0, value - 2));
  const high = numberValue(entry?.high, value + 2);
  return { value, low, high };
}

/**
 * Format forecast range for display.
 */
function formatForecastRange(entry) {
  if (!entry) return '--';
  const low = numberValue(entry.low, 0);
  const high = numberValue(entry.high, 0);
  return `${low.toFixed(1)} - ${high.toFixed(1)} bicis`;
}

/**
 * Select a station and optionally open its popup or pan to it.
 */
async function selectStation(stationId, options = {}) {
  if (!stationId || !appState.stationById.has(stationId)) return;
  appState.selectedStationId = stationId;
  const station = appState.stationById.get(stationId);
  updateMarkers();
  updateSidebar(station);

  if (options.panTo !== false && map && station) {
    const lat = numberValue(station.lat, null);
    const lon = numberValue(station.lon, null);
    if (Number.isFinite(lat) && Number.isFinite(lon)) {
      map.setView([lat, lon], Math.max(map.getZoom(), 15), { animate: true });
    }
  }

  if (options.openPopup !== false && markers.has(stationId)) {
    markers.get(stationId).openPopup();
  }

  if (!options.silent) {
    await fetchForecast(stationId);
  } else {
    fetchForecast(stationId);
  }
}

/**
 * Update the heatmap layer from trip data.
 */
function updateHeatmap() {
  if (!map) return;
  const points = appState.heatmap
    .map((row) => {
      const station = appState.stationById.get(row.station_id);
      if (!station) return null;
      const lat = numberValue(station.lat, NaN);
      const lon = numberValue(station.lon, NaN);
      if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;
      return [lat, lon, Math.max(0.05, numberValue(row.intensity, 0.1))];
    })
    .filter(Boolean);

  if (heatLayer) {
    map.removeLayer(heatLayer);
    heatLayer = null;
  }

  if (appState.heatVisible && points.length && window.L.heatLayer) {
    heatLayer = L.heatLayer(points, {
      radius: 30,
      blur: 24,
      maxZoom: 17,
      minOpacity: 0.2,
      gradient: { 0.1: '#0f172a', 0.35: '#38bdf8', 0.6: '#34d399', 0.85: '#fbbf24', 1: '#fb7185' },
    }).addTo(map);
  }

  const heatToggle = document.getElementById('heat-toggle');
  if (heatToggle) {
    heatToggle.textContent = appState.heatVisible ? 'Ocultar heatmap' : 'Mostrar heatmap';
  }
}

/**
 * Load stations from the API for a given city.
 */
async function loadStations(city = appState.city, preserveSelection = false) {
  try {
    const response = await requestJSON(`/api/stations?city=${encodeURIComponent(city)}`);
    const items = Array.isArray(response?.items) ? response.items : [];
    appState.stations = items;
    appState.stationById = new Map(items.map((station) => [getStationId(station), station]));

    ensureMap(city);
    panToCity(city);
    updateMarkers();

    const nextSelection = preserveSelection && appState.selectedStationId && appState.stationById.has(appState.selectedStationId)
      ? appState.selectedStationId
      : items[0] ? getStationId(items[0]) : null;

    if (nextSelection) {
      await selectStation(nextSelection, { openPopup: false, panTo: false, silent: true });
    } else {
      appState.selectedStationId = null;
      updateSidebar(null);
    }
  } catch (error) {
    console.error('loadStations failed', error);
    setConnection(false, 'Sin conexión');
  }
}

/**
 * Refresh station statuses from the API.
 */
async function refreshStationStatuses() {
  if (!appState.stations.length) return;
  const requests = appState.stations.map(async (station) => {
    const id = getStationId(station);
    try {
      const status = await requestJSON(`/api/stations/${encodeURIComponent(id)}/status`);
      appState.statuses.set(id, status);
    } catch (error) {
      console.warn('Status refresh failed for', id, error);
    }
  });

  await Promise.allSettled(requests);
  appState.lastGoodDataAt = Date.now();
  updateMarkers();
  updateSidebar(appState.stationById.get(appState.selectedStationId) || appState.stations[0] || null);
}

/**
 * Load heatmap data from the API.
 */
async function loadHeatmap(city = appState.city) {
  try {
    const rows = await requestJSON(`/api/weather/trips/heatmap?city=${encodeURIComponent(city)}`);
    appState.heatmap = Array.isArray(rows) ? rows : [];
    updateHeatmap();
    setConnection(true, `Conectado · ${cityLabel(city)}`);
    appState.lastGoodDataAt = Date.now();
  } catch (error) {
    console.warn('Heatmap failed', error);
    appState.heatmap = [];
    updateHeatmap();
    setConnection(false, 'Sin conexión');
  }
}

/**
 * Initialize the map module and return public API.
 */
export function initMap(city) {
  appState.city = city;
  ensureMap(city);
  return {
    loadStations: () => loadStations(appState.city),
    refreshStations: refreshStationStatuses,
    loadHeatmap: () => loadHeatmap(appState.city),
    updateCity,
    selectStation,
    invalidateMapSize,
  };
}

/**
 * Update the map for a new city.
 */
export async function updateCity(city) {
  appState.city = city;
  appState.statuses.clear();
  appState.forecasts.clear();
  appState.selectedStationId = null;
  await loadStations(city, false);
  await Promise.allSettled([
    refreshStationStatuses(),
    loadHeatmap(city),
  ]);
}

export function invalidateMapSize() {
  if (map) {
    map.invalidateSize();
  }
}

/**
 * Export internal functions for coordinator access if needed.
 */
export function toggleHeat() {
  appState.heatVisible = !appState.heatVisible;
  updateHeatmap();
}

export function refreshData() {
  refreshStationStatuses();
  loadHeatmap(appState.city);
}