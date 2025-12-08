import React, { useEffect, useState } from 'react'

interface BacktrackSummary {
    total_decisions: number
    execution_rate: number
    win_rate_overall: number
    avg_profit_per_trade: number
    avg_loss_per_trade: number
}

interface PerformanceByCategory {
    by_operation: { [key: string]: { win_rate: number; total: number; wins: number } }
    by_symbol: { [key: string]: { win_rate: number; total: number; wins: number } }
    by_direction: { [key: string]: { win_rate: number; total: number; wins: number } }
}

interface ExitReasonStats {
    [reason: string]: number
}

interface ImprovementArea {
    content: string
    status: string
    id: string
}

interface BacktrackReport {
    generated_at: string
    analysis_period_days: number
    summary: BacktrackSummary
    performance_by_category: PerformanceByCategory
    exit_reasons: ExitReasonStats
    improvement_areas: {
        recommendations: string[]
    }
}

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export function BacktrackAnalysis() {
    const [report, setReport] = useState<BacktrackReport | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [days, setDays] = useState(30)

    const fetchBacktrackData = async (daysParam: number = 30) => {
        try {
            setLoading(true)
            const res = await fetch(`${API_BASE_URL}/api/backtrack-analysis?days=${daysParam}`)
            if (!res.ok) throw new Error('Failed to fetch backtrack data')
            const data = await res.json()
            setReport(data)
            setError(null)
        } catch (e) {
            console.error("Error fetching backtrack analysis", e)
            setError(e instanceof Error ? e.message : 'Unknown error')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchBacktrackData(days)
    }, [days])

    const formatCurrency = (value: number) => {
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value)
    }

    const formatPercentage = (value: number) => {
        return `${value.toFixed(1)}%`
    }

    if (loading) {
        return (
            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
                <div className="animate-pulse">
                    <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
                    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                        {[...Array(4)].map((_, i) => (
                            <div key={i} className="h-20 bg-gray-200 rounded"></div>
                        ))}
                    </div>
                    <div className="h-40 bg-gray-200 rounded"></div>
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
                <div className="text-center text-red-600">
                    <h3 className="text-lg font-semibold mb-2">Error Loading Backtrack Data</h3>
                    <p className="text-sm">{error}</p>
                    <button
                        onClick={() => fetchBacktrackData(days)}
                        className="mt-4 px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                    >
                        Retry
                    </button>
                </div>
            </div>
        )
    }

    if (!report) {
        return (
            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
                <div className="text-center text-gray-500">
                    <h3 className="text-lg font-semibold mb-2">No Data Available</h3>
                    <p className="text-sm">Run backtrack analysis to see insights</p>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6">
            {/* Header with controls */}
            <div className="bg-gradient-to-br from-purple-50 to-blue-50 rounded-xl border border-purple-200 p-6 shadow-md">
                <div className="flex justify-between items-start mb-6">
                    <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-10 h-10 rounded-lg bg-purple-600 flex items-center justify-center">
                                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                            </div>
                            <div>
                                <h2 className="text-2xl font-bold text-gray-900">Analisi delle Decisioni AI</h2>
                                <p className="text-sm text-gray-600 mt-1">
                                    Panoramica completa delle performance e insights delle decisioni prese dall'AI negli ultimi <span className="font-semibold text-purple-700">{days} giorni</span>
                                </p>
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 bg-white rounded-lg px-4 py-2 shadow-sm border border-gray-200">
                        <label className="text-sm font-medium text-gray-700">Periodo:</label>
                        <select
                            value={days}
                            onChange={(e) => setDays(Number(e.target.value))}
                            className="px-3 py-2 border border-gray-300 rounded-lg text-sm font-medium focus:outline-none focus:ring-2 focus:ring-purple-500"
                        >
                            <option value={7}>7 giorni</option>
                            <option value={30}>30 giorni</option>
                            <option value={90}>90 giorni</option>
                        </select>
                        <button
                            onClick={() => fetchBacktrackData(days)}
                            className="px-4 py-2 bg-purple-600 text-white rounded-lg text-sm font-medium hover:bg-purple-700 transition-colors flex items-center gap-2"
                        >
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                            </svg>
                            Aggiorna
                        </button>
                    </div>
                </div>

                {/* Summary Metrics */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
                    {/* Total Decisions */}
                    <div className="bg-white rounded-xl border-2 border-gray-200 p-5 hover:shadow-lg transition-shadow">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-10 h-10 rounded-lg bg-gray-100 flex items-center justify-center">
                                <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                                </svg>
                            </div>
                            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Decisioni Totali</div>
                        </div>
                        <div className="text-3xl font-bold text-gray-900">{report.summary.total_decisions}</div>
                        <div className="text-xs text-gray-500 mt-1">Decisioni prese dall'AI</div>
                    </div>

                    {/* Execution Rate */}
                    <div className="bg-white rounded-xl border-2 border-blue-200 p-5 hover:shadow-lg transition-shadow">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center">
                                <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                            </div>
                            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Tasso Esecuzione</div>
                        </div>
                        <div className="text-3xl font-bold text-blue-600">{formatPercentage(report.summary.execution_rate)}</div>
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                            <div className="bg-blue-600 h-2 rounded-full transition-all duration-500" style={{ width: `${report.summary.execution_rate}%` }}></div>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">Decisioni effettivamente eseguite</div>
                    </div>

                    {/* Win Rate */}
                    <div className="bg-white rounded-xl border-2 border-green-200 p-5 hover:shadow-lg transition-shadow">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-10 h-10 rounded-lg bg-green-100 flex items-center justify-center">
                                <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                            </div>
                            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Win Rate</div>
                        </div>
                        <div className="text-3xl font-bold text-green-600">{formatPercentage(report.summary.win_rate_overall)}</div>
                        <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                            <div className="bg-green-600 h-2 rounded-full transition-all duration-500" style={{ width: `${report.summary.win_rate_overall}%` }}></div>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">Percentuale trade vincenti</div>
                    </div>

                    {/* Avg Profit */}
                    <div className="bg-white rounded-xl border-2 border-emerald-200 p-5 hover:shadow-lg transition-shadow">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-10 h-10 rounded-lg bg-emerald-100 flex items-center justify-center">
                                <svg className="w-5 h-5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                                </svg>
                            </div>
                            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Profitto Medio</div>
                        </div>
                        <div className="text-3xl font-bold text-emerald-600">{formatCurrency(report.summary.avg_profit_per_trade)}</div>
                        <div className="text-xs text-gray-500 mt-1">Per trade vincente</div>
                    </div>

                    {/* Avg Loss */}
                    <div className="bg-white rounded-xl border-2 border-red-200 p-5 hover:shadow-lg transition-shadow">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-10 h-10 rounded-lg bg-red-100 flex items-center justify-center">
                                <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                                </svg>
                            </div>
                            <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Perdita Media</div>
                        </div>
                        <div className="text-3xl font-bold text-red-600">{formatCurrency(report.summary.avg_loss_per_trade)}</div>
                        <div className="text-xs text-gray-500 mt-1">Per trade perdente</div>
                    </div>
                </div>
            </div>

            {/* Performance by Category */}
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-md">
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
                        <svg className="w-5 h-5 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                        </svg>
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-gray-900">Performance per Categoria</h3>
                        <p className="text-sm text-gray-500">Analisi dettagliata delle performance suddivise per tipo, simbolo e direzione</p>
                    </div>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* By Operation */}
                    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg p-4 border border-blue-200">
                        <h4 className="text-sm font-bold mb-3 text-indigo-700 flex items-center gap-2">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 10h16M4 14h16M4 18h16" />
                            </svg>
                            Per Tipo Operazione
                        </h4>
                        <div className="space-y-3">
                            {Object.entries(report.performance_by_category.by_operation).map(([op, stats]) => (
                                <div key={op} className="bg-white rounded-lg p-3 border border-blue-100">
                                    <div className="flex justify-between items-center mb-2">
                                        <span className="text-sm font-bold capitalize text-gray-800">{op}</span>
                                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full font-semibold">{stats.total} trade</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                                            <div className={`h-2 rounded-full transition-all duration-500 ${stats.win_rate >= 50 ? 'bg-green-500' : 'bg-red-500'}`} style={{ width: `${stats.win_rate}%` }}></div>
                                        </div>
                                        <span className={`text-sm font-bold ${stats.win_rate >= 50 ? 'text-green-600' : 'text-red-600'}`}>
                                            {stats.win_rate.toFixed(1)}%
                                        </span>
                                    </div>
                                    <div className="text-xs text-gray-500 mt-1">{stats.wins} vittorie su {stats.total}</div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* By Symbol */}
                    <div className="bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg p-4 border border-purple-200">
                        <h4 className="text-sm font-bold mb-3 text-purple-700 flex items-center gap-2">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                            Per Simbolo
                        </h4>
                        <div className="space-y-3 max-h-64 overflow-y-auto pr-2">
                            {Object.entries(report.performance_by_category.by_symbol)
                                .sort(([, a], [, b]) => b.total - a.total)
                                .map(([symbol, stats]) => (
                                    <div key={symbol} className="bg-white rounded-lg p-3 border border-purple-100">
                                        <div className="flex justify-between items-center mb-2">
                                            <span className="text-sm font-bold text-gray-800">{symbol}</span>
                                            <span className="text-xs bg-purple-100 text-purple-700 px-2 py-1 rounded-full font-semibold">{stats.total} trade</span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <div className="flex-1 bg-gray-200 rounded-full h-2">
                                                <div className={`h-2 rounded-full transition-all duration-500 ${stats.win_rate >= 50 ? 'bg-green-500' : 'bg-red-500'}`} style={{ width: `${stats.win_rate}%` }}></div>
                                            </div>
                                            <span className={`text-sm font-bold ${stats.win_rate >= 50 ? 'text-green-600' : 'text-red-600'}`}>
                                                {stats.win_rate.toFixed(1)}%
                                            </span>
                                        </div>
                                        <div className="text-xs text-gray-500 mt-1">{stats.wins} vittorie su {stats.total}</div>
                                    </div>
                                ))}
                        </div>
                    </div>

                    {/* By Direction */}
                    <div className="bg-gradient-to-br from-green-50 to-emerald-50 rounded-lg p-4 border border-green-200">
                        <h4 className="text-sm font-bold mb-3 text-green-700 flex items-center gap-2">
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                            </svg>
                            Per Direzione
                        </h4>
                        <div className="space-y-3">
                            {Object.entries(report.performance_by_category.by_direction).map(([dir, stats]) => (
                                <div key={dir} className="bg-white rounded-lg p-3 border border-green-100">
                                    <div className="flex justify-between items-center mb-2">
                                        <div className="flex items-center gap-2">
                                            <span className={`w-6 h-6 rounded flex items-center justify-center text-xs font-bold ${dir === 'long' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                                                {dir === 'long' ? '↗' : '↘'}
                                            </span>
                                            <span className="text-sm font-bold capitalize text-gray-800">{dir}</span>
                                        </div>
                                        <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-semibold">{stats.total} trade</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                                            <div className={`h-2 rounded-full transition-all duration-500 ${stats.win_rate >= 50 ? 'bg-green-500' : 'bg-red-500'}`} style={{ width: `${stats.win_rate}%` }}></div>
                                        </div>
                                        <span className={`text-sm font-bold ${stats.win_rate >= 50 ? 'text-green-600' : 'text-red-600'}`}>
                                            {stats.win_rate.toFixed(1)}%
                                        </span>
                                    </div>
                                    <div className="text-xs text-gray-500 mt-1">{stats.wins} vittorie su {stats.total}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Exit Reasons */}
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-md">
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
                        <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-gray-900">Motivi di Uscita</h3>
                        <p className="text-sm text-gray-500">Distribuzione dei motivi per cui sono stati chiusi i trade</p>
                    </div>
                </div>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {Object.entries(report.exit_reasons)
                        .sort(([, a], [, b]) => b - a)
                        .map(([reason, count]) => {
                            const total = Object.values(report.exit_reasons).reduce((a, b) => a + b, 0)
                            const percentage = (count / total * 100).toFixed(1)

                            const getReasonIcon = (r: string) => {
                                if (r.includes('profit')) return { icon: '🎯', color: 'from-green-50 to-emerald-50 border-green-200' }
                                if (r.includes('loss')) return { icon: '🛡️', color: 'from-red-50 to-rose-50 border-red-200' }
                                if (r.includes('signal')) return { icon: '📊', color: 'from-blue-50 to-cyan-50 border-blue-200' }
                                if (r.includes('trend')) return { icon: '📈', color: 'from-purple-50 to-pink-50 border-purple-200' }
                                if (r.includes('manual')) return { icon: '👤', color: 'from-gray-50 to-slate-50 border-gray-200' }
                                if (r.includes('circuit')) return { icon: '⚡', color: 'from-orange-50 to-amber-50 border-orange-200' }
                                return { icon: '📋', color: 'from-gray-50 to-slate-50 border-gray-200' }
                            }

                            const { icon, color } = getReasonIcon(reason)

                            return (
                                <div key={reason} className={`bg-gradient-to-br ${color} p-4 rounded-lg border hover:shadow-md transition-shadow`}>
                                    <div className="text-center">
                                        <div className="text-2xl mb-2">{icon}</div>
                                        <div className="text-2xl font-bold text-gray-900 mb-1">{count}</div>
                                        <div className="text-xs text-gray-600 font-semibold uppercase mb-2">
                                            {reason.replace(/_/g, ' ')}
                                        </div>
                                        <div className="w-full bg-gray-200 rounded-full h-1.5">
                                            <div className="bg-indigo-600 h-1.5 rounded-full transition-all duration-500" style={{ width: `${percentage}%` }}></div>
                                        </div>
                                        <div className="text-xs text-gray-500 mt-1">{percentage}% del totale</div>
                                    </div>
                                </div>
                            )
                        })}
                </div>
            </div>

            {/* Recommendations */}
            {report.improvement_areas.recommendations.length > 0 && (
                <div className="bg-gradient-to-br from-orange-50 to-amber-50 rounded-xl border-2 border-orange-200 p-6 shadow-lg">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="w-10 h-10 rounded-lg bg-orange-600 flex items-center justify-center">
                            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                            </svg>
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-orange-800">Raccomandazioni per Migliorare</h3>
                            <p className="text-sm text-orange-700">Suggerimenti basati sull'analisi delle performance</p>
                        </div>
                    </div>
                    <div className="space-y-3">
                        {report.improvement_areas.recommendations.map((rec, index) => (
                            <div key={index} className="bg-white border-2 border-orange-300 rounded-lg p-4 hover:shadow-md transition-shadow">
                                <div className="flex items-start gap-3">
                                    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center">
                                        <span className="text-orange-600 font-bold text-lg">💡</span>
                                    </div>
                                    <div className="flex-1">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className="text-xs font-bold text-orange-600 uppercase bg-orange-100 px-2 py-1 rounded">Suggerimento #{index + 1}</span>
                                        </div>
                                        <p className="text-sm text-gray-800 leading-relaxed font-medium">{rec}</p>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Footer */}
            <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 text-center">
                <div className="flex items-center justify-center gap-2 text-xs text-gray-500">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span>Report generato il: <span className="font-semibold text-gray-700">{new Date(report.generated_at).toLocaleString('it-IT', { dateStyle: 'full', timeStyle: 'short' })}</span></span>
                </div>
            </div>
        </div>
    )
}
