# 🏆 Håndbold AI Forudsigelser Dashboard

Dette er en moderne web-applikation til at visualisere og analysere håndboldmodel forudsigelser for både Herreliga og Kvindeliga. Systemet består af en Python Flask API backend og en React/Next.js frontend.

## 📁 Projektoversigt

### Backend (Flask API)
- **Fil**: `../api_backend.py`
- **Port**: 5000
- **Funktion**: Serverer AI model predictions som JSON via REST API

### Frontend (Next.js App)
- **Mappe**: `handball-ui/`
- **Port**: 3000
- **Funktion**: Moderne UI til at visualisere predictions og statistikker

## 🚀 Sådan starter du systemet

### 1. Start Flask API (Backend)
```bash
# Fra hovedmappen
cd ..
python api_backend.py
```

### 2. Start Next.js Frontend
```bash
# Fra handball-ui mappen
npm run dev
```

### 3. Åbn i browser
- **Frontend UI**: http://localhost:3000
- **API Health Check**: http://localhost:5000/api/health

## 📊 Funktioner

### Hovedfunktioner
- 📈 **Forudsigelser Dashboard**: Se alle AI model predictions for test-data
- 🔄 **Liga Vælger**: Skift mellem Herreliga, Kvindeliga eller begge
- 📊 **Statistik Oversigt**: Detaljerede performance metrics for modellerne
- 🃏 **Prediction Cards**: Individuelle kamp forudsigelser med alle detaljer

### Detaljeret Information for hver kamp
- 🏠 Hjemme vs Ude hold
- 🎯 Model forudsigelse vs faktisk resultat
- 📈 Sandsynligheder for hver side
- 🔍 Model sikkerhed (confidence)
- ✅/❌ Om forudsigelsen var korrekt
- 📅 Kampkategori og sæson

### Statistikker og Analyser
- **Samlet Nøjagtighed**: Hvor ofte modellen forudsiger korrekt
- **Liga-specifik Performance**: Sammenlign Herreliga vs Kvindeliga
- **Hjemme/Ude Bias**: Analyse af model bias
- **Confidence Analyse**: Model sikkerhed vs nøjagtighed
- **Performance Status**: Visuelt feedback på model kvalitet

## 🛠️ Teknisk Stack

### Backend
- **Flask**: Web framework til API
- **Flask-CORS**: Cross-origin requests til frontend
- **Pandas/NumPy**: Data manipulation
- **Scikit-learn**: AI model support

### Frontend
- **Next.js 14**: React framework med App Router
- **TypeScript**: Type-sikker JavaScript
- **TailwindCSS**: Utility-first CSS framework
- **ShadCN/UI**: Moderne UI komponenter

## 📡 API Endpoints

### Tilgængelige Endpoints
- `GET /api/health` - Health check
- `GET /api/predictions/herreliga` - Herreliga predictions
- `GET /api/predictions/kvindeliga` - Kvindeliga predictions  
- `GET /api/predictions` - Begge ligaer kombineret
- `GET /api/team-performance/<league>` - Team-specifik performance

### Eksempel Response
```json
{
  "league": "Herreliga",
  "total_matches": 150,
  "predictions": [
    {
      "id": 1,
      "match_date": "2024-10-15",
      "home_team": "Team A",
      "away_team": "Team B",
      "predicted_home_win": true,
      "actual_home_win": false,
      "home_win_probability": 0.65,
      "confidence": 0.30,
      "correct_prediction": false
    }
  ],
  "summary": {
    "accuracy": 0.72,
    "accuracy_percentage": "72.0%",
    "total_matches": 150,
    "correct_predictions": 108
  }
}
```

## 🎨 UI Komponenter

### Hovedkomponenter
- **HomePage**: Hovedside med dashboard layout
- **PredictionCard**: Individuelle kamp forudsigelser
- **LeagueSelector**: Liga valg komponenter  
- **StatsOverview**: Overordnede statistikker
- **ErrorBoundary**: Fejlhåndtering

### Design Principper
- 📱 **Responsivt design** - fungerer på alle skærmstørrelser
- 🎨 **Moderne UI** - ren og intuitive brugeroplevelse
- 🚀 **Performance** - optimeret med caching og lazy loading
- ♿ **Tilgængelighed** - ARIA labels og keyboard navigation
- 🔍 **Debugging** - omfattende console logging

## 🚦 Status Indikationer

### Forudsigelse Status
- ✅ **Grøn**: Korrekt forudsigelse
- ❌ **Rød**: Forkert forudsigelse
- 📊 **Blå**: Model forudsigelse
- 🎯 **Grøn highlight**: Faktisk vinder

### Performance Farver
- 🟢 **Grøn**: Fremragende (70%+ accuracy)
- 🟡 **Gul**: God (60-70% accuracy)
- 🔴 **Rød**: Forbedring påkrævet (<60% accuracy)

## 🐛 Debugging

### Console Logs
Alle komponenter har detaljeret console logging for debugging:
- 🚀 Component lifecycle events
- 📡 API requests og responses
- 🎯 Data transformationer
- ❌ Fejl og warnings

### Browser DevTools
Åbn browser DevTools (F12) for at se:
- Network tab: API calls
- Console tab: Debug logs
- Elements tab: Component struktur

## 📈 Performance Tips

### Optimering
- **API Caching**: 5 minutters cache på predictions
- **Parallel Requests**: Begge ligaer hentes samtidigt
- **Error Boundaries**: Graceful fejlhåndtering
- **Loading States**: Brugervenlige loading indikatorer

### Skalering
- Systemet kan håndtere hundredvis af kampe
- Responsivt design til alle enheder
- Optimeret for ASUS Vivobook S 15 hardware

## 🔧 Fejlfinding

### Almindelige problemer
1. **API ikke tilgængelig**: Tjek at Flask serveren kører på port 5000
2. **CORS fejl**: Sørg for Flask-CORS er installeret
3. **Ingen data**: Verificer at ML modeller og data eksisterer
4. **UI fejl**: Tjek console logs i browser

### Support
For støtte, tjek:
- Console logs i browser
- Flask server output
- API endpoint responses
- Network tab i DevTools

---

**Oprettet af**: AI Assistant  
**Version**: 1.0  
**Dato**: December 2024 