import { useEffect, useState, useRef } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export function SystemLogs() {
  const [logs, setLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const scrollRef = useRef<HTMLDivElement>(null)

  const fetchLogs = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/system-logs?lines=200`)
      if (res.ok) {
        const data = await res.json()
        setLogs(data.logs)
      }
    } catch (error) {
      console.error('Error fetching system logs:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
    const interval = setInterval(fetchLogs, 5000) // Poll every 5s
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs])

  return (
    <div className="bg-[#1e1e1e] text-gray-300 rounded-lg border border-gray-700 shadow-sm overflow-hidden flex flex-col h-full max-h-[400px]">
      <div className="bg-[#2d2d2d] px-4 py-2 border-b border-gray-700 flex justify-between items-center">
        <h3 className="text-sm font-mono font-bold text-white flex items-center gap-2">
          <span className="text-green-400">➜</span> System Logs
        </h3>
        <div className="flex items-center gap-2">
             <button 
                onClick={fetchLogs} 
                className="p-1 hover:bg-[#3d3d3d] rounded text-gray-400 hover:text-white transition-colors"
                title="Aggiorna log"
            >
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
            </button>
            <span className="text-[10px] text-gray-500 bg-[#1e1e1e] px-2 py-0.5 rounded border border-gray-700">tail -n 200</span>
        </div>
      </div>
      
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-1 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-transparent"
      >
        {loading && logs.length === 0 ? (
          <div className="text-gray-500 italic">Loading logs...</div>
        ) : logs.length === 0 ? (
          <div className="text-gray-500 italic">No logs available.</div>
        ) : (
          logs.map((log, i) => (
            <div key={i} className="whitespace-pre-wrap break-all hover:bg-[#2d2d2d] px-1 -mx-1 rounded">
              {log}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
