interface OpenPosition {
  id: number
  snapshot_id: number
  symbol: string
  side: string
  size: number
  entry_price: number | null
  mark_price: number | null
  pnl_usd: number | null
  leverage: string | null
  snapshot_created_at: string
}

interface OpenPositionsProps {
  positions: OpenPosition[]
}

export function OpenPositions({ positions }: OpenPositionsProps) {
  if (!positions || positions.length === 0) {
    return (
      <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
        <svg className="w-16 h-16 mx-auto mb-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
        </svg>
        <p className="text-sm font-medium text-gray-600">Nessuna posizione aperta al momento</p>
        <p className="text-xs text-gray-500 mt-1">Le posizioni aperte appariranno qui</p>
      </div>
    )
  }

  return (
    <div className="flex gap-4 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100">
      {positions.map((pos) => {
        const isLong = pos.side?.toLowerCase() === 'long'
        const isProfitable = (pos.pnl_usd ?? 0) >= 0

        return (
          <div
            key={pos.id}
            className={`min-w-[260px] rounded-xl border-2 p-4 bg-gradient-to-br shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 ${
              isLong
                ? 'border-green-200 from-green-50 to-emerald-50'
                : 'border-red-200 from-red-50 to-rose-50'
            }`}
          >
            {/* Header */}
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
                  <h3 className="text-lg font-bold text-gray-900">{pos.symbol}</h3>
                  <span className="text-xs text-gray-500">ID #{pos.id}</span>
                </div>
              </div>
              <span
                className={`rounded-full px-3 py-1 text-xs font-bold whitespace-nowrap shadow-sm ${
                  isLong
                    ? 'bg-green-500 text-white'
                    : 'bg-red-500 text-white'
                }`}
              >
                {isLong ? '↗ LONG' : '↘ SHORT'}
              </span>
            </div>

            {/* Metrics Grid */}
            <div className="space-y-2.5 mb-3">
              {/* Size */}
              <div className="flex items-center justify-between bg-white/70 rounded-lg px-3 py-2 border border-gray-200">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
                  </svg>
                  <span className="text-xs font-medium text-gray-600">Size</span>
                </div>
                <span className="text-sm font-bold text-gray-900">{pos.size.toFixed(4)}</span>
              </div>

              {/* Entry Price */}
              <div className="flex items-center justify-between bg-white/70 rounded-lg px-3 py-2 border border-gray-200">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                  </svg>
                  <span className="text-xs font-medium text-gray-600">Entry</span>
                </div>
                <span className="text-sm font-bold text-blue-600">
                  ${pos.entry_price !== null ? pos.entry_price.toFixed(2) : '-'}
                </span>
              </div>

              {/* Mark Price */}
              <div className="flex items-center justify-between bg-white/70 rounded-lg px-3 py-2 border border-gray-200">
                <div className="flex items-center gap-2">
                  <svg className="w-4 h-4 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  <span className="text-xs font-medium text-gray-600">Mark</span>
                </div>
                <span className="text-sm font-bold text-purple-600">
                  ${pos.mark_price !== null ? pos.mark_price.toFixed(2) : '-'}
                </span>
              </div>

              {/* PnL */}
              <div className={`flex items-center justify-between rounded-lg px-3 py-2.5 border-2 ${
                isProfitable ? 'bg-green-100 border-green-300' : 'bg-red-100 border-red-300'
              }`}>
                <div className="flex items-center gap-2">
                  <svg className={`w-4 h-4 ${isProfitable ? 'text-green-600' : 'text-red-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span className="text-xs font-bold text-gray-700">PnL</span>
                </div>
                {pos.pnl_usd !== null ? (
                  <div className="flex items-center gap-1">
                    <span className={`text-base font-bold ${isProfitable ? 'text-green-700' : 'text-red-700'}`}>
                      {isProfitable ? '+' : ''}{pos.pnl_usd.toFixed(2)} USD
                    </span>
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
                ) : (
                  <span className="text-sm text-gray-500">-</span>
                )}
              </div>
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between pt-3 border-t border-gray-200">
              <div className="flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                <span className="text-xs font-semibold text-gray-600">
                  Leva: <span className={`${isLong ? 'text-green-700' : 'text-red-700'}`}>{pos.leverage || '-'}x</span>
                </span>
              </div>
              <div className="flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span className="text-xs text-gray-500">
                  {new Date(pos.snapshot_created_at).toLocaleString('it-IT', {
                    day: '2-digit',
                    month: '2-digit',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}








