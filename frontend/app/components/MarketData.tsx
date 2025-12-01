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

export function MarketData({ symbols = ['BTC'] }: { symbols?: string[] }) {
    const [selectedSymbol, setSelectedSymbol] = useState<string>(symbols[0] || 'BTC')
    const [marketData, setMarketData] = useState<Record<string, MarketDataSnapshot>>({})
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Helper per formattazione sicura
    const safeToLocaleString = (val: number | null | undefined, options?: Intl.NumberFormatOptions) => {
        if (val === null || val === undefined) return '-'
        return val.toLocaleString(undefined, options)
    }

    const safeToFixed = (val: number | null | undefined, digits: number) => {
        if (val === null || val === undefined) return '-'
        return val.toFixed(digits)
    }

    const fetchAllData = async () => {
        // Non settare loading a true se abbiamo già dati (refresh background)
        if (Object.keys(marketData).length === 0) setLoading(true)

        try {
            // Fetch parallelo per tutti i simboli
            const promises = symbols.map(async (sym) => {
                try {
                    const res = await fetch(`${API_BASE_URL}/api/market-data/aggregate?symbol=${sym}`)
                    if (!res.ok) return null
                    const data = await res.json()
                    return { symbol: sym, data }
                } catch (e) {
                    console.error(`Error fetching ${sym}:`, e)
                    return null
                }
            })

            const results = await Promise.all(promises)

            const newData: Record<string, MarketDataSnapshot> = {}
            let hasData = false

            results.forEach(res => {
                if (res && res.data) {
                    newData[res.symbol] = res.data
                    hasData = true
                }
            })

            if (hasData) {
                setMarketData(prev => ({ ...prev, ...newData }))
                setError(null)
            } else {
                // Se falliscono tutti e non abbiamo dati precedenti
                if (Object.keys(marketData).length === 0) {
                    setError('Impossibile recuperare dati di mercato')
                }
            }
        } catch (err) {
            console.error('Error fetching market data:', err)
            if (Object.keys(marketData).length === 0) {
                setError('Errore di connessione')
            }
        } finally {
            setLoading(false)
        }
    }

    // Aggiorna selectedSymbol se la lista symbols cambia e il selezionato non c'è più
    useEffect(() => {
        if (symbols.length > 0 && !symbols.includes(selectedSymbol)) {
            setSelectedSymbol(symbols[0])
        }
        // Reset dati se cambiano drasticamente i simboli per evitare stale data
        // Ma manteniamo cache se possibile
    }, [symbols])

    useEffect(() => {
        fetchAllData()
        const interval = setInterval(fetchAllData, 30000) // 30s refresh per tutti
        return () => clearInterval(interval)
    }, [symbols]) // Ricarica se cambia la lista simboli

    if (loading && Object.keys(marketData).length === 0) {
        return (
            <div className="bg-white border rounded-lg p-4 shadow-sm min-h-[200px] flex items-center justify-center">
                <p className="text-gray-500 text-sm animate-pulse">Caricamento dati mercato...</p>
            </div>
        )
    }

    if (error && Object.keys(marketData).length === 0) {
        return (
            <div className="bg-white border rounded-lg p-4 shadow-sm">
                <div className="text-center text-red-500 text-sm">
                    {error}
                    <button onClick={fetchAllData} className="ml-2 text-blue-500 hover:underline">Riprova</button>
                </div>
            </div>
        )
    }

    // Dati del simbolo attualmente selezionato per il dettaglio
    const currentData = marketData[selectedSymbol]?.global_market

    return (
        <div className="bg-white border rounded-lg p-4 shadow-sm">
            <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold text-gray-800 flex items-center gap-2">
                    <span className="text-xl">📊</span>
                    Dati Mercato
                </h3>
                <button
                    onClick={fetchAllData}
                    className="p-1 hover:bg-gray-100 rounded-full text-gray-400 hover:text-gray-600 transition-colors"
                    title="Aggiorna dati"
                >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                </button>
            </div>

            {/* Watchlist Grid - mostra prezzi per TUTTE le coin attive */}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2 mb-6">
                {symbols.map(sym => {
                    const data = marketData[sym]?.global_market
                    const price = data?.average_price
                    const isSelected = selectedSymbol === sym

                    return (
                        <button
                            key={sym}
                            onClick={() => setSelectedSymbol(sym)}
                            className={`flex flex-col items-center p-2 rounded-lg border transition-all ${isSelected
                                    ? 'bg-blue-50 border-blue-200 shadow-sm'
                                    : 'bg-white border-gray-100 hover:border-gray-200 hover:bg-gray-50'
                                }`}
                        >
                            <span className={`text-xs font-bold ${isSelected ? 'text-blue-700' : 'text-gray-600'}`}>
                                {sym}
                            </span>
                            <span className="text-sm font-mono font-semibold text-gray-900">
                                ${price ? safeToLocaleString(price, { maximumFractionDigits: price < 1 ? 4 : 2 }) : '-'}
                            </span>
                        </button>
                    )
                })}
            </div>

            {/* Detailed View for Selected Symbol */}
            {currentData ? (
                <div className="bg-gray-50 rounded-lg p-4 border border-gray-100">
                    <div className="flex items-center justify-between mb-3">
                        <h4 className="text-sm font-semibold text-gray-700">Dettagli {selectedSymbol}</h4>
                        <span className="text-xs text-gray-500">
                            Sources: {currentData.sources_count}
                        </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                        <div>
                            <div className="text-xs text-gray-500 uppercase mb-1">Avg Price</div>
                            <div className="font-mono font-bold text-gray-900">
                                ${safeToLocaleString(currentData.average_price, { maximumFractionDigits: 2 })}
                            </div>
                        </div>

                        <div>
                            <div className="text-xs text-gray-500 uppercase mb-1">Spread</div>
                            <div className="font-mono font-bold text-gray-900">
                                {safeToFixed(currentData.price_spread_pct, 3)}%
                            </div>
                        </div>

                        <div>
                            <div className="text-xs text-gray-500 uppercase mb-1">Funding Rate</div>
                            <div className={`font-mono font-bold ${(currentData.average_funding_rate || 0) > 0 ? 'text-green-600' : 'text-red-600'
                                }`}>
                                {safeToFixed(currentData.average_funding_rate, 6)}%
                            </div>
                        </div>

                        <div>
                            <div className="text-xs text-gray-500 uppercase mb-1">HL Deviation</div>
                            <div className={`font-mono font-bold ${(currentData.hyperliquid_deviation_pct || 0) > 0 ? 'text-amber-600' : 'text-blue-600'
                                }`}>
                                {currentData.hyperliquid_deviation_pct !== null
                                    ? `${currentData.hyperliquid_deviation_pct > 0 ? '+' : ''}${currentData.hyperliquid_deviation_pct.toFixed(4)}%`
                                    : '-'}
                            </div>
                        </div>
                    </div>
                </div>
            ) : (
                <div className="text-center py-8 text-gray-400 text-sm bg-gray-50 rounded-lg border border-dashed border-gray-200">
                    Seleziona una coin per vedere i dettagli
                </div>
            )}
        </div>
    )
}
