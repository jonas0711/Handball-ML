# 🏆 HANDBALL ELO SYSTEM - RESULTATER

Denne mappe indeholder alle organiserede resultater fra håndbol ELO systemerne.

## 📁 MAPPESTRUKTUR

### 🎯 **Player_Seasonal_CSV/**
Sæson-baserede spiller ELO resultater:
- `herreliga_seasonal_elo_YYYY_YYYY.csv` - Herreliga sæsonresultater

### 🏐 **Team_CSV/**
Hold-baserede ELO resultater organiseret efter liga:

#### **Herreliga/**
- `herreliga_team_seasonal_elo_YYYY_YYYY.csv` - Sæsonresultater
- `herreliga_team_career_analysis.csv` - Karriere analyse
- `herreliga_team_seasonal_summary_report.csv` - Samlet rapport

#### **Kvindeliga/**
- `kvindeliga_team_seasonal_elo_YYYY_YYYY.csv` - Sæsonresultater  
- `kvindeliga_team_career_analysis.csv` - Karriere analyse
- `kvindeliga_team_seasonal_summary_report.csv` - Samlet rapport

#### **Combined/**
- `team_seasonal_elo_YYYY_YYYY.csv` - Kombinerede sæsonresultater
- `team_career_analysis.csv` - Kombineret karriere analyse
- `team_seasonal_summary_report.csv` - Kombineret rapport

### 📊 **Analysis_CSV/**
Analyse og validerings data:
- `positional_bias_*.csv` - Positions bias analyser
- `position_distribution_*.csv` - Positions fordeling
- `advanced_player_profiles.csv` - Detaljerede spiller profiler

## 🔄 BRUG AF RESULTATER

### Aktive ELO Systemer (rod-mappen):
- `handball_elo_master.py` - Master spiller ELO system
- `herreliga_team_seasonal_elo.py` - Herreliga team ELO
- `kvindeliga_team_seasonal_elo.py` - Kvindeliga team ELO  
- `team_seasonal_elo_system.py` - Kombineret team ELO

### Hovedapplikationer:
- `app.py` - Hovedapplikation med web interface
- `dataset.py` - Data processering
- `player_team_statistics.py` - Spiller/team statistikker

---
**📅 Opdateret:** December 2024  
**🎯 Formål:** Organiseret opbevaring af ELO system resultater 