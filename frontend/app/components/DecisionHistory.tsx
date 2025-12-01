import React, { useEffect, useState } from 'react'

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
}

interface DecisionData {
    operation: string
    symbol: string
    direction: string
    confidence: number
    reason: string
    trend_info?: string
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
    const [expandedId, setExpandedId] = useState<number | null>(null)

    const fetchHistory = async () => {
        try {
            // Fetch last 20 operations
            const res = await fetch(`${API_BASE_URL}/api/bot-operations?limit=20`)
            if (!res.ok) throw new Error('Failed to fetch history')
            const data = await res.json()
            setHistory(data)
        } catch (e) {
            console.error("Error fetching decision history", e)
        } finally {
            setLoading(false)
        }
    }

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

    if (loading) {
        return <div className="p-4 text-center text-gray-500 text-sm animate-pulse">Caricamento storico...</div>
    }

    if (history.length === 0) {
        return <div className="p-4 text-center text-gray-500 text-sm">Nessuna decisione registrata.</div>
    }

    return (
        <div className="overflow-hidden">
            <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                    <thead className="bg-gray-50 text-gray-600 border-b border-gray-200">
                        <tr>
                            <th className="py-3 px-4 font-medium w-[140px]">Data</th>
                            <th className="py-3 px-4 font-medium w-[80px]">Symbol</th>
                            <th className="py-3 px-4 font-medium w-[100px]">Azione</th>
                            <th className="py-3 px-4 font-medium w-[160px]">Stato</th>
                            <th className="py-3 px-4 font-medium w-[80px]">Conf.</th>
                            <th className="py-3 px-4 font-medium">Motivazione</th>
                            <th className="py-3 px-4 w-[40px]"></th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                        {history.map((op) => {
                            const payload = parsePayload(op.raw_payload)
                            if (!payload) return null

                            const isExpanded = expandedId === op.id
                            const date = new Date(op.created_at).toLocaleString(undefined, {
                                month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                            })

                            return (
                                <>
                                    {/* React Fragment to allow multiple rows from one map iteration */}
                                    <React.Fragment key={op.id}>
                                        <tr
                                            className={`hover:bg-blue-50/30 transition-colors cursor-pointer ${isExpanded ? 'bg-blue-50/50' : ''}`}
                                            onClick={() => setExpandedId(isExpanded ? null : op.id)}
                                        >
                                            <td className="py-3 px-4 text-gray-500 whitespace-nowrap text-xs">{date}</td>
                                            <td className="py-3 px-4 font-bold text-gray-800">{payload.symbol || 'N/A'}</td>
                                            <td className="py-3 px-4">{getOperationBadge(payload)}</td>
                                            <td className="py-3 px-4">{getStatusBadge(payload)}</td>
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
                                                <td colSpan={7} className="p-4 border-b border-gray-100">
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
                                </>
                            )
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

