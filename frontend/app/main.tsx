import React, { useState } from 'react'
import ReactDOM from 'react-dom/client'
import './index.css'
import { Toaster } from 'react-hot-toast'
import { ModelSelector } from './components/ModelSelector'
import { Dashboard } from './components/Dashboard'
import { VersionModal, VERSION } from './components/VersionModal'
import logo from '../assets/logo.png'

function App() {
  const [versionModalOpen, setVersionModalOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-200 via-gray-50 to-gray-100 flex flex-col">
      <header className="border-b border-gray-200 p-4 sm:p-6">
        <div className="container mx-auto max-w-[1600px]">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3 sm:gap-4">
              <img
                src={logo}
                alt="Trading Agent Logo"
                className="h-12 sm:h-16 lg:h-20 w-auto"
              />
              <h1 className="text-xl sm:text-2xl lg:text-3xl font-bold text-slate-900 tracking-tight">
                Trading Agent
              </h1>
            </div>
            <div className="w-full sm:w-auto">
              <ModelSelector />
            </div>
          </div>
        </div>
      </header>
      <main className="pb-6 flex-1">
        <Dashboard />
      </main>
      <footer className="border-t border-gray-200 py-3 sm:py-4 mt-auto">
        <div className="container mx-auto max-w-[1600px] px-4 sm:px-6">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-xs sm:text-sm text-muted-foreground">
            <p className="text-center sm:text-left">© {new Date().getFullYear()} Trading Agent Dashboard. All rights reserved.</p>
            <button
              onClick={() => setVersionModalOpen(true)}
              className="hover:text-foreground transition-colors cursor-pointer"
            >
              Versione {VERSION}
            </button>
          </div>
        </div>
      </footer>
      <VersionModal open={versionModalOpen} onOpenChange={setVersionModalOpen} />
      <Toaster position="top-right" />
    </div>
  )
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <Toaster position="top-right" />
    <App />
  </React.StrictMode>,
)
