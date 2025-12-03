import { useEffect, useRef } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import { Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

interface BalancePoint {
  timestamp: string
  balance_usd: number
}

interface EquityCurveProps {
  data: BalancePoint[]
}

export function EquityCurve({ data }: EquityCurveProps) {
  const chartRef = useRef<ChartJS<'line'>>(null)

  if (!data || data.length === 0) {
    return (
      <div className="h-[250px] sm:h-[300px] lg:h-[380px] flex items-center justify-center text-muted-foreground">
        <p className="text-sm">Nessun dato di saldo trovato.</p>
      </div>
    )
  }

  const labels = data.map((p) => p.timestamp)
  const values = data.map((p) => p.balance_usd)
  const initialValue = values.length > 0 ? values[0] : null

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Saldo USD',
        data: values,
        borderColor: '#2563eb',
        backgroundColor: 'rgba(37, 99, 235, 0.08)',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.25,
        fill: true,
      },
      ...(initialValue !== null
        ? [
            {
              label: 'Valore iniziale',
              data: Array(values.length).fill(initialValue),
              borderColor: '#9ca3af',
              borderDash: [5, 4],
              borderWidth: 1,
              pointRadius: 0,
              tension: 0,
            },
          ]
        : []),
    ],
  }

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    layout: {
      padding: {
        left: 0,
        right: 5,
        top: 5,
        bottom: 0,
      },
    },
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        display: true,
        labels: {
          color: '#374151',
          font: { size: 10 },
          boxWidth: 30,
        },
      },
      tooltip: {
        callbacks: {
          label: function (context: any) {
            const value = context.parsed.y
            return 'Saldo: $' + value.toFixed(2)
          },
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: '#4b5563',
          font: { size: 10 },
          maxTicksLimit: window.innerWidth < 640 ? 4 : 6,
          maxRotation: 45,
          minRotation: 0,
          callback: function (value: any, index: number, ticks: any[]) {
            const raw = labels[index]
            const d = new Date(raw)
            if (isNaN(d.getTime())) return raw
            return d.toLocaleString('it-IT', {
              day: '2-digit',
              month: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
            })
          },
        },
        grid: { display: false },
      },
      y: {
        ticks: {
          color: '#4b5563',
          font: { size: 10 },
          callback: function (value: any) {
            return '$' + value
          },
        },
        grid: {
          color: 'rgba(148, 163, 184, 0.3)',
        },
      },
    },
  }

  return (
    <div className="h-[250px] sm:h-[300px] lg:h-[380px] p-1 sm:p-2 pb-2 sm:pb-3">
      <Line ref={chartRef} data={chartData} options={options} />
    </div>
  )
}





