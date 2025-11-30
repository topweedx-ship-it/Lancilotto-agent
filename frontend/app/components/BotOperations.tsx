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
  const [expandedReasons, setExpandedReasons] = useState<Set<number>>(new Set())
  const [expandedPrompts, setExpandedPrompts] = useState<Set<number>>(new Set())
  const [expandedJsons, setExpandedJsons] = useState<Set<number>>(new Set())

  if (!operations || operations.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Nessuna operazione trovata nel range selezionato.
      </p>
    )
  }

  const toggleReason = (id: number) => {
    const newSet = new Set(expandedReasons)
    if (newSet.has(id)) {
      newSet.delete(id)
    } else {
      newSet.add(id)
    }
    setExpandedReasons(newSet)
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
    <div className="flex flex-col gap-2.5 sm:gap-3">
      {operations.map((op) => {
        const reason = getReason(op)
        return (
          <article
            key={op.id}
            className="rounded-lg border border-gray-200 p-2.5 sm:p-3 bg-gray-50"
          >
            <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-1 sm:gap-2 mb-1.5">
              <div className="text-sm sm:text-base">
                <strong className="uppercase">{op.operation}</strong>
                {op.symbol && <span> · {op.symbol}</span>}
              </div>
              <small className="text-[10px] sm:text-xs text-muted-foreground">
                {new Date(op.created_at).toLocaleString('it-IT', {
                  day: '2-digit',
                  month: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </small>
            </div>

            <div className="flex gap-1 sm:gap-1.5 flex-wrap text-[10px] sm:text-xs mb-2">
              <span className="rounded-full px-2 sm:px-2.5 py-0.5 border border-gray-300 bg-white">
                ID #{op.id}
              </span>
              {op.direction && (
                <span
                  className={`rounded-full px-2 sm:px-2.5 py-0.5 border ${
                    op.direction.toLowerCase() === 'long'
                      ? 'bg-green-50 border-green-500 text-green-800'
                      : op.direction.toLowerCase() === 'short'
                      ? 'bg-red-50 border-red-300 text-red-700'
                      : 'bg-white border-gray-300'
                  }`}
                >
                  {op.direction.charAt(0).toUpperCase() + op.direction.slice(1)}
                </span>
              )}
              {op.target_portion_of_balance !== null && (
                <span className="rounded-full px-2 sm:px-2.5 py-0.5 border border-gray-300 bg-white">
                  Target: {(op.target_portion_of_balance * 100).toFixed(1)}%
                </span>
              )}
              {op.leverage !== null && (
                <span className="rounded-full px-2 sm:px-2.5 py-0.5 border border-gray-300 bg-white">
                  Lev: {op.leverage}x
                </span>
              )}
            </div>

            {reason && (
              <>
                {reason.length > 180 ? (
                  <>
                    {!expandedReasons.has(op.id) ? (
                      <p className="mt-2 mb-2 text-xs sm:text-sm">{truncate(reason, 180)}</p>
                    ) : (
                      <p className="mt-2 mb-2 text-xs sm:text-sm">{reason}</p>
                    )}
                    <details className="mt-1">
                      <summary
                        className="cursor-pointer text-muted-foreground text-[10px] sm:text-xs hover:text-blue-600"
                        onClick={(e) => {
                          e.preventDefault()
                          toggleReason(op.id)
                        }}
                      >
                        {expandedReasons.has(op.id)
                          ? 'Nascondi ragionamento'
                          : 'Vedi ragionamento completo'}
                      </summary>
                    </details>
                  </>
                ) : (
                  <p className="mt-2 mb-2 text-xs sm:text-sm">{reason}</p>
                )}
              </>
            )}

            {op.system_prompt && (
              <details className="mt-1">
                <summary
                  className="cursor-pointer text-muted-foreground text-[10px] sm:text-xs hover:text-blue-600"
                  onClick={(e) => {
                    e.preventDefault()
                    togglePrompt(op.id)
                  }}
                >
                  {expandedPrompts.has(op.id) ? 'Nascondi prompt' : 'Vedi full prompt'}
                </summary>
                {expandedPrompts.has(op.id) && (
                  <pre className="whitespace-pre-wrap break-words max-h-[200px] sm:max-h-[260px] overflow-y-auto text-[10px] sm:text-xs bg-gray-100 p-2 rounded border border-gray-200 mt-1">
                    {op.system_prompt}
                  </pre>
                )}
              </details>
            )}

            <details className="mt-1">
              <summary
                className="cursor-pointer text-muted-foreground text-[10px] sm:text-xs hover:text-blue-600"
                onClick={(e) => {
                  e.preventDefault()
                  toggleJson(op.id)
                }}
              >
                {expandedJsons.has(op.id) ? 'Nascondi JSON' : 'Vedi JSON completo'}
              </summary>
              {expandedJsons.has(op.id) && (
                <pre className="whitespace-pre-wrap break-words max-h-[200px] sm:max-h-[260px] overflow-y-auto text-[10px] sm:text-xs bg-gray-100 p-2 rounded border border-gray-200 mt-1">
                  {JSON.stringify(op.raw_payload, null, 2)}
                </pre>
              )}
            </details>
          </article>
        )
      })}
    </div>
  )
}

