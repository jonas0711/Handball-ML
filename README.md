# Håndboldhændelser Konverter

Et værktøj til at konvertere håndboldkamp-tekstfiler til strukturerede JSON-data og SQLite-databaser ved hjælp af Gemini API.

## Oversigt

Dette projekt indeholder scripts til at:

1. Læse håndboldkamp-tekstfiler (konverteret fra PDF)
2. Dele dem i chunks for at håndtere store filer
3. Konvertere hver chunk til struktureret JSON-data ved hjælp af Gemini API
4. Kombinere JSON-data fra alle chunks
5. Gemme de kombinerede data i en SQLite-database

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

- `handball_converter.py` - Hovedscriptet til konvertering
- `system_prompt_chunk.txt` - System prompt til Gemini API
- `check_database.py` - Værktøj til at tjekke oprettede databaser
- `test_conversion.py` - Testscript til en enkelt fil
- `requirements.txt` - Nødvendige Python-pakker

## Brug

### Konvertere en enkelt fil (til test)

```
python test_conversion.py Kvindeliga-txt-tabel/2024-2025/match_748182_a.txt
```

### Konvertere alle filer i input-mappen

```
python handball_converter.py
```

### Tjekke en oprettet database

```
python check_database.py Kvindeliga-database/4-9-2024_Ringkøbing_Håndbold_vs_Nykøbing_F._Håndbold.db
```

### Tjekke alle databaser i output-mappen

```
python check_database.py
```

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

## Fejlfinding

Hvis du oplever problemer:

1. Kontroller at din API-nøgle er korrekt konfigureret
2. Tjek logfilerne (`handball_converter.log` eller `test_conversion.log`)
3. Kontroller at tekstfilerne har det forventede format
4. Brug `check_database.py` til at validere de oprettede databaser

## Anbefalinger til yderligere udvikling

1. Implementer en grafisk brugergrænseflade
2. Tilføj flere valideringsregler i system prompten
3. Inkluder dataanalyseværktøjer til at visualisere kamphændelser
4. Implementer batch-behandling af flere filer parallelt
5. Tilføj muligheden for at eksportere til andre formater (CSV, Excel, etc.) 