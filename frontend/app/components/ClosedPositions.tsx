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
    const [loadingMore, setLoadingMore] = useState(false)
    const [hasMore, setHasMore] = useState(true)
    const [page, setPage] = useState(1)
    const [directionFilter, setDirectionFilter] = useState<'all' | 'long' | 'short'>('all')
    const [profitFilter, setProfitFilter] = useState<'all' | 'profit' | 'loss'>('all')
    const LIMIT = 6

    const fetchData = async (reset: boolean = false) => {
        if (reset) {
            setLoading(true)
            setPage(1)
            setTrades([])
        } else {
            setLoadingMore(true)
        }

        try {
            // If filters are active, load all trades (up to 500)
            const hasFiltersActive = directionFilter !== 'all' || profitFilter !== 'all'
            const limit = hasFiltersActive ? 500 : LIMIT
            const currentPage = reset ? 1 : page

            let tradesUrl = `${API_BASE_URL}/api/trades?status=closed&limit=${limit}&page=${currentPage}`

            if (directionFilter !== 'all') {
                tradesUrl += `&direction=${directionFilter}`
            }

            const [statsRes, tradesRes] = await Promise.all([
                fetch(`${API_BASE_URL}/api/trades/stats?days=30`),
                fetch(tradesUrl)
            ])

            if (statsRes.ok) {
                setStats(await statsRes.json())
            }
            if (tradesRes.ok) {
                const newTrades = await tradesRes.json()

                // Apply profit/loss filter on client side
                let filteredTrades = newTrades
                if (profitFilter !== 'all') {
                    filteredTrades = newTrades.filter((t: Trade) => {
                        if (profitFilter === 'profit') return (t.pnl_usd || 0) > 0
                        if (profitFilter === 'loss') return (t.pnl_usd || 0) < 0
                        return true
                    })
                }

                if (reset) {
                    setTrades(filteredTrades)
                } else {
                    setTrades(prev => [...prev, ...filteredTrades])
                }

                // Only show "load more" if no filters are active and we got a full page
                setHasMore(!hasFiltersActive && newTrades.length === limit)
            }
        } catch (error) {
            console.error('Error fetching closed positions data:', error)
        } finally {
            setLoading(false)
            setLoadingMore(false)
        }
    }

    const loadMore = () => {
        setPage(prev => prev + 1)
    }

    useEffect(() => {
        fetchData(true)
    }, [directionFilter, profitFilter])

    useEffect(() => {
        if (page > 1) {
            fetchData(false)
        }
    }, [page])

    useEffect(() => {
        // Initial fetch
        fetchData(true)

        // Refresh every 30 seconds
        const interval = setInterval(() => fetchData(true), 30000)
        return () => clearInterval(interval)
    }, [])

    if (loading && !stats) {
        return <div className="p-4 text-center text-gray-500">Caricamento storico...</div>
    }

    return (
        <div className="flex flex-col gap-4 relative">
            {/* Filters Section */}
            <div className="flex flex-wrap gap-3 items-center p-4 bg-gradient-to-r from-emerald-50 to-teal-50 rounded-xl border-2 border-emerald-200 shadow-sm">
                <div className="flex items-center gap-2">
                    <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
                    </svg>
                    <span className="text-sm font-bold text-emerald-700 uppercase">Filtri:</span>
                </div>

                {/* Direction Filter */}
                <div className="flex flex-col gap-1">
                    <label className="text-xs font-bold text-emerald-700 uppercase tracking-wide">Direzione</label>
                    <div className="flex gap-1 bg-white rounded-lg p-1.5 border-2 border-emerald-200 shadow-sm">
                        <button
                            onClick={() => setDirectionFilter('all')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${directionFilter === 'all'
                                ? 'bg-emerald-600 text-white shadow-md'
                                : 'text-gray-600 hover:bg-gray-100'
                                }`}
                        >
                            Tutte
                        </button>
                        <button
                            onClick={() => setDirectionFilter('long')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${directionFilter === 'long'
                                ? 'bg-green-500 text-white shadow-md'
                                : 'text-gray-600 hover:bg-gray-100'
                                }`}
                        >
                            ↗ Long
                        </button>
                        <button
                            onClick={() => setDirectionFilter('short')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${directionFilter === 'short'
                                ? 'bg-red-500 text-white shadow-md'
                                : 'text-gray-600 hover:bg-gray-100'
                                }`}
                        >
                            ↘ Short
                        </button>
                    </div>
                </div>

                {/* Profit/Loss Filter */}
                <div className="flex flex-col gap-1">
                    <label className="text-xs font-bold text-emerald-700 uppercase tracking-wide">Risultato</label>
                    <div className="flex gap-1 bg-white rounded-lg p-1.5 border-2 border-emerald-200 shadow-sm">
                        <button
                            onClick={() => setProfitFilter('all')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${profitFilter === 'all'
                                ? 'bg-emerald-600 text-white shadow-md'
                                : 'text-gray-600 hover:bg-gray-100'
                                }`}
                        >
                            Tutti
                        </button>
                        <button
                            onClick={() => setProfitFilter('profit')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${profitFilter === 'profit'
                                ? 'bg-green-500 text-white shadow-md'
                                : 'text-gray-600 hover:bg-gray-100'
                                }`}
                        >
                            💰 Profitto
                        </button>
                        <button
                            onClick={() => setProfitFilter('loss')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${profitFilter === 'loss'
                                ? 'bg-red-500 text-white shadow-md'
                                : 'text-gray-600 hover:bg-gray-100'
                                }`}
                        >
                            📉 Perdita
                        </button>
                    </div>
                </div>
            </div>

            {/* Win Rate Section */}
            {stats && (
                <div className="bg-gradient-to-br from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl p-5 shadow-md relative group hover:shadow-lg transition-shadow">
                    <button
                        onClick={() => fetchData(true)}
                        className="absolute top-3 right-3 p-2 bg-white hover:bg-green-100 rounded-full text-green-600 hover:text-green-700 transition-all shadow-sm opacity-0 group-hover:opacity-100"
                        title="Aggiorna statistiche"
                    >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                    </button>

                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-12 h-12 rounded-xl bg-green-600 flex items-center justify-center shadow-md">
                            <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <div className="flex-1">
                            <div className="text-xs font-bold text-green-700 uppercase tracking-wider mb-1">Win Rate Complessivo</div>
                            <div className="text-4xl font-bold text-green-900">{stats.win_rate.toFixed(1)}%</div>
                        </div>
                    </div>

                    <div className="w-full bg-green-200 rounded-full h-3 mb-4 overflow-hidden shadow-inner">
                        <div
                            className="bg-gradient-to-r from-green-500 to-emerald-600 h-3 rounded-full transition-all duration-500 shadow-sm"
                            style={{ width: `${stats.win_rate}%` }}
                        ></div>
                    </div>

                    <div className="flex justify-between items-center">
                        <div className="flex items-center gap-2 bg-white/70 px-3 py-2 rounded-lg border border-green-200">
                            <div className="w-3 h-3 rounded-full bg-green-500 shadow-sm"></div>
                            <span className="font-bold text-green-800 text-sm">{stats.winning_trades}</span>
                            <span className="text-xs text-green-600 font-medium">Vittorie</span>
                        </div>
                        <div className="flex items-center gap-2 bg-white/70 px-3 py-2 rounded-lg border border-red-200">
                            <div className="w-3 h-3 rounded-full bg-red-500 shadow-sm"></div>
                            <span className="font-bold text-red-800 text-sm">{stats.losing_trades}</span>
                            <span className="text-xs text-red-600 font-medium">Sconfitte</span>
                        </div>
                    </div>
                </div>
            )}

            {/* Recent Trades Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {trades.map(trade => {
                    const isLong = trade.direction === 'long'
                    const isProfitable = (trade.pnl_usd || 0) >= 0

                    return (
                        <div key={trade.id} className={`bg-gradient-to-br rounded-xl p-4 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 border-2 ${
                            isLong ? 'from-green-50 to-emerald-50 border-green-200' : 'from-red-50 to-rose-50 border-red-200'
                        }`}>
                            <div className="flex justify-between items-start mb-3">
                                <div className="flex items-center gap-2">
                                    <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                                        isLong ? 'bg-green-100' : 'bg-red-100'
                                    }`}>
                                        <svg className={`w-5 h-5 ${isLong ? 'text-green-600' : 'text-red-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            {isLong ? (
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                                            ) : (
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                                            )}
                                        </svg>
                                    </div>
                                    <div>
                                        <div className="font-bold text-xl text-gray-900">{trade.symbol}</div>
                                        <div className="text-xs text-gray-500">ID #{trade.id}</div>
                                    </div>
                                </div>
                                <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase shadow-sm ${
                                    isLong ? 'bg-green-500 text-white' : 'bg-red-500 text-white'
                                }`}>
                                    {isLong ? '↗ LONG' : '↘ SHORT'}
                                </span>
                            </div>

                            <div className="space-y-2 mb-3">
                                <div className="flex items-center justify-between bg-white/70 rounded-lg px-3 py-2 border border-gray-200">
                                    <div className="flex items-center gap-2">
                                        <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                                        </svg>
                                        <span className="text-xs font-medium text-gray-600">Entry</span>
                                    </div>
                                    <span className="font-mono font-bold text-sm text-blue-700">${trade.entry_price?.toFixed(trade.entry_price < 1 ? 4 : 2)}</span>
                                </div>

                                <div className="flex items-center justify-between bg-white/70 rounded-lg px-3 py-2 border border-gray-200">
                                    <div className="flex items-center gap-2">
                                        <svg className="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                                        </svg>
                                        <span className="text-xs font-medium text-gray-600">Exit</span>
                                    </div>
                                    <span className="font-mono font-bold text-sm text-purple-700">${trade.exit_price?.toFixed(trade.exit_price < 1 ? 4 : 2)}</span>
                                </div>
                            </div>

                            <div className={`flex items-center justify-between pt-3 border-t-2 ${
                                isProfitable ? 'border-green-200' : 'border-red-200'
                            }`}>
                                <div className="flex items-center gap-1.5 text-xs text-gray-500">
                                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    {trade.closed_at ? format(new Date(trade.closed_at), 'dd/MM HH:mm') : '-'}
                                </div>
                                <div className="flex items-center gap-1">
                                    <div className={`font-bold text-lg ${isProfitable ? 'text-green-700' : 'text-red-700'}`}>
                                        {isProfitable ? '+' : ''}{(trade.pnl_usd || 0).toFixed(2)} $
                                    </div>
                                    {isProfitable ? (
                                        <svg className="w-4 h-4 text-green-700" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                                        </svg>
                                    ) : (
                                        <svg className="w-4 h-4 text-red-700" fill="currentColor" viewBox="0 0 20 20">
                                            <path fillRule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                        </svg>
                                    )}
                                </div>
                            </div>
                        </div>
                    )
                })}
                {trades.length === 0 && !loading && (
                    <div className="col-span-full bg-gradient-to-br from-gray-50 to-gray-100 rounded-xl border-2 border-dashed border-gray-300 p-8 text-center">
                        <svg className="w-16 h-16 mx-auto mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <p className="text-sm font-medium text-gray-600">Nessuna posizione chiusa trovata</p>
                        <p className="text-xs text-gray-500 mt-1">Prova a modificare i filtri</p>
                    </div>
                )}
            </div>

            {/* Load More Button */}
            {hasMore && trades.length > 0 && (
                <div className="flex justify-center mt-2">
                    <button
                        onClick={loadMore}
                        disabled={loadingMore}
                        className="px-6 py-2.5 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 text-white rounded-lg font-medium transition-colors shadow-sm hover:shadow-md disabled:cursor-not-allowed flex items-center gap-2"
                    >
                        {loadingMore ? (
                            <>
                                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                                Caricamento...
                            </>
                        ) : (
                            <>
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                                Carica altre posizioni
                            </>
                        )}
                    </button>
                </div>
            )}

            {!hasMore && trades.length > 0 && (
                <div className="text-center py-2 text-gray-400 text-sm">
                    Tutte le posizioni sono state caricate
                </div>
            )}
        </div>
    )
}
