interface PerformanceOverviewProps {
    balance: {
        timestamp: string
        balance_usd: number
    }[]
}

export function PerformanceOverview({ balance }: PerformanceOverviewProps) {
    if (!balance || balance.length === 0) {
        return null
    }

    // Trova il primo saldo non-zero per evitare calcoli falsati se lo storico inizia da 0
    const firstNonZero = balance.find(b => b.balance_usd > 0)
    const initialBalance = firstNonZero ? firstNonZero.balance_usd : (balance[0]?.balance_usd || 0)

    const currentBalance = balance[balance.length - 1].balance_usd
    const totalPnl = currentBalance - initialBalance

    // Gestisci divisione per zero
    const totalPnlPct = initialBalance > 0 ? (totalPnl / initialBalance) * 100 : 0

    return (
        <div className="bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 rounded-xl border-2 border-blue-200 p-6 shadow-lg mb-6">
            {/* Header */}
            <div className="flex items-center gap-3 mb-6">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-600 to-indigo-600 flex items-center justify-center shadow-md">
                    <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                    </svg>
                </div>
                <div>
                    <h2 className="text-2xl font-bold text-gray-900">Panoramica Performance</h2>
                    <p className="text-sm text-gray-600">
                        Riepilogo completo delle performance dal lancio del trading bot
                    </p>
                </div>
            </div>

            {/* Metrics Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Current Balance */}
                <div className="bg-white rounded-xl border-2 border-blue-200 p-5 hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-12 h-12 rounded-lg bg-blue-100 flex items-center justify-center">
                            <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                            </svg>
                        </div>
                        <div className="text-xs font-bold text-gray-500 uppercase tracking-wide">Saldo Attuale</div>
                    </div>
                    <div className="text-3xl font-bold text-gray-900 mb-1">
                        ${currentBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        Capitale disponibile
                    </div>
                </div>

                {/* Total PnL USD */}
                <div className={`bg-white rounded-xl border-2 p-5 hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 ${totalPnl >= 0 ? 'border-green-200' : 'border-red-200'}`}>
                    <div className="flex items-center gap-3 mb-3">
                        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${totalPnl >= 0 ? 'bg-green-100' : 'bg-red-100'}`}>
                            <svg className={`w-6 h-6 ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                {totalPnl >= 0 ? (
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                                ) : (
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
                                )}
                            </svg>
                        </div>
                        <div className="text-xs font-bold text-gray-500 uppercase tracking-wide">PnL Totale ($)</div>
                    </div>
                    <div className="flex items-baseline gap-2">
                        <div className={`text-3xl font-bold ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {totalPnl >= 0 ? '+' : ''}${Math.abs(totalPnl).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                        </div>
                        <div className={`flex items-center gap-1 ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {totalPnl >= 0 ? (
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
                                </svg>
                            ) : (
                                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                                    <path fillRule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                </svg>
                            )}
                        </div>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-gray-500 mt-1">
                        Profitto/Perdita in dollari
                    </div>
                </div>

                {/* Total PnL Percentage */}
                <div className={`bg-white rounded-xl border-2 p-5 hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 ${totalPnlPct >= 0 ? 'border-emerald-200' : 'border-rose-200'}`}>
                    <div className="flex items-center gap-3 mb-3">
                        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${totalPnlPct >= 0 ? 'bg-emerald-100' : 'bg-rose-100'}`}>
                            <svg className={`w-6 h-6 ${totalPnlPct >= 0 ? 'text-emerald-600' : 'text-rose-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                        </div>
                        <div className="text-xs font-bold text-gray-500 uppercase tracking-wide">PnL Totale (%)</div>
                    </div>
                    <div className={`text-3xl font-bold ${totalPnlPct >= 0 ? 'text-emerald-600' : 'text-rose-600'} mb-2`}>
                        {totalPnlPct >= 0 ? '+' : ''}{totalPnlPct.toFixed(2)}%
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                        <div
                            className={`h-2 rounded-full transition-all duration-500 ${totalPnlPct >= 0 ? 'bg-emerald-600' : 'bg-rose-600'}`}
                            style={{ width: `${Math.min(Math.abs(totalPnlPct), 100)}%` }}
                        ></div>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                        Rendimento percentuale
                    </div>
                </div>

                {/* Initial Balance */}
                <div className="bg-white rounded-xl border-2 border-gray-200 p-5 hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-12 h-12 rounded-lg bg-gray-100 flex items-center justify-center">
                            <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        </div>
                        <div className="text-xs font-bold text-gray-500 uppercase tracking-wide">Saldo Iniziale</div>
                    </div>
                    <div className="text-3xl font-bold text-gray-700 mb-1">
                        ${initialBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                    <div className="flex items-center gap-1 text-xs text-gray-500">
                        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                        </svg>
                        Capitale di partenza
                    </div>
                </div>
            </div>

            {/* Progress Summary */}
            <div className="mt-6 bg-white/50 backdrop-blur-sm rounded-lg border border-gray-200 p-4">
                <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center gap-2">
                        <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <span className="font-semibold text-gray-700">Riepilogo:</span>
                    </div>
                    <div className="flex items-center gap-6">
                        <div className="text-gray-600">
                            <span className="font-medium">Variazione:</span>{' '}
                            <span className={`font-bold ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {totalPnl >= 0 ? '+' : ''}{totalPnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USD
                            </span>
                        </div>
                        <div className="text-gray-600">
                            <span className="font-medium">ROI:</span>{' '}
                            <span className={`font-bold ${totalPnlPct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                {totalPnlPct >= 0 ? '+' : ''}{totalPnlPct.toFixed(2)}%
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}

