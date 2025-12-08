import React, { useEffect, useState } from 'react'

interface TradeResult {
    trade_id: number
    pnl_usd: number | null
    pnl_pct: number | null
    status: string
    exit_reason: string | null
    closed_at: string | null
}

interface BotOperation {
    id: number
    created_at: string
    operation: string
    symbol: string | null
    direction: string | null
    target_portion_of_balance: number | null
    leverage: number | null
    raw_payload: any
    system_prompt: string | null
    trade_result: TradeResult | null
}

interface DecisionData {
    operation: string
    symbol: string
    direction: string
    confidence: number
    reason: string
    trend_info?: string
    cycle_id?: string
    _model_name?: string
    execution_result?: {
        status: string
        reason?: string
    }
}

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export function DecisionHistory() {
    const [history, setHistory] = useState<BotOperation[]>([])
    const [loading, setLoading] = useState(true)
    const [loadingMore, setLoadingMore] = useState(false)
    const [expandedId, setExpandedId] = useState<number | null>(null)
    const [statusFilter, setStatusFilter] = useState<'all' | 'success' | 'blocked' | 'skipped' | 'hold'>('all')
    const [actionFilter, setActionFilter] = useState<'all' | 'open' | 'close' | 'hold'>('all')
    const [tradeFilter, setTradeFilter] = useState<'all' | 'profit' | 'loss'>('all')
    const [displayLimit, setDisplayLimit] = useState(30)
    const [totalAvailable, setTotalAvailable] = useState(0)

    const fetchHistory = async () => {
        try {
            setLoading(true)
            // Always fetch a reasonable amount to check if there's more
            const limit = 500

            const res = await fetch(`${API_BASE_URL}/api/bot-operations?limit=${limit}`)
            if (!res.ok) throw new Error('Failed to fetch history')
            const data = await res.json()
            setHistory(data)
            setTotalAvailable(data.length)
        } catch (e) {
            console.error("Error fetching decision history", e)
        } finally {
            setLoading(false)
        }
    }

    const handleLoadMore = () => {
        setLoadingMore(true)
        // Increase display limit by 30
        setDisplayLimit(prev => prev + 30)
        setTimeout(() => setLoadingMore(false), 300)
    }

    useEffect(() => {
        setDisplayLimit(30) // Reset display limit when filters change
        fetchHistory()
    }, [statusFilter, actionFilter, tradeFilter])

    useEffect(() => {
        fetchHistory()
        // Refresh every 30s
        const interval = setInterval(fetchHistory, 30000)
        return () => clearInterval(interval)
    }, [])

    const parsePayload = (raw: any): DecisionData | null => {
        if (typeof raw === 'string') {
            try {
                return JSON.parse(raw)
            } catch {
                return null
            }
        }
        return raw
    }

    const getConfidenceColor = (conf: number) => {
        if (conf >= 0.8) return 'bg-green-500'
        if (conf >= 0.6) return 'bg-blue-500'
        if (conf >= 0.4) return 'bg-yellow-500'
        return 'bg-gray-300'
    }

    const getOperationBadge = (payload: DecisionData) => {
        const op = payload.operation.toUpperCase()
        if (op === 'HOLD') return <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded text-xs font-bold">HOLD</span>

        const dir = payload.direction?.toUpperCase()
        if (op === 'OPEN') {
            return dir === 'LONG'
                ? <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-bold">LONG</span>
                : <span className="bg-red-100 text-red-700 px-2 py-0.5 rounded text-xs font-bold">SHORT</span>
        }
        if (op === 'CLOSE') return <span className="bg-orange-100 text-orange-700 px-2 py-0.5 rounded text-xs font-bold">CLOSE</span>

        return <span className="bg-gray-100 text-gray-500 px-2 py-0.5 rounded text-xs">{op}</span>
    }

    const getStatusBadge = (payload: DecisionData) => {
        const status = payload.execution_result?.status || 'unknown'

        if (status === 'blocked') return <span className="bg-red-100 text-red-700 px-2 py-0.5 rounded text-xs font-bold flex items-center justify-center gap-1">⛔ BLOCCATO</span>
        if (status === 'ok' || status === 'success') return <span className="bg-green-100 text-green-700 px-2 py-0.5 rounded text-xs font-bold flex items-center justify-center gap-1">✅ ESEGUITO</span>
        if (status === 'skipped') return <span className="bg-yellow-50 text-yellow-700 px-2 py-0.5 rounded text-xs font-medium">SKIPPED</span>
        if (status === 'hold') return <span className="bg-gray-100 text-gray-500 px-2 py-0.5 rounded text-xs">HOLD</span>

        return <span className="bg-gray-50 text-gray-400 px-2 py-0.5 rounded text-xs">{status}</span>
    }

    const getTradeResultBadge = (tradeResult: TradeResult | null) => {
        if (!tradeResult) {
            return <span className="text-gray-400 text-xs">-</span>
        }

        if (tradeResult.status === 'open') {
            return <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded text-xs font-medium">APERTO</span>
        }

        if (tradeResult.pnl_usd === null || tradeResult.pnl_usd === undefined) {
            return <span className="text-gray-400 text-xs">N/A</span>
        }

        if (tradeResult.pnl_usd > 0) {
            return (
                <span className="text-green-600 font-bold text-xs whitespace-nowrap">
                    +${tradeResult.pnl_usd.toFixed(2)}
                </span>
            )
        } else if (tradeResult.pnl_usd < 0) {
            return (
                <span className="text-red-600 font-bold text-xs whitespace-nowrap">
                    ${tradeResult.pnl_usd.toFixed(2)}
                </span>
            )
        }

        return <span className="text-gray-500 text-xs">$0.00</span>
    }

    const filterHistory = (ops: BotOperation[]) => {
        return ops.filter(op => {
            const payload = parsePayload(op.raw_payload)
            if (!payload) return false

            // Status filter
            if (statusFilter !== 'all') {
                const status = payload.execution_result?.status || 'unknown'
                if (statusFilter === 'success' && status !== 'ok' && status !== 'success') return false
                if (statusFilter === 'blocked' && status !== 'blocked') return false
                if (statusFilter === 'skipped' && status !== 'skipped') return false
                if (statusFilter === 'hold' && status !== 'hold') return false
            }

            // Action filter
            if (actionFilter !== 'all') {
                const operation = payload.operation.toLowerCase()
                if (actionFilter !== operation) return false
            }

            // Trade result filter
            if (tradeFilter !== 'all') {
                if (!op.trade_result || op.trade_result.pnl_usd === null) return false
                if (tradeFilter === 'profit' && op.trade_result.pnl_usd <= 0) return false
                if (tradeFilter === 'loss' && op.trade_result.pnl_usd >= 0) return false
            }

            return true
        })
    }

    if (loading) {
        return <div className="p-4 text-center text-gray-500 text-sm animate-pulse">Caricamento storico...</div>
    }

    if (history.length === 0) {
        return <div className="p-4 text-center text-gray-500 text-sm">Nessuna decisione registrata.</div>
    }

    const filteredHistory = filterHistory(history)
    const displayedHistory = filteredHistory.slice(0, displayLimit)
    const hasMore = displayLimit < filteredHistory.length

    return (
        <div className="overflow-hidden">
            {/* Filters Section */}
            <div className="flex flex-wrap gap-3 mb-4 p-5 bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl border border-indigo-200 shadow-sm">
                {/* Status Filter */}
                <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold text-indigo-700 uppercase tracking-wide flex items-center gap-1">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Stato
                    </label>
                    <div className="flex gap-1 bg-white rounded-lg p-1.5 border-2 border-indigo-200 shadow-sm">
                        <button
                            onClick={() => setStatusFilter('all')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${statusFilter === 'all' ? 'bg-indigo-600 text-white shadow-md' : 'text-gray-600 hover:bg-gray-100'}`}
                        >
                            Tutti
                        </button>
                        <button
                            onClick={() => setStatusFilter('success')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${statusFilter === 'success' ? 'bg-green-500 text-white shadow-md' : 'text-gray-600 hover:bg-gray-100'}`}
                        >
                            ✓ Eseguiti
                        </button>
                        <button
                            onClick={() => setStatusFilter('blocked')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${statusFilter === 'blocked' ? 'bg-red-500 text-white shadow-md' : 'text-gray-600 hover:bg-gray-100'}`}
                        >
                            ⛔ Bloccati
                        </button>
                        <button
                            onClick={() => setStatusFilter('hold')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${statusFilter === 'hold' ? 'bg-gray-500 text-white shadow-md' : 'text-gray-600 hover:bg-gray-100'}`}
                        >
                            Hold
                        </button>
                    </div>
                </div>

                {/* Action Filter */}
                <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold text-indigo-700 uppercase tracking-wide flex items-center gap-1">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        Azione
                    </label>
                    <div className="flex gap-1 bg-white rounded-lg p-1.5 border-2 border-indigo-200 shadow-sm">
                        <button
                            onClick={() => setActionFilter('all')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${actionFilter === 'all' ? 'bg-indigo-600 text-white shadow-md' : 'text-gray-600 hover:bg-gray-100'}`}
                        >
                            Tutte
                        </button>
                        <button
                            onClick={() => setActionFilter('open')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${actionFilter === 'open' ? 'bg-blue-500 text-white shadow-md' : 'text-gray-600 hover:bg-gray-100'}`}
                        >
                            📈 Open
                        </button>
                        <button
                            onClick={() => setActionFilter('close')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${actionFilter === 'close' ? 'bg-orange-500 text-white shadow-md' : 'text-gray-600 hover:bg-gray-100'}`}
                        >
                            🔒 Close
                        </button>
                        <button
                            onClick={() => setActionFilter('hold')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${actionFilter === 'hold' ? 'bg-gray-500 text-white shadow-md' : 'text-gray-600 hover:bg-gray-100'}`}
                        >
                            ⏸ Hold
                        </button>
                    </div>
                </div>

                {/* Trade Result Filter */}
                <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-bold text-indigo-700 uppercase tracking-wide flex items-center gap-1">
                        <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Risultato
                    </label>
                    <div className="flex gap-1 bg-white rounded-lg p-1.5 border-2 border-indigo-200 shadow-sm">
                        <button
                            onClick={() => setTradeFilter('all')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${tradeFilter === 'all' ? 'bg-indigo-600 text-white shadow-md' : 'text-gray-600 hover:bg-gray-100'}`}
                        >
                            Tutti
                        </button>
                        <button
                            onClick={() => setTradeFilter('profit')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${tradeFilter === 'profit' ? 'bg-green-500 text-white shadow-md' : 'text-gray-600 hover:bg-gray-100'}`}
                        >
                            💰 Profitto
                        </button>
                        <button
                            onClick={() => setTradeFilter('loss')}
                            className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all duration-200 ${tradeFilter === 'loss' ? 'bg-red-500 text-white shadow-md' : 'text-gray-600 hover:bg-gray-100'}`}
                        >
                            📉 Perdita
                        </button>
                    </div>
                </div>

                {/* Results count */}
                <div className="ml-auto flex items-end">
                    <div className="bg-white rounded-lg px-4 py-2 border-2 border-indigo-200 shadow-sm">
                        <div className="flex items-center gap-2">
                            <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                            </svg>
                            <span className="text-sm font-bold text-gray-900">
                                {filteredHistory.length} <span className="text-gray-500">/ {history.length}</span>
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            <div className="overflow-x-auto rounded-xl border-2 border-gray-200 shadow-md">
                <table className="min-w-full text-left text-sm">
                    <thead className="bg-gradient-to-r from-indigo-50 to-purple-50 border-b-2 border-indigo-200">
                        <tr>
                            <th className="py-4 px-4 font-bold text-indigo-800 uppercase text-xs tracking-wide w-[140px]">
                                <div className="flex items-center gap-1.5">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                    </svg>
                                    Data
                                </div>
                            </th>
                            <th className="py-4 px-4 font-bold text-indigo-800 uppercase text-xs tracking-wide w-[100px]">Ciclo</th>
                            <th className="py-4 px-4 font-bold text-indigo-800 uppercase text-xs tracking-wide w-[80px]">Symbol</th>
                            <th className="py-4 px-4 font-bold text-indigo-800 uppercase text-xs tracking-wide w-[100px]">Azione</th>
                            <th className="py-4 px-4 font-bold text-indigo-800 uppercase text-xs tracking-wide w-[160px]">Stato</th>
                            <th className="py-4 px-4 font-bold text-indigo-800 uppercase text-xs tracking-wide w-[120px]">
                                <div className="flex items-center gap-1.5">
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                    </svg>
                                    Risultato
                                </div>
                            </th>
                            <th className="py-4 px-4 font-bold text-indigo-800 uppercase text-xs tracking-wide w-[100px]">Conf.</th>
                            <th className="py-4 px-4 font-bold text-indigo-800 uppercase text-xs tracking-wide">Motivazione</th>
                            <th className="py-4 px-4 w-[40px]"></th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {displayedHistory.map((op) => {
                            const payload = parsePayload(op.raw_payload)
                            if (!payload) return null

                            const isExpanded = expandedId === op.id
                            const date = new Date(op.created_at).toLocaleString(undefined, {
                                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                            })

                            return (
                                <React.Fragment key={op.id}>
                                    <tr
                                        className={`hover:bg-indigo-50 transition-all duration-200 cursor-pointer border-l-4 hover:border-l-indigo-500 ${
                                            isExpanded ? 'bg-indigo-50/70 border-l-indigo-600' : 'border-l-transparent'
                                        }`}
                                        onClick={() => setExpandedId(isExpanded ? null : op.id)}
                                    >
                                        <td className="py-4 px-4 text-gray-600 whitespace-nowrap text-xs font-medium">{date}</td>
                                        <td className="py-4 px-4 text-gray-400 text-[10px] font-mono truncate max-w-[80px]" title={payload.cycle_id}>
                                            {payload.cycle_id ? payload.cycle_id.replace('cycle_', '') : '-'}
                                        </td>
                                        <td className="py-4 px-4 font-bold text-gray-900 text-sm">{payload.symbol || 'N/A'}</td>
                                        <td className="py-3 px-4">{getOperationBadge(payload)}</td>
                                        <td className="py-3 px-4">{getStatusBadge(payload)}</td>
                                        <td className="py-3 px-4 text-center">{getTradeResultBadge(op.trade_result)}</td>
                                        <td className="py-3 px-4">
                                            <div className="flex items-center gap-2">
                                                <div className="w-12 h-1.5 bg-gray-200 rounded-full overflow-hidden">
                                                    <div
                                                        className={`h-full rounded-full ${getConfidenceColor(payload.confidence)}`}
                                                        style={{ width: `${(payload.confidence || 0) * 100}%` }}
                                                    />
                                                </div>
                                                <span className="text-xs text-gray-500 font-mono">{(payload.confidence * 100).toFixed(0)}%</span>
                                            </div>
                                        </td>
                                        <td className="py-3 px-4 text-gray-600 truncate max-w-[300px]">
                                            {payload.reason}
                                        </td>
                                        <td className="py-3 px-4 text-gray-400">
                                            <svg className={`w-4 h-4 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                            </svg>
                                        </td>
                                    </tr>
                                    {isExpanded && (
                                        <tr className="bg-gray-50/50">
                                            <td colSpan={9} className="p-4 border-b border-gray-100">
                                                <div className="space-y-3 text-xs text-gray-700">
                                                    <div>
                                                        <span className="font-bold uppercase text-gray-500 mb-1 block">Motivazione Completa</span>
                                                        <p className="leading-relaxed bg-white p-3 rounded border border-gray-200">{payload.reason}</p>
                                                    </div>

                                                    {payload.trend_info && (
                                                        <div>
                                                            <span className="font-bold uppercase text-gray-500 mb-1 block">Dettagli Trend</span>
                                                            <pre className="whitespace-pre-wrap font-mono bg-gray-800 text-gray-100 p-3 rounded text-[10px] overflow-x-auto">
                                                                {payload.trend_info}
                                                            </pre>
                                                        </div>
                                                    )}

                                                    <div className="flex gap-4 text-gray-500 pt-2 border-t border-gray-200 mt-2">
                                                        <span>ID Op: <b>{op.id}</b></span>
                                                        {payload._model_name && <span>Modello: <b>{payload._model_name}</b></span>}
                                                        {payload.execution_result && (
                                                            <span className={`${payload.execution_result.status === 'blocked' ? 'text-red-600 font-bold' : ''}`}>
                                                                Stato: {payload.execution_result.status}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>
                                            </td>
                                        </tr>
                                    )}
                                </React.Fragment>
                            )
                        })}
                    </tbody>
                </table>

                {filteredHistory.length === 0 && (
                    <div className="text-center py-8 text-gray-500 text-sm">
                        Nessuna decisione trovata con i filtri selezionati.
                    </div>
                )}
            </div>

            {/* Load More Button */}
            {hasMore && (
                <div className="flex justify-center mt-6">
                    <button
                        onClick={handleLoadMore}
                        disabled={loadingMore}
                        className="flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold rounded-xl shadow-lg hover:shadow-xl hover:from-indigo-700 hover:to-purple-700 transition-all duration-300 transform hover:-translate-y-0.5 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {loadingMore ? (
                            <>
                                <svg className="animate-spin w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                                Caricamento...
                            </>
                        ) : (
                            <>
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                                Carica altri ({displayedHistory.length} di {filteredHistory.length})
                            </>
                        )}
                    </button>
                </div>
            )}
        </div>
    )
}

