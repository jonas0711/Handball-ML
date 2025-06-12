'use client'

import React from 'react'

// TypeScript interface for prediction data
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

interface PredictionCardProps {
  prediction: Prediction
}

export function PredictionCard({ prediction }: PredictionCardProps) {
  // Log for debugging - hjælper med at spore hvilke predictions bliver vist
  console.log('🃏 Rendering PredictionCard for:', prediction.home_team, 'vs', prediction.away_team)
  
  // Formatér dato til dansk format med weekday
  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return {
      short: date.toLocaleDateString('da-DK', {
        day: '2-digit',
        month: '2-digit', 
        year: 'numeric'
      }),
      long: date.toLocaleDateString('da-DK', {
        weekday: 'long',
        day: 'numeric',
        month: 'long',
        year: 'numeric'
      })
    }
  }

  // Få farve baseret på om forudsigelsen var korrekt
  const getAccuracyColor = (correct: boolean) => {
    return correct ? 'text-green-600 bg-green-50' : 'text-red-600 bg-red-50'
  }

  // Få confidence farve baseret på hvor sikker modellen var
  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.3) return 'text-green-700 bg-green-50 border-green-200' // Høj confidence
    if (confidence >= 0.15) return 'text-yellow-700 bg-yellow-50 border-yellow-200' // Medium confidence  
    return 'text-gray-700 bg-gray-50 border-gray-200' // Lav confidence
  }

  // Få baggrundfarve for hele kortet baseret på accuracy
  const getCardBorderColor = (correct: boolean) => {
    return correct ? 'border-l-green-500' : 'border-l-red-500'
  }

  // Formatér probability til procenttal
  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(1)}%`
  }

  return (
    <div className={`bg-white rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 border-l-4 ${getCardBorderColor(prediction.correct_prediction)} overflow-hidden hover:scale-105`}>
      {/* Header med dato og venue - forbedret layout for lange navne */}
      <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-4 py-3 border-b">
        <div className="flex flex-col gap-2">
          <div className="text-sm font-medium text-blue-800 text-center">
            📅 {formatDate(prediction.match_date).short}
          </div>
          <div className="text-xs text-gray-600 text-center break-words">
            <div className="leading-tight">{prediction.venue}</div>
          </div>
        </div>
      </div>

      {/* Hovedindhold med øget padding */}
      <div className="p-5">
        {/* Hold matchup med responsivt design for lange navne */}
        <div className="text-center mb-6">
          <div className="flex items-start justify-between gap-2">
            {/* Hjemmehold med forbedret styling og plads til lange navne */}
            <div className="flex-1 text-center min-w-0">
              <div className={`text-sm sm:text-base font-bold mb-2 leading-tight break-words ${prediction.predicted_home_win ? 'text-blue-800' : 'text-gray-800'}`}>
                {prediction.home_team}
              </div>
              <div className="text-xs text-blue-600 font-medium bg-blue-100 px-2 py-1 rounded-full mb-2 whitespace-nowrap">
                🏠 Hjemme
              </div>
              {/* Status badges med bedre design */}
              <div className="space-y-1">
                {prediction.predicted_home_win && (
                  <div className="text-xs text-blue-700 bg-blue-50 border border-blue-200 px-2 py-1 rounded-full inline-block">
                    🎯 Forudsagt
                  </div>
                )}
                {prediction.actual_home_win && (
                  <div className="text-xs text-green-700 bg-green-50 border border-green-200 px-2 py-1 rounded-full inline-block">
                    🏆 Vandt
                  </div>
                )}
              </div>
            </div>

            {/* VS separator med responsive størrelse */}
            <div className="px-2 sm:px-4 flex-shrink-0">
              <div className="text-xl sm:text-2xl font-bold text-gray-300 bg-gray-100 rounded-full w-12 h-12 sm:w-14 sm:h-14 flex items-center justify-center shadow-inner">
                VS
              </div>
            </div>

            {/* Udehold med forbedret styling og plads til lange navne */}
            <div className="flex-1 text-center min-w-0">
              <div className={`text-sm sm:text-base font-bold mb-2 leading-tight break-words ${!prediction.predicted_home_win ? 'text-orange-800' : 'text-gray-800'}`}>
                {prediction.away_team}
              </div>
              <div className="text-xs text-orange-600 font-medium bg-orange-100 px-2 py-1 rounded-full mb-2 whitespace-nowrap">
                ✈️ Ude
              </div>
              {/* Status badges med bedre design */}
              <div className="space-y-1">
                {!prediction.predicted_home_win && (
                  <div className="text-xs text-blue-700 bg-blue-50 border border-blue-200 px-2 py-1 rounded-full inline-block">
                    🎯 Forudsagt
                  </div>
                )}
                {!prediction.actual_home_win && (
                  <div className="text-xs text-green-700 bg-green-50 border border-green-200 px-2 py-1 rounded-full inline-block">
                    🏆 Vandt
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Sandsynligheder med forbedret responsive design */}
        <div className="mb-6 bg-gradient-to-r from-indigo-50 to-blue-50 rounded-xl p-4 border border-indigo-100">
          <div className="text-sm font-bold text-indigo-800 mb-4 text-center">📊 Model Sandsynligheder</div>
          <div className="flex flex-col sm:flex-row justify-between items-center gap-4">
            <div className="text-center flex-1 min-w-0">
              <div className="text-xl sm:text-2xl font-bold text-blue-700 mb-2">
                {formatPercentage(prediction.home_win_probability)}
              </div>
              <div className="text-xs text-blue-600 font-medium bg-blue-100 px-2 py-1 rounded-full whitespace-nowrap">
                🏠 Hjemme
              </div>
            </div>
            <div className="text-gray-300 text-xl sm:text-2xl">•</div>
            <div className="text-center flex-1 min-w-0">
              <div className="text-xl sm:text-2xl font-bold text-orange-700 mb-2">
                {formatPercentage(prediction.away_win_probability)}
              </div>
              <div className="text-xs text-orange-600 font-medium bg-orange-100 px-2 py-1 rounded-full whitespace-nowrap">
                ✈️ Ude
              </div>
            </div>
          </div>
        </div>

        {/* Metrics med forbedret responsive design */}
        <div className="space-y-3">
          {/* Accuracy badge */}
          <div className="flex flex-col sm:flex-row justify-between items-center gap-2">
            <span className="text-sm font-bold text-gray-800 whitespace-nowrap">🎯 Resultat:</span>
            <span className={`px-3 py-2 rounded-full text-sm font-bold border-2 whitespace-nowrap ${
              prediction.correct_prediction 
                ? 'text-green-700 bg-green-50 border-green-200' 
                : 'text-red-700 bg-red-50 border-red-200'
            }`}>
              {prediction.correct_prediction ? '✅ Korrekt' : '❌ Forkert'}
            </span>
          </div>

          {/* Confidence */}
          <div className="flex flex-col sm:flex-row justify-between items-center gap-2">
            <span className="text-sm font-bold text-gray-800 whitespace-nowrap">🎲 Sikkerhed:</span>
            <span className={`px-3 py-2 rounded-full text-sm font-bold border-2 whitespace-nowrap ${getConfidenceColor(prediction.confidence)}`}>
              {formatPercentage(prediction.confidence)}
            </span>
          </div>

          {/* Season */}
          <div className="flex flex-col sm:flex-row justify-between items-center gap-2">
            <span className="text-sm font-bold text-gray-800 whitespace-nowrap">📅 Sæson:</span>
            <span className="text-sm font-medium text-gray-700 bg-gray-100 px-3 py-1 rounded-full whitespace-nowrap">
              {prediction.season}
            </span>
          </div>
        </div>

        {/* Detailed prediction info med bedre wrapping */}
        <div className="mt-4 pt-3 border-t border-gray-200">
          <div className="text-xs text-gray-500 space-y-2">
            <div className="break-words">
              <span className="font-medium">Forudsagt:</span> {prediction.predicted_winner}
            </div>
            <div className="break-words">
              <span className="font-medium">Faktisk:</span> {prediction.actual_winner}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
} 