#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Håndboldhændelser Manual TXT til DB Konverter

Dette script konverterer manuelt TXT filer til DB filer, hvilket er nyttigt 
når der opstår fejl i det almindelige workflow.

Konfigurer scriptet ved at ændre variablerne i KONFIGURATION-sektionen 
og kør derefter scriptet direkte:

    python txt_to_db_manual_converter.py

Du kan også bruge kommandolinjeargumenter:

    # Konverter en enkelt fil
    python txt_to_db_manual_converter.py --file=Kvindeliga-txt-tabel/2024-2025/match_123456_a.txt --output=Mine-DB-Filer
    
    # Konverter alle filer i en mappe
    python txt_to_db_manual_converter.py --folder=Kvindeliga-txt-tabel/2024-2025 --output=Mine-DB-Filer
"""

import os
import sys
import re
import json
import glob
import sqlite3
import time
import logging
import argparse
import hashlib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# ======================================================
# KONFIGURATION - Ændr disse variabler efter behov
# ======================================================
# Vælg enten INPUT_FILE eller INPUT_FOLDER (sæt den anden til None)
#INPUT_FILE = "Kvindeliga-txt-tabel/2024-2025/match_748182_a.txt"  # Specifik fil at konvertere
INPUT_FILE = None  # Kommentér ud denne linje og fjern # fra linjen ovenfor for at konvertere enkelt fil

#INPUT_FOLDER = None  # Mappe med TXT filer at konvertere
INPUT_FOLDER = "Herreliga-txt-tabel/2023-2024"  # Kommentér ud denne linje og fjern # for at konvertere en mappe

# Output mappe (sæt til None for at bruge standard placering)
#OUTPUT_DIR = None  # Automatisk baseret på input sti
OUTPUT_DIR = "Herreliga-database/2023-2024"  # Specifik output mappe

# Øvrige indstillinger
FORCE_OVERWRITE = False  # Sæt til True for at overskrive eksisterende DB filer
VERBOSE_OUTPUT = True    # Sæt til True for at få mere detaljeret output
GEMINI_API_KEY = None    # API nøgle (sæt til None for at bruge miljøvariabel)

# System prompt og logging konfiguration
SYSTEM_PROMPT_PATH = "gemini_api_instructions.txt"  # Sti til system prompt fil
LOG_FILE = "Logs/manual_converter.log"              # Sti til log fil
# ======================================================

# Prøv at importere Gemini
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("ADVARSEL: Google Generative AI (Gemini) er ikke installeret.")
    print("Installer med: pip install google-generativeai")
    print("Fortsætter for at verificere andre afhængigheder...")

# Indlæs miljøvariabler fra .env filen
load_dotenv()

# Konfigurer logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """
    Parserer kommandolinje-argumenter
    
    Returns:
        argparse.Namespace: De parserede argumenter
    """
    parser = argparse.ArgumentParser(description='Manuel konvertering af TXT filer til DB filer')
    
    # Input gruppe - enten fil eller mappe
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument('--file', type=str, help='Sti til en enkelt TXT fil der skal konverteres')
    input_group.add_argument('--folder', type=str, help='Sti til en mappe med TXT filer der skal konverteres')
    
    # Output mappe
    parser.add_argument('--output', type=str, help='Sti til output mappe for DB filer. Hvis ikke angivet, bruges samme struktur som input')
    
    # Valgfri parametre
    parser.add_argument('--force', action='store_true', help='Tving konvertering, selvom DB filen allerede findes')
    parser.add_argument('--verbose', action='store_true', help='Vis detaljeret output')
    
    # Liga og sæson (valgfri hvis stier indeholder disse oplysninger)
    parser.add_argument('--liga', type=str, help='Liga (kvindeligaen, herreligaen)')
    parser.add_argument('--saeson', type=str, help='Sæson (f.eks. 2024-2025)')
    
    return parser.parse_args()

def extract_match_id_from_filename(filename):
    """
    Udtrækker kamp-ID fra filnavnet.
    
    Args:
        filename (str): Filnavn at udtrække fra 
    
    Returns:
        str or None: Kamp-ID hvis det findes, ellers None
    """
    # Match på mønstre som "match_748182_a.txt" eller lignende
    match = re.search(r'match_(\d+)', filename)
    if match:
        return match.group(1)
    return None

def extract_match_id_from_content(file_path):
    """
    Udtrækker kamp-ID fra tekstfilens indhold.
    
    Args:
        file_path (str): Sti til tekstfilen
        
    Returns:
        str or None: Kamp-ID hvis det findes, ellers None
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read(2000)  # Læs kun de første 2000 tegn for at spare tid
            
            # Søg efter kamp-ID i indholdet
            match = re.search(r'(\d{6})\s*/\s*\d{1,2}-\d{1,2}-\d{4}', content)
            if match:
                return match.group(1)
    except Exception as e:
        logger.error(f"Fejl ved læsning af fil for kamp-ID: {str(e)}")
    
    return None

def load_system_prompt():
    """
    Indlæs system prompt fra fil
    
    Returns:
        str: System prompt tekst
    """
    try:
        with open(SYSTEM_PROMPT_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"System prompt-fil ikke fundet: {SYSTEM_PROMPT_PATH}")
        print(f"FEJL: System prompt-fil ikke fundet: {SYSTEM_PROMPT_PATH}")
        print("System prompt er nødvendig for at bruge Gemini API")
        sys.exit(1)

def is_first_chunk(chunk_text):
    """
    Kontrollerer om dette er det første chunk af en tekstfil ved at se efter 'KAMPHÆNDELSER'
    
    Args:
        chunk_text (str): Tekst chunk
    
    Returns:
        bool: True hvis dette er det første chunk
    """
    return "KAMPHÆNDELSER" in chunk_text

def split_file_into_chunks(file_path, max_events_per_chunk=50):
    """
    Del tekstfilen i chunks baseret på 'KAMPHÆNDELSER' og sideinddelinger.
    
    Args:
        file_path: Sti til tekstfilen der skal behandles
        max_events_per_chunk: Maksimalt antal hændelser per chunk
        
    Returns:
        List[str]: Liste af tekstchunks
    """
    logger.info(f"Opdeler fil i chunks: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Fejl ved læsning af fil {file_path}: {str(e)}")
        return []
    
    # Find indholdet før første sideskift (topinformation og første del af hændelser)
    # Dette skal altid være det første chunk
    first_page_end = content.find("--- Side 2 ---")
    if first_page_end == -1:
        # Hvis der kun er én side, er hele filen et chunk
        logger.info("Kun én side fundet i filen. Behandler hele filen som ét chunk.")
        return [content]
    
    first_chunk = content[:first_page_end].strip()
    chunks = [first_chunk]
    
    # Del resten af indholdet i chunks baseret på sider og antal hændelser
    remaining_content = content[first_page_end:]
    
    # Del på sideinddelinger
    sides = re.split(r'--- Side \d+ ---', remaining_content)
    
    current_chunk_lines = []
    event_count = 0
    
    # Spring den første del over, da det er en tom streng efter split
    for side in sides[1:]:  
        lines = side.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                # Spring tomme linjer over
                continue
                
            current_chunk_lines.append(line)
            
            # Tæl linjer der ser ud til at være hændelser (har tid-format i starten)
            if re.match(r'^\d+\.\d+', line.strip()):
                event_count += 1
            
            # Hvis vi når maksimalt antal hændelser, lav et nyt chunk
            if event_count >= max_events_per_chunk:
                chunks.append('\n'.join(current_chunk_lines))
                current_chunk_lines = []
                event_count = 0
    
    # Tilføj det sidste chunk hvis der er noget tilbage
    if current_chunk_lines:
        chunks.append('\n'.join(current_chunk_lines))
    
    logger.info(f"Fil opdelt i {len(chunks)} chunks")
    return chunks

def correct_goalkeeper_placement(events):
    """
    Korrigerer placering af målvogter-data
    
    Args:
        events: Liste af hændelser
    
    Returns:
        tuple: (korrigerede hændelser, antal korrigerede hændelser)
    """
    events_corrected = 0
    
    # Hændelser der typisk involverer en målvogter
    goalkeeper_events = ['Mål', 'Skud reddet', 'Skud forbi', 'Skud på stolpe', 'Mål på straffe', 'Straffekast reddet']
    
    # Kendte målvogternavne og numre (opdateres dynamisk under korrektion)
    known_goalkeepers = set()
    
    # Første gennemløb: Find kendte målvogtere
    for event in events:
        if event.get('nr_mv') and event.get('mv'):
            known_goalkeepers.add((event.get('nr_mv'), event.get('mv')))
    
    # Andet gennemløb: Korriger baseret på hændelsestype og kendte målvogtere
    for event in events:
        # Hvis hændelsen er en af dem, der typisk involverer en målvogter
        if event.get('haendelse_1') in goalkeeper_events:
            # Tilfælde 1: nr_2/navn_2 er udfyldt, men nr_mv/mv er tomme, og haendelse_2 er tom
            if (event.get('nr_2') and not event.get('nr_mv') and not event.get('haendelse_2')):
                # Flyt data fra nr_2/navn_2 til nr_mv/mv
                event['nr_mv'] = event['nr_2']
                event['mv'] = event['navn_2']
                event['nr_2'] = None
                event['navn_2'] = None
                events_corrected += 1
                logger.debug(f"Korrigerede målvogterplacering for hændelse: {event.get('tid')} - {event.get('haendelse_1')}")
                
                # Tilføj denne målvogter til kendte målvogtere
                known_goalkeepers.add((event.get('nr_mv'), event.get('mv')))
            
            # Tilfælde 2: nr_2/navn_2 er udfyldt, og vi genkender dem som en målvogter fra tidligere hændelser
            elif (event.get('nr_2') and event.get('navn_2') and (event.get('nr_2'), event.get('navn_2')) in known_goalkeepers):
                # Flyt data fra nr_2/navn_2 til nr_mv/mv
                event['nr_mv'] = event['nr_2']
                event['mv'] = event['navn_2']
                event['nr_2'] = None
                event['navn_2'] = None
                events_corrected += 1
                logger.debug(f"Korrigerede målvogterplacering baseret på kendt målvogter: {event.get('tid')} - {event.get('haendelse_1')}")
    
    # Tredje gennemløb: Korriger baseret på mønstergenkendelse i data
    for i, event in enumerate(events):
        # Hvis vi har en hændelse uden målvogter, men med samme tid som en anden hændelse med målvogter
        if event.get('haendelse_1') in goalkeeper_events and not event.get('nr_mv') and i > 0:
            # Tjek om forrige hændelse har samme tid og en målvogter
            prev_event = events[i-1]
            if prev_event.get('tid') == event.get('tid') and prev_event.get('nr_mv'):
                event['nr_mv'] = prev_event.get('nr_mv')
                event['mv'] = prev_event.get('mv')
                events_corrected += 1
                logger.debug(f"Korrigerede målvogterplacering baseret på tidsmønster: {event.get('tid')} - {event.get('haendelse_1')}")
    
    return events, events_corrected

def process_chunk_with_gemini(chunk_content, api_key):
    """
    Send et chunk til Gemini API for behandling
    
    Args:
        chunk_content: Tekstchunk der skal behandles
        api_key: Gemini API-nøgle
        
    Returns:
        dict: JSON-svar fra Gemini API
    """
    # Tjek om dette er det første chunk
    first_chunk = is_first_chunk(chunk_content)
    logger.info(f"Behandler {'første' if first_chunk else 'ikke-første'} chunk")
    
    if not GEMINI_AVAILABLE:
        logger.error("Gemini API ikke tilgængelig. Installer det med: pip install google-generativeai")
        return {"match_info": {}, "match_events": []}
    
    try:
        # Konfigurer Gemini API-klienten
        client = genai.Client(api_key=api_key)
        
        # Hent system prompt
        system_prompt = load_system_prompt()
        
        # Log API-anmodningen
        logger.info(f"Sender anmodning til Gemini API - chunk størrelse: {len(chunk_content)} tegn")
        
        # Konfigurer API-kaldet
        generate_content_config = types.GenerateContentConfig(
            temperature=0.1,
            top_p=0.95,
            top_k=40,
            max_output_tokens=8192,
            response_mime_type="application/json",
            system_instruction=[types.Part.from_text(text=system_prompt)]
        )
        
        # Kald API'en
        start_time = time.time()
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=[types.Content(
                role="user",
                parts=[types.Part.from_text(text=chunk_content)]
            )],
            config=generate_content_config
        )
        end_time = time.time()
        
        # Log API-svaret
        logger.info(f"Gemini API svar modtaget på {end_time - start_time:.2f} sekunder")
        
        # Parse JSON-svar
        try:
            result = json.loads(response.text)
            
            # Log en opsummering af resultatet
            if 'match_info' in result and result['match_info']:
                logger.info(f"Modtog match_info data for kamp_id: {result['match_info'].get('kamp_id', 'ukendt')}")
            
            if 'match_events' in result:
                logger.info(f"Modtog {len(result['match_events'])} match_events")
                
                # Ekstra validering og korrektion af målvogtere
                if 'match_events' in result and result['match_events']:
                    corrected_events, events_corrected = correct_goalkeeper_placement(result['match_events'])
                    result['match_events'] = corrected_events
                    if events_corrected > 0:
                        logger.info(f"Korrigerede {events_corrected} hændelser med forkert placerede målvogtere")
            
            return result
        except json.JSONDecodeError:
            # Log fejlen
            logger.error(f"Fejl ved parsing af JSON-svar: {response.text[:200]}...")
            return {"match_info": {}, "match_events": []}
            
    except Exception as e:
        logger.error(f"Fejl ved kald til Gemini API: {str(e)}")
        return {"match_info": {}, "match_events": []}

