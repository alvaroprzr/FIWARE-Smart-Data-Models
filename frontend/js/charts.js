// Charts module: CO2 savings doughnut chart powered by heatmap data.

import { appState, numberValue, requestJSON } from './utils.js';

let co2Chart = null;

/**
 * Update the CO2 chart based on heatmap data.
 */function updateCharts(data) {
  const totalKg = (data || []).reduce((sum, row) => {
    const count = numberValue(row.trip_count, 0);
    const avgDistance = numberValue(row.avg_distance, 0);
    // CO₂ savings: 0.21 kg per km of distance
    return sum + (count * (avgDistance / 1000.0) * 0.21);
  }, 0);

  const goalKg = Math.max(100, totalKg * 1.45);
  const remainder = Math.max(goalKg - totalKg, 0);

  const co2Value = document.getElementById('co2-value');
  if (co2Value) {
    co2Value.textContent = `${totalKg.toFixed(1)} kg`;
  }

  if (!window.Chart) return;

  if (!co2Chart) {
    const centerLabelPlugin = {
      id: 'centerLabel',
      beforeDraw(chart) {
        const { ctx, chartArea } = chart;
        if (!chartArea) return;
        const saved = Number(chart.data?.datasets?.[0]?.data?.[0] || 0);
        ctx.save();
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillStyle = '#ecf3ff';
        ctx.font = '700 18px Space Grotesk';
        ctx.fillText(`${saved.toFixed(1)} kg`, chartArea.left + chartArea.width / 2, chartArea.top + chartArea.height / 2 - 5);
        ctx.fillStyle = '#8ca0be';
        ctx.font = '500 11px IBM Plex Mono';
        ctx.fillText('CO2 ahorrado', chartArea.left + chartArea.width / 2, chartArea.top + chartArea.height / 2 + 16);
        ctx.restore();
      },
    };

    const canvas = document.getElementById('co2-chart');
    if (!canvas) return;

    co2Chart = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: ['Ahorro acumulado', 'Objetivo restante'],
        datasets: [{
          data: [totalKg, remainder],
          backgroundColor: ['#34d399', 'rgba(148, 163, 184, 0.16)'],
          borderColor: ['rgba(52, 211, 153, 0.9)', 'rgba(148, 163, 184, 0.1)'],
          borderWidth: 1,
          hoverOffset: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '72%',
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              color: '#d6e2f3',
              usePointStyle: true,
              boxWidth: 10,
            },
          },
          tooltip: {
            callbacks: {
              label(context) {
                return `${context.label}: ${Number(context.raw).toFixed(1)} kg`;
              },
            },
          },
        },
      },
      plugins: [centerLabelPlugin],
    });
  } else {
    co2Chart.data.datasets[0].data = [totalKg, remainder];
    co2Chart.update();
  }
}

/**
 * Initialize the charts module.
 */
export async function initCharts() {
  // Initial render: fetch heatmap/trips aggregation from backend
  try {
    const rows = await requestJSON('/api/weather/trips/heatmap');
    updateCharts(rows || []);
  } catch (e) {
    updateCharts([]);
  }
}

/**
 * Update the charts with new heatmap data (called by coordinator).
 */
export async function updateChartsData(heatmapData) {
  if (typeof heatmapData === 'undefined') {
    try {
      const rows = await requestJSON('/api/weather/trips/heatmap');
      updateCharts(rows || []);
      return;
    } catch (e) {
      updateCharts([]);
      return;
    }
  }
  updateCharts(heatmapData);
}