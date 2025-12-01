import { useEffect, useState } from 'react'
import { EquityCurve } from './EquityCurve'
import { OpenPositions } from './OpenPositions'
import { BotOperations } from './BotOperations'
import { TokenUsage } from './TokenUsage'
import { ClosedPositions } from './ClosedPositions'
import { SystemLogs } from './SystemLogs'
import { PerformanceOverview } from './PerformanceOverview'
import { SystemConfig } from './SystemConfig'
import { DecisionViewer } from './DecisionViewer'
import { DecisionHistory } from './DecisionHistory'

interface BalancePoint {
  timestamp: string
  balance_usd: number
}

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

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export function Dashboard() {
  const [balance, setBalance] = useState<BalancePoint[]>([])
  const [openPositions, setOpenPositions] = useState<OpenPosition[]>([])
  const [botOperations, setBotOperations] = useState<BotOperation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Removed activeTickers state as MarketData component is removed
  // const [activeTickers, setActiveTickers] = useState<string[]>(['BTC'])

  const fetchData = async (retryCount = 0, isRefresh = false) => {
    const maxRetries = 5
    const retryDelay = 2000 // 2 seconds

    if (!isRefresh) {
      setLoading(true)
    }

    if (retryCount === 0) {
      setError(null)
    }

    try {
      const baseUrl = API_BASE_URL || ''
      const [balanceRes, positionsRes, operationsRes] = await Promise.all([
        fetch(`${baseUrl}/api/balance`),
        fetch(`${baseUrl}/api/open-positions`),
        fetch(`${baseUrl}/api/bot-operations?limit=10`), // Limit to 10 as per screenshot text
      ])

      if (!balanceRes.ok) throw new Error(`Errore nel caricamento del saldo: ${balanceRes.statusText}`)
      if (!positionsRes.ok) throw new Error(`Errore nel caricamento delle posizioni: ${positionsRes.statusText}`)
      if (!operationsRes.ok) throw new Error(`Errore nel caricamento delle operazioni: ${operationsRes.statusText}`)

      const [balanceData, positionsData, operationsData] = await Promise.all([
        balanceRes.json(),
        positionsRes.json(),
        operationsRes.json(),
      ])

      setBalance(balanceData)
      setOpenPositions(positionsData)
      setBotOperations(operationsData)
      setError(null) // Clear error on success
    } catch (err) {
      // Check if it's a connection error
      const isConnectionError = err instanceof TypeError && err.message.includes('fetch')
      const isNetworkError = err instanceof TypeError || (err as Error)?.message?.includes('ECONNREFUSED')

      if ((isConnectionError || isNetworkError) && retryCount < maxRetries) {
        // Retry with exponential backoff
        const delay = retryDelay * Math.pow(2, retryCount)
        console.log(`Backend non disponibile, retry in ${delay}ms... (tentativo ${retryCount + 1}/${maxRetries})`)
        setTimeout(() => fetchData(retryCount + 1, isRefresh), delay)
        return
      }

      // Only show error if it's not a connection error or we've exhausted retries
      if (!isConnectionError && !isNetworkError) {
        setError(err instanceof Error ? err.message : 'Errore sconosciuto')
      } else if (retryCount >= maxRetries) {
        setError('Backend non disponibile. Assicurati che il server sia avviato.')
      }

      if (retryCount === 0) {
        console.error('Errore nel caricamento dei dati:', err)
      }
    } finally {
      if (retryCount === 0 || retryCount >= maxRetries) {
        setLoading(false)
      }
    }
  }

  // Wrapper for button clicks
  const handleRefresh = () => {
    fetchData(0, true)
  }

  useEffect(() => {
    // Delay initial fetch to give backend time to start
    const initialDelay = setTimeout(() => {
      fetchData()
    }, 2000) // 2 second delay

    const intervalId = setInterval(() => fetchData(0, true), 30000) // 30 secondi (30000 ms)
    return () => {
      clearTimeout(initialDelay)
      clearInterval(intervalId)
    }
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <p className="text-muted-foreground animate-pulse">Caricamento dashboard...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center p-6 bg-red-50 rounded-lg border border-red-100">
          <p className="text-red-500 mb-4">Errore: {error}</p>
          <button
            onClick={handleRefresh}
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            Riprova
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-[1280px] px-4 sm:px-6 py-6 space-y-6">

      {/* Header Actions */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Trading Agent Dashboard</h1>
          <p className="text-sm text-muted-foreground">Monitoraggio in tempo reale</p>
        </div>
        <button
          onClick={handleRefresh}
          className="rounded-full border border-gray-200 px-4 py-2 text-sm font-medium bg-white text-gray-700 hover:border-blue-500 hover:text-blue-600 hover:bg-blue-50 inline-flex items-center gap-2 transition-all shadow-sm"
        >
          <span>Aggiorna tutto</span>
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
        </button>
      </div>

      {/* Main Grid Layout */}
      <div className="grid grid-cols-1 xl:grid-cols-[1fr_450px] 2xl:grid-cols-[1.5fr_500px] gap-6 items-start">

        {/* Left Column */}
        <div className="space-y-6 min-w-0">

          {/* Performance Overview */}
          <PerformanceOverview balance={balance} />

          {/* Equity Curve */}
          <article className="p-6 rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="mb-4">
              <h2 className="text-lg font-bold flex items-center gap-2 mb-1 text-gray-900">
                <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                Equity curve
              </h2>
              <p className="text-sm text-muted-foreground">
                Valore del conto nel tempo, dalla prima osservazione all'ultima disponibile.
              </p>
            </div>
            <EquityCurve data={balance} />
          </article>

          {/* Open Positions */}
          <article className="p-6 rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="mb-4">
              <h2 className="text-lg font-bold flex items-center gap-2 mb-1 text-gray-900">
                <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                Posizioni aperte
              </h2>
              <p className="text-sm text-muted-foreground">
                Snapshot più recente delle posizioni correnti, con PnL colorato.
              </p>
            </div>
            <OpenPositions positions={openPositions} />
          </article>

          {/* Latest Decision Analysis (replaces Market Data prominence) */}
          <article>
            <DecisionViewer />
          </article>

          {/* Decision History Table */}
          <article className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
            <div className="p-6 border-b border-gray-100">
              <h2 className="text-lg font-bold flex items-center gap-2 text-gray-900">
                <span className="w-2 h-2 rounded-full bg-purple-600"></span>
                Cronologia Decisioni AI
              </h2>
              <p className="text-sm text-muted-foreground">
                Storico delle ultime 20 analisi e decisioni prese dall'agente.
              </p>
            </div>
            <DecisionHistory />
          </article>

          {/* Closed Positions */}
          <article className="p-6 rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="mb-4">
              <h2 className="text-lg font-bold flex items-center gap-2 mb-1 text-gray-900">
                <span className="w-2 h-2 rounded-full bg-gray-500"></span>
                Posizioni chiuse
              </h2>
              <p className="text-sm text-muted-foreground">
                Storico operazioni chiuse (da Hyperliquid).
              </p>
            </div>
            <ClosedPositions />
          </article>

          {/* System Logs */}
          <article className="p-6 rounded-xl border border-gray-200 bg-white shadow-sm">
            <div className="mb-4">
              <h2 className="text-lg font-bold flex items-center gap-2 mb-1 text-gray-900">
                <span className="w-2 h-2 rounded-full bg-gray-800"></span>
                System Logs
              </h2>
              <p className="text-sm text-muted-foreground">
                Log di sistema in tempo reale per debug.
              </p>
            </div>
            <SystemLogs />
          </article>

          {/* Token Usage */}
          <article className="p-6 rounded-xl border border-gray-200 bg-white shadow-sm">
            <TokenUsage />
          </article>

        </div>

        {/* Right Column: Recent Operations */}
        <aside className="p-6 rounded-xl border border-gray-200 bg-white shadow-sm sticky top-6">
          <div className="mb-4 flex justify-between items-start">
            <div>
              <h2 className="text-lg font-bold flex items-center gap-2 mb-1 text-gray-900">
                <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                Operazioni recenti
              </h2>
              <p className="text-sm text-muted-foreground">
                Ultime 10 operazioni loggate dall'agente.
              </p>
            </div>
            <button
              onClick={handleRefresh}
              className="p-1.5 hover:bg-gray-100 rounded-full text-gray-400 hover:text-blue-600 transition-colors"
              title="Aggiorna lista"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            </button>
          </div>
          <div className="max-h-[calc(100vh-200px)] overflow-y-auto scrollbar-thin pr-1 mb-6">
            <BotOperations operations={botOperations} />
          </div>

          {/* System Configuration - Moved here */}
          <SystemConfig />
        </aside>

      </div>
    </div>
  )
}
