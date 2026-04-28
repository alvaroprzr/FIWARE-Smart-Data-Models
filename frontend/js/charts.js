// TODO: connect the chart to historical and predictive availability datasets.

export function initializeCharts(canvasId = 'availability-chart') {
  const canvas = document.getElementById(canvasId);
  if (!canvas || typeof window.Chart === 'undefined') {
    return null;
  }

  return new window.Chart(canvas, {
    type: 'line',
    data: {
      labels: ['Ahora', '+30m', '+60m'],
      datasets: [
        {
          label: 'Bicis disponibles',
          data: [6, 7, 5],
          borderColor: '#30d5c8',
          backgroundColor: 'rgba(48, 213, 200, 0.15)',
          tension: 0.35,
          fill: true,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          labels: {
            color: '#f5f7fb',
          },
        },
      },
      scales: {
        x: {
          ticks: {
            color: '#aac0da',
          },
          grid: {
            color: 'rgba(255, 255, 255, 0.08)',
          },
        },
        y: {
          beginAtZero: true,
          ticks: {
            color: '#aac0da',
          },
          grid: {
            color: 'rgba(255, 255, 255, 0.08)',
          },
        },
      },
    },
  });
}