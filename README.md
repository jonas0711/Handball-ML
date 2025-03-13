# Håndboldhændelser Konverter

Et værktøj til at konvertere håndboldkamp-tekstfiler til strukturerede JSON-data og SQLite-databaser ved hjælp af Gemini API.

## Oversigt

Dette projekt indeholder scripts til at:

1. Downloade håndboldkamp PDF-filer fra tophaandbold.dk
2. Konvertere PDF-filer til tekst med bevarelse af tabelstruktur
3. Læse håndboldkamp-tekstfiler og dele dem i chunks for at håndtere store filer
4. Konvertere hver chunk til struktureret JSON-data ved hjælp af Gemini API
5. Kombinere JSON-data fra alle chunks
6. Gemme de kombinerede data i en SQLite-database

Projektet inkluderer nu også et komplet workflow-script, der automatiserer hele processen og sikrer at filer ikke behandles dobbelt. Systemet understøtter både Kvindeligaen og Herreligaen, samt forskellige sæsoner.

## Forudsætninger

Før du kører scriptet, skal du have:

1. Python 3.8 eller nyere installeret
2. En gyldig API-nøgle til Gemini API
3. De nødvendige Python-pakker installeret (se requirements.txt)

## Installation

1. Klon dette repository eller download filerne

2. Installer de nødvendige afhængigheder:
   ```
   pip install -r requirements.txt
   ```

3. Sæt din Gemini API-nøgle som miljøvariabel:
   ```
   # På Windows (PowerShell)
   $env:GEMINI_API_KEY = "din-api-nøgle-her"
   
   # På macOS/Linux
   export GEMINI_API_KEY="din-api-nøgle-her"
   ```

## Filstruktur

### Workflow
- `handball_workflow.py` - Master script der kører alle trin og sikrer at filer ikke behandles dobbelt

### Data indsamling
- `handball_pdf_downloader.py` - Script til at downloade PDF-filer fra tophaandbold.dk

### Data konvertering
- `pdf_to_text_converter.py` - Konverterer PDF-filer til tekst med bevarelse af tabelstruktur
- `handball_data_processor.py` - Hovedscript til at konvertere tekstfiler til JSON og SQLite

### Værktøjer og validering
- `database_validator.py` - Værktøj til at tjekke og validere oprettede databaser
- `single_file_tester.py` - Testscript til konvertering af en enkelt fil

### Konfiguration
- `gemini_api_instructions.txt` - System prompt til Gemini API
- `requirements.txt` - Nødvendige Python-pakker
- `.env` - Fil til at gemme API-nøgle lokalt

## Mappestruktur

Systemet opretter automatisk følgende mappestruktur:

```
Handball-ML/
├── Kvindeliga/                  # PDF-filer for Kvindeligaen
│   ├── 2023-2024/               # Sorteret efter sæson
│   └── 2024-2025/
├── Kvindeliga-txt-tabel/        # Konverterede tekstfiler for Kvindeligaen
│   ├── 2023-2024/
│   └── 2024-2025/
├── Kvindeliga-database/         # Databasefiler for Kvindeligaen
│   ├── 2023-2024/
│   └── 2024-2025/
├── Herreliga/                   # PDF-filer for Herreligaen
│   ├── 2023-2024/
│   └── 2024-2025/
├── Herreliga-txt-tabel/         # Konverterede tekstfiler for Herreligaen
│   ├── 2023-2024/
│   └── 2024-2025/
└── Herreliga-database/          # Databasefiler for Herreligaen
    ├── 2023-2024/
    └── 2024-2025/
```

## Brug

### Kør hele workflowet automatisk
```
# Standardindstillinger (Kvindeligaen, sæson 2024-2025)
python handball_workflow.py

# Vælg specifik liga og sæson
python handball_workflow.py --liga=kvindeligaen --sæson=2024-2025
python handball_workflow.py --liga=herreligaen --sæson=2023-2024
```
Dette vil køre alle trin i den korrekte rækkefølge og sikre at filer ikke behandles dobbelt:
1. Downloade nye PDF-filer (springer over allerede downloadede filer)
2. Konvertere PDF-filer til tekst (springer over allerede konverterede filer)
3. Behandle tekstfiler til databaser (springer over allerede behandlede filer)

### Download PDF-filer manuelt
```
python handball_pdf_downloader.py --liga=kvindeligaen --sæson=2024-2025
```

### Konverter PDF-filer til tekst manuelt
```
python pdf_to_text_converter.py --liga=kvindeligaen --sæson=2024-2025
```

### Konvertere en enkelt fil (til test)
```
python single_file_tester.py Kvindeliga-txt-tabel/2024-2025/match_748182_a.txt
```

### Konvertere alle filer i input-mappen manuelt
```
python handball_data_processor.py --liga=kvindeligaen --sæson=2024-2025
```

### Tjekke en oprettet database
```
python database_validator.py Kvindeliga-database/2024-2025/4-9-2024_Ringkøbing_Håndbold_vs_Nykøbing_F._Håndbold.db
```

### Tjekke alle databaser i output-mappen
```
python database_validator.py
```

## Undgå dobbelt databehandling

Projektet implementerer nu robuste tjek på alle niveauer for at undgå dobbelt behandling:

1. **PDF-download tjek**: `handball_pdf_downloader.py` tjekker om en PDF-fil allerede er downloadet og har indhold før den forsøger at downloade den igen.

2. **PDF til TXT tjek**: `pdf_to_text_converter.py` tjekker om en tekstfil allerede er konverteret før den behandler den tilsvarende PDF igen.

3. **TXT til database tjek**: `handball_data_processor.py` tjekker om en tekstfil allerede er behandlet ved at søge efter matchende kamp-ID i de eksisterende databaser.

4. **Workflow integration**: `handball_workflow.py` kører alle scripts i den korrekte rækkefølge og logger resultaterne på en overskuelig måde.

## Understøttede ligaer og sæsoner

Systemet understøtter følgende ligaer:
- **Kvindeligaen** (`--liga=kvindeligaen`)
- **Herreligaen** (`--liga=herreligaen`)

Du kan angive enhver sæson i formatet YYYY-YYYY, f.eks.:
- `--sæson=2023-2024`
- `--sæson=2024-2025`

Systemet vil automatisk oprette de nødvendige mapper og hente data fra den korrekte URL på tophaandbold.dk.

## Datastruktur

De konverterede data gemmes i to tabeller:

### match_info

Indeholder overordnet kampinformation:
- kamp_id: Kampens unikke ID-nummer
- hold_hjemme: Hjemmeholdet
- hold_ude: Udeholdet
- resultat: Slutresultatet
- halvleg_resultat: Resultatet ved halvleg
- dato: Kampens dato
- sted: Spillestedet
- turnering: Turneringens navn

### match_events

Indeholder detaljerede kamphændelser:
- id: Unik hændelses-ID (autoincrement)
- kamp_id: Fremmednøgle til match_info
- tid: Tidspunktet i kampen
- maal: Målstillingen, hvis der scores
- hold: Holdkoden for holdet involveret i hændelsen
- haendelse_1: Den primære hændelse
- pos: Positionen hvorfra hændelsen skete
- nr_1: Spillernummer for primær hændelse
- navn_1: Spillernavn for primær hændelse
- haendelse_2: Sekundær hændelse (hvis relevant)
- nr_2: Spillernummer for sekundær hændelse
- navn_2: Spillernavn for sekundær hændelse
- nr_mv: Målvogterens spillernummer
- mv: Målvogterens navn

## Gemini API Integration

Scriptet bruger Gemini 2.0 Flash Lite modellen til at konvertere tekstdata til JSON. Det sender hver chunk til API'en med en detaljeret system prompt, der beskriver, hvordan teksten skal tolkes og konverteres.

### System Prompt

System prompten indeholder detaljerede instruktioner om:
- Hvilke felter der skal udtrækkes
- Hvordan forskellige linjetyper skal fortolkes
- Regler for korrekt datafelt-tildeling
- Håndtering af målvogterdata vs. sekundære hændelser

## Logging og fejlfinding

Systemet inkluderer omfattende logging:

1. **Workflow log**: `handball_workflow.log` indeholder information om hele kørslen af workflowet.
2. **Konvertering log**: `handball_converter.log` indeholder detaljeret information om konverteringsprocessen.
3. **API kald log**: `api_calls.log` indeholder information om kald til Gemini API.

Hvis du oplever problemer:

1. Kontroller at din API-nøgle er korrekt konfigureret
2. Tjek logfilerne for at identificere eventuelle fejl
3. Kontroller at tekstfilerne har det forventede format
4. Brug `database_validator.py` til at validere de oprettede databaser

## Anbefalinger til yderligere udvikling

1. Implementer en grafisk brugergrænseflade
2. Tilføj flere valideringsregler i system prompten
3. Inkluder dataanalyseværktøjer til at visualisere kamphændelser
4. Implementer batch-behandling af flere filer parallelt
5. Tilføj muligheden for at eksportere til andre formater (CSV, Excel, etc.) 