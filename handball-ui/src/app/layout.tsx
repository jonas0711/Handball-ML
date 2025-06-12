import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

// Initialiserer Inter skrifttype fra Google Fonts
// Inter er en moderne, læsbar skrifttype perfekt til UI'er
const inter = Inter({ subsets: ['latin'] })

// Metadata for hele applikationen - vises i browser tabs og søgemaskiner
export const metadata: Metadata = {
  title: 'Håndbold Forudsigelser - AI Model Dashboard',
  description: 'Visualiser og analyser håndboldmodel forudsigelser for Herreliga og Kvindeliga',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  // Log til console for debugging - hjælper med at spore app lifecycle
  console.log('🚀 Root Layout rendering - Application starting')
  
  return (
    <html lang="da">
      <body className={inter.className}>
        {/* 
          Main wrapper div med responsivt design
          - min-h-screen: Fylder mindst hele skærmhøjden
          - bg-background: Bruger CSS custom property fra globals.css
          - text-foreground: Standard tekstfarve
        */}
        <div className="min-h-screen bg-background text-foreground">
          {children}
        </div>
      </body>
    </html>
  )
} 