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
        <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm mb-6">
            <div className="mb-4">
                <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                    Performance Overview
                </h2>
                <p className="text-sm text-muted-foreground">
                    Riepilogo delle performance dal lancio del bot.
                </p>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-center">
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <div className="text-xs text-gray-500 uppercase font-semibold mb-1">SALDO ATTUALE</div>
                    <div className="text-2xl font-bold text-gray-900">
                        ${currentBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                </div>

                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <div className="text-xs text-gray-500 uppercase font-semibold mb-1">PNL TOTALE ($)</div>
                    <div className={`text-2xl font-bold ${totalPnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {totalPnl >= 0 ? '+' : ''}{totalPnl.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                </div>

                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <div className="text-xs text-gray-500 uppercase font-semibold mb-1">PNL TOTALE (%)</div>
                    <div className={`text-2xl font-bold ${totalPnlPct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {totalPnlPct >= 0 ? '+' : ''}{totalPnlPct.toFixed(2)}%
                    </div>
                </div>

                <div className="p-4 bg-gray-50 rounded-lg border border-gray-100">
                    <div className="text-xs text-gray-500 uppercase font-semibold mb-1">SALDO INIZIALE</div>
                    <div className="text-2xl font-bold text-gray-500">
                        ${initialBalance.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </div>
                </div>
            </div>
        </div>
    )
}

