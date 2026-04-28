// TODO: connect the map to the live station feed and city selector.

export function initializeMap(containerId = 'map') {
  const container = document.getElementById(containerId);
  if (!container || typeof window.L === 'undefined') {
    return null;
  }

  const map = window.L.map(container, { zoomControl: true }).setView([43.3718, -8.396], 13);

  window.L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors',
    maxZoom: 19,
  }).addTo(map);

  window.L.marker([43.37095, -8.3958]).addTo(map).bindPopup('Praza de Maria Pita');
  return map;
}