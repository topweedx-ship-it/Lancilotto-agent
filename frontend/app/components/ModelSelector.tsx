import { useEffect, useState } from 'react'

interface CurrentModel {
    id: string
    name: string
    model_id: string
    provider: string
    available: boolean
}

// Use relative URLs in development (via Vite proxy) or absolute URL if VITE_API_URL is set
const API_BASE_URL = import.meta.env.VITE_API_URL || ''

export function ModelSelector() {
    const [currentModel, setCurrentModel] = useState<CurrentModel | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetchCurrentModel()
    }, [])

    const fetchCurrentModel = async () => {
        try {
            const response = await fetch(`${API_BASE_URL}/api/models/current`)
            if (!response.ok) throw new Error('Failed to fetch current model')
            const data = await response.json()
            setCurrentModel(data)
        } catch (error) {
            console.error('Error fetching current model:', error)
        } finally {
            setLoading(false)
        }
    }

    if (loading) {
        return (
            <div className="flex items-center gap-2 text-xs sm:text-sm text-muted-foreground">
                <span>Caricamento modello...</span>
            </div>
        )
    }

    if (!currentModel) {
        return (
            <div className="flex items-center gap-2 text-xs sm:text-sm text-muted-foreground">
                <span>Nessun modello disponibile</span>
            </div>
        )
    }

    return (
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-2 sm:gap-3">
            <span className="text-xs sm:text-sm text-muted-foreground hidden sm:inline">Modello:</span>
            <div className="flex items-center gap-2 px-2.5 sm:px-3 py-1.5 text-xs sm:text-sm bg-background border border-input rounded-md w-full sm:w-auto">
                <span className="font-medium">{currentModel.name}</span>
                <span className="text-[10px] sm:text-xs text-muted-foreground">
                    ({currentModel.provider})
                </span>
            </div>
            <div className="flex items-center gap-1 text-[10px] sm:text-xs text-muted-foreground">
                <span className="px-2 py-1 bg-muted rounded-sm truncate max-w-[200px] sm:max-w-none">
                    {currentModel.model_id}
                </span>
            </div>
        </div>
    )
}
