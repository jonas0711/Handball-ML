'use client'

import React, { Component, ErrorInfo, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: ErrorInfo
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  }

  public static getDerivedStateFromError(error: Error): State {
    // Opdater state så næste render viser fejl UI
    console.error('🚨 ErrorBoundary caught an error:', error)
    return { hasError: true, error }
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log fejlen til console for debugging
    console.error('💥 Uncaught error in React component:', error, errorInfo)
    
    // Opdater state med fejlinformation
    this.setState({
      error,
      errorInfo
    })
  }

  public render() {
    if (this.state.hasError) {
      // Log til console når fejl UI vises
      console.log('🔄 ErrorBoundary rendering error fallback UI')
      
      // Hvis en custom fallback er provided, brug den
      if (this.props.fallback) {
        return this.props.fallback
      }

      // Standard fejl UI
      return (
        <div className="min-h-screen bg-gradient-to-br from-red-50 to-pink-100 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-lg p-8 max-w-lg w-full">
            <div className="text-center">
              {/* Fejl ikon */}
              <div className="text-red-500 text-6xl mb-4">💥</div>
              
              {/* Fejl overskrift */}
              <h1 className="text-2xl font-bold text-gray-800 mb-2">
                Noget gik galt
              </h1>
              
              {/* Fejl beskrivelse */}
              <p className="text-gray-600 mb-6">
                Der opstod en uventet fejl i applikationen. Prøv at genindlæse siden.
              </p>
              
              {/* Fejl detaljer - kun i development mode */}
              {process.env.NODE_ENV === 'development' && this.state.error && (
                <div className="text-left bg-gray-100 rounded-lg p-4 mb-6 max-h-64 overflow-auto">
                  <h3 className="font-semibold text-gray-800 mb-2">Fejl detaljer:</h3>
                  <pre className="text-sm text-red-600 whitespace-pre-wrap">
                    {this.state.error.toString()}
                  </pre>
                  {this.state.errorInfo && (
                    <details className="mt-2">
                      <summary className="cursor-pointer font-semibold text-gray-700">
                        Component Stack
                      </summary>
                      <pre className="text-xs text-gray-600 whitespace-pre-wrap mt-2">
                        {this.state.errorInfo.componentStack}
                      </pre>
                    </details>
                  )}
                </div>
              )}
              
              {/* Action buttons */}
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <button
                  onClick={() => window.location.reload()}
                  className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-2 rounded-lg transition-colors font-medium"
                >
                  🔄 Genindlæs siden
                </button>
                
                <button
                  onClick={() => {
                    // Reset error boundary state
                    this.setState({ hasError: false, error: undefined, errorInfo: undefined })
                    console.log('🔄 ErrorBoundary reset - attempting to recover')
                  }}
                  className="bg-gray-500 hover:bg-gray-600 text-white px-6 py-2 rounded-lg transition-colors font-medium"
                >
                  🔧 Prøv igen
                </button>
              </div>
              
              {/* Footer tekst */}
              <div className="mt-6 pt-4 border-t border-gray-200">
                <p className="text-sm text-gray-500">
                  Hvis problemet fortsætter, kontakt venligst support eller tjek console log for mere information.
                </p>
              </div>
            </div>
          </div>
        </div>
      )
    }

    // Hvis ingen fejl, render children normalt
    return this.props.children
  }
}

// Functional component wrapper for easier usage
export function ErrorBoundaryWrapper({ children, fallback }: Props) {
  return (
    <ErrorBoundary fallback={fallback}>
      {children}
    </ErrorBoundary>
  )
} 