'use client'

import React from 'react'

interface LeagueSelectorProps {
  selectedLeague: 'herreliga' | 'kvindeliga' | 'both'
  onLeagueChange: (league: 'herreliga' | 'kvindeliga' | 'both') => void
}

export function LeagueSelector({ selectedLeague, onLeagueChange }: LeagueSelectorProps) {
  // Log for debugging - hjælper med at spore league selection changes
  console.log('🔄 LeagueSelector rendering with selected league:', selectedLeague)

  // Handler function til at håndtere league changes
  const handleLeagueChange = (newLeague: 'herreliga' | 'kvindeliga' | 'both') => {
    console.log('🏆 League selection changing from', selectedLeague, 'to', newLeague)
    onLeagueChange(newLeague)
  }

  // Få styling for buttons baseret på om de er aktive
  const getButtonClass = (league: 'herreliga' | 'kvindeliga' | 'both') => {
    const baseClasses = "px-4 py-2 text-sm font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
    
    if (selectedLeague === league) {
      // Active state - blå baggrund og hvid tekst
      return `${baseClasses} bg-blue-600 text-white shadow-md hover:bg-blue-700`
    } else {
      // Inactive state - grå baggrund og mørk tekst
      return `${baseClasses} bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300`
    }
  }

  // Få emoji for hver liga type
  const getLeagueEmoji = (league: 'herreliga' | 'kvindeliga' | 'both') => {
    switch (league) {
      case 'herreliga':
        return '👨'
      case 'kvindeliga':
        return '👩'
      case 'both':
        return '⚽'
      default:
        return ''
    }
  }

  // Få display navn for hver liga
  const getLeagueDisplayName = (league: 'herreliga' | 'kvindeliga' | 'both') => {
    switch (league) {
      case 'herreliga':
        return 'Herreliga'
      case 'kvindeliga':
        return 'Kvindeliga'
      case 'both':
        return 'Begge Ligaer'
      default:
        return ''
    }
  }

  return (
    <div className="flex flex-col sm:flex-row gap-2">
      {/* Label for mobile accessibility */}
      <div className="sr-only sm:not-sr-only text-sm font-medium text-gray-700 flex items-center mb-2 sm:mb-0 sm:mr-3">
        Liga valg:
      </div>
      
      {/* Button group */}
      <div className="flex rounded-lg bg-gray-50 p-1 border border-gray-200">
        {/* Herreliga button */}
        <button
          onClick={() => handleLeagueChange('herreliga')}
          className={getButtonClass('herreliga')}
          type="button"
          aria-pressed={selectedLeague === 'herreliga'}
          title="Vis kun Herreliga forudsigelser"
        >
          <span className="flex items-center gap-2">
            <span>{getLeagueEmoji('herreliga')}</span>
            <span>{getLeagueDisplayName('herreliga')}</span>
          </span>
        </button>

        {/* Kvindeliga button */}
        <button
          onClick={() => handleLeagueChange('kvindeliga')}
          className={getButtonClass('kvindeliga')}
          type="button"
          aria-pressed={selectedLeague === 'kvindeliga'}
          title="Vis kun Kvindeliga forudsigelser"
        >
          <span className="flex items-center gap-2">
            <span>{getLeagueEmoji('kvindeliga')}</span>
            <span>{getLeagueDisplayName('kvindeliga')}</span>
          </span>
        </button>

        {/* Both leagues button */}
        <button
          onClick={() => handleLeagueChange('both')}
          className={getButtonClass('both')}
          type="button"
          aria-pressed={selectedLeague === 'both'}
          title="Vis forudsigelser for begge ligaer"
        >
          <span className="flex items-center gap-2">
            <span>{getLeagueEmoji('both')}</span>
            <span>{getLeagueDisplayName('both')}</span>
          </span>
        </button>
      </div>

      {/* Active selection indicator for screen readers */}
      <div className="sr-only">
        Aktuel valg: {getLeagueDisplayName(selectedLeague)}
      </div>
    </div>
  )
} 