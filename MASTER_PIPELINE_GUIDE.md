# 🏐 Master Handball Data Pipeline Guide

## Oversigt

Master pipeline scriptet `master_handball_pipeline.py` orchestrerer hele handball data pipeline processen automatisk i den korrekte rækkefølge.

## Hvad gør scriptet?

### 🔄 Processen (2 faser for hver liga/sæson):

1. **📥 PDF Download + TXT Konvertering**
   - Kalder `handball_pdf_downloader.py`
   - Downloader PDF'er fra tophaandbold.dk
   - Konverterer automatisk PDFs til TXT-filer

2. **🗄️ TXT → Database Konvertering**
   - Kalder `handball_data_processor.py`
   - Bruger Gemini API til at parse TXT-filer
   - Opretter SQLite databaser med kampdata

### 📅 Processering Rækkefølge:

#### 1️⃣ **Liga Kampe Først** (2024-2025 → 2017-2018)
- **Herreligaen** og **Kvindeligaen**
- For hver sæson: først herrer, så kvinder
- Total: 8 sæsoner × 2 ligaer = 16 kombinationer

#### 2️⃣ **1. Division Bagefter** (2024-2025 → 2018-2019)
- **1. Division Herrer** og **1. Division Damer**
- For hver sæson: først herrer, så damer
- Total: 7 sæsoner × 2 ligaer = 14 kombinationer

### 📊 Total Belastning:
- **30 liga/sæson kombinationer**
- **60 jobs** (30 × 2 faser per kombination)

## 🚀 Sådan Bruger Du Scriptet

### 1. Kør Master Pipeline:
```bash
python master_handball_pipeline.py
```

### 2. Forventet Output:
```
╔══════════════════════════════════════════════════════════════════════════════╗
║                        🏐 HANDBALL DATA PIPELINE 🏐                        ║
║                                                                              ║
║  Master script der håndterer komplet data pipeline:                         ║
║  📥 PDF Download → 📄 TXT Konvertering → 🗄️ Database Oprettelse            ║
║                                                                              ║
║  Processering rækkefølge:                                                    ║
║  1️⃣ Liga kampe (2024-2025 → 2017-2018)                                     ║
║  2️⃣ 1. Division (2024-2025 → 2018-2019)                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

📋 EKSEKUTIONSPLAN:
🎯 Liga kampe (Herreliga & Kvindeliga):
   📅 Sæsoner: 2024-2025, 2023-2024, ..., 2017-2018 (8 sæsoner)
   🏆 Ligaer: herreligaen + kvindeligaen (2 ligaer)
   📊 Jobs: 8 × 2 × 2 faser = 32 jobs

🎯 1. Division kampe:
   📅 Sæsoner: 2024-2025, 2023-2024, ..., 2018-2019 (7 sæsoner)
   🏆 Ligaer: 1-division-herrer + 1-division-damer (2 ligaer)
   📊 Jobs: 7 × 2 × 2 faser = 28 jobs

📈 TOTAL: 60 jobs vil blive kørt

🤔 Vil du starte pipeline? (y/N):
```

### 3. Bekræft Start:
Tryk `y` og Enter for at starte processen.

## 📈 Live Progress Tracking

Scriptet viser detaljeret progression:

```
[16:45:23] 🔄 Starter komplet pipeline: herreligaen 2024-2025 (Liga kampe)
[16:45:23] 📥 Download PDFs + TXT konvertering: herreligaen 2024-2025
[16:45:45] ✅ PDF+TXT fase færdig: herreligaen 2024-2025 (22.3s)
[16:45:45] 📊 Progression: 1/60 jobs (1.7%) | ⏱️ Elapsed: 0.4min | ❌ Fejl: 0

[16:45:46] 🗄️ TXT → Database konvertering: herreligaen 2024-2025
[16:46:12] ✅ TXT→DB fase færdig: herreligaen 2024-2025 (26.1s)
[16:46:12] 📊 Progression: 2/60 jobs (3.3%) | ⏱️ Elapsed: 0.8min | ❌ Fejl: 0
[16:46:12] 🎉 Komplet: herreligaen 2024-2025 - begge faser succesfulde!
```

## 🎯 Features

### ✅ Automatisk Skip Logic:
- Spring over allerede downloadede og validerede PDFs
- Spring over allerede processerede TXT→DB konverteringer
- Intelligent genoptagelse hvis scriptet afbrydes

### 📊 Real-time Statistik:
- Live progression (jobs/total, percentage)
- Elapsed time tracking
- Error counting
- Success rate beregning

### 🎨 Farvekodet Output:
- 🟢 Grøn: Succesfulde operationer
- 🟡 Gul: Advarsler og partielle succeser
- 🔴 Rød: Fejl og mislykkede operationer
- 🔵 Blå: Progress og info meddelelser
- 🟣 Lilla: Headers og fase-skift

### ⚡ Smart Error Handling:
- Fortsætter selvom individuelle jobs fejler
- Detaljeret fejl-rapportering
- Graceful recovery fra netværksfejl

## 🏁 Slutresultat

Ved afslutning får du en samlet rapport:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                            🏁 PIPELINE FÆRDIG                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ⏱️  Total tid: 45.2 minutter (2712 sekunder)
║  📊 Success rate: 96.7% (29/30)
║  ✅ Succesfulde: 29 liga/sæson kombinationer
║  ❌ Fejlede: 1 liga/sæson kombinationer
║  📈 Jobs kørt: 60/60
╚══════════════════════════════════════════════════════════════════════════════╝
```

## 🛠️ Systemkrav

### Dependencies:
- Python 3.8+
- Alle dependencies fra `handball_pdf_downloader.py`
- Alle dependencies fra `handball_data_processor.py`
- Gemini API nøgle i `.env` filen

### Forventet Køretid:
- **Estimat**: 30-60 minutter total
- **Per liga/sæson**: 1-3 minutter
- **Afhænger af**: Internetforbindelse, API hastighed, antal nye filer

## 🔧 Troubleshooting

### Hvis Scriptet Afbrydes:
- **Kør igen**: Scriptet genoptager automatisk og springer over allerede behandlede filer
- **Ctrl+C**: Graceful shutdown med status-rapport

### Hvis Individuelle Jobs Fejler:
- Scriptet fortsætter med næste job
- Fejlede jobs rapporteres i slutstatistikken
- Tjek individuelle script logs for detaljer:
  - `Logs/handball_pdf_downloader.log`
  - `Logs/handball_converter.log`

### Almindelige Problemer:
1. **Gemini API fejl**: Tjek API nøgle i `.env`
2. **Netværksfejl**: Scriptet prøver igen automatisk
3. **Diskplads**: Sørg for tilstrækkelig plads til PDFs og databaser

## 📁 Output Struktur

Efter kørsel vil du have:

```
Handball-ML/
├── Herreliga/
│   ├── 2024-2025/
│   │   ├── match_123456_a.pdf
│   │   └── ...
│   └── 2023-2024/
├── Herreliga-txt-tabel/
│   ├── 2024-2025/
│   │   ├── match_123456_a.txt
│   │   └── ...
├── Herreliga-database/
│   ├── 2024-2025/
│   │   ├── 20240525_GOG_vs_Skjern_Håndbold.db
│   │   └── ...
├── Kvindeliga/... (samme struktur)
├── 1-Division-Herrer/... (samme struktur)
└── 1-Division-Kvinder/... (samme struktur)
```

## 🎉 Resultado

Efter succesfuld kørsel har du:
- ✅ Alle tilgængelige PDFs downloadet
- ✅ Alle PDFs konverteret til TXT
- ✅ Alle TXT filer konverteret til SQLite databaser
- ✅ Komplet handball data pipeline klar til analyse!

---

**💡 Tip**: Kør scriptet på et tidspunkt hvor du ikke har brug for computeren i 30-60 minutter, da det kører mange API kald og downloads. 