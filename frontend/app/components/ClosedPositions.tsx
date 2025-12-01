import { useEffect, useState } from 'react'
import { format } from 'date-fns'

interface Trade {
  id: number
  created_at: string
  closed_at: string | null
  trade_type: string
  symbol: string
  direction: string
  entry_price: number
  exit_price: number | null
  size: number
  leverage: number
  pnl_usd: number | null
  pnl_pct: number | null
  duration_minutes: number | null
  exit_reason: string | null
  status: string
}

interface TradeStats {
  total_trades: number
  winning_trades: number
  losing_trades: number
  win_rate: number
  total_pnl: number
  avg_pnl: number
}

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export function ClosedPositions() {
  const [trades, setTrades] = useState<Trade[]>([])
  const [stats, setStats] = useState<TradeStats | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    setLoading(true)
    try {
      const [statsRes, tradesRes] = await Promise.all([
        fetch(`${API_BASE_URL}/api/trades/stats?days=30`),
        fetch(`${API_BASE_URL}/api/trades?status=closed&limit=6`)
      ])

      if (statsRes.ok) {
        setStats(await statsRes.json())
      }
      if (tradesRes.ok) {
        setTrades(await tradesRes.json())
      }
    } catch (error) {
      console.error('Error fetching closed positions data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  if (loading && !stats) {
    return <div className="p-4 text-center text-gray-500">Caricamento storico...</div>
  }

  return (
    <div className="flex flex-col gap-4 relative">
      {/* Refresh Button Overlay (Top Right of container, absolute positioned relative to this wrapper if needed, but let's put it in a header if one existed, or just floating) */}
       <div className="absolute top-[-40px] right-0 flex gap-2">
             {/* This component is usually inside a card with a header. 
                 Since the header is in Dashboard.tsx, we can't easily put a button there from here without props.
                 Instead, let's just put a small refresh text/icon at the top right of this content area.
             */}
        </div>
        
        {/* Actually, the header is outside. Let's put a small refresh row or just assume the auto-refresh is enough?
            The user asked for individual update capability. 
            Let's add a small "Refresh" text button at the top right of the win rate card.
        */}

      {/* Win Rate Section */}
      {stats && (
        <div className="bg-white border rounded-lg p-4 shadow-sm relative group">
           <button 
                onClick={fetchData} 
                className="absolute top-2 right-2 p-1.5 bg-gray-50 hover:bg-gray-100 rounded-full text-gray-400 hover:text-blue-600 transition-colors opacity-0 group-hover:opacity-100"
                title="Aggiorna statistiche"
            >
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
           </button>

           <div className="flex justify-between items-end mb-2">
             <span className="text-sm font-medium text-gray-500 uppercase tracking-wider">Win Rate</span>
             <span className="text-2xl font-bold text-gray-900">{stats.win_rate.toFixed(1)}%</span>
           </div>
           
           <div className="w-full bg-gray-100 rounded-full h-2.5 mb-3 overflow-hidden">
             <div 
               className="bg-green-500 h-2.5 rounded-full transition-all duration-500" 
               style={{ width: `${stats.win_rate}%` }}
             ></div>
           </div>
           
           <div className="flex justify-between text-sm">
             <div className="flex items-center gap-1.5">
               <span className="w-2 h-2 rounded-full bg-green-500"></span>
               <span className="font-medium text-green-700">{stats.winning_trades} Wins</span>
             </div>
             <div className="flex items-center gap-1.5">
               <span className="w-2 h-2 rounded-full bg-red-500"></span>
               <span className="font-medium text-red-700">{stats.losing_trades} Losses</span>
             </div>
           </div>
        </div>
      )}

      {/* Recent Trades Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {trades.map(trade => (
          <div key={trade.id} className="bg-white border rounded-lg p-3 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between">
            <div className="flex justify-between items-start mb-3">
              <div>
                <div className="font-bold text-lg text-gray-900">{trade.symbol}</div>
              </div>
              <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${
                trade.direction === 'long' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
              }`}>
                {trade.direction}
              </span>
            </div>
            
            <div className="grid grid-cols-2 gap-x-2 gap-y-1 text-sm mb-3">
              <div className="text-gray-500 text-xs">Entry</div>
              <div className="text-right font-mono text-gray-700">${trade.entry_price?.toFixed(trade.entry_price < 1 ? 4 : 2)}</div>
              
              <div className="text-gray-500 text-xs">Exit</div>
              <div className="text-right font-mono text-gray-700">${trade.exit_price?.toFixed(trade.exit_price < 1 ? 4 : 2)}</div>
            </div>
            
            <div className="flex justify-between items-end pt-2 border-t border-gray-100">
              <div className="text-xs text-gray-400">
                {trade.closed_at ? format(new Date(trade.closed_at), 'dd/MM HH:mm') : '-'}
              </div>
              <div className={`font-bold ${
                (trade.pnl_usd || 0) >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                {(trade.pnl_usd || 0) >= 0 ? '+' : ''}{(trade.pnl_usd || 0).toFixed(2)} $
              </div>
            </div>
          </div>
        ))}
        {trades.length === 0 && (
          <div className="col-span-full text-center py-4 text-gray-500 text-sm">
            Nessuna posizione chiusa recente.
          </div>
        )}
      </div>
    </div>
  )
}
