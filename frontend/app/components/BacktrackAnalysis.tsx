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
            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
                <div className="flex justify-between items-center mb-4">
                    <div>
                        <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                            <span className="w-2 h-2 rounded-full bg-purple-600"></span>
                            Backtrack Analysis
                        </h2>
                        <p className="text-sm text-muted-foreground">
                            AI decision analysis and performance insights over the last {days} days
                        </p>
                    </div>
                    <div className="flex items-center gap-2">
                        <label className="text-sm font-medium">Period:</label>
                        <select
                            value={days}
                            onChange={(e) => setDays(Number(e.target.value))}
                            className="px-3 py-1 border border-gray-300 rounded text-sm"
                        >
                            <option value={7}>7 days</option>
                            <option value={30}>30 days</option>
                            <option value={90}>90 days</option>
                        </select>
                        <button
                            onClick={() => fetchBacktrackData(days)}
                            className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
                        >
                            Refresh
                        </button>
                    </div>
                </div>

                {/* Summary Metrics */}
                <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 text-center">
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-1">TOTAL DECISIONS</div>
                        <div className="text-xl font-bold text-gray-900">{report.summary.total_decisions}</div>
                    </div>

                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 text-center">
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-1">EXECUTION RATE</div>
                        <div className="text-xl font-bold text-blue-600">{formatPercentage(report.summary.execution_rate)}</div>
                    </div>

                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 text-center">
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-1">WIN RATE</div>
                        <div className="text-xl font-bold text-green-600">{formatPercentage(report.summary.win_rate_overall)}</div>
                    </div>

                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 text-center">
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-1">AVG PROFIT</div>
                        <div className="text-xl font-bold text-green-600">{formatCurrency(report.summary.avg_profit_per_trade)}</div>
                    </div>

                    <div className="p-4 bg-gray-50 rounded-lg border border-gray-100 text-center">
                        <div className="text-xs text-gray-500 uppercase font-semibold mb-1">AVG LOSS</div>
                        <div className="text-xl font-bold text-red-600">{formatCurrency(report.summary.avg_loss_per_trade)}</div>
                    </div>
                </div>
            </div>

            {/* Performance by Category */}
            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
                <h3 className="text-md font-semibold mb-4">Performance by Category</h3>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    {/* By Operation */}
                    <div>
                        <h4 className="text-sm font-medium mb-2 text-gray-700">By Operation Type</h4>
                        <div className="space-y-2">
                            {Object.entries(report.performance_by_category.by_operation).map(([op, stats]) => (
                                <div key={op} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                                    <span className="text-sm font-medium capitalize">{op}</span>
                                    <div className="text-right">
                                        <div className="text-xs text-gray-500">{stats.total} trades</div>
                                        <div className="text-sm font-semibold text-green-600">{stats.win_rate.toFixed(1)}%</div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* By Symbol */}
                    <div>
                        <h4 className="text-sm font-medium mb-2 text-gray-700">By Symbol</h4>
                        <div className="space-y-2 max-h-40 overflow-y-auto">
                            {Object.entries(report.performance_by_category.by_symbol)
                                .sort(([, a], [, b]) => b.total - a.total)
                                .map(([symbol, stats]) => (
                                    <div key={symbol} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                                        <span className="text-sm font-medium">{symbol}</span>
                                        <div className="text-right">
                                            <div className="text-xs text-gray-500">{stats.total} trades</div>
                                            <div className={`text-sm font-semibold ${stats.win_rate >= 50 ? 'text-green-600' : 'text-red-600'}`}>
                                                {stats.win_rate.toFixed(1)}%
                                            </div>
                                        </div>
                                    </div>
                                ))}
                        </div>
                    </div>

                    {/* By Direction */}
                    <div>
                        <h4 className="text-sm font-medium mb-2 text-gray-700">By Direction</h4>
                        <div className="space-y-2">
                            {Object.entries(report.performance_by_category.by_direction).map(([dir, stats]) => (
                                <div key={dir} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                                    <span className="text-sm font-medium capitalize">{dir}</span>
                                    <div className="text-right">
                                        <div className="text-xs text-gray-500">{stats.total} trades</div>
                                        <div className={`text-sm font-semibold ${stats.win_rate >= 50 ? 'text-green-600' : 'text-red-600'}`}>
                                            {stats.win_rate.toFixed(1)}%
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>

            {/* Exit Reasons */}
            <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
                <h3 className="text-md font-semibold mb-4">Exit Reason Distribution</h3>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                    {Object.entries(report.exit_reasons)
                        .sort(([, a], [, b]) => b - a)
                        .map(([reason, count]) => (
                            <div key={reason} className="p-3 bg-gray-50 rounded-lg text-center">
                                <div className="text-lg font-bold text-gray-900">{count}</div>
                                <div className="text-xs text-gray-500 uppercase font-semibold">
                                    {reason.replace('_', ' ')}
                                </div>
                            </div>
                        ))}
                </div>
            </div>

            {/* Recommendations */}
            {report.improvement_areas.recommendations.length > 0 && (
                <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
                    <h3 className="text-md font-semibold mb-4 text-orange-700">Improvement Recommendations</h3>
                    <div className="space-y-3">
                        {report.improvement_areas.recommendations.map((rec, index) => (
                            <div key={index} className="p-3 bg-orange-50 border border-orange-200 rounded-lg">
                                <div className="flex items-start gap-2">
                                    <span className="text-orange-600 font-bold text-sm">💡</span>
                                    <p className="text-sm text-orange-800">{rec}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Footer */}
            <div className="text-center text-xs text-gray-500">
                Report generated: {new Date(report.generated_at).toLocaleString()}
            </div>
        </div>
    )
}
