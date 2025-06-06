# HÅNDBOL ELO SYSTEM - KOMPLET ANALYSE OG PLAN

## 🎯 PROJEKTMÅL

Vi ønsker at udvikle et komplet ELO-system for danske håndboldholdligaer baseret på detaljerede kampdata fra 2018-2019 til 2024-2025. Systemet skal kunne:

1. **Spillerklassificering**: Kategorisere hver spiller i position og klub baseret på datamønster
2. **Multi-sæson ELO**: Køre på tværs af sæsoner men også individuelt per sæson 
3. **Intelligent overførsel**: Startratings for nye sæsoner baseret på tidligere performance
4. **Klubskifte håndtering**: Håndtere spillere der skifter klub mellem sæsoner
5. **ML dataset**: Skabe features til machine learning forudsigelser

## 📊 DATA STRUKTUR (baseret på data.md)

### Database Filer
- **Herreliga-database/[sæson]/[kamp].db** - hver fil er én kamp
- **Kvindeliga-database/[sæson]/[kamp].db** - kvindeligaen (ikke i scope pt.)

### Tabeller per kamp
- **match_info**: Grundlæggende kampinfo (hold, resultat, dato, etc.)
- **match_events**: Detaljerede hændelser kronologisk

### Spilleridentifikation i events
- **navn_1 + nr_1**: Primær spiller - tilhører holdet i "hold" feltet
- **navn_2 + nr_2**: Sekundær spiller - hold afhænger af hændelse type:
  - "Assist": Samme hold som primær
  - "Bold erobret", "Forårs. str.", "Blokeret af": Modstanderhold
- **mv + nr_mv**: Målvogter - tilhører ALTID modstanderholdet ved målrelaterede hændelser

### Positionsdata
- **pos felt**: Angiver position for hændelsen (Gbr, PL, 2:e, ST, 1:e, HF, VF, VB, HB)
- **Målvogtere identificeres IKKE gennem pos** - kun gennem mv/nr_mv felter!

## 🔍 ANALYSE AF NUVÆRENDE SYSTEMER

### handball_elo_master.py - Status ✅❌
**Styrker:**
- ✅ Korrekt målvogteridentifikation gennem nr_mv/mv felter
- ✅ Position mapping til 7 standardpositioner
- ✅ Intelligent holdtilknytning baseret på hændelsestype
- ✅ Avanceret action vægtning med kontekst

**Problemer identificeret:**
- ❌ Ingen sæson-specifik ELO tracking
- ❌ Ingen systematisk klubtilknytning for spillere
- ❌ Ingen carryover mellem sæsoner
- ❌ Position kun baseret på enkelte hændelser, ikke samlet tælling

### handball_ml_ultimate_features.py - Status ✅❌
**Styrker:**
- ✅ Omfattende feature engineering
- ✅ Sæson-baseret processing
- ✅ ELO carryover mellem sæsoner (basic)

**Problemer identificeret:**
- ❌ Mangelfuld spillerposition klassificering
- ❌ Ingen detaljeret klubtilknytning
- ❌ Utilstrækkelig målvogteridentifikation
- ❌ Ingen individuel sæson ELO tracking

## 🎯 KRAV TIL NYT SYSTEM

### 1. Spillerpositions-klassificering
- **Metode**: Tæl aktioner per position for hver spiller gennem alle kampe
- **Standard positioner**: VF, VB, PL, HB, HF, ST, MV
- **Hovedposition**: Den position spilleren har flest aktioner på
- **Målvogtere**: Kun identificeret gennem nr_mv/mv felter (IKKE pos)
- **Mapping af pos-felter**:
  - VF → VF (Venstre fløj)
  - VB → VB (Venstre back)  
  - PL → PL (Playmaker)
  - HB → HB (Højre back)
  - HF → HF (Højre fløj)
  - ST → ST (Streg)
  - Gbr → VB (Gennembrud dette er ikke en position men et udtryk for at en spiller har spillet sig til en fri chance og dermed et nærskud - enten via en finte hvor spilleren kommer fri, eller hvor holdet har spillet sig til en hel fri chance)
  - 1:e → HB (Første bølge er en fri kontra)
  - 2:e → PL (Anden bølge er en kontrafase hvor holdet rammer modstanderholdet i ubalance da forsvarsholdet løber retur fra deres eget angreb)

### 2. Klubtilknytning
- **Per sæson**: Tæl hvor mange gange spilleren optræder for hver klub
- **Hovedklub**: Den klub spilleren har flest optræden for i sæsonen
- **Fejlhåndtering**: Hvis spiller optræder 90% for klub A og 10% for klub B → hovedklub A
- **Klubskifte**: Spillere kan have forskellige hovedklubber i forskellige sæsoner

### 3. Multi-sæson ELO struktur
```
Spiller ELO = {
    "samlet_elo": 1500,           # ELO på tværs af alle sæsoner
    "2018-2019": 1450,            # Individuel sæson ELO
    "2019-2020": 1520,            # Individuel sæson ELO  
    "2020-2021": 1580,            # Individuel sæson ELO
    ...
}
```

### 4. Sæson carryover algoritme
```python
# Ved sæsonstart
ny_sæson_start_elo = (forrige_sæson_slut_elo * 0.8) + (samlet_elo * 0.2)

# Eksempel: 
# Spiller sluttede 2022-23 med 1600 ELO
# Samlet ELO er 1550
# Start 2023-24: (1600 * 0.8) + (1550 * 0.2) = 1280 + 310 = 1590
```

### 5. ELO systemparametre
- **K-faktorer**: Team=16, Spiller=8, Målvogter=5
- **Rating bounds**: 900-1700
- **Start ratings**: Nye spillere=1200, Målvogtere=1300
- **Action vægte**: Optimeret per position

## 🛠️ IMPLEMENTATIONSPLAN

### Fase 1: Data Preprocessing ✅
1. **Spillerpositions-tæller**: Bygge komplet positions-profil for hver spiller
2. **Klubtilknytningstæller**: Bygge sæson-specifik klubtilknytning
3. **Datarensning**: Identificere og håndtere dataanomalier

### Fase 2: Core ELO System ⚡
1. **Multi-sæson struktur**: Implementere dual ELO tracking
2. **Sæson carryover**: Intelligent startrating beregning
3. **Position-specifik vægtning**: Optimerede K-faktorer per position
4. **Målvogter specialisering**: Korrekt identifikation og vægtning

### Fase 3: Advanced Features 🚀
1. **Momentum tracking**: Seneste spils påvirkning på ELO
2. **Kontekst vægtning**: Kampens betydning påvirker ELO ændringer
3. **Klub-baserede features**: Samlede holdratings baseret på spillere
4. **Head-to-head historik**: Holdspecifikke møder

### Fase 4: ML Dataset Generation 📊
1. **Feature engineering**: Omfattende sæt af ELO-baserede features
2. **Historiske features**: ELO inden kamp som features
3. **Performance metrics**: Sammenligne forskellige modeller
4. **Prediction pipeline**: Forudsigelse af kommende kampe

## 🔧 TEKNISK ARKITEKTUR

### Core Classes
```python
class AdvancedHandballEloSystem:
    - SpillerPositionAnalyzer    # Positionsklassificering
    - KlubtilknytningTracker     # Klubtilknytning per sæson  
    - MultiSeasonEloManager      # Dual ELO tracking
    - SæsonCarryoverCalculator   # Intelligent overførsel
    - MålvogterSpecialist        # Målvogter identifikation
    - FeatureGenerator           # ML features
```

### Data Flow
```
Raw Database → Position Analysis → Club Assignment → 
Multi-Season ELO → Feature Generation → ML Dataset
```

## 📈 FORVENTEDE RESULTATER

### Spillerprofile eksempel
```python
{
    "navn": "Anders Hansen",
    "hovedposition": "PL",
    "positions_fordeling": {"PL": 156, "HB": 23, "VB": 8},
    "sæson_klubber": {
        "2022-23": "AAH",
        "2023-24": "SKH"  # Klubskifte
    },
    "elo_historie": {
        "samlet": 1650,
        "2022-23": 1580,
        "2023-24": 1720
    }
}
```

### Hold features
```python
{
    "AAH": {
        "hold_elo": 1545,
        "gennemsnit_spiller_elo": 1487,
        "målvogter_elo": 1623,
        "højeste_spiller_elo": 1734,
        "position_styrke": {
            "MV": 1623, "VF": 1456, "VB": 1501,
            "PL": 1734, "HB": 1445, "HF": 1398, "ST": 1512
        }
    }
}
```

## 🎯 SUCCESS KRITERIER

1. **Positionsnøjagtighed**: >95% korrekt positionsklassificering
2. **Klubnøjagtighed**: >98% korrekt klubtilknytning per sæson
3. **ELO stability**: Stabile ratings over sæsoner med naturlig variation
4. **Målvogter identifikation**: 100% korrekt identificering
5. **ML performance**: Forudsigelses accuracy >65% på kampresultater

## 📋 NÆSTE SKRIDT

1. **Analyser nuværende kode** grundigt for at identificere alle problemer
2. **Implementér SpillerPositionAnalyzer** med korrekt pos-mapping og målvogter logic
3. **Bygge KlubtilknytningTracker** med sæson-specifik clustering
4. **Redesigne ELO core** med multi-sæson struktur
5. **Teste på små datasæt** før fuld implementering
6. **Validere resultater** mod kendt data

Systemet skal være robust, skalerbart og producere pålidelige ratings til både analyse og machine learning. 