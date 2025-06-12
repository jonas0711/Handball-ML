'use client'

import React from 'react'

// TypeScript interfaces for data structures
interface LeagueData {
  league: string
  total_matches: number
  predictions: any[]
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

interface StatsOverviewProps {
  herrerigaData: LeagueData | null
  kvindeligaData: LeagueData | null
  selectedLeague: 'herreliga' | 'kvindeliga' | 'both'
}

export function StatsOverview({ herrerigaData, kvindeligaData, selectedLeague }: StatsOverviewProps) {
  // Log for debugging - hjælper med at spore hvilke stats der vises
  console.log('📊 StatsOverview rendering with league:', selectedLeague, {
    herrerigaData: !!herrerigaData,
    kvindeligaData: !!kvindeligaData
  })

  // Funktion til at få data baseret på valgt liga
  const getRelevantData = () => {
    if (selectedLeague === 'herreliga') return [herrerigaData]
    if (selectedLeague === 'kvindeliga') return [kvindeligaData]
    return [herrerigaData, kvindeligaData].filter(Boolean) // Fjern null values
  }

  // Kombineret statistik for 'both' selection
  const getCombinedStats = () => {
    const allData = getRelevantData()
    if (allData.length === 0) return null

    const totalMatches = allData.reduce((sum, data) => sum + (data?.total_matches || 0), 0)
    const totalCorrect = allData.reduce((sum, data) => sum + (data?.summary.correct_predictions || 0), 0)
    const combinedAccuracy = totalMatches > 0 ? totalCorrect / totalMatches : 0

    return {
      totalMatches,
      totalCorrect,
      combinedAccuracy,
      herrerigaAccuracy: herrerigaData?.summary.accuracy || 0,
      kvindeligaAccuracy: kvindeligaData?.summary.accuracy || 0
    }
  }

  const relevantData = getRelevantData()
  const combinedStats = getCombinedStats()

  // Hvis ingen data er tilgængelig
  if (!combinedStats || relevantData.length === 0) {
    console.log('⚠️ No stats data available')
    return (
      <div className="text-center py-8">
        <div className="text-gray-400 text-4xl mb-2">📊</div>
        <p className="text-gray-500">Ingen statistikker tilgængelige</p>
      </div>
    )
  }

  // Formatér procenttal
  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`
  }

  // Få farve baseret på accuracy
  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 0.7) return 'text-green-600' // 70%+ er godt
    if (accuracy >= 0.6) return 'text-yellow-600' // 60-70% er ok
    return 'text-red-600' // Under 60% er dårligt
  }

  return (
    <div className="space-y-6">
      {/* Hovedstatistikker */}
      {selectedLeague === 'both' ? (
        // Kombineret view for begge ligaer
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Total Accuracy */}
          <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-l-blue-500">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-800">Samlet Nøjagtighed</h3>
                <div className={`text-3xl font-bold ${getAccuracyColor(combinedStats.combinedAccuracy)}`}>
                  {formatPercentage(combinedStats.combinedAccuracy)}
                </div>
                <p className="text-sm text-gray-500 mt-1">
                  {combinedStats.totalCorrect} af {combinedStats.totalMatches} kampe
                </p>
              </div>
              <div className="text-4xl">🎯</div>
            </div>
          </div>

          {/* Herreliga Stats */}
          {herrerigaData && (
            <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-l-blue-600">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-800">👨 Herreliga</h3>
                  <div className={`text-3xl font-bold ${getAccuracyColor(herrerigaData.summary.accuracy)}`}>
                    {herrerigaData.summary.accuracy_percentage}
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    {herrerigaData.summary.correct_predictions} af {herrerigaData.total_matches} kampe
                  </p>
                </div>
                <div className="text-4xl">👨</div>
              </div>
            </div>
          )}

          {/* Kvindeliga Stats */}
          {kvindeligaData && (
            <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-l-pink-500">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-gray-800">👩 Kvindeliga</h3>
                  <div className={`text-3xl font-bold ${getAccuracyColor(kvindeligaData.summary.accuracy)}`}>
                    {kvindeligaData.summary.accuracy_percentage}
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    {kvindeligaData.summary.correct_predictions} af {kvindeligaData.total_matches} kampe
                  </p>
                </div>
                <div className="text-4xl">👩</div>
              </div>
            </div>
          )}
        </div>
      ) : (
        // Single league view
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {relevantData.map((data) => (
            <React.Fragment key={data?.league}>
              {/* Main accuracy */}
              <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-l-blue-500">
                <div className="text-center">
                  <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Nøjagtighed</h3>
                  <div className={`text-4xl font-bold ${getAccuracyColor(data?.summary.accuracy || 0)} mt-2`}>
                    {data?.summary.accuracy_percentage}
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    {data?.summary.correct_predictions} / {data?.total_matches}
                  </p>
                </div>
              </div>

              {/* Total matches */}
              <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-l-green-500">
                <div className="text-center">
                  <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Kampe Analyseret</h3>
                  <div className="text-4xl font-bold text-green-600 mt-2">
                    {data?.total_matches}
                  </div>
                  <p className="text-sm text-gray-500 mt-1">Test kampe</p>
                </div>
              </div>

              {/* High confidence accuracy */}
              <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-l-purple-500">
                <div className="text-center">
                  <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Høj Sikkerhed</h3>
                  <div className="text-4xl font-bold text-purple-600 mt-2">
                    {formatPercentage(data?.summary.high_confidence_accuracy || 0)}
                  </div>
                  <p className="text-sm text-gray-500 mt-1">
                    {data?.summary.high_confidence_matches} kampe
                  </p>
                </div>
              </div>

              {/* Average confidence */}
              <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-l-orange-500">
                <div className="text-center">
                  <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">Gennemsnitlig Sikkerhed</h3>
                  <div className="text-4xl font-bold text-orange-600 mt-2">
                    {formatPercentage(data?.summary.average_confidence || 0)}
                  </div>
                  <p className="text-sm text-gray-500 mt-1">Model tillid</p>
                </div>
              </div>
            </React.Fragment>
          ))}
        </div>
      )}

      {/* Additional insights */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-gray-800 mb-4">📈 Model Indsigter</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
          {relevantData.map((data) => (
            <React.Fragment key={data?.league}>
              <div className="bg-gray-50 rounded-lg p-4">
                <h4 className="font-medium text-gray-700 mb-2">
                  {data?.league} - Hjemme/Ude Bias
                </h4>
                <div className="space-y-1">
                  <div>Forudsagt hjemme sejr: {formatPercentage(data?.summary.predicted_home_win_rate || 0)}</div>
                  <div>Faktisk hjemme sejr: {formatPercentage(data?.summary.actual_home_win_rate || 0)}</div>
                  <div className="text-xs text-gray-500">
                    Bias: {formatPercentage(Math.abs((data?.summary.predicted_home_win_rate || 0) - (data?.summary.actual_home_win_rate || 0)))}
                  </div>
                </div>
              </div>
            </React.Fragment>
          ))}

          <div className="bg-blue-50 rounded-lg p-4">
            <h4 className="font-medium text-gray-700 mb-2">🎯 Performance Status</h4>
            <div className="space-y-1">
              {combinedStats.combinedAccuracy >= 0.7 ? (
                <div className="text-green-600">🟢 Fremragende performance</div>
              ) : combinedStats.combinedAccuracy >= 0.6 ? (
                <div className="text-yellow-600">🟡 God performance</div>
              ) : (
                <div className="text-red-600">🔴 Forbedring påkrævet</div>
              )}
              <div className="text-xs text-gray-500">
                Baseret på {combinedStats.totalMatches} test kampe
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 