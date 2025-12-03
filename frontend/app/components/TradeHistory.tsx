import { useState, useEffect } from 'react'
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

// Use relative path for API to work with proxy or same domain
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export function TradeHistory() {
    const [trades, setTrades] = useState<Trade[]>([])
    const [stats, setStats] = useState<TradeStats | null>(null)
    const [filter, setFilter] = useState({
        symbol: 'all',
        direction: 'all',
        status: 'all',
        dateFrom: '',
        dateTo: ''
    })
    const [page, setPage] = useState(1)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchTrades()
        fetchStats()
    }, [filter, page])

    const fetchTrades = async () => {
        setLoading(true)
        const params = new URLSearchParams({
            page: page.toString(),
            limit: '50',
            ...(filter.symbol !== 'all' && { symbol: filter.symbol }),
            ...(filter.direction !== 'all' && { direction: filter.direction }),
            ...(filter.status !== 'all' && { status: filter.status }),
            ...(filter.dateFrom && { date_from: filter.dateFrom }),
            ...(filter.dateTo && { date_to: filter.dateTo })
        })

        try {
            const res = await fetch(`${API_BASE_URL}/api/trades?${params}`)
            if (!res.ok) throw new Error('Failed to fetch trades')
            const data = await res.json()
            setTrades(data) // API returns list directly based on python code in main.py
        } catch (error) {
            console.error('Error fetching trades:', error)
        } finally {
            setLoading(false)
        }
    }

    const fetchStats = async () => {
        try {
            const params = new URLSearchParams()
            if (filter.symbol !== 'all') params.append('symbol', filter.symbol)

            const res = await fetch(`${API_BASE_URL}/api/trades/stats?${params}`)
            if (!res.ok) throw new Error('Failed to fetch stats')
            const data = await res.json()
            setStats(data)
        } catch (error) {
            console.error('Error fetching stats:', error)
        }
    }

    return (
        <div className="space-y-6">
            <h2 className="text-2xl font-bold text-gray-800">Trade History</h2>

            {/* Stats Cards */}
            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                    <StatCard label="Total Trades" value={stats.total_trades} />
                    <StatCard
                        label="Win Rate"
                        value={`${stats.win_rate}%`}
                        color={stats.win_rate >= 50 ? 'green' : 'red'}
                    />
                    <StatCard
                        label="Total P&L"
                        value={`$${stats.total_pnl.toFixed(2)}`}
                        color={stats.total_pnl >= 0 ? 'green' : 'red'}
                    />
                    <StatCard label="Winning Trades" value={stats.winning_trades} color="green" />
                    <StatCard label="Losing Trades" value={stats.losing_trades} color="red" />
                    <StatCard
                        label="Avg P&L"
                        value={`$${stats.avg_pnl.toFixed(2)}`}
                        color={stats.avg_pnl >= 0 ? 'green' : 'red'}
                    />
                </div>
            )}

            {/* Filters */}
            <div className="flex flex-wrap gap-3 p-4 bg-white rounded-lg border shadow-sm">
                <select
                    value={filter.symbol}
                    onChange={e => { setFilter({ ...filter, symbol: e.target.value }); setPage(1); }}
                    className="px-3 py-2 text-sm border rounded-md focus:ring-2 focus:ring-blue-500 outline-none"
                >
                    <option value="all">All Symbols</option>
                    <option value="BTC">BTC</option>
                    <option value="ETH">ETH</option>
                    <option value="SOL">SOL</option>
                </select>

                <select
                    value={filter.direction}
                    onChange={e => { setFilter({ ...filter, direction: e.target.value }); setPage(1); }}
                    className="px-3 py-2 text-sm border rounded-md focus:ring-2 focus:ring-blue-500 outline-none"
                >
                    <option value="all">All Directions</option>
                    <option value="long">Long Only</option>
                    <option value="short">Short Only</option>
                </select>

                <select
                    value={filter.status}
                    onChange={e => { setFilter({ ...filter, status: e.target.value }); setPage(1); }}
                    className="px-3 py-2 text-sm border rounded-md focus:ring-2 focus:ring-blue-500 outline-none"
                >
                    <option value="all">All Statuses</option>
                    <option value="open">Open</option>
                    <option value="closed">Closed</option>
                </select>

                <input
                    type="date"
                    value={filter.dateFrom}
                    onChange={e => { setFilter({ ...filter, dateFrom: e.target.value }); setPage(1); }}
                    className="px-3 py-2 text-sm border rounded-md focus:ring-2 focus:ring-blue-500 outline-none"
                    placeholder="From Date"
                />

                <input
                    type="date"
                    value={filter.dateTo}
                    onChange={e => { setFilter({ ...filter, dateTo: e.target.value }); setPage(1); }}
                    className="px-3 py-2 text-sm border rounded-md focus:ring-2 focus:ring-blue-500 outline-none"
                    placeholder="To Date"
                />
            </div>

            {/* Trade Table */}
            <div className="bg-white rounded-lg border shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-gray-50 text-gray-600 font-medium border-b">
                            <tr>
                                <th className="px-4 py-3">Date</th>
                                <th className="px-4 py-3">Symbol</th>
                                <th className="px-4 py-3">Dir</th>
                                <th className="px-4 py-3 text-right">Entry</th>
                                <th className="px-4 py-3 text-right">Exit</th>
                                <th className="px-4 py-3 text-right">Size</th>
                                <th className="px-4 py-3 text-right">Lev</th>
                                <th className="px-4 py-3 text-right">P&L ($)</th>
                                <th className="px-4 py-3 text-right">P&L (%)</th>
                                <th className="px-4 py-3">Duration</th>
                                <th className="px-4 py-3">Exit Reason</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-100">
                            {loading ? (
                                <tr>
                                    <td colSpan={11} className="px-4 py-8 text-center text-gray-500">
                                        Loading trades...
                                    </td>
                                </tr>
                            ) : trades.length === 0 ? (
                                <tr>
                                    <td colSpan={11} className="px-4 py-8 text-center text-gray-500">
                                        No trades found.
                                    </td>
                                </tr>
                            ) : (
                                trades.map(trade => (
                                    <tr key={trade.id} className="hover:bg-gray-50 transition-colors">
                                        <td className="px-4 py-3 text-xs text-gray-500 whitespace-nowrap">
                                            {format(new Date(trade.created_at), 'dd/MM HH:mm')}
                                        </td>
                                        <td className="px-4 py-3 font-medium">{trade.symbol}</td>
                                        <td className={`px-4 py-3 font-semibold ${trade.direction === 'long' ? 'text-green-600' : 'text-red-600'}`}>
                                            {trade.direction.toUpperCase()}
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-gray-600">
                                            ${trade.entry_price?.toFixed(2)}
                                        </td>
                                        <td className="px-4 py-3 text-right font-mono text-gray-600">
                                            {trade.exit_price ? `$${trade.exit_price.toFixed(2)}` : '-'}
                                        </td>
                                        <td className="px-4 py-3 text-right text-gray-600">{trade.size}</td>
                                        <td className="px-4 py-3 text-right text-gray-500">{trade.leverage}x</td>
                                        <td className={`px-4 py-3 text-right font-medium ${trade.pnl_usd === null ? 'text-gray-400' :
                                                trade.pnl_usd >= 0 ? 'text-green-600' : 'text-red-600'
                                            }`}>
                                            {trade.pnl_usd !== null ? `$${trade.pnl_usd.toFixed(2)}` : '-'}
                                        </td>
                                        <td className={`px-4 py-3 text-right ${trade.pnl_pct === null ? 'text-gray-400' :
                                                trade.pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'
                                            }`}>
                                            {trade.pnl_pct !== null ? `${trade.pnl_pct.toFixed(2)}%` : '-'}
                                        </td>
                                        <td className="px-4 py-3 text-xs text-gray-500">
                                            {trade.duration_minutes ? `${Math.round(trade.duration_minutes)}m` : '-'}
                                        </td>
                                        <td className="px-4 py-3">
                                            <span className={`px-2 py-1 text-xs rounded-full ${trade.exit_reason === 'take_profit' ? 'bg-green-100 text-green-700' :
                                                    trade.exit_reason === 'stop_loss' ? 'bg-red-100 text-red-700' :
                                                        trade.status === 'open' ? 'bg-blue-100 text-blue-700' :
                                                            'bg-gray-100 text-gray-700'
                                                }`}>
                                                {trade.exit_reason || trade.status}
                                            </span>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* Pagination */}
            <div className="flex justify-center gap-3 items-center">
                <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1 || loading}
                    className="px-4 py-2 text-sm bg-white border rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    ← Previous
                </button>
                <span className="px-2 text-sm text-gray-600">Page {page}</span>
                <button
                    onClick={() => setPage(p => p + 1)}
                    disabled={trades.length < 50 || loading}
                    className="px-4 py-2 text-sm bg-white border rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Next →
                </button>
            </div>
        </div>
    )
}

function StatCard({ label, value, color }: { label: string, value: string | number, color?: string }) {
    const colorClass = color === 'green' ? 'text-green-600' :
        color === 'red' ? 'text-red-600' : 'text-gray-900'

    return (
        <div className="p-4 bg-white rounded-lg border shadow-sm">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">{label}</p>
            <p className={`text-xl font-bold ${colorClass}`}>{value}</p>
        </div>
    )
}




