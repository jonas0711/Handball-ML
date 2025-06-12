'use client'

import { useEffect, useState } from 'react'
import { PredictionCard } from '../components/PredictionCard'
import { LeagueSelector } from '../components/LeagueSelector'
import { StatsOverview } from '../components/StatsOverview'
import { ErrorBoundary } from '../components/ErrorBoundary'

// TypeScript interfaces til at definere datastrukturer
interface Prediction {
  id: number
  match_date: string
  home_team: string
  away_team: string
  season: string
  venue: string
  predicted_home_win: boolean
  actual_home_win: boolean
  home_win_probability: number
  away_win_probability: number
  confidence: number
  correct_prediction: boolean
  predicted_winner: string
  actual_winner: string
  prediction_accuracy: string
}

interface LeagueData {
  league: string
  total_matches: number
  predictions: Prediction[]
  summary: {
    total_matches: number
    correct_predictions: number
    accuracy: number
    accuracy_percentage: string
    predicted_home_wins: number
    actual_home_wins: number
    predicted_home_win_rate: number
    actual_home_win_rate: number
    high_confidence_matches: number
    high_confidence_accuracy: number
    average_confidence: number
    date_range: {
      start: string
      end: string
    }
  }
  last_updated: string
}

export default function HomePage() {
  // State for data management - holder styr på al data fra API'en
  const [herrerigaData, setHerrerigaData] = useState<LeagueData | null>(null)
  const [kvindeligaData, setKvindeligaData] = useState<LeagueData | null>(null)
  const [selectedLeague, setSelectedLeague] = useState<'herreliga' | 'kvindeliga' | 'both'>('both')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Tilføj ny state for sortering
  const [sortBy, setSortBy] = useState<'date_desc' | 'date_asc' | 'confidence_desc' | 'confidence_asc' | 'accuracy'>('date_desc')

  // Console logging for debugging - hjælper med at følge component lifecycle
  console.log('🎯 HomePage component rendering', {
    selectedLeague,
    herrerigaDataLoaded: !!herrerigaData,
    kvindeligaDataLoaded: !!kvindeligaData,
    loading,
    error
  })

  // useEffect hook til at hente data fra API når komponenten loader
  useEffect(() => {
    console.log('📡 Starting data fetch for predictions')
    fetchPredictionsData()
  }, []) // Tom dependency array betyder det kun kører en gang

  // useEffect til at logge sortBy ændringer
  useEffect(() => {
    console.log('🔄 Sort criteria changed to:', sortBy)
  }, [sortBy])

  // Async funktion til at hente forudsigelsesdata fra Flask API
  const fetchPredictionsData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      console.log('🔄 Fetching data from Flask API...')
      
      // Parallel API calls for bedre performance
      const [herrerigaResponse, kvindeligaResponse] = await Promise.all([
        fetch('http://localhost:5000/api/predictions/herreliga'),
        fetch('http://localhost:5000/api/predictions/kvindeliga')
      ])

      console.log('📊 API Response status:', {
        herreriga: herrerigaResponse.status,
        kvindeliga: kvindeligaResponse.status
      })

      // Tjek om API calls var vellykkede
      if (!herrerigaResponse.ok) {
        throw new Error(`Herreliga API error: ${herrerigaResponse.status}`)
      }
      if (!kvindeligaResponse.ok) {
        throw new Error(`Kvindeliga API error: ${kvindeligaResponse.status}`)
      }

      // Parse JSON data
      const herrerigaData = await herrerigaResponse.json()
      const kvindeligaData = await kvindeligaResponse.json()

      console.log('✅ Successfully fetched prediction data:', {
        herrerigaMatches: herrerigaData.total_matches,
        kvindeligaMatches: kvindeligaData.total_matches,
        herrerigaAccuracy: herrerigaData.summary?.accuracy_percentage,
        kvindeligaAccuracy: kvindeligaData.summary?.accuracy_percentage
      })

      // Opdater state med fetched data
      setHerrerigaData(herrerigaData)
      setKvindeligaData(kvindeligaData)

    } catch (err) {
      console.error('❌ Error fetching predictions:', err)
      setError(err instanceof Error ? err.message : 'Ukendt fejl opstod')
    } finally {
      setLoading(false)
      console.log('🏁 Data fetch completed')
    }
  }

  // Funktion til at sortere predictions baseret på valgt kriterium
  const sortPredictions = (predictions: Prediction[]): Prediction[] => {
    console.log(`🔄 Sorting ${predictions.length} predictions by: ${sortBy}`)
    
    return [...predictions].sort((a, b) => {
      switch (sortBy) {
        case 'date_desc':
          // Nyeste først
          const dateA_desc = new Date(a.match_date).getTime()
          const dateB_desc = new Date(b.match_date).getTime()
          if (isNaN(dateA_desc) || isNaN(dateB_desc)) return 0
          return dateB_desc - dateA_desc
        
        case 'date_asc':
          // Ældste først
          const dateA_asc = new Date(a.match_date).getTime()
          const dateB_asc = new Date(b.match_date).getTime()
          if (isNaN(dateA_asc) || isNaN(dateB_asc)) return 0
          return dateA_asc - dateB_asc
        
        case 'confidence_desc':
          // Højeste confidence først
          return (b.confidence || 0) - (a.confidence || 0)
        
        case 'confidence_asc':
          // Laveste confidence først
          return (a.confidence || 0) - (b.confidence || 0)
        
        case 'accuracy':
          // Korrekte predictions først, derefter efter confidence
          if (a.correct_prediction !== b.correct_prediction) {
            return a.correct_prediction ? -1 : 1
          }
          return (b.confidence || 0) - (a.confidence || 0)
        
        default:
          return 0
      }
    })
  }

  // Funktion til at få de predictions der skal vises baseret på valgt liga
  const getDisplayPredictions = (): Prediction[] => {
    console.log(`🔍 Getting display predictions for: ${selectedLeague}`)
    
    let predictions: Prediction[] = []
    
    switch (selectedLeague) {
      case 'herreliga':
        predictions = herrerigaData?.predictions || []
        break
      case 'kvindeliga':
        predictions = kvindeligaData?.predictions || []
        break
      case 'both':
        // Kombiner begge ligaer
        predictions = [
          ...(herrerigaData?.predictions || []),
          ...(kvindeligaData?.predictions || [])
        ]
        break
      default:
        predictions = []
    }
    
    // Anvend sortering
    const sortedPredictions = sortPredictions(predictions)
    
    // Log sorting results for debugging
    if (sortedPredictions.length > 0) {
      console.log('📊 Sorting results:', {
        sortBy,
        firstMatch: {
          date: sortedPredictions[0]?.match_date,
          confidence: sortedPredictions[0]?.confidence,
          correct: sortedPredictions[0]?.correct_prediction
        },
        lastMatch: {
          date: sortedPredictions[sortedPredictions.length - 1]?.match_date,
          confidence: sortedPredictions[sortedPredictions.length - 1]?.confidence,
          correct: sortedPredictions[sortedPredictions.length - 1]?.correct_prediction
        },
        totalMatches: sortedPredictions.length
      })
    }
    
    return sortedPredictions
  }

  // Loading state UI
  if (loading) {
    console.log('⏳ Showing loading state')
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-blue-600 mb-4"></div>
          <h2 className="text-2xl font-semibold text-gray-700">Henter forudsigelser...</h2>
          <p className="text-gray-500 mt-2">Vent venligst mens data indlæses fra AI modellerne</p>
        </div>
      </div>
    )
  }

  // Error state UI
  if (error) {
    console.log('❌ Showing error state:', error)
    return (
      <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-100 flex items-center justify-center">
        <div className="text-center bg-white p-8 rounded-lg shadow-lg max-w-md">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-semibold text-gray-800 mb-2">Fejl ved indlæsning</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button 
            onClick={fetchPredictionsData}
            className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded transition-colors"
          >
            Prøv igen
          </button>
        </div>
      </div>
    )
  }

  const displayPredictions = getDisplayPredictions()
  console.log(`📊 Displaying ${displayPredictions.length} predictions sorted by: ${sortBy}`)

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
        {/* Header section med optimeret layout */}
        <header className="bg-white shadow-lg border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
              <div className="text-center lg:text-left">
                <h1 className="text-4xl lg:text-5xl font-bold text-gray-900 mb-2">
                  🏆 Håndbold AI Forudsigelser
                </h1>
                <p className="text-lg text-gray-600 max-w-2xl">
                  Visualiser og analyser AI model performance på test data fra 2024-2025 sæsonen
                </p>
                <div className="mt-3 text-sm text-gray-500">
                  ⚡ Real-time predictions • 📊 Detaljeret analyse • 🎯 Model insights
                </div>
              </div>
              
              {/* Liga selector med bedre styling */}
              <div className="flex justify-center lg:justify-end">
                <div className="bg-gray-50 p-4 rounded-xl border border-gray-200">
                  <LeagueSelector 
                    selectedLeague={selectedLeague}
                    onLeagueChange={setSelectedLeague}
                  />
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* Stats overview section med forbedret spacing */}
        <div className="bg-gray-50 py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">📊 Model Performance Oversigt</h2>
              <p className="text-gray-600">Real-time statistikker fra AI modellernes predictions på test data</p>
            </div>
            <StatsOverview 
              herrerigaData={herrerigaData}
              kvindeligaData={kvindeligaData}
              selectedLeague={selectedLeague}
            />
          </div>
        </div>

        {/* Predictions grid med optimeret layout */}
        <div className="bg-white py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-10">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">
                🎯 Alle Forudsigelser
              </h2>
              <div className="flex flex-col sm:flex-row justify-center items-center gap-4 text-gray-600 mb-6">
                <span className="flex items-center gap-2">
                  📊 {displayPredictions.length} kampe analyseret
                </span>
                <span className="hidden sm:block">•</span>
                <span className="flex items-center gap-2">
                  🏆 {selectedLeague === 'both' ? 'Begge ligaer' : selectedLeague}
                </span>
              </div>

              {/* Sortering Controls */}
              <div className="flex flex-col sm:flex-row justify-center items-center gap-4 bg-gray-50 rounded-xl p-4 max-w-2xl mx-auto">
                <label className="text-sm font-bold text-gray-800 flex items-center gap-2">
                  🔄 Sorter efter:
                </label>
                <select 
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="bg-white border border-gray-300 rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:border-blue-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-200 transition-colors"
                >
                  <option value="date_desc">📅 Dato (nyeste først)</option>
                  <option value="date_asc">📅 Dato (ældste først)</option>
                  <option value="confidence_desc">🎲 Confidence (høj → lav)</option>
                  <option value="confidence_asc">🎲 Confidence (lav → høj)</option>
                  <option value="accuracy">✅ Nøjagtighed (korrekte først)</option>
                </select>
                
                {/* Sortering status */}
                <div className="text-xs text-gray-500 bg-white px-3 py-1 rounded-full border">
                  {sortBy === 'date_desc' && '📅 Nyeste kampe øverst'}
                  {sortBy === 'date_asc' && '📅 Ældste kampe øverst'}
                  {sortBy === 'confidence_desc' && '🎲 Højeste confidence øverst'}
                  {sortBy === 'confidence_asc' && '🎲 Laveste confidence øverst'}
                  {sortBy === 'accuracy' && '✅ Korrekte predictions øverst'}
                </div>
              </div>
            </div>

            {/* Grid med prediction cards - forbedret responsive design med mere plads */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
              {displayPredictions.map((prediction) => (
                <PredictionCard 
                  key={`${prediction.home_team}-${prediction.away_team}-${prediction.match_date}-${prediction.season}`}
                  prediction={prediction}
                />
              ))}
            </div>

            {/* Empty state med forbedret design */}
            {displayPredictions.length === 0 && (
              <div className="text-center py-16">
                <div className="bg-gray-100 rounded-full w-24 h-24 flex items-center justify-center mx-auto mb-6">
                  <div className="text-gray-400 text-4xl">📊</div>
                </div>
                <h3 className="text-2xl font-semibold text-gray-800 mb-3">
                  Ingen forudsigelser fundet
                </h3>
                <p className="text-gray-600 max-w-md mx-auto">
                  Der blev ikke fundet nogen test data for den valgte liga. 
                  Prøv at vælge en anden liga eller tjek at API'en kører korrekt.
                </p>
                <button 
                  onClick={fetchPredictionsData}
                  className="mt-6 bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-lg transition-colors font-medium"
                >
                  🔄 Genindlæs data
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Footer med systeminfo */}
        <footer className="bg-gray-900 text-white py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div>
                <h3 className="text-lg font-semibold mb-3">🏆 Håndbold AI System</h3>
                <p className="text-gray-300 text-sm">
                  Avanceret AI forudsigelsessystem for dansk håndbold med machine learning baseret på omfattende historiske data.
                </p>
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-3">📊 Teknisk Info</h3>
                <ul className="text-gray-300 text-sm space-y-1">
                  <li>• Flask API Backend (Python)</li>
                  <li>• Next.js Frontend (TypeScript)</li>
                  <li>• Real-time predictions</li>
                  <li>• Test data fra 2024-2025</li>
                </ul>
              </div>
              <div>
                <h3 className="text-lg font-semibold mb-3">🎯 Performance</h3>
                <div className="text-gray-300 text-sm space-y-1">
                  <div className="flex justify-between">
                    <span>Herreliga:</span>
                    <span className="text-yellow-400">{herrerigaData?.summary.accuracy_percentage || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Kvindeliga:</span>
                    <span className="text-green-400">{kvindeligaData?.summary.accuracy_percentage || 'N/A'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Total kampe:</span>
                    <span className="text-blue-400">{(herrerigaData?.total_matches || 0) + (kvindeligaData?.total_matches || 0)}</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="border-t border-gray-700 mt-8 pt-6 text-center text-gray-400 text-sm">
              <p>© 2024 Håndbold AI Forudsigelser Dashboard • Udviklet med Next.js og TailwindCSS</p>
            </div>
          </div>
        </footer>
      </div>
    </ErrorBoundary>
  )
} 