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
      <p className="text-sm text-muted-foreground">Nessuna posizione aperta trovata.</p>
    )
  }

  return (
    <div className="flex gap-3 sm:gap-3.5 overflow-x-auto pb-1 scrollbar-thin">
      {positions.map((pos) => (
        <div
          key={pos.id}
          className="min-w-[180px] sm:min-w-[220px] rounded-lg border border-gray-200 p-2.5 sm:p-3 bg-gray-50"
        >
          <div className="flex justify-between items-center mb-1 gap-2">
            <strong className="text-sm sm:text-base">{pos.symbol}</strong>
            {pos.side && (
              <span
                className={`rounded-full px-2 sm:px-2.5 py-0.5 text-xs border whitespace-nowrap ${
                  pos.side.toLowerCase() === 'long'
                    ? 'bg-green-50 border-green-500 text-green-800'
                    : pos.side.toLowerCase() === 'short'
                    ? 'bg-red-50 border-red-300 text-red-700'
                    : 'bg-white border-gray-300'
                }`}
              >
                {pos.side.charAt(0).toUpperCase() + pos.side.slice(1)}
              </span>
            )}
          </div>
          <p className="mb-1 text-xs sm:text-sm">Size: {pos.size.toFixed(6)}</p>
          <p className="mb-1 text-xs sm:text-sm">
            Entry:{' '}
            {pos.entry_price !== null ? pos.entry_price.toFixed(4) : '-'}
          </p>
          <p className="mb-1 text-xs sm:text-sm">
            Mark:{' '}
            {pos.mark_price !== null ? pos.mark_price.toFixed(4) : '-'}
          </p>
          <p className="mb-1 text-xs sm:text-sm">
            PnL:{' '}
            {pos.pnl_usd !== null ? (
              <span
                className={
                  pos.pnl_usd >= 0 ? 'text-green-600 font-semibold' : 'text-red-500 font-semibold'
                }
              >
                {pos.pnl_usd.toFixed(4)} USD
              </span>
            ) : (
              '-'
            )}
          </p>
          <p className="mb-1">
            <small className="text-[10px] sm:text-xs text-muted-foreground">
              Leverage: {pos.leverage || '-'}
            </small>
          </p>
          <p className="mb-0">
            <small className="text-[10px] sm:text-xs text-muted-foreground">
              {new Date(pos.snapshot_created_at).toLocaleString('it-IT', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
              })}
            </small>
          </p>
        </div>
      ))}
    </div>
  )
}

