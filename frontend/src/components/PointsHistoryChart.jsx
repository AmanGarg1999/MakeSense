import React from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler);

export default function PointsHistoryChart({ data = [] }) {
  if (!data || data.length === 0) {
    return <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem', padding: '1.5rem 0' }}>No points logged yet. Take a quiz or complete a lesson to track engagement!</p>;
  }

  // Reverse so chronological left to right
  const sorted = [...data].reverse();
  const labels = sorted.map(item => {
    if (!item.created_at) return '';
    const d = new Date(item.created_at);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  });
  const points = sorted.map(item => item.points || 0);

  const chartData = {
    labels: labels.length > 0 ? labels : ['Start'],
    datasets: [
      {
        label: 'Points Earned',
        data: points.length > 0 ? points : [0],
        borderColor: '#4f46e5',
        backgroundColor: 'rgba(79, 70, 229, 0.12)',
        tension: 0.35,
        fill: true,
        pointBackgroundColor: '#4f46e5',
        pointRadius: 4,
        pointHoverRadius: 6,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0f172a',
        titleFont: { family: 'Plus Jakarta Sans', size: 12, weight: 'bold' },
        bodyFont: { family: 'Plus Jakarta Sans', size: 12 },
        padding: 10,
        cornerRadius: 8,
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { font: { family: 'Plus Jakarta Sans', size: 11 }, color: '#64748b' },
      },
      y: {
        beginAtZero: true,
        grid: { color: 'rgba(226, 232, 240, 0.6)' },
        ticks: { font: { family: 'Plus Jakarta Sans', size: 11 }, color: '#64748b' },
      },
    },
  };

  return (
    <div style={{ height: 240, width: '100%', position: 'relative' }}>
      <Line data={chartData} options={options} />
    </div>
  );
}
