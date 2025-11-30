import { useEffect, useState } from 'react'
import { EquityCurve } from './EquityCurve'
import { OpenPositions } from './OpenPositions'
import { BotOperations } from './BotOperations'

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

// Usa il proxy di Vite se disponibile, altrimenti usa l'URL diretto
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export function Dashboard() {
  const [balance, setBalance] = useState<BalancePoint[]>([])
  const [openPositions, setOpenPositions] = useState<OpenPosition[]>([])
  const [botOperations, setBotOperations] = useState<BotOperation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    setLoading(true)
    setError(null)

    try {
      const baseUrl = API_BASE_URL || '' // Se vuoto, usa il proxy di Vite
      const [balanceRes, positionsRes, operationsRes] = await Promise.all([
        fetch(`${baseUrl}/api/balance`),
        fetch(`${baseUrl}/api/open-positions`),
        fetch(`${baseUrl}/api/bot-operations?limit=50`),
      ])

      if (!balanceRes.ok) {
        throw new Error(`Errore nel caricamento del saldo: ${balanceRes.statusText}`)
      }
      if (!positionsRes.ok) {
        throw new Error(`Errore nel caricamento delle posizioni: ${positionsRes.statusText}`)
      }
      if (!operationsRes.ok) {
        throw new Error(`Errore nel caricamento delle operazioni: ${operationsRes.statusText}`)
      }

      const [balanceData, positionsData, operationsData] = await Promise.all([
        balanceRes.json(),
        positionsRes.json(),
        operationsRes.json(),
      ])

      setBalance(balanceData)
      setOpenPositions(positionsData)
      setBotOperations(operationsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore sconosciuto')
      console.error('Errore nel caricamento dei dati:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <p className="text-muted-foreground">Caricamento statistiche...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <p className="text-red-500 mb-2">Errore: {error}</p>
          <button
            onClick={fetchData}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Riprova
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto max-w-[1180px] px-4 sm:px-6 py-4 sm:py-6">
      <div className="flex justify-end mb-2">
        <button
          onClick={fetchData}
          className="rounded-full border border-gray-300 px-3 sm:px-4 py-1.5 text-xs sm:text-sm bg-white text-gray-900 hover:border-blue-600 hover:text-blue-600 hover:bg-blue-50 inline-flex items-center gap-1.5"
        >
          🔄 <span className="hidden xs:inline">Aggiorna tutto</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1.8fr_1fr] gap-4 sm:gap-5 items-start">
        {/* Colonna sinistra: equity curve + posizioni aperte */}
        <div className="flex flex-col gap-3 sm:gap-4">
          <article className="p-3 sm:p-4 rounded-lg border border-gray-200 bg-white shadow-sm">
            <div className="mb-2">
              <h2 className="text-sm sm:text-base flex items-center gap-2 mb-0.5 text-gray-900">
                <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                Equity curve
              </h2>
              <p className="text-xs text-muted-foreground mb-2 sm:mb-3">
                Valore del conto nel tempo, dalla prima osservazione all'ultima disponibile.
              </p>
            </div>
            <EquityCurve data={balance} />
          </article>

          <article className="p-3 sm:p-4 rounded-lg border border-gray-200 bg-white shadow-sm">
            <div className="mb-2">
              <h2 className="text-sm sm:text-base flex items-center gap-2 mb-0.5 text-gray-900">
                <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                Posizioni aperte
              </h2>
              <p className="text-xs text-muted-foreground mb-2 sm:mb-3">
                Snapshot più recente delle posizioni correnti, con PnL colorato.
              </p>
            </div>
            <OpenPositions positions={openPositions} />
          </article>
        </div>

        {/* Colonna destra: ultime operazioni dell'agente */}
        <aside className="p-3 sm:p-4 rounded-lg border border-gray-200 bg-white shadow-sm">
          <div className="mb-2">
            <h2 className="text-sm sm:text-base flex items-center gap-2 mb-0.5 text-gray-900">
              <span className="w-2 h-2 rounded-full bg-blue-600"></span>
              Operazioni recenti
            </h2>
            <p className="text-xs text-muted-foreground mb-2 sm:mb-3">
              Ultime 50 operazioni loggate dall'agente, con ragionamento e prompt.
            </p>
          </div>
          <div className="max-h-[60vh] lg:max-h-[72vh] overflow-y-auto scrollbar-thin">
            <BotOperations operations={botOperations} />
          </div>
        </aside>
      </div>
    </div>
  )
}

