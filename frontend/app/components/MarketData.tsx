import { useEffect, useState } from 'react'

interface MarketDataSnapshot {
  timestamp: string
  symbol: string
  global_market: {
    average_price: number
    min_price: number
    max_price: number
    price_spread_pct: number
    total_volume_global: number
    average_funding_rate: number
    sources_count: number
    hyperliquid_deviation_pct: number | null
    is_hyperliquid_premium: boolean | null
  }
  hyperliquid: any
  providers: Record<string, any>
}

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export function MarketData({ symbol = 'BTC' }: { symbol?: string }) {
  const [data, setData] = useState<MarketDataSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/api/market-data/aggregate?symbol=${symbol}`)
      if (!res.ok) throw new Error('Failed to fetch market data')
      setData(await res.json())
      setError(null)
    } catch (err) {
      console.error('Error fetching market data:', err)
      setError('Dati non disponibili')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 60000) // 1 min refresh
    return () => clearInterval(interval)
  }, [symbol])

  if (loading && !data) return <div className="p-4 text-center text-gray-500 text-xs">Caricamento dati mercato...</div>
  if (error) return (
    <div className="p-4 text-center text-red-500 text-xs">
      {error}
      <button onClick={fetchData} className="ml-2 text-blue-500 hover:underline">Riprova</button>
    </div>
  )
  if (!data) return null

  const { global_market } = data

  return (
    <div className="bg-white border rounded-lg p-4 shadow-sm">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-bold text-gray-800 flex items-center gap-2">
          <span className="text-xl">📊</span>
          Dati Aggregati ({symbol})
        </h3>
        <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">Sources: {global_market.sources_count}</span>
            <button 
                onClick={fetchData} 
                className="p-1 hover:bg-gray-100 rounded-full text-gray-400 hover:text-gray-600 transition-colors"
                title="Aggiorna dati"
            >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            </button>
        </div>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-3 bg-gray-50 rounded border border-gray-100">
          <div className="text-xs text-gray-500 uppercase mb-1">Avg Price</div>
          <div className="font-mono font-bold text-gray-900">${global_market.average_price.toLocaleString(undefined, { maximumFractionDigits: 2 })}</div>
        </div>

        <div className="p-3 bg-gray-50 rounded border border-gray-100">
          <div className="text-xs text-gray-500 uppercase mb-1">Spread</div>
          <div className="font-mono font-bold text-gray-900">{global_market.price_spread_pct.toFixed(3)}%</div>
        </div>

        <div className="p-3 bg-gray-50 rounded border border-gray-100">
          <div className="text-xs text-gray-500 uppercase mb-1">Avg Funding</div>
          <div className={`font-mono font-bold ${global_market.average_funding_rate > 0 ? 'text-green-600' : 'text-red-600'}`}>
            {global_market.average_funding_rate.toFixed(6)}%
          </div>
        </div>

        <div className="p-3 bg-gray-50 rounded border border-gray-100">
            <div className="text-xs text-gray-500 uppercase mb-1">HL Deviation</div>
             <div className={`font-mono font-bold ${
                (global_market.hyperliquid_deviation_pct || 0) > 0 ? 'text-amber-600' : 'text-blue-600'
             }`}>
                {global_market.hyperliquid_deviation_pct ? `${global_market.hyperliquid_deviation_pct > 0 ? '+' : ''}${global_market.hyperliquid_deviation_pct.toFixed(4)}%` : '-'}
             </div>
        </div>
      </div>
    </div>
  )
}
