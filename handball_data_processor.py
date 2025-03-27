#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Håndboldhændelser Konverter

Dette script behandler håndboldkamp-tekstfiler fra tekstfil-mappen
og konverterer dem til struktureret JSON-data ved hjælp af Gemini API.
Resultaterne gemmes derefter i SQLite-databaser, en for hver kamp.

Optimeret version:
- Bruger tracking-system for at undgå at behandle allerede konverterede filer
- Integrerer med handball_workflow.py for konsistent filhåndtering

Brug:
    python handball_data_processor.py --liga=kvindeligaen --sæson=2024-2025
    python handball_data_processor.py --liga=herreligaen --sæson=2023-2024
"""

import os
import re
import json
import sqlite3
import glob
import time
import logging
import argparse
import sys
import hashlib
from pathlib import Path
from datetime import datetime
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Indlæs miljøvariabler fra .env filen
load_dotenv()

# Tracking-fil for at holde styr på processerede filer (samme som i workflow)
TRACKING_FILE = "JSON/processed_files.json"

# Sikr at JSON-mappen eksisterer
json_dir = os.path.dirname(TRACKING_FILE)
if json_dir:  # Kun kald makedirs hvis der faktisk er en sti
    os.makedirs(json_dir, exist_ok=True)

# --------------
# TRACKING-SYSTEM FUNKTIONER
# --------------

def load_tracking_data():
    """
    Indlæser tracking-data fra JSON-fil
    
    Returns:
        dict: Tracking-data
    """
    if os.path.exists(TRACKING_FILE):
        try:
            with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Kunne ikke læse tracking-filen. Opretter ny.")
            return {
                "pdf_files": {},
                "txt_files": {},
                "db_files": {}
            }
    
    return {
        "pdf_files": {},
        "txt_files": {},
        "db_files": {}
    }

def save_tracking_data(tracking_data):
    """
    Gemmer tracking-data til JSON-fil
    
    Args:
        tracking_data: Data der skal gemmes
    """
    with open(TRACKING_FILE, 'w', encoding='utf-8') as f:
        json.dump(tracking_data, f, indent=2)

def get_file_hash(file_path):
    """
    Beregner hash af en fil for at detektere ændringer
    
    Args:
        file_path: Sti til filen
        
    Returns:
        str: MD5 hash af filen eller None hvis filen ikke findes
    """
    if not os.path.exists(file_path):
        return None
    
    md5_hash = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            # For store filer, læs kun starten og slutningen
            if os.path.getsize(file_path) > 100000:  # 100KB
                # Læs de første 5KB
                start_chunk = f.read(5120)
                md5_hash.update(start_chunk)
                
                # Gå til slutningen og læs de sidste 5KB
                f.seek(-5120, os.SEEK_END)
                end_chunk = f.read(5120)
                md5_hash.update(end_chunk)
            else:
                # For mindre filer, læs hele indholdet
                md5_hash.update(f.read())
    except Exception as e:
        logger.error(f"Fejl ved beregning af hash for fil {file_path}: {str(e)}")
        return None
    
    return md5_hash.hexdigest()

def is_file_processed(file_path, file_type, tracking_data):
    """
    Tjekker om en fil allerede er behandlet
    
    Args:
        file_path: Sti til filen
        file_type: Filtype ('pdf', 'txt', 'db')
        tracking_data: Tracking data
        
    Returns:
        bool: True hvis filen er behandlet
    """
    # Sikr at filen findes
    if not os.path.exists(file_path):
        return False
    
    # Få filnavn til lookup
    file_name = os.path.basename(file_path)
    
    # Find korrekt tracking dictionary
    if file_type == 'pdf':
        tracking_dict = tracking_data["pdf_files"]
    elif file_type == 'txt':
        tracking_dict = tracking_data["txt_files"]
    elif file_type == 'db':
        tracking_dict = tracking_data["db_files"]
    else:
        logger.error(f"Ukendt filtype: {file_type}")
        return False
    
    # Tjek om filen allerede er i tracking_dict
    if file_name in tracking_dict:
        # Få tidligere gemt hash
        old_hash = tracking_dict[file_name]
        
        # Beregn aktuel hash
        current_hash = get_file_hash(file_path)
        
        # Hvis hashen er den samme, er filen ikke ændret
        if current_hash == old_hash:
            return True
    
    return False

def mark_file_processed(file_path, file_type, tracking_data):
    """
    Markerer en fil som behandlet i tracking-data
    
    Args:
        file_path: Sti til filen
        file_type: Filtype ('pdf', 'txt', 'db')
        tracking_data: Tracking data
    """
    # Sikr at filen findes
    if not os.path.exists(file_path):
        logger.warning(f"Forsøger at markere en ikke-eksisterende fil som behandlet: {file_path}")
        return
    
    # Få filnavn til lagring
    file_name = os.path.basename(file_path)
    
    # Beregn hash
    file_hash = get_file_hash(file_path)
    
    # Kontroller at hash blev beregnet korrekt
    if file_hash is None:
        logger.warning(f"Kunne ikke beregne hash for {file_path}, springer over")
        return
    
    # Find korrekt tracking dictionary
    if file_type == 'pdf':
        tracking_dict = tracking_data["pdf_files"]
    elif file_type == 'txt':
        tracking_dict = tracking_data["txt_files"]
    elif file_type == 'db':
        tracking_dict = tracking_data["db_files"]
    else:
        logger.error(f"Ukendt filtype: {file_type}")
        return
    
    # Tilføj eller opdater filen i tracking
    tracking_dict[file_name] = file_hash
    logger.debug(f"Markeret {file_name} som behandlet ({file_type})")

def get_unprocessed_txt_files(txt_dir, db_dir, tracking_data):
    """
    Finder tekstfiler der endnu ikke er blevet konverteret til databaser
    
    Args:
        txt_dir (str): Mappe med tekstfiler
        db_dir (str): Mappe med databaser
        tracking_data (dict): Tracking data
        
    Returns:
        list: Liste med stier til tekstfiler der skal behandles
    """
    # Tjek om txt_dir findes
    if not os.path.exists(txt_dir):
        logger.error(f"Tekstmappe findes ikke: {txt_dir}")
        return []
    
    # Find alle TXT-filer i mappen
    file_pattern = os.path.join(txt_dir, "*.txt")
    txt_files = glob.glob(file_pattern)
    
    logger.info(f"Fandt {len(txt_files)} tekstfiler i {txt_dir}")
    
    # Filtrer til kun ubehandlede filer
    unprocessed_files = []
    
    for txt_path in txt_files:
        # Spring filen over hvis den allerede er markeret som behandlet i tracking-systemet
        if is_file_processed(txt_path, 'txt', tracking_data):
            continue
            
        # Eller spring filen over hvis den findes i en database
        if is_already_processed(txt_path, db_dir):
            continue
            
        unprocessed_files.append(txt_path)
    
    logger.info(f"Fandt {len(unprocessed_files)} nye txt-filer der skal konverteres")
    return unprocessed_files

def parse_arguments():
    """
    Parserer kommandolinje-argumenter
    
    Returns:
        argparse.Namespace: De parserede argumenter
    """
    parser = argparse.ArgumentParser(description='Behandl håndbold tekstfiler til databaser')
    
    # Liga parameter (default: kvindeligaen)
    parser.add_argument('--liga', type=str, default='kvindeligaen',
                        help='Ligaen der skal behandles (kvindeligaen, herreligaen)')
    
    # Sæson parameter (default: 2024-2025)
    parser.add_argument('--sæson', type=str, default='2024-2025',
                        help='Sæsonen der skal behandles (f.eks. 2024-2025)')
    
    # Konverter argumenter til lowercase for konsistens
    args = parser.parse_args()
    args.liga = args.liga.lower()
    
    # Valider liga-værdien
    valid_leagues = ['kvindeligaen', 'herreligaen']
    if args.liga not in valid_leagues:
        print(f"Fejl: Ugyldig liga: {args.liga}. Gyldige værdier er: {', '.join(valid_leagues)}")
        sys.exit(1)
    
    # Valider sæson-format (YYYY-YYYY)
    if not re.match(r'^\d{4}-\d{4}$', args.sæson):
        print(f"Fejl: Ugyldig sæson: {args.sæson}. Formatet skal være YYYY-YYYY, f.eks. 2024-2025")
        sys.exit(1)
    
    return args

def setup_configuration(args):
    """
    Opsætter konfiguration baseret på kommandolinje-argumenter
    
    Args:
        args (argparse.Namespace): Kommandolinje-argumenter
        
    Returns:
        tuple: (input_dir, output_db_dir)
    """
    # Konverter liga-navn til mappenavn (fjern 'en' fra slutningen)
    liga_mappe = args.liga
    if liga_mappe.endswith('en'):
        liga_mappe = liga_mappe[:-2]
    liga_mappe = liga_mappe.capitalize()
    
    # Definer stier for input og output
    INPUT_DIR = os.path.join(f"{liga_mappe}-txt-tabel", args.sæson)
    OUTPUT_DB_DIR = f"{liga_mappe}-database"
    OUTPUT_DB_SEASON_DIR = os.path.join(OUTPUT_DB_DIR, args.sæson)
    
    # Sørg for at output-mapperne eksisterer
    os.makedirs(OUTPUT_DB_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DB_SEASON_DIR, exist_ok=True)
    
    return INPUT_DIR, OUTPUT_DB_SEASON_DIR

# Konfiguration for system prompt og logging
SYSTEM_PROMPT_PATH = "gemini_api_instructions.txt"
LOG_FILE = "Logs/handball_converter.log"

# Sikrer at de nødvendige mapper eksisterer
log_dir = os.path.dirname(LOG_FILE)
if log_dir:  # Kun kald makedirs hvis der faktisk er en sti
    os.makedirs(log_dir, exist_ok=True)

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

# Tilføj mere detaljeret logging for API kald
# Opret en separat logger for API kald
api_logger = logging.getLogger('api_calls')
api_logger.setLevel(logging.DEBUG)
api_handler = logging.FileHandler('Logs/api_calls.log')
api_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
api_logger.addHandler(api_handler)

def load_system_prompt():
    """Indlæs system prompt fra fil"""
    try:
        with open(SYSTEM_PROMPT_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"System prompt-fil ikke fundet: {SYSTEM_PROMPT_PATH}")
        raise

def is_first_chunk(chunk_text):
    """Kontrollerer om dette er det første chunk af en tekstfil ved at se efter 'KAMPHÆNDELSER'"""
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
    
    try:
        # Konfigurer Gemini API-klienten
        client = genai.Client(api_key=api_key)
        
        # Hent system prompt
        system_prompt = load_system_prompt()
        
        # Log API-anmodningen (uden at inkludere hele prompt-teksten, som kan være meget stor)
        api_logger.info(f"Sender anmodning til Gemini API - chunk størrelse: {len(chunk_content)} tegn")
        api_logger.debug(f"Første 100 tegn af chunk: {chunk_content[:100]}...")
        
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
        api_logger.info(f"Gemini API svar modtaget på {end_time - start_time:.2f} sekunder")
        
        # Parse JSON-svar
        try:
            result = json.loads(response.text)
            
            # Log en opsummering af resultatet (uden at dumpe hele JSON-strukturen)
            if 'match_info' in result and result['match_info']:
                api_logger.info(f"Modtog match_info data for kamp_id: {result['match_info'].get('kamp_id', 'ukendt')}")
            
            if 'match_events' in result:
                api_logger.info(f"Modtog {len(result['match_events'])} match_events")
                
                # Ekstra validering og korrektion af målvogtere
                if 'match_events' in result and result['match_events']:
                    corrected_events, events_corrected = correct_goalkeeper_placement(result['match_events'])
                    result['match_events'] = corrected_events
                    if events_corrected > 0:
                        logger.info(f"Korrigerede {events_corrected} hændelser med forkert placerede målvogtere")
            
            return result
        except json.JSONDecodeError:
            # Log fejlen og de første 200 tegn af svaret for debugging
            api_logger.error(f"Fejl ved parsing af JSON-svar: {response.text[:200]}...")
            logger.error(f"Fejl ved parsing af JSON-svar: {response.text[:200]}...")
            return {"match_info": {}, "match_events": []}
            
    except Exception as e:
        api_logger.error(f"Fejl ved kald til Gemini API: {str(e)}")
        logger.error(f"Fejl ved kald til Gemini API: {str(e)}")
        return {"match_info": {}, "match_events": []}

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
        
    except Exception as e:
        logger.error(f"Fejl ved oprettelse af database {db_path}: {str(e)}")

def process_file(file_path, api_key, db_dir, tracking_data):
    """
    Behandl en enkelt tekstfil fra start til slut
    
    Args:
        file_path: Sti til tekstfilen der skal behandles
        api_key: Gemini API-nøgle
        db_dir: Output mappe til databaser
        tracking_data: Tracking data for at markere filer som behandlet
        
    Returns:
        str: Sti til den oprettede database
    """
    filename = os.path.basename(file_path)
    logger.info(f"Starter behandling af fil: {filename}")
    
    start_time = time.time()
    
    # Del filen i chunks
    chunks = split_file_into_chunks(file_path)
    if not chunks:
        logger.error(f"Ingen chunks fundet i filen: {filename}")
        return None
    
    # Behandl hvert chunk og kombiner resultater
    all_json_data = {"match_info": {}, "match_events": []}
    match_info_found = False
    
    for i, chunk in enumerate(chunks):
        logger.info(f"Behandler chunk {i+1} af {len(chunks)} for {filename}")
        
        # Send chunk til Gemini API
        json_result = process_chunk_with_gemini(chunk, api_key)
        
        # Gem match_info fra første chunk med gyldige data
        if 'match_info' in json_result and json_result['match_info'] and not match_info_found:
            all_json_data['match_info'] = json_result['match_info']
            match_info_found = True
            logger.info(f"Match info fundet: {json_result['match_info'].get('kamp_id')} - {json_result['match_info'].get('hold_hjemme')} vs {json_result['match_info'].get('hold_ude')}")
        
        # Tilføj alle match_events fra dette chunk
        if 'match_events' in json_result and json_result['match_events']:
            all_json_data['match_events'].extend(json_result['match_events'])
            logger.info(f"Tilføjet {len(json_result['match_events'])} hændelser fra chunk {i+1}")
    
    # Kontroller om vi har fundet match_info
    if not match_info_found:
        logger.error(f"Ingen match_info fundet i filen: {filename}")
        return None
    
    # Opret database-filnavn baseret på kampinformation
    match_info = all_json_data['match_info']
    dato = match_info.get('dato', '').replace('-', '')
    hold_hjemme = match_info.get('hold_hjemme', '').replace(' ', '_')
    hold_ude = match_info.get('hold_ude', '').replace(' ', '_')
    
    db_filename = f"{dato}_{hold_hjemme}_vs_{hold_ude}.db"
    db_path = os.path.join(db_dir, db_filename)
    
    # Opret databasen
    create_database_from_json(all_json_data, db_path)
    
    # Markér filer som behandlet
    mark_file_processed(file_path, 'txt', tracking_data)
    mark_file_processed(db_path, 'db', tracking_data)
    
    end_time = time.time()
    duration = end_time - start_time
    logger.info(f"Behandling af {filename} fuldført på {duration:.2f} sekunder.")
    logger.info(f"Database gemt som: {db_filename}")
    logger.info(f"Total antal hændelser: {len(all_json_data['match_events'])}")
    
    return db_path

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

def is_already_processed(file_path, output_db_dir):
    """
    Tjekker om en tekstfil allerede er behandlet ved at søge efter en tilsvarende database
    
    Args:
        file_path (str): Sti til tekstfilen
        output_db_dir (str): Sti til output database-mappen
    
    Returns:
        bool: True hvis filen allerede er behandlet, ellers False
    """
    filename = os.path.basename(file_path)
    logger.info(f"Tjekker om {filename} allerede er behandlet...")
    
    # Forsøg at udtrække match_id fra filnavnet
    match_id = extract_match_id_from_filename(filename)
    
    if not match_id:
        # Hvis match_id ikke kunne udtrækkes fra filnavnet, prøv at finde det i indholdet
        match_id = extract_match_id_from_content(file_path)
        
        if not match_id:
            logger.warning(f"Kunne ikke udtrække match_id fra {filename}, kan ikke tjekke om den er behandlet")
            return False
    
    # Tjek om der findes en database-fil med dette match_id
    db_pattern = os.path.join(output_db_dir, f"*{match_id}*.db")
    db_files = glob.glob(db_pattern)
    
    if db_files:
        logger.info(f"Fandt eksisterende database for kamp {match_id}: {os.path.basename(db_files[0])}")
        
        # Tjek om databasen er gyldig ved at forsøge at åbne den
        try:
            db_file = db_files[0]
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Tjek om tabellerne eksisterer og har indhold
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            if not tables:
                logger.warning(f"Database {os.path.basename(db_file)} har ingen tabeller, behandler filen igen")
                return False
            
            # Tjek om match_events-tabellen har indhold
            cursor.execute("SELECT COUNT(*) FROM match_events")
            event_count = cursor.fetchone()[0]
            
            conn.close()
            
            if event_count > 0:
                logger.info(f"Database {os.path.basename(db_file)} har {event_count} hændelser, springer over")
                return True
            else:
                logger.warning(f"Database {os.path.basename(db_file)} har ingen hændelser, behandler filen igen")
                return False
                
        except Exception as e:
            logger.error(f"Fejl ved tjek af database {db_file}: {str(e)}")
    
    logger.info(f"Fil {filename} med kamp_id {match_id} er ikke tidligere behandlet.")
    return False

def main():
    """Hovedfunktion der behandler alle tekstfiler i input-mappen"""
    logger.info("==== Starter konverteringsproces ====")
    
    # Parse kommandolinje-argumenter
    args = parse_arguments()
    
    # Gør OUTPUT_DB_DIR tilgængelig globalt, så process_file kan bruge den
    global OUTPUT_DB_DIR
    
    # Opsæt konfiguration baseret på argumenter
    INPUT_DIR, OUTPUT_DB_DIR = setup_configuration(args)
    
    # Hent API-nøgle fra miljøvariabel
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY miljøvariabel ikke fundet")
        return
    
    # Indlæs tracking data fra JSON-fil (delt med workflow)
    tracking_data = load_tracking_data()
    
    # Find ubehandlede tekstfiler ved hjælp af tracking-systemet
    files_to_process = get_unprocessed_txt_files(INPUT_DIR, OUTPUT_DB_DIR, tracking_data)
    
    logger.info(f"Fandt {len(files_to_process)} txt-filer der skal behandles")
    
    # Behandl hver fil
    successful_files = 0
    failed_files = 0
    
    # Beregn antallet af allerede behandlede filer til logging
    all_txt_files = glob.glob(os.path.join(INPUT_DIR, "*.txt"))
    already_processed = len(all_txt_files) - len(files_to_process)
    
    for file_path in files_to_process:
        try:
            # Behandl fil og track om den er behandlet
            db_path = process_file(file_path, api_key, OUTPUT_DB_DIR, tracking_data)
            
            # Gem tracking data efter hver fil for at undgå at gøre dobbeltarbejde
            save_tracking_data(tracking_data)
            
            if db_path:
                successful_files += 1
            else:
                failed_files += 1
        except Exception as e:
            logger.error(f"Uventet fejl ved behandling af {os.path.basename(file_path)}: {str(e)}")
            failed_files += 1
    
    logger.info("==== Konverteringsproces afsluttet ====")
    logger.info(f"Behandlet {len(files_to_process)} filer: {successful_files} succesfulde, {failed_files} fejlede")
    logger.info(f"Sprunget over {already_processed} allerede behandlede filer")
    
    # Vis opsummering
    print("\nKonvertering afsluttet!")
    print(f"Vellykket: {successful_files}")
    print(f"Mislykkedes: {failed_files}")
    print(f"Sprunget over: {already_processed}")
    print(f"Total: {len(all_txt_files)}")

if __name__ == "__main__":
    main()