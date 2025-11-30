import * as Dialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'

interface VersionModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const VERSION = '0.1.0'

export function VersionModal({ open, onOpenChange }: VersionModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-lg shadow-xl p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto z-50 border border-gray-200">
          <Dialog.Title className="text-2xl font-bold mb-4">
            Trading Agent - Specifiche
          </Dialog.Title>
          
          <div className="space-y-4">
            <div>
              <h3 className="font-semibold text-lg mb-2">Versione</h3>
              <p className="text-muted-foreground">{VERSION}</p>
            </div>

            <div>
              <h3 className="font-semibold text-lg mb-2">Caratteristiche principali</h3>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                <li>Analisi multi-sorgente: integra dati di mercato, news, sentiment analysis e whale alert</li>
                <li>Previsioni: utilizza modelli di forecasting per anticipare i movimenti di prezzo</li>
                <li>Modularità: ogni componente è gestito da moduli separati, facilmente estendibili</li>
                <li>Ispirazione Alpha Arena: approccio competitivo e AI-driven</li>
                <li>Gestione multi-modello AI: supporta GPT-5.1, GPT-4o-mini e DeepSeek con selezione dinamica</li>
              </ul>
            </div>

            <div>
              <h3 className="font-semibold text-lg mb-2">Modelli AI supportati</h3>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                <li><strong>GPT-5.1</strong> (gpt-5.1-2025-11-13) - Modello di default</li>
                <li><strong>GPT-4o-mini</strong> - Modello veloce ed economico</li>
                <li><strong>DeepSeek</strong> - Modello alternativo</li>
              </ul>
            </div>

            <div>
              <h3 className="font-semibold text-lg mb-2">Stack tecnologico</h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <h4 className="font-semibold mb-1">Backend</h4>
                  <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                    <li>FastAPI</li>
                    <li>PostgreSQL</li>
                    <li>Uvicorn</li>
                    <li>Python 3.10+</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold mb-1">Frontend</h4>
                  <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                    <li>React 18</li>
                    <li>TypeScript</li>
                    <li>Vite</li>
                    <li>Tailwind CSS</li>
                    <li>Chart.js</li>
                  </ul>
                </div>
              </div>
            </div>

            <div>
              <h3 className="font-semibold text-lg mb-2">Funzionalità Dashboard</h3>
              <ul className="list-disc list-inside space-y-1 text-muted-foreground">
                <li>Equity Curve: visualizzazione del saldo nel tempo</li>
                <li>Posizioni aperte: snapshot delle posizioni correnti con PnL</li>
                <li>Operazioni recenti: log delle operazioni con ragionamento e prompt completo</li>
                <li>Selezione modello AI in tempo reale</li>
              </ul>
            </div>

            <div>
              <h3 className="font-semibold text-lg mb-2">Licenza</h3>
              <p className="text-muted-foreground">MIT License</p>
            </div>
          </div>

          <Dialog.Close asChild>
            <button
              className="absolute top-4 right-4 text-muted-foreground hover:text-foreground"
              aria-label="Close"
            >
              <X className="h-5 w-5" />
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

export { VERSION }

