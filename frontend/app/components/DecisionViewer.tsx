import { useEffect, useState } from 'react'

interface DecisionData {
  operation: string
  symbol: string
  direction: string
  confidence: number
  reason: string
  trend_info?: string
  execution_result?: {
    status: string
    reason?: string
    error?: string
  }
  _model_name?: string
}

interface BotOperation {
  id: number
  created_at: string
  operation: string
  symbol: string | null
  direction: string | null
  raw_payload: any
}

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export function DecisionViewer() {
  const [latestOp, setLatestOp] = useState<BotOperation | null>(null)
  const [decision, setDecision] = useState<DecisionData | null>(null)
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    try {
      // Fetch latest operation (limit 1)
      const res = await fetch(`${API_BASE_URL}/api/bot-operations?limit=1`)
      if (!res.ok) return
      const data = await res.json()
      
      if (data && data.length > 0) {
        const op = data[0]
        setLatestOp(op)
        
        // Parse raw payload if string
        let payload = op.raw_payload
        if (typeof payload === 'string') {
          try {
            payload = JSON.parse(payload)
          } catch (e) {
            console.error("Error parsing payload", e)
          }
        }
        setDecision(payload)
      }
    } catch (e) {
      console.error("Error fetching decision", e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000) // Update every 10s
    return () => clearInterval(interval)
  }, [])

  if (loading && !decision) {
    return (
      <div className="bg-white border rounded-lg p-6 shadow-sm min-h-[200px] flex items-center justify-center">
        <p className="text-gray-500 animate-pulse">Caricamento decisioni...</p>
      </div>
    )
  }

  if (!decision) {
    return (
      <div className="bg-white border rounded-lg p-6 shadow-sm">
        <p className="text-gray-500 text-center">Nessuna decisione recente disponibile.</p>
      </div>
    )
  }

  // Determine status color/badge
  const isExecuted = decision.execution_result?.status === 'ok' || decision.execution_result?.status === 'success'
  const isBlocked = decision.execution_result?.status === 'blocked'
  const isSkipped = decision.execution_result?.status === 'skipped'
  const isHold = decision.operation === 'hold'

  let statusColor = 'bg-gray-100 text-gray-700'
  let statusText = decision.execution_result?.status || 'Unknown'

  if (isExecuted) {
    statusColor = 'bg-green-100 text-green-700'
    statusText = 'Eseguito'
  } else if (isBlocked) {
    statusColor = 'bg-red-100 text-red-700'
    statusText = 'Bloccato'
  } else if (isHold) {
    statusColor = 'bg-blue-50 text-blue-700'
    statusText = 'Hold'
  } else if (isSkipped) {
    statusColor = 'bg-yellow-50 text-yellow-700'
    statusText = 'Skipped'
  }

  return (
    <div className="bg-white border rounded-lg p-6 shadow-sm">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="font-bold text-gray-800 flex items-center gap-2">
            <span className="text-xl">🤖</span>
            Decisione AI
            {decision._model_name && (
              <span className="text-xs font-normal text-gray-500 bg-gray-50 px-2 py-0.5 rounded border">
                {decision._model_name}
              </span>
            )}
          </h3>
          <p className="text-xs text-gray-400 mt-1">
            {latestOp ? new Date(latestOp.created_at).toLocaleString() : ''}
          </p>
        </div>
        
        <span className={`px-3 py-1 rounded-full text-xs font-bold uppercase ${statusColor}`}>
          {statusText}
        </span>
      </div>

      {/* Main Decision Info */}
      <div className="flex items-center gap-4 mb-4 p-3 bg-gray-50 rounded-lg border border-gray-100">
        <div className="text-center min-w-[80px]">
          <div className="text-2xl font-black text-gray-900">{decision.symbol}</div>
          <div className={`text-xs font-bold uppercase ${
            decision.direction === 'long' ? 'text-green-600' : 
            decision.direction === 'short' ? 'text-red-600' : 'text-gray-500'
          }`}>
            {decision.operation === 'hold' ? 'HOLD' : decision.direction}
          </div>
        </div>
        
        <div className="flex-1 border-l border-gray-200 pl-4">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs font-semibold text-gray-500">Confidence:</span>
            <div className="h-2 w-24 bg-gray-200 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full ${
                  decision.confidence > 0.7 ? 'bg-green-500' : 
                  decision.confidence > 0.4 ? 'bg-blue-500' : 'bg-yellow-500'
                }`}
                style={{ width: `${(decision.confidence || 0) * 100}%` }}
              />
            </div>
            <span className="text-xs font-mono">{(decision.confidence * 100).toFixed(0)}%</span>
          </div>
          
          {decision.operation !== 'hold' && (
             <div className="text-xs text-gray-600 space-x-3">
                <span>Lev: <b>{decision.leverage || 1}x</b></span>
                {decision.target_portion_of_balance && (
                    <span>Size: <b>{(decision.target_portion_of_balance * 100).toFixed(1)}%</b></span>
                )}
             </div>
          )}
        </div>
      </div>

      {/* Reasoning */}
      <div className="mb-4">
        <h4 className="text-xs font-bold text-gray-700 uppercase mb-2">Motivazione</h4>
        <div className="text-sm text-gray-600 bg-blue-50/50 p-3 rounded border border-blue-100 leading-relaxed">
          {decision.reason}
        </div>
      </div>

      {/* Execution/Block Reason */}
      {(isBlocked || isSkipped) && decision.execution_result?.reason && (
        <div className="mb-4 p-3 bg-red-50 rounded border border-red-100 text-sm text-red-700">
          <strong>Motivo blocco:</strong> {decision.execution_result.reason}
        </div>
      )}

      {/* Trend Info (if available) */}
      {decision.trend_info && (
        <div>
          <h4 className="text-xs font-bold text-gray-700 uppercase mb-2">Analisi Trend</h4>
          <pre className="text-[10px] text-gray-600 bg-gray-50 p-3 rounded border overflow-x-auto whitespace-pre-wrap font-mono">
            {decision.trend_info}
          </pre>
        </div>
      )}
    </div>
  )
}

