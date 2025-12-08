import { useEffect, useState } from 'react'
import { Line, Pie } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
)

interface TokenUsageData {
  period: string
  total_tokens: number
  input_tokens: number
  output_tokens: number
  total_cost_usd: number
  input_cost_usd: number
  output_cost_usd: number
  api_calls_count: number
  avg_tokens_per_call: number
  avg_response_time_ms: number
  breakdown_by_model: Record<string, { tokens: number; cost: number; calls: number }>
  breakdown_by_purpose: Record<string, { tokens: number; cost: number; calls: number }>
}

interface HistoryDataPoint {
  date: string
  tokens: number
  cost: number
  calls: number
}

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export function TokenUsage() {
  const [usage, setUsage] = useState<TokenUsageData | null>(null)
  const [history, setHistory] = useState<HistoryDataPoint[]>([])
  const [period, setPeriod] = useState<string>('today')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Budget configurabili (TODO: prenderli da .env o config)
  const DAILY_BUDGET = 5.0
  const MONTHLY_BUDGET = 100.0

  const fetchData = async () => {
    setLoading(true)
    setError(null)

    try {
      const [usageRes, historyRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/token-usage?period=${period}`),
        fetch(`${API_BASE_URL}/api/token-usage/history?days=7`),
      ])

      if (!usageRes.ok) throw new Error('Errore nel caricamento usage')
      if (!historyRes.ok) throw new Error('Errore nel caricamento history')

      const [usageData, historyData] = await Promise.all([
        usageRes.json(),
        historyRes.json(),
      ])

      setUsage(usageData)
      setHistory(historyData.data || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore sconosciuto')
      console.error('Errore caricamento token usage:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    // Auto-refresh ogni 60 secondi
    const interval = setInterval(fetchData, 60000)
    return () => clearInterval(interval)
  }, [period])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[200px]">
        <p className="text-sm text-muted-foreground">Caricamento statistiche token...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[200px]">
        <div className="text-center">
          <p className="text-red-500 text-sm mb-2">Errore: {error}</p>
          <button
            onClick={fetchData}
            className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Riprova
          </button>
        </div>
      </div>
    )
  }

  if (!usage) return null

  // Calcola percentuale del budget
  const currentCost = period === 'today' ? usage.total_cost_usd : 0
  const budget = period === 'today' ? DAILY_BUDGET : MONTHLY_BUDGET
  const budgetPercentage = (currentCost / budget) * 100
  const budgetColor =
    budgetPercentage < 50 ? 'text-green-600' :
    budgetPercentage < 80 ? 'text-yellow-600' :
    'text-red-600'

  // Chart data per breakdown modelli (Pie)
  const modelData = {
    labels: Object.keys(usage.breakdown_by_model),
    datasets: [
      {
        data: Object.values(usage.breakdown_by_model).map((m) => m.cost),
        backgroundColor: [
          'rgba(59, 130, 246, 0.8)',  // blue
          'rgba(16, 185, 129, 0.8)',   // green
          'rgba(245, 158, 11, 0.8)',   // yellow
          'rgba(239, 68, 68, 0.8)',    // red
          'rgba(139, 92, 246, 0.8)',   // purple
        ],
        borderColor: [
          'rgb(59, 130, 246)',
          'rgb(16, 185, 129)',
          'rgb(245, 158, 11)',
          'rgb(239, 68, 68)',
          'rgb(139, 92, 246)',
        ],
        borderWidth: 1,
      },
    ],
  }

  // Chart data per Costi (Line)
  const costChartData = {
    labels: history.map((h) => new Date(h.date).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' })),
    datasets: [
      {
        label: 'Costo ($)',
        data: history.map((h) => h.cost),
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        borderWidth: 2,
        pointRadius: 3,
        tension: 0.3,
      },
    ],
  }

  // Chart data per Token (Line)
  const tokenChartData = {
    labels: history.map((h) => new Date(h.date).toLocaleDateString('it-IT', { day: '2-digit', month: '2-digit' })),
    datasets: [
      {
        label: 'Token (K)',
        data: history.map((h) => h.tokens / 1000),
        borderColor: 'rgb(16, 185, 129)',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        borderWidth: 2,
        pointRadius: 3,
        tension: 0.3,
      },
    ],
  }

  const commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: {
      mode: 'index' as const,
      intersect: false,
    },
    plugins: {
      legend: {
        display: true,
        position: 'top' as const,
        labels: { font: { size: 10 }, boxWidth: 20 },
      },
    },
    scales: {
      x: {
        ticks: { font: { size: 10 } },
        grid: { display: false },
      },
    },
  }

  const costOptions = {
    ...commonOptions,
    plugins: {
      ...commonOptions.plugins,
      tooltip: {
        callbacks: {
          label: function (context: any) {
            let label = context.dataset.label || ''
            if (label) label += ': '
            if (context.parsed.y !== null) {
              label += '$' + context.parsed.y.toFixed(4)
            }
            return label
          },
        },
      },
    },
    scales: {
      ...commonOptions.scales,
      y: {
        type: 'linear' as const,
        display: true,
        ticks: {
          font: { size: 10 },
          callback: function (value: any) {
            return '$' + value
          },
        },
        grid: { color: 'rgba(148, 163, 184, 0.2)' },
      },
    },
  }

  const tokenOptions = {
    ...commonOptions,
    plugins: {
      ...commonOptions.plugins,
      tooltip: {
        callbacks: {
          label: function (context: any) {
            let label = context.dataset.label || ''
            if (label) label += ': '
            if (context.parsed.y !== null) {
              label += context.parsed.y.toFixed(1) + 'K'
            }
            return label
          },
        },
      },
    },
    scales: {
      ...commonOptions.scales,
      y: {
        type: 'linear' as const,
        display: true,
        ticks: {
          font: { size: 10 },
          callback: function (value: any) {
            return value + 'K'
          },
        },
        grid: { color: 'rgba(148, 163, 184, 0.2)' },
      },
    },
  }

  const pieOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: true,
        position: 'right' as const,
        labels: { font: { size: 10 }, boxWidth: 15 },
      },
      tooltip: {
        callbacks: {
          label: function (context: any) {
            const label = context.label || ''
            const value = context.parsed || 0
            const total = context.dataset.data.reduce((a: number, b: number) => a + b, 0)
            const percentage = ((value / total) * 100).toFixed(1)
            return `${label}: $${value.toFixed(4)} (${percentage}%)`
          },
        },
      },
    },
  }

  return (
    <div className="space-y-6">
      {/* Header con selettore periodo */}
      <div className="bg-gradient-to-r from-cyan-50 to-blue-50 rounded-xl border-2 border-cyan-200 p-5 shadow-sm">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-xl bg-cyan-600 flex items-center justify-center shadow-md">
              <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Consumo Token LLM</h2>
              <p className="text-sm text-cyan-700">Monitoraggio usage e costi API</p>
            </div>
          </div>
          <div className="flex gap-2 flex-wrap">
            {['today', 'week', 'month', 'all'].map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-4 py-2 text-xs font-bold rounded-lg border-2 transition-all duration-200 ${
                  period === p
                    ? 'bg-cyan-600 text-white border-cyan-600 shadow-md'
                    : 'bg-white text-gray-700 border-cyan-200 hover:border-cyan-500'
                }`}
              >
                {p === 'today' ? 'Oggi' : p === 'week' ? 'Settimana' : p === 'month' ? 'Mese' : 'Tutto'}
              </button>
            ))}
            <button
              onClick={fetchData}
              className="px-4 py-2 text-xs rounded-lg border-2 border-cyan-200 bg-white text-cyan-700 hover:bg-cyan-50 hover:border-cyan-500 transition-all"
              title="Aggiorna dati"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Statistiche principali */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="p-3 rounded-lg border border-gray-200 bg-white">
          <p className="text-xs text-muted-foreground mb-1">Token Totali</p>
          <p className="text-lg sm:text-xl font-bold text-gray-900">{usage.total_tokens.toLocaleString()}</p>
          <p className="text-xs text-muted-foreground mt-1">{usage.api_calls_count} chiamate</p>
        </div>

        <div className="p-3 rounded-lg border border-gray-200 bg-white">
          <p className="text-xs text-muted-foreground mb-1">Costo Totale</p>
          <p className={`text-lg sm:text-xl font-bold ${budgetColor}`}>${usage.total_cost_usd.toFixed(4)}</p>
          {period === 'today' && (
            <p className="text-xs text-muted-foreground mt-1">{budgetPercentage.toFixed(1)}% del budget</p>
          )}
        </div>

        <div className="p-3 rounded-lg border border-gray-200 bg-white">
          <p className="text-xs text-muted-foreground mb-1">Media/Chiamata</p>
          <p className="text-lg sm:text-xl font-bold text-gray-900">
            {Math.round(usage.avg_tokens_per_call).toLocaleString()}
          </p>
          <p className="text-xs text-muted-foreground mt-1">token</p>
        </div>

        <div className="p-3 rounded-lg border border-gray-200 bg-white">
          <p className="text-xs text-muted-foreground mb-1">Tempo Risposta</p>
          <p className="text-lg sm:text-xl font-bold text-gray-900">{Math.round(usage.avg_response_time_ms)}ms</p>
          <p className="text-xs text-muted-foreground mt-1">medio</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Breakdown per modello */}
        <div className="p-4 rounded-lg border border-gray-200 bg-white">
          <h3 className="text-sm font-semibold mb-3">Costi per Modello</h3>
          {Object.keys(usage.breakdown_by_model).length > 0 ? (
            <div className="h-[200px] sm:h-[250px]">
              <Pie data={modelData} options={pieOptions} />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">Nessun dato disponibile</p>
          )}
        </div>

        {/* Trend Costi */}
        <div className="p-4 rounded-lg border border-gray-200 bg-white">
          <h3 className="text-sm font-semibold mb-3">Trend Costi (7gg)</h3>
          {history.length > 0 ? (
            <div className="h-[200px] sm:h-[250px]">
              <Line data={costChartData} options={costOptions} />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">Nessuno storico disponibile</p>
          )}
        </div>

        {/* Trend Token */}
        <div className="p-4 rounded-lg border border-gray-200 bg-white lg:col-span-2">
          <h3 className="text-sm font-semibold mb-3">Trend Token (7gg)</h3>
          {history.length > 0 ? (
            <div className="h-[200px] sm:h-[250px]">
              <Line data={tokenChartData} options={tokenOptions} />
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">Nessuno storico disponibile</p>
          )}
        </div>
      </div>

      {/* Breakdown dettagliato */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Per modello */}
        <div className="p-4 rounded-lg border border-gray-200 bg-white">
          <h3 className="text-sm font-semibold mb-3">Dettaglio Modelli</h3>
          <div className="space-y-2">
            {Object.entries(usage.breakdown_by_model).map(([model, data]) => (
              <div key={model} className="flex justify-between items-center text-xs border-b border-gray-100 pb-2">
                <span className="font-medium">{model}</span>
                <div className="text-right">
                  <span className="text-blue-600 font-semibold">${data.cost.toFixed(4)}</span>
                  <span className="text-muted-foreground ml-2">({data.tokens.toLocaleString()} tok)</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Per purpose */}
        <div className="p-4 rounded-lg border border-gray-200 bg-white">
          <h3 className="text-sm font-semibold mb-3">Dettaglio per Scopo</h3>
          <div className="space-y-2">
            {Object.entries(usage.breakdown_by_purpose).map(([purpose, data]) => (
              <div key={purpose} className="flex justify-between items-center text-xs border-b border-gray-100 pb-2">
                <span className="font-medium capitalize">{purpose.replace('_', ' ')}</span>
                <div className="text-right">
                  <span className="text-blue-600 font-semibold">${data.cost.toFixed(4)}</span>
                  <span className="text-muted-foreground ml-2">({data.calls} calls)</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