def create_database_from_json(combined_data, db_path):
    """
    Opret en SQLite-database fra JSON-data
    
    Args:
        combined_data: Kombineret JSON-data med match_info og match_events
        db_path: Sti til den SQLite-database der skal oprettes
    """
    logger.info(f"Opretter database: {db_path}")
    
    # Sørg for at output-mappen eksisterer
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Opret tabeller
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS match_info (
            kamp_id TEXT PRIMARY KEY,
            hold_hjemme TEXT,
            hold_ude TEXT,
            resultat TEXT,
            halvleg_resultat TEXT,
            dato TEXT,
            sted TEXT,
            turnering TEXT
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS match_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kamp_id TEXT,
            tid TEXT,
            maal TEXT,
            hold TEXT,
            haendelse_1 TEXT,
            pos TEXT,
            nr_1 INTEGER,
            navn_1 TEXT,
            haendelse_2 TEXT,
            nr_2 INTEGER,
            navn_2 TEXT,
            nr_mv INTEGER,
            mv TEXT,
            FOREIGN KEY (kamp_id) REFERENCES match_info (kamp_id)
        )
        ''')
        
        # Indsæt match_info
        match_info = combined_data.get('match_info', {})
        if match_info:
            cursor.execute('''
            INSERT INTO match_info (kamp_id, hold_hjemme, hold_ude, resultat, halvleg_resultat, dato, sted, turnering)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                match_info.get('kamp_id'),
                match_info.get('hold_hjemme'),
                match_info.get('hold_ude'),
                match_info.get('resultat'),
                match_info.get('halvleg_resultat'),
                match_info.get('dato'),
                match_info.get('sted'),
                match_info.get('turnering')
            ))
        
        # Indsæt match_events
        match_events = combined_data.get('match_events', [])
        kamp_id = match_info.get('kamp_id') if match_info else None
        
        for event in match_events:
            # Konvertér numeriske værdier til int hvor muligt
            nr_1 = event.get('nr_1')
            nr_2 = event.get('nr_2')
            nr_mv = event.get('nr_mv')
            
            # Håndter None-værdier korrekt
            if nr_1 == '0' or nr_1 == '':
                nr_1 = None
            if nr_2 == '0' or nr_2 == '':
                nr_2 = None
            if nr_mv == '0' or nr_mv == '':
                nr_mv = None
            
            cursor.execute('''
            INSERT INTO match_events (
                kamp_id, tid, maal, hold, haendelse_1, pos, nr_1, navn_1,
                haendelse_2, nr_2, navn_2, nr_mv, mv
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                kamp_id,
                event.get('tid'),
                event.get('maal'),
                event.get('hold'),
                event.get('haendelse_1'),
                event.get('pos'),
                nr_1,
                event.get('navn_1'),
                event.get('haendelse_2'),
                nr_2,
                event.get('navn_2'),
                nr_mv,
                event.get('mv')
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Database oprettet: {db_path} med {len(match_events)} hændelser")
        return True
        
    except Exception as e:
        logger.error(f"Fejl ved oprettelse af database {db_path}: {str(e)}")
        return False

def process_file(file_path, output_dir, force=False, verbose=False):
    """
    Behandl en enkelt tekstfil og konverter den til en database
    
    Args:
        file_path: Sti til tekstfilen der skal behandles
        output_dir: Output mappe hvor DB filen skal gemmes
        force: Om eksisterende DB filer skal overskrives
        verbose: Om detaljeret output skal vises
        
    Returns:
        bool: True hvis konverteringen var succesfuld, ellers False
    """
    filename = os.path.basename(file_path)
    
    if verbose:
        print(f"Behandler fil: {filename}")
    
    logger.info(f"Starter behandling af fil: {filename}")
    
    # Tjek om filen eksisterer
    if not os.path.exists(file_path):
        print(f"Fejl: Filen findes ikke: {file_path}")
        logger.error(f"Filen findes ikke: {file_path}")
        return False
    
    # Tjek om filen er en TXT fil
    if not file_path.lower().endswith('.txt'):
        print(f"Fejl: Filen er ikke en TXT fil: {file_path}")
        logger.error(f"Filen er ikke en TXT fil: {file_path}")
        return False
    
    # Hent API-nøgle fra konfiguration eller miljøvariabel
    api_key = GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Fejl: GEMINI_API_KEY ikke fundet. Sæt den i konfigurationssektionen eller som miljøvariabel.")
        logger.error("GEMINI_API_KEY ikke fundet")
        return False
    
    # Start timing
    start_time = time.time()
    
    # Del filen i chunks
    chunks = split_file_into_chunks(file_path)
    if not chunks:
        print(f"Fejl: Ingen chunks fundet i filen: {filename}")
        logger.error(f"Ingen chunks fundet i filen: {filename}")
        return False
    
    # Behandl hvert chunk og kombiner resultater
    all_json_data = {"match_info": {}, "match_events": []}
    match_info_found = False
    
    for i, chunk in enumerate(chunks):
        if verbose:
            print(f"  Behandler chunk {i+1} af {len(chunks)}")
        logger.info(f"Behandler chunk {i+1} af {len(chunks)} for {filename}")
        
        # Send chunk til Gemini API
        json_result = process_chunk_with_gemini(chunk, api_key)
        
        # Gem match_info fra første chunk med gyldige data
        if 'match_info' in json_result and json_result['match_info'] and not match_info_found:
            all_json_data['match_info'] = json_result['match_info']
            match_info_found = True
            if verbose:
                print(f"  Match info fundet: {json_result['match_info'].get('kamp_id', 'ukendt')} - {json_result['match_info'].get('hold_hjemme', 'ukendt')} vs {json_result['match_info'].get('hold_ude', 'ukendt')}")
            logger.info(f"Match info fundet: {json_result['match_info'].get('kamp_id')} - {json_result['match_info'].get('hold_hjemme')} vs {json_result['match_info'].get('hold_ude')}")
        
        # Tilføj alle match_events fra dette chunk
        if 'match_events' in json_result and json_result['match_events']:
            all_json_data['match_events'].extend(json_result['match_events'])
            if verbose:
                print(f"  Tilføjet {len(json_result['match_events'])} hændelser fra chunk {i+1}")
            logger.info(f"Tilføjet {len(json_result['match_events'])} hændelser fra chunk {i+1}")
    
    # Kontroller om vi har fundet match_info
    if not match_info_found:
        print(f"Fejl: Ingen match_info fundet i filen: {filename}")
        logger.error(f"Ingen match_info fundet i filen: {filename}")
        return False
    
    # Opret database-filnavn baseret på kampinformation
    match_info = all_json_data['match_info']
    dato = match_info.get('dato', '').replace('-', '')
    hold_hjemme = match_info.get('hold_hjemme', '').replace(' ', '_')
    hold_ude = match_info.get('hold_ude', '').replace(' ', '_')
    
    db_filename = f"{dato}_{hold_hjemme}_vs_{hold_ude}.db"
    db_path = os.path.join(output_dir, db_filename)
    
    # Tjek om databasen allerede findes og om vi skal overskrive den
    if os.path.exists(db_path) and not force:
        print(f"Database findes allerede: {db_filename}")
        print("Brug --force for at overskrive den eksisterende database")
        logger.info(f"Database findes allerede: {db_path}, springer over (brug --force for at overskrive)")
        return False
    
    # Opret databasen
    success = create_database_from_json(all_json_data, db_path)
    
    end_time = time.time()
    duration = end_time - start_time
    
    if success:
        print(f"Konvertering af {filename} gennemført på {duration:.2f} sekunder.")
        print(f"Database gemt som: {db_filename}")
        print(f"Total antal hændelser: {len(all_json_data['match_events'])}")
        logger.info(f"Behandling af {filename} fuldført på {duration:.2f} sekunder.")
        logger.info(f"Database gemt som: {db_filename}")
        logger.info(f"Total antal hændelser: {len(all_json_data['match_events'])}")
        return True
    else:
        print(f"Fejl ved konvertering af {filename}")
        return False

def process_folder(folder_path, output_dir, force=False, verbose=False):
    """
    Behandl alle TXT filer i en mappe og konverter dem til databaser
    
    Args:
        folder_path: Sti til mappen med TXT filer
        output_dir: Output mappe hvor DB filer skal gemmes
        force: Om eksisterende DB filer skal overskrives
        verbose: Om detaljeret output skal vises
        
    Returns:
        tuple: (succesfulde, fejlede, sprunget_over)
    """
    # Tjek om mappen eksisterer
    if not os.path.exists(folder_path):
        print(f"Fejl: Mappen findes ikke: {folder_path}")
        logger.error(f"Mappen findes ikke: {folder_path}")
        return 0, 0, 0
    
    # Find alle TXT filer i mappen
    txt_files = glob.glob(os.path.join(folder_path, "*.txt"))
    
    if not txt_files:
        print(f"Ingen TXT filer fundet i mappen: {folder_path}")
        logger.info(f"Ingen TXT filer fundet i mappen: {folder_path}")
        return 0, 0, 0
    
    print(f"Fandt {len(txt_files)} TXT filer i mappen: {folder_path}")
    logger.info(f"Fandt {len(txt_files)} TXT filer i mappen: {folder_path}")
    
    # Behandl hver fil
    successful = 0
    failed = 0
    skipped = 0
    
    for file_path in txt_files:
        if process_file(file_path, output_dir, force, verbose):
            successful += 1
        else:
            # Tjek om det er fordi filen allerede er behandlet (eksisterende DB fil)
            match_info = extract_match_id_from_filename(file_path) or extract_match_id_from_content(file_path)
            if match_info and glob.glob(os.path.join(output_dir, f"*{match_info}*.db")) and not force:
                skipped += 1
            else:
                failed += 1
    
    return successful, failed, skipped

def figure_out_output_dir(input_path, output_arg=None):
    """
    Bestemmer output-mappen baseret på input-sti og output-argument
    
    Args:
        input_path: Input sti (fil eller mappe)
        output_arg: Output argument fra kommandolinjen
        
    Returns:
        str: Output mappe sti
    """
    if output_arg:
        # Brug den specificerede output mappe
        output_dir = output_arg
        os.makedirs(output_dir, exist_ok=True)
        return output_dir
    
    # Hvis ingen output er angivet, brug standard mappe baseret på input
    input_path = os.path.abspath(input_path)
    
    if os.path.isfile(input_path):
        # For filer, udled output mappe baseret på filens placering
        input_dir = os.path.dirname(input_path)
    else:
        # For mapper, brug selve inputmappen
        input_dir = input_path
    
    # Erstat '-txt-tabel' med '-database' i stien
    if '-txt-tabel' in input_dir:
        output_dir = input_dir.replace('-txt-tabel', '-database')
    else:
        # Hvis '-txt-tabel' ikke findes i stien, tilføj blot '-database' som undermappe
        output_dir = os.path.join(input_dir, 'database')
    
    # Sørg for at output-mappen eksisterer
    os.makedirs(output_dir, exist_ok=True)
    
    return output_dir

def main():
    """Hovedfunktion der starter konverteringsprocessen"""
    # Parse kommandolinje-argumenter
    args = parse_arguments()
    
    # Bestem om vi skal bruge kommandolinjeargumenter eller konfiguration
    use_cmd_args = (args.file is not None or args.folder is not None)
    
    if use_cmd_args:
        # Bruger kommandolinjeargumenter
        logger.info("Bruger kommandolinje-argumenter")
        if args.verbose:
            global VERBOSE_OUTPUT
            VERBOSE_OUTPUT = True
            logger.setLevel(logging.DEBUG)
        
        # Bestem input (fil eller mappe)
        if args.file:
            input_path = args.file
            is_file = True
        else:
            input_path = args.folder
            is_file = False
        
        # Bestem output mappe
        output_dir = figure_out_output_dir(input_path, args.output)
        force = args.force
        verbose = args.verbose
    else:
        # Bruger konfiguration fra toppen af scriptet
        logger.info("Bruger konfiguration fra scriptet")
        
        # Konfigurer logging niveau baseret på VERBOSE_OUTPUT
        if VERBOSE_OUTPUT:
            logger.setLevel(logging.DEBUG)
        
        # Valider indstillinger i konfigurationen
        if INPUT_FILE is None and INPUT_FOLDER is None:
            print("Fejl: Enten INPUT_FILE eller INPUT_FOLDER skal angives i konfigurationen")
            logger.error("Hverken INPUT_FILE eller INPUT_FOLDER er angivet i konfigurationen")
            return
        
        if INPUT_FILE is not None and INPUT_FOLDER is not None:
            print("Fejl: Både INPUT_FILE og INPUT_FOLDER er angivet i konfigurationen. Vælg kun én.")
            logger.error("Både INPUT_FILE og INPUT_FOLDER er angivet i konfigurationen")
            return
        
        # Bestem input (fil eller mappe)
        if INPUT_FILE is not None:
            input_path = INPUT_FILE
            is_file = True
        else:
            input_path = INPUT_FOLDER
            is_file = False
        
        # Bestem output mappe
        output_dir = OUTPUT_DIR or figure_out_output_dir(input_path)
        force = FORCE_OVERWRITE
        verbose = VERBOSE_OUTPUT
    
    # Log konfiguration
    logger.info("==== Starter manuel TXT til DB konvertering ====")
    logger.info(f"Input sti: {input_path}")
    logger.info(f"Output mappe: {output_dir}")
    logger.info(f"Tving overskrivning: {force}")
    logger.info(f"Detaljeret output: {verbose}")
    
    print(f"Output mappe: {output_dir}")
    
    # Start konvertering
    if is_file:
        # Konverter en enkelt fil
        success = process_file(input_path, output_dir, force, verbose)
        
        if success:
            print("\nKonvertering af filen gennemført!")
            logger.info("Konvertering af filen gennemført!")
        else:
            print("\nKonvertering af filen fejlede!")
            logger.error("Konvertering af filen fejlede!")
    else:
        # Konverter alle filer i en mappe
        successful, failed, skipped = process_folder(input_path, output_dir, force, verbose)
        
        print("\nKonvertering af mappen afsluttet!")
        print(f"Vellykket: {successful}")
        print(f"Mislykkedes: {failed}")
        print(f"Sprunget over: {skipped}")
        print(f"Total: {successful + failed + skipped}")
        
        logger.info("==== Konverteringsproces afsluttet ====")
        logger.info(f"Behandlet {successful + failed + skipped} filer: {successful} succesfulde, {failed} fejlede, {skipped} sprunget over")
    
    logger.info("==== Manuel TXT til DB konvertering afsluttet ====")

if __name__ == "__main__":
    main()