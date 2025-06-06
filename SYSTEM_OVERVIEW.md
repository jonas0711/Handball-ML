# 🏆 HANDBALL ML SYSTEM - OVERSIGT

## 🎯 **AKTIVE SYSTEMER (MUST KEEP)**

### 🏐 **ELO Systemer (Core)**
- `handball_elo_master.py` - **MASTER SPILLER ELO** (bruges normalt)
- `herreliga_team_seasonal_elo.py` - **HERRELIGA TEAM ELO** (separate system)
- `kvindeliga_team_seasonal_elo.py` - **KVINDELIGA TEAM ELO** (separate system)
- `team_seasonal_elo_system.py` - **KOMBINERET TEAM ELO** (backup system)

### 🌐 **Hovedapplikationer**
- `app.py` - **WEB INTERFACE** (hovedapplikation)
- `dataset.py` - **DATA PROCESSING** (core functionality)
- `player_team_statistics.py` - **STATISTIKKER** (bruges normalt)

### 🔄 **Data Pipeline**
- `master_handball_pipeline.py` - **MASTER PIPELINE** (koordinering)
- `handball_data_processor.py` - **DATA PROCESSOR** (core processing)
- `process_all_seasons.py` - **SÆSON PROCESSING** (bruges til bulk updates)

### 📄 **Data Conversion**
- `txt_to_db_manual_converter.py` - **TXT TIL DB** (bruges til ny data)
- `pdf_to_text_converter.py` - **PDF TIL TEXT** (bruges til ny data)

## ⚠️ **ARKIV KANDIDATER (Can Archive)**

### 🧪 **Udviklingsscripts**
- `advanced_handball_elo_system.py` - Tidligere ELO version
- `handball_ml_ultimate_features.py` - Feature development
- `handball_workflow.py` - Workflow experiments
- `complete.py` - Legacy processing

### 📥 **Download Scripts**
- `handball_pdf_downloader.py` - PDF download (bruges sjældent)

## 📁 **ALLEREDE ORGANISERET**

### ✅ **ELO_Results/**
- Alle CSV resultater organiseret efter type og liga
- Player_Seasonal_CSV/ - Spiller sæsonresultater
- Team_CSV/ - Hold resultater (opdelt efter liga)
- Analysis_CSV/ - Analyse og validering

### ✅ **Archive/**
- Old_Scripts/ - Gamle analyse scripts
- Gamle data filer (advanced_elo_data.json, etc.)

## 🗂️ **DATABASE DIRECTORIES (KEEP)**
- `Herreliga-database/` - Herreliga kampe
- `Kvindeliga-database/` - Kvindeliga kampe
- `1-Division-*-database/` - 1. division kampe
- Alle txt-tabel directories

## 📋 **CONFIGURATION FILES (KEEP)**
- `data.md` - **DATABASE DOKUMENTATION**
- `README.md` - Projekt dokumentation
- `requirements.txt` - Python dependencies
- `.gitignore` - Git konfiguration

---
**📅 Opdateret:** December 2024  
**🎯 Status:** Organiseret og ryddet op 