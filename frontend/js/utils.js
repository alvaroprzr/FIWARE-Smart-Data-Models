// Shared utilities and state for Smart Mobility Hub frontend modules.

export const API_BASE = window.__SMART_MOBILITY_API_BASE__ || (
  window.location.protocol === 'file:' || window.location.origin === 'null'
    ? 'http://localhost:8000'
    : ''
);

export const CITY_CONFIG = {
  acoruna: { label: 'A Coruña', center: [43.366, -8.412], zoom: 14 },
};

// Shared application state
export const appState = {
  city: 'acoruna',
  stations: [],
  stationById: new Map(),
  selectedStationId: null,
  statuses: new Map(),
  forecasts: new Map(),
  heatmap: [],
  heatVisible: true,
  mapMode: 'map',
  lastGoodDataAt: null,
};

/**
 * Fetch JSON with error handling and content-type header.
 */
export async function requestJSON(path, options = {}) {
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
      ...options,
    });

    if (!response.ok) {
      const text = await response.text().catch(() => '');
      throw new Error(text || `HTTP ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error(`Request failed: ${path}`, error);
    throw error;
  }
}

/**
 * Extract numeric value from NGSI-LD wrapped format.
 */
export function unwrapValue(value, fallback = null) {
  if (value == null) return fallback;
  if (typeof value === 'object' && !Array.isArray(value)) {
    if ('value' in value) return value.value;
    if ('object' in value) return value.object;
  }
  return value;
}

/**
 * Extract numeric value, coerce to number, return fallback if invalid.
 */
export function numberValue(value, fallback = 0) {
  const raw = unwrapValue(value, fallback);
  const parsed = Number(raw);
  return Number.isFinite(parsed) ? parsed : fallback;
}

/**
 * Extract station ID from item (handles multiple field names).
 */
export function getStationId(item) {
  return item?.station_id || item?.stationId || item?.id || '';
}

/**
 * Extract station name from item (handles multiple field names).
 */
export function getStationName(item) {
  return item?.name || item?.station_name || item?.short_name || item?.stationId || getStationId(item) || 'Estación';
}

/**
 * Get availability CSS class (good, warn, bad).
 */
export function getAvailabilityClass(value) {
  if (value > 5) return 'availability-good';
  if (value > 0) return 'availability-warn';
  return 'availability-bad';
}

/**
 * Get availability color (hex string).
 */
export function getAvailabilityColor(value) {
  if (value > 5) return '#22c55e';
  if (value > 0) return '#f59e0b';
  return '#ef4444';
}

/**
 * Get availability color (hex number for Three.js).
 */
export function getAvailabilityHex(value) {
  if (value > 5) return 0x22c55e;
  if (value > 0) return 0xf59e0b;
  return 0xef4444;
}

/**
 * Render relative time from unix timestamp.
 */
export function relativeTime(value) {
  const timestamp = Number(value) * 1000;
  if (!Number.isFinite(timestamp) || timestamp <= 0) return 'sin dato';
  const delta = Date.now() - timestamp;
  if (delta < 0) return 'ahora';
  const minutes = Math.floor(delta / 60000);
  if (minutes < 1) return 'hace <1 min';
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `hace ${hours} h`;
}

/**
 * Escape HTML to prevent XSS.
 */
export function escapeHtml(text) {
  return String(text ?? '').replace(/[&<>"']/g, (char) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[char]));
}

/**
 * Get city label from configuration.
 */
export function cityLabel(city) {
  return CITY_CONFIG[city]?.label || 'A Coruña';
}

/**
 * Update the connection status indicator on the page.
 */
export function setConnection(online, message) {
  const pill = document.getElementById('connection-pill');
  const dot = document.getElementById('connection-dot');
  const label = document.getElementById('connection-label');

  if (pill && dot && label) {
    pill.className = `flex items-center gap-2 rounded-2xl px-4 py-3 text-sm font-medium ${
      online ? 'border border-emerald-400/20 bg-emerald-400/10 text-emerald-300'
        : 'border border-rose-400/20 bg-rose-400/10 text-rose-300'
    }`;
    dot.className = `h-2.5 w-2.5 rounded-full ${online ? 'bg-emerald-400' : 'bg-rose-400'}`;
    label.textContent = message || (online ? 'Conectado' : 'Sin conexión');
  }
}
