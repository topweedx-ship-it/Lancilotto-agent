import { useState } from 'react'

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

interface BotOperationsProps {
  operations: BotOperation[]
}

export function BotOperations({ operations }: BotOperationsProps) {
  const [expandedPrompts, setExpandedPrompts] = useState<Set<number>>(new Set())
  const [expandedJsons, setExpandedJsons] = useState<Set<number>>(new Set())

  if (!operations || operations.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Nessuna operazione trovata nel range selezionato.
      </p>
    )
  }

  const togglePrompt = (id: number) => {
    const newSet = new Set(expandedPrompts)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }
    setExpandedPrompts(newSet)
  }

  const toggleJson = (id: number) => {
    const newSet = new Set(expandedJsons)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }
    setExpandedJsons(newSet)
  }

  const getReason = (op: BotOperation): string | null => {
    return (
      op.raw_payload?.reason ||
      op.raw_payload?.motivation ||
      op.raw_payload?.comment ||
      null
    )
  }

  const truncate = (text: string, maxLength: number): string => {
    if (text.length <= maxLength) return text
    return text.slice(0, maxLength - 1) + '…'
  }

  return (
    <div className="flex flex-col gap-4">
      {operations.map((op) => {
        const reason = getReason(op)
        const marketData = op.raw_payload?.market_data
        const forecast = op.raw_payload?.forecast
        
        return (
          <article
            key={op.id}
            className="rounded-lg border border-gray-200 p-4 bg-white shadow-sm"
          >
            {/* Header: Operation Type & Symbol */}
            <div className="flex justify-between items-start mb-3">
              <div className="flex items-center gap-2">
                 <strong className="text-sm font-bold text-gray-900 uppercase">
                  {op.operation} {op.symbol ? `· ${op.symbol}` : ''}
                 </strong>
                 <span className="text-xs text-gray-500">
                  {new Date(op.created_at).toLocaleString('it-IT', {
                      day: '2-digit',
                      month: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit'
                    })}
                 </span>
              </div>
            </div>

            {/* Badges Row */}
            <div className="flex gap-2 flex-wrap mb-4">
               <span className="px-3 py-1 rounded-full border border-gray-200 text-xs text-gray-600 bg-white">
                 ID #{op.id}
               </span>
               {op.direction && (
                <span className={`px-3 py-1 rounded-full border text-xs font-medium ${
                   op.direction.toLowerCase() === 'long'
                      ? 'bg-green-50 border-green-200 text-green-700'
                      : op.direction.toLowerCase() === 'short'
                      ? 'bg-red-50 border-red-200 text-red-700'
                      : 'bg-gray-50 border-gray-200 text-gray-700'
                }`}>
                  {op.direction.charAt(0).toUpperCase() + op.direction.slice(1)}
                </span>
               )}
               {op.target_portion_of_balance !== null && (
                 <span className="px-3 py-1 rounded-full border border-gray-200 text-xs text-gray-600 bg-white">
                   Target: {(op.target_portion_of_balance * 100).toFixed(1)}%
                 </span>
               )}
               {op.leverage !== null && (
                 <span className="px-3 py-1 rounded-full border border-gray-200 text-xs text-gray-600 bg-white">
                   Lev: {op.leverage}x
                 </span>
               )}
            </div>

            {/* Market Data & Forecast Box */}
            {(marketData || forecast) && (
              <div className="bg-slate-50 rounded-lg p-3 mb-4 border border-slate-100 grid grid-cols-2 gap-4">
                 {marketData && (
                   <div>
                     <h4 className="text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wide">Market Data</h4>
                     <div className="space-y-1">
                        {marketData.price && (
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-600">Price:</span>
                            <span className="font-mono font-bold text-slate-900">${marketData.price}</span>
                          </div>
                        )}
                        {marketData.rsi_7 && (
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-600">RSI (7):</span>
                            <span className="font-mono text-slate-900">{marketData.rsi_7.toFixed(1)}</span>
                          </div>
                        )}
                         {marketData.macd && (
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-600">MACD:</span>
                            <span className="font-mono text-slate-900">{marketData.macd.toFixed(4)}</span>
                          </div>
                        )}
                     </div>
                   </div>
                 )}

                 {forecast && (
                   <div className="border-l border-slate-200 pl-4">
                      <h4 className="text-xs font-semibold text-slate-500 mb-2 uppercase tracking-wide">AI Forecast</h4>
                      <div className="space-y-1">
                        {forecast.target_price && (
                          <div className="flex justify-between text-xs">
                            <span className="text-slate-600">Target:</span>
                            <span className="font-mono font-bold text-slate-900">${forecast.target_price}</span>
                          </div>
                        )}
                        {forecast.price_range && (
                          <div className="text-xs mt-1">
                            <span className="text-slate-600 block mb-0.5">Range:</span>
                            <span className="font-mono text-slate-500">
                              {Array.isArray(forecast.price_range) 
                                ? `$${forecast.price_range[0]} - $${forecast.price_range[1]}` 
                                : forecast.price_range}
                            </span>
                          </div>
                        )}
                      </div>
                   </div>
                 )}
              </div>
            )}

            {/* Reason / Reasoning */}
            {reason && (
               <div className="mb-3">
                 <p className="text-sm text-gray-700 leading-relaxed">
                   {reason.length > 280 ? (
                      <>
                        {truncate(reason, 280)}
                        <button className="ml-1 text-blue-600 hover:underline text-xs font-medium">
                          Vedi ragionamento completo ›
                        </button>
                      </>
                   ) : reason}
                 </p>
               </div>
            )}

            {/* Expandable Sections */}
            <div className="flex flex-col gap-1 border-t border-gray-100 pt-2 mt-2">
               {op.system_prompt && (
                 <button
                   onClick={() => togglePrompt(op.id)}
                   className="flex items-center justify-between w-full py-1.5 px-2 text-xs text-gray-500 hover:bg-gray-50 rounded transition-colors text-left"
                 >
                   <span>Vedi full prompt</span>
                   <span className="text-gray-400">{expandedPrompts.has(op.id) ? '▲' : '›'}</span>
                 </button>
               )}
               {expandedPrompts.has(op.id) && op.system_prompt && (
                 <div className="bg-gray-900 text-gray-300 p-3 rounded text-[10px] font-mono overflow-x-auto mb-2">
                   <pre>{op.system_prompt}</pre>
                 </div>
               )}

               <button
                  onClick={() => toggleJson(op.id)}
                  className="flex items-center justify-between w-full py-1.5 px-2 text-xs text-gray-500 hover:bg-gray-50 rounded transition-colors text-left"
               >
                  <span>Vedi JSON completo</span>
                  <span className="text-gray-400">{expandedJsons.has(op.id) ? '▲' : '›'}</span>
               </button>
               {expandedJsons.has(op.id) && (
                 <div className="bg-gray-50 border border-gray-200 text-gray-700 p-3 rounded text-[10px] font-mono overflow-x-auto">
                   <pre>{JSON.stringify(op.raw_payload, null, 2)}</pre>
                 </div>
               )}
            </div>

          </article>
        )
      })}
    </div>
  )
}
