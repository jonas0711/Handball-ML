#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Håndboldhændelser - Forbedret Workflow Script

Dette script kører hele workflowet med fokus på at sikre:
1. At kun gyldige PDF-filer downloades og beholdes
2. At alle filer går gennem hele processen (PDF → TXT → DB)
3. At allerede behandlede filer ikke behandles igen

Hovedforbedringer:
- Grundig validering af PDF-filer for at undgå korrupte eller tomme filer
- Tracking af hele processeringskæden (PDF → TXT → DB)
- Automatisk identifikation og genbehandling af filer der er strandet på mellemtrin
- Robust håndtering af fejl i alle trin af processen
"""

import os
import sys
import time
import subprocess
import logging
import argparse
import re
import requests
import hashlib
import json
import io
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup

# Importer PyPDF2 til PDF-validering
try:
    import PyPDF2
except ImportError:
    print("PyPDF2 ikke fundet. Installerer...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "PyPDF2"])
    import PyPDF2

#---------------------------
# KONFIGURATION
#---------------------------
# Vælg liga: 'kvindeligaen', 'herreligaen', eller 'begge'
DEFAULT_LIGA = 'kvindeligaen'

# Vælg sæson (format: 'ÅÅÅÅ-ÅÅÅÅ')
DEFAULT_SAESON = '2024-2025'

# Detaljeret logging til terminal
VERBOSE_OUTPUT = True

# Log-filnavn
LOG_FILE = "handball_workflow_detailed.log"

# Tracking-fil for at holde styr på processerede filer
TRACKING_FILE = "processed_files.json"

# Tærskelværdier for PDF-validering
MIN_PDF_SIZE = 50000        # 50KB - små filer er ofte tomme
EMPTY_PDF_SIZE = 280000     # Typisk størrelse for tomme kamprapporter
MIN_TEXT_CONTENT = 500      # Minimum antal tegn af indhold i en gyldig PDF

#---------------------------
# OPSÆTNING - Logging og systemstartsmeldinger
#---------------------------

# Sikr at log-mappen eksisterer
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
logger = logging.getLogger("workflow")

# Få aktuel arbejdsmappe
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd()

# Hjælpefunktion til at formatere output med indrykning
def log(message, level=0, is_important=False):
    """
    Logger en meddelelse med indrykning og fremhævning efter behov
    
    Args:
        message: Meddelelsen der skal logges
        level: Indrykningsniveau (0 = ingen indrykning)
        is_important: Om meddelelsen skal fremhæves
    """
    indent = "  " * level
    formatted_message = f"{indent}{message}"
    
    if is_important:
        # Fremhæv vigtige meddelelser
        border = "=" * len(formatted_message)
        logger.info(border)
        logger.info(formatted_message)
        logger.info(border)
        
        if VERBOSE_OUTPUT:
            print(border)
            print(formatted_message)
            print(border)
    else:
        logger.info(formatted_message)
        
        if VERBOSE_OUTPUT:
            print(formatted_message)

#---------------------------
# FIL-TRACKING SYSTEM - For at undgå genbehandling
#---------------------------

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
            log(f"Advarsel: Kunne ikke læse tracking-filen. Opretter ny.", level=1)
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
        log(f"Fejl ved beregning af hash for fil {file_path}: {str(e)}", level=1)
        return None
    
    return md5_hash.hexdigest()

def unmark_file(file_path, file_type, tracking_data):
    """
    Fjerner en fil fra tracking-data
    
    Args:
        file_path: Sti til filen
        file_type: Filtype ('pdf', 'txt', 'db')
        tracking_data: Tracking data
    """
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
        log(f"Ukendt filtype: {file_type}", level=1)
        return
    
    # Fjern filen fra tracking hvis den findes
    if file_name in tracking_dict:
        del tracking_dict[file_name]
        log(f"Fjernet {file_name} fra tracking ({file_type})", level=2)

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
        log(f"Ukendt filtype: {file_type}", level=1)
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
        log(f"Advarsel: Forsøger at markere en ikke-eksisterende fil som behandlet: {file_path}", level=1)
        return
    
    # Få filnavn til lagring
    file_name = os.path.basename(file_path)
    
    # Beregn hash
    file_hash = get_file_hash(file_path)
    
    # Kontroller at hash blev beregnet korrekt
    if file_hash is None:
        log(f"Advarsel: Kunne ikke beregne hash for {file_path}, springer over", level=1)
        return
    
    # Find korrekt tracking dictionary
    if file_type == 'pdf':
        tracking_dict = tracking_data["pdf_files"]
    elif file_type == 'txt':
        tracking_dict = tracking_data["txt_files"]
    elif file_type == 'db':
        tracking_dict = tracking_data["db_files"]
    else:
        log(f"Ukendt filtype: {file_type}", level=1)
        return
    
    # Tilføj eller opdater filen i tracking
    tracking_dict[file_name] = file_hash
    log(f"Markeret {file_name} som behandlet ({file_type})", level=3)

#---------------------------
# ARGUMENT PARSING - Til kommandolinje brug
#---------------------------

def parse_arguments():
    """
    Parser kommandolinje-argumenter med defaults fra konfigurationen
    
    Returns:
        argparse.Namespace: De parserede argumenter
    """
    parser = argparse.ArgumentParser(description='Kør håndboldhændelser workflow')
    
    # Liga parameter (default: fra konfiguration)
    parser.add_argument('--liga', type=str, default=DEFAULT_LIGA,
                        help=f'Ligaen der skal behandles (kvindeligaen, herreligaen, eller begge). Default: {DEFAULT_LIGA}')
    
    # Sæson parameter (default: fra konfiguration)
    parser.add_argument('--sæson', type=str, default=DEFAULT_SAESON,
                        help=f'Sæsonen der skal behandles (f.eks. 2024-2025). Default: {DEFAULT_SAESON}')
    
    # Verbose flag
    parser.add_argument('--verbose', action='store_true', 
                        help='Vis detaljeret output i terminalen')
    
    # Parse argumenterne
    args = parser.parse_args()
    
    # Konverter liga-argument til lowercase for konsistens
    args.liga = args.liga.lower()
    
    # Valider liga-værdien
    valid_leagues = ['kvindeligaen', 'herreligaen', 'begge']
    if args.liga not in valid_leagues:
        log(f"Fejl: Ugyldig liga: {args.liga}. Gyldige værdier er: {', '.join(valid_leagues)}", is_important=True)
        sys.exit(1)
    
    # Valider sæson-format (YYYY-YYYY)
    if not re.match(r'^\d{4}-\d{4}$', args.sæson):
        log(f"Fejl: Ugyldig sæson: {args.sæson}. Formatet skal være YYYY-YYYY, f.eks. 2024-2025", is_important=True)
        sys.exit(1)
    
    # Opdater global VERBOSE_OUTPUT baseret på argumenter
    global VERBOSE_OUTPUT
    if args.verbose:
        VERBOSE_OUTPUT = True
    
    return args

#---------------------------
# MAPPESTRUKTURER - Til fil og mappeopsætning
#---------------------------

def setup_configuration(args, liga_name=None):
    """
    Opsætter konfiguration baseret på kommandolinje-argumenter og liga
    
    Args:
        args: Kommandolinje-argumenter
        liga_name: Liganavn (hvis None, bruges args.liga)
        
    Returns:
        tuple: Tupler med stier til input, output og øvrige mappeinformationer
    """
    # Brug liga fra argumenter hvis ikke specifikt angivet
    if liga_name is None:
        liga_name = args.liga
    
    # Konverter liga-navn til mappenavn (fjern 'en' fra slutningen)
    liga_mappe = liga_name
    if liga_mappe.endswith('en'):
        liga_mappe = liga_mappe[:-2]
    liga_mappe = liga_mappe.capitalize()
    
    # Oprette basisstinavne for mapper
    pdf_dir = os.path.join(liga_mappe, args.sæson)
    txt_dir = os.path.join(f"{liga_mappe}-txt-tabel", args.sæson)
    db_dir = os.path.join(f"{liga_mappe}-database", args.sæson)
    
    # Vis de opsatte stier
    log(f"Opsætter mappestruktur for {liga_mappe}:", level=1)
    log(f"PDF-mappe: {pdf_dir}", level=2)
    log(f"TXT-mappe: {txt_dir}", level=2)
    log(f"DB-mappe: {db_dir}", level=2)
    
    # Sørg for at alle mapper eksisterer
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(txt_dir, exist_ok=True)
    os.makedirs(db_dir, exist_ok=True)
    
    # Første år i sæsonen, bruges i URL
    year = args.sæson.split('-')[0]
    
    # Opret URL til liga
    base_url = "https://tophaandbold.dk"
    kampprogram_url = f"{base_url}/kampprogram/{liga_name}?year={year}&team=&home_game=0&home_game=1&away_game=0&away_game=1"
    
    return pdf_dir, txt_dir, db_dir, base_url, kampprogram_url

#---------------------------
# FORBEDRET PDF VALIDERING - For at sikre at PDF-filer indeholder reel data
#---------------------------

def is_valid_pdf(pdf_path):
    """
    Grundigere validering af om en PDF-fil indeholder brugbare kampdata
    
    Args:
        pdf_path: Sti til PDF-filen
        
    Returns:
        bool: True hvis PDF'en er gyldig og indeholder kampdata
    """
    # Tjek om filen eksisterer
    if not os.path.exists(pdf_path):
        return False
    
    # 1. Tjek filstørrelse - for små filer er sandsynligvis ikke gyldige
    file_size = os.path.getsize(pdf_path)
    if file_size < MIN_PDF_SIZE:
        log(f"PDF-fil er for lille ({file_size} bytes < {MIN_PDF_SIZE})", level=2)
        return False
        
    # 2. Tjek om filen er omkring størrelsen af tomme kamprapporter
    if abs(file_size - EMPTY_PDF_SIZE) < 5000:  # Inden for 5KB af den typiske tomme størrelse
        log(f"PDF-fil har mistænkelig størrelse nær tom skabelon ({file_size} bytes)", level=2)
        # Vi fortsætter med yderligere validering for at være sikre
    
    # 3. Prøv at åbne PDF-filen og analysere indholdet
    try:
        with open(pdf_path, 'rb') as file:
            # Tjek om den kan åbnes som PDF
            try:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # Tjek antal sider
                if len(pdf_reader.pages) == 0:
                    log(f"PDF-fil har ingen sider", level=2)
                    return False
                
                # Tjek for tekstindhold
                total_text = ""
                for i in range(min(3, len(pdf_reader.pages))):  # Tjek kun de første 3 sider
                    page = pdf_reader.pages[i]
                    text = page.extract_text()
                    total_text += text if text else ""
                
                # Hvis der er for lidt tekst, er PDF'en sandsynligvis tom eller korrupt
                if len(total_text) < MIN_TEXT_CONTENT:
                    log(f"PDF-fil indeholder for lidt tekst ({len(total_text)} tegn < {MIN_TEXT_CONTENT})", level=2)
                    return False
                
                # Tjek for nøgleord der forventes i en kamphændelses-rapport
                keywords = ["Tid", "Mål", "Hold", "Hændelse", "Pos", "Nr", "Navn"]
                keyword_count = sum(1 for keyword in keywords if keyword in total_text)
                
                if keyword_count < 4:  # Kræver mindst 4 matchende nøgleord
                    log(f"PDF-fil indeholder kun {keyword_count}/7 forventede nøgleord", level=2)
                    return False
                
                # Tjek specifikt efter tabeller med kamphændelser
                if "KAMPHÆNDELSER" not in total_text and "hændelser" not in total_text.lower():
                    log(f"PDF-fil indeholder ikke ordet 'KAMPHÆNDELSER'", level=2)
                    return False
                
                # Hvis alle validereringer er bestået, er PDF'en sandsynligvis gyldig
                return True
                
            except PyPDF2.errors.PdfReadError:
                log(f"Kunne ikke læse PDF-filen - sandsynligvis korrupt", level=2)
                return False
            
    except Exception as e:
        log(f"Fejl ved validering af PDF: {str(e)}", level=2)
        return False

def validate_pdf_after_download(pdf_path, tracking_data):
    """
    Validerer en PDF-fil efter download og sletter den, hvis den er ugyldig
    
    Args:
        pdf_path: Sti til PDF-filen
        tracking_data: Tracking data
        
    Returns:
        bool: True hvis PDF'en er gyldig, False hvis den blev slettet
    """
    # Tjek om PDF'en er gyldig
    if not is_valid_pdf(pdf_path):
        log(f"Ugyldig PDF-fil: {os.path.basename(pdf_path)} - sletter filen", level=2)
        
        # Fjern filen fra tracking
        unmark_file(pdf_path, 'pdf', tracking_data)
        
        # Slet filen
        try:
            os.remove(pdf_path)
            log(f"Slettet ugyldig PDF-fil: {os.path.basename(pdf_path)}", level=2)
            return False
        except Exception as e:
            log(f"Fejl ved sletning af ugyldig PDF-fil: {str(e)}", level=2)
            return False
    
    return True

#---------------------------
# SCRIPTKØRSEL - For at eksekvere underliggende scripts
#---------------------------

def get_script_path(script_name):
    """
    Finder den korrekte sti til et script
    
    Args:
        script_name: Navnet på scriptet
        
    Returns:
        str: Fuld sti til scriptet
    """
    # Liste over mulige placeringer
    possible_locations = [
        os.path.join(CURRENT_DIR, script_name),
        os.path.join(os.getcwd(), script_name),
        script_name
    ]
    
    # Tjek hver placering
    for location in possible_locations:
        if os.path.exists(location):
            return location
    
    # Hvis scriptet ikke findes, brug relativ sti som fallback
    return script_name

def run_script(script_name, description, args, extra_args=None):
    """
    Kører et Python-script med logging af resultatet og sender liga/sæson som argumenter
    
    Args:
        script_name: Navnet på scriptet der skal køres
        description: Beskrivelse af hvad scriptet gør
        args: Kommandolinje-argumenter
        extra_args: Ekstra argumenter til scriptet (optional)
        
    Returns:
        bool: True hvis scriptet kørte succesfuldt, ellers False
    """
    log(f"===== Starter {description} ({args.liga}, {args.sæson}) =====", is_important=True)
    
    try:
        # Find korrekt sti til scriptet
        script_path = get_script_path(script_name)
        
        # Opret kommando
        cmd = [sys.executable, script_path, f"--liga={args.liga}", f"--sæson={args.sæson}"]
        
        # Tilføj ekstra argumenter hvis angivet
        if extra_args:
            cmd.extend(extra_args)
        
        # Vis kommando
        log(f"Kører kommando: {' '.join(cmd)}", level=1)
        
        # Kør scriptet med argumenterne og vent på at det er færdigt
        start_time = time.time()
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True
        )
        end_time = time.time()
        
        # Log resultatet
        duration = end_time - start_time
        log(f"Script {script_name} afsluttet på {duration:.2f} sekunder", level=1)
        
        # Log output
        if result.stdout:
            if VERBOSE_OUTPUT:
                log(f"Output fra {script_name}:", level=1)
                for line in result.stdout.splitlines():
                    log(f"  > {line}", level=2)
            else:
                # Log kun de vigtigste linjer
                important_lines = [line for line in result.stdout.splitlines() 
                                 if "Vellykket:" in line or "Mislykkedes:" in line or 
                                    "Sprunget over:" in line or "Total:" in line]
                if important_lines:
                    log(f"Vigtige resultater fra {script_name}:", level=1)
                    for line in important_lines:
                        log(f"  > {line}", level=2)
            
        # Tjek for fejl
        if result.returncode != 0:
            log(f"Script {script_name} fejlede med returnkode {result.returncode}", level=1, is_important=True)
            if result.stderr:
                log(f"Fejl fra {script_name}:", level=1)
                for line in result.stderr.splitlines():
                    log(f"  > {line}", level=2)
            return False
        
        return True
        
    except Exception as e:
        log(f"Uventet fejl ved kørsel af {script_name}: {str(e)}", level=1, is_important=True)
        return False

#---------------------------
# TRACKING AF PROCESSERINGSKÆDEN - PDF→TXT→DB
#---------------------------

def check_full_processing_chain(pdf_path, txt_dir, db_dir, tracking_data):
    """
    Tjekker om en PDF-fil er blevet fuldstændigt behandlet gennem hele kæden
    (PDF -> TXT -> DB)
    
    Args:
        pdf_path: Sti til PDF-filen
        txt_dir: Mappe med TXT-filer
        db_dir: Mappe med DB-filer
        tracking_data: Tracking data
        
    Returns:
        tuple: (bool: er_færdigbehandlet, dict: status)
    """
    status = {
        "pdf_exists": False,
        "pdf_valid": False,
        "pdf_processed": False,
        "txt_exists": False,
        "txt_processed": False,
        "db_exists": False,
        "db_processed": False
    }
    
    # Tjek PDF-filen
    if not os.path.exists(pdf_path):
        return False, status
    
    status["pdf_exists"] = True
    
    # Tjek om PDF'en er gyldig
    if not is_valid_pdf(pdf_path):
        return False, status
    
    status["pdf_valid"] = True
    
    # Tjek om PDF'en er markeret som behandlet
    if is_file_processed(pdf_path, 'pdf', tracking_data):
        status["pdf_processed"] = True
    
    # Find forventede TXT- og DB-filer
    pdf_filename = os.path.basename(pdf_path)
    expected_txt_filename = pdf_filename.replace('.pdf', '.txt')
    txt_path = os.path.join(txt_dir, expected_txt_filename)
    
    # Tjek TXT-filen
    if os.path.exists(txt_path) and os.path.getsize(txt_path) > 100:  # TXT skal have noget indhold
        status["txt_exists"] = True
        
        # Tjek om TXT-filen er markeret som behandlet
        if is_file_processed(txt_path, 'txt', tracking_data):
            status["txt_processed"] = True
    
    # Ekstrahér match_id fra filnavnet for at finde DB-filen
    match_id_match = re.search(r'match_(\d+)', pdf_filename)
    if match_id_match:
        match_id = match_id_match.group(1)
        
        # Søg efter DB-filer med dette match_id
        for db_filename in os.listdir(db_dir):
            if db_filename.endswith('.db') and match_id in db_filename:
                db_path = os.path.join(db_dir, db_filename)
                
                # Tjek om DB-filen er gyldig (har indhold)
                if os.path.getsize(db_path) > 1000:  # DB skal være over 1KB
                    status["db_exists"] = True
                    
                    # Tjek om DB-filen er markeret som behandlet
                    if is_file_processed(db_path, 'db', tracking_data):
                        status["db_processed"] = True
                    
                    break
    
    # En fil er kun fuldt behandlet hvis den har gået gennem hele kæden
    fully_processed = (status["pdf_processed"] and status["txt_processed"] and status["db_processed"])
    
    return fully_processed, status

def find_unprocessed_files(pdf_dir, txt_dir, db_dir, tracking_data):
    """
    Finder PDF-filer der ikke er blevet fuldt behandlet gennem PDF→TXT→DB kæden
    
    Args:
        pdf_dir: Mappe med PDF-filer
        txt_dir: Mappe med TXT-filer
        db_dir: Mappe med DB-filer
        tracking_data: Tracking data
        
    Returns:
        dict: Information om ubehandlede filer
    """
    result = {
        "pdfs_need_txt": [],  # PDF-filer der mangler TXT-konvertering
        "txts_need_db": [],   # TXT-filer der mangler DB-konvertering
        "invalid_pdfs": []    # Ugyldige PDF-filer der skal slettes
    }
    
    # Gennemgå alle PDF-filer
    if os.path.exists(pdf_dir):
        for pdf_filename in os.listdir(pdf_dir):
            if not pdf_filename.endswith('.pdf'):
                continue
                
            pdf_path = os.path.join(pdf_dir, pdf_filename)
            fully_processed, status = check_full_processing_chain(pdf_path, txt_dir, db_dir, tracking_data)
            
            # Hvis PDF'en er ugyldig, marker den til sletning
            if status["pdf_exists"] and not status["pdf_valid"]:
                result["invalid_pdfs"].append(pdf_path)
                continue
            
            # Hvis PDF'en er valid men ikke fuldt behandlet
            if not fully_processed and status["pdf_valid"]:
                if not status["txt_exists"] or not status["txt_processed"]:
                    # PDF mangler konvertering til TXT
                    result["pdfs_need_txt"].append(pdf_path)
                elif status["txt_exists"] and not status["db_exists"]:
                    # TXT mangler konvertering til DB
                    txt_path = os.path.join(txt_dir, pdf_filename.replace('.pdf', '.txt'))
                    result["txts_need_db"].append(txt_path)
    
    return result

def process_unfinished_files(unprocessed_info, args, tracking_data):
    """
    Behandler filer der ikke er gået igennem hele behandlingskæden
    
    Args:
        unprocessed_info: Information om ubehandlede filer
        args: Kommandolinje-argumenter
        tracking_data: Tracking data
        
    Returns:
        dict: Statistik over behandlede filer
    """
    results = {
        "invalid_pdfs_removed": 0,
        "txt_converted": 0,
        "db_processed": 0
    }
    
    # 1. Slet ugyldige PDF-filer
    for pdf_path in unprocessed_info["invalid_pdfs"]:
        log(f"Sletter ugyldig PDF-fil: {os.path.basename(pdf_path)}", level=1)
        unmark_file(pdf_path, 'pdf', tracking_data)
        try:
            os.remove(pdf_path)
            results["invalid_pdfs_removed"] += 1
        except:
            log(f"Kunne ikke slette fil: {pdf_path}", level=1)
    
    # 2. Konverter PDF-filer der mangler TXT-konvertering
    if unprocessed_info["pdfs_need_txt"]:
        log(f"Fandt {len(unprocessed_info['pdfs_need_txt'])} PDF-filer der mangler TXT-konvertering", level=1)
        pdf_to_text_script = get_script_path("pdf_to_text_converter.py")
        
        if os.path.exists(pdf_to_text_script):
            log(f"Kører PDF til TXT konvertering...", level=1)
            success = run_script("pdf_to_text_converter.py", "PDF til TXT konvertering", args)
            
            if success:
                # Kontroller hvilke TXT-filer der er blevet genereret
                converted_count = 0
                for pdf_path in unprocessed_info["pdfs_need_txt"]:
                    pdf_filename = os.path.basename(pdf_path)
                    pdf_dir = os.path.dirname(pdf_path)
                    liga_mappe = os.path.basename(os.path.dirname(os.path.dirname(pdf_path))) if os.path.dirname(os.path.dirname(pdf_path)) else ""
                    
                    # Find den tilsvarende TXT-mappe
                    txt_dir = pdf_dir.replace(liga_mappe, f"{liga_mappe}-txt-tabel")
                    txt_path = os.path.join(txt_dir, pdf_filename.replace('.pdf', '.txt'))
                    
                    # Hvis TXT-filen blev oprettet, marker den som behandlet
                    if os.path.exists(txt_path) and os.path.getsize(txt_path) > 100:
                        mark_file_processed(txt_path, 'txt', tracking_data)
                        converted_count += 1
                
                results["txt_converted"] = converted_count
                log(f"Konverterede {converted_count} PDF-filer til TXT", level=1)
                
            else:
                log(f"PDF til TXT konvertering fejlede", level=1)
        else:
            log(f"PDF til TXT konverteringsscript ikke fundet: {pdf_to_text_script}", level=1)
    
    # 3. Konverter TXT-filer der mangler DB-konvertering
    if unprocessed_info["txts_need_db"]:
        log(f"Fandt {len(unprocessed_info['txts_need_db'])} TXT-filer der mangler DB-konvertering", level=1)
        db_processor_script = get_script_path("handball_data_processor.py")
        
        if os.path.exists(db_processor_script):
            log(f"Kører TXT til DB konvertering...", level=1)
            success = run_script("handball_data_processor.py", "TXT til DB konvertering", args)
            
            if success:
                # Efter konvertering, find nyoprettede DB-filer
                db_processed_count = 0
                
                # For hver TXT-fil, find tilsvarende DB-fil
                for txt_path in unprocessed_info["txts_need_db"]:
                    txt_filename = os.path.basename(txt_path)
                    match_id_match = re.search(r'match_(\d+)', txt_filename)
                    
                    if match_id_match:
                        match_id = match_id_match.group(1)
                        db_dir = os.path.dirname(txt_path).replace("-txt-tabel", "-database")
                        
                        # Søg efter DB-filer med dette match_id
                        for db_filename in os.listdir(db_dir):
                            if db_filename.endswith('.db') and match_id in db_filename:
                                db_path = os.path.join(db_dir, db_filename)
                                
                                # Marker DB-filen som behandlet
                                if os.path.getsize(db_path) > 1000:  # DB skal være over 1KB
                                    mark_file_processed(db_path, 'db', tracking_data)
                                    db_processed_count += 1
                                    break
                
                results["db_processed"] = db_processed_count
                log(f"Konverterede {db_processed_count} TXT-filer til DB", level=1)
                
            else:
                log(f"TXT til DB konvertering fejlede", level=1)
        else:
            log(f"TXT til DB konverteringsscript ikke fundet: {db_processor_script}", level=1)
    
    # Gem tracking data
    save_tracking_data(tracking_data)
    
    return results

#---------------------------
# FORBEDRET PDF DOWNLOAD - Med validering og tracking
#---------------------------

def download_pdf(url, output_file, tracking_data, base_url):
    """
    Download PDF fra URL og gem den med det givne filnavn
    
    Args:
        url: URL til PDF-filen
        output_file: Filnavn PDF'en skal gemmes som
        tracking_data: Tracking data
        base_url: Base URL for at bygge komplette URL'er
        
    Returns:
        bool: True hvis download var succesfuld, ellers False
    """
    # Tjek om filen allerede er behandlet gennem hele kæden
    pdf_dir = os.path.dirname(output_file)
    txt_dir = pdf_dir.replace("Herreliga", "Herreliga-txt-tabel").replace("Kvindeliga", "Kvindeliga-txt-tabel")
    db_dir = pdf_dir.replace("Herreliga", "Herreliga-database").replace("Kvindeliga", "Kvindeliga-database")
    
    # Hvis filerne ikke eksisterer, opret mapperne
    os.makedirs(txt_dir, exist_ok=True)
    os.makedirs(db_dir, exist_ok=True)
    
    fully_processed, status = check_full_processing_chain(output_file, txt_dir, db_dir, tracking_data)
    
    # Hvis filen er helt færdigbehandlet, spring over
    if fully_processed:
        log(f"Filen {os.path.basename(output_file)} er allerede færdigbehandlet (PDF→TXT→DB). Springer over.", level=2)
        return True
    
    # Hvis PDF-filen findes og er gyldig, men ikke færdigbehandlet, spring over download
    if status["pdf_exists"] and status["pdf_valid"]:
        log(f"PDF-filen {os.path.basename(output_file)} findes og er gyldig, men mangler viderebehandling.", level=2)
        
        # Marker PDF'en som behandlet hvis den ikke allerede er
        if not status["pdf_processed"]:
            mark_file_processed(output_file, 'pdf', tracking_data)
            save_tracking_data(tracking_data)
        
        return True
    
    # Hvis filen findes men er ugyldig, slet den og gendownload
    if status["pdf_exists"] and not status["pdf_valid"]:
        log(f"PDF-filen {os.path.basename(output_file)} findes men er ugyldig. Sletter og gendownloader.", level=2)
        unmark_file(output_file, 'pdf', tracking_data)
        try:
            os.remove(output_file)
        except:
            pass
    
    # Download filen
    log(f"Downloader: {os.path.basename(output_file)}", level=2)
    
    try:
        # Sikr at URL'en er komplet
        if not url.startswith('http'):
            if url.startswith('/'):
                url = base_url + url
            else:
                url = base_url + '/' + url
        
        # Tilføj download=0 parameter hvis den ikke allerede er der
        if "download=" not in url:
            if "?" in url:
                url += "&download=0"
            else:
                url += "?download=0"
        
        # Log URL (kun når vi faktisk skal downloade)
        log(f"  URL: {url}", level=3)
        
        # Download filen
        response = requests.get(url, timeout=15)
        
        # Tjek om vi fik et gyldigt svar
        if response.status_code != 200:
            log(f"Fejl ved download: Status kode {response.status_code}", level=2)
            return False
        
        # Tjek at indholdet ligner en PDF
        is_pdf = response.content.startswith(b'%PDF-') or 'application/pdf' in response.headers.get('Content-Type', '')
        if not is_pdf:
            log(f"Advarsel: Indholdet ligner ikke en PDF-fil. Content-Type: {response.headers.get('Content-Type')}", level=2)
            return False
        
        # Gem filen
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        # Valider PDF-filen efter download
        if not validate_pdf_after_download(output_file, tracking_data):
            log(f"PDF-fil validering fejlede efter download, filen er slettet: {os.path.basename(output_file)}", level=2)
            return False
        
        # Verificer filstørrelsen
        file_size = os.path.getsize(output_file)
        log(f"PDF-fil gemt: {os.path.basename(output_file)} ({file_size} bytes)", level=2)
        
        # Markér filen som behandlet i tracking systemet
        mark_file_processed(output_file, 'pdf', tracking_data)
        save_tracking_data(tracking_data)
        
        return True
    except Exception as e:
        log(f"Fejl ved download af {url}: {str(e)}", level=2)
        # Skriv fejlbesked til en fil for at hjælpe med fejlsøgning
        try:
            with open(output_file + ".error", "w") as f:
                f.write(f"Download fejlet: {str(e)}")
        except:
            pass
        return False

def extract_match_id_from_href(href):
    """
    Udtrækker match_id og match_type fra en URL
    
    Args:
        href: URL at undersøge
        
    Returns:
        tuple: (match_id, match_type) eller (None, None)
    """
    # Pattern for links som "/intranet/pdfs/game/2024/9010199/748777/a?download=0"
    match = re.search(r'/pdfs/game/\d+/\d+/(\d+)/([a-z])', href)
    if match:
        return match.group(1), match.group(2)
    return None, None

def download_liga_pdf_files(args, liga_name, tracking_data):
    """
    Download PDF-filer for specifik liga
    
    Args:
        args: Kommandolinje-argumenter
        liga_name: Liganavn at downloade for
        tracking_data: Tracking data for processerede filer
        
    Returns:
        tuple: (antal_downloadet, antal_sprunget_over, antal_fejlet)
    """
    # Opsæt mappestruktur
    pdf_dir, _, _, base_url, kampprogram_url = setup_configuration(args, liga_name)
    
    log(f"===== Starter PDF download for {liga_name} ({args.sæson}) =====", is_important=True)
    log(f"Henter kampprogramside fra: {kampprogram_url}", level=1)
    
    start_time = time.time()
    
    try:
        # Hent kampprogram-siden
        log(f"Henter kampprogram-siden...", level=1)
        response = requests.get(kampprogram_url, timeout=30)
        
        if response.status_code != 200:
            log(f"Fejl ved hentning af kampprogram-siden: Status kode {response.status_code}", level=1)
            return 0, 0, 0
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Gem en kopi af HTML for debugging
        debug_file = f'debug_page_{liga_name}.html'
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        log(f"HTML-side gemt som {debug_file} for debugging", level=1)
        
        # Find alle 'Alle hændelser' links
        alle_links = []
        
        # Metode 1: Søg i dropdown-items
        for link in soup.find_all('a', class_='dropdown-item'):
            text = link.get_text(strip=True)
            href = link.get('href')
            
            if href and text and ("Alle hændelser" in text or "alle hændelser" in text.lower()):
                match_id, match_type = extract_match_id_from_href(href)
                if match_id and match_type:
                    alle_links.append((href, match_id, match_type))
        
        # Metode 2: Generel søgning efter links
        if not alle_links:
            log("Ingen 'Alle hændelser' links fundet via dropdown-items, prøver generel søgning...", level=1)
            for link in soup.find_all('a'):
                text = link.get_text(strip=True)
                href = link.get('href')
                
                if href and text and ("Alle hændelser" in text or "alle hændelser" in text.lower()):
                    match_id, match_type = extract_match_id_from_href(href)
                    if match_id and match_type:
                        alle_links.append((href, match_id, match_type))
        
        # Statistik for download
        downloadet = 0
        sprunget_over = 0
        fejlet = 0
        
        if alle_links:
            log(f"Fandt {len(alle_links)} 'Alle hændelser' links", level=1)
            
            for url, match_id, match_type in alle_links:
                output_file = os.path.join(pdf_dir, f"match_{match_id}_{match_type}.pdf")
                
                # Tjek om filen allerede er behandlet gennem hele kæden
                txt_dir = pdf_dir.replace("Herreliga", "Herreliga-txt-tabel").replace("Kvindeliga", "Kvindeliga-txt-tabel") 
                db_dir = pdf_dir.replace("Herreliga", "Herreliga-database").replace("Kvindeliga", "Kvindeliga-database")
                fully_processed, _ = check_full_processing_chain(output_file, txt_dir, db_dir, tracking_data)
                
                if fully_processed:
                    log(f"Fil allerede fuldt proceseret: match_{match_id}_{match_type}.pdf", level=2)
                    sprunget_over += 1
                    continue
                
                # Ellers download/kontroller PDF
                if download_pdf(url, output_file, tracking_data, base_url):
                    downloadet += 1
                else:
                    fejlet += 1
                
                # Lille pause mellem downloads for at undgå at blive begrænset af serveren
                time.sleep(0.5)
            
            end_time = time.time()
            duration = end_time - start_time
            
            log(f"PDF download for {liga_name} afsluttet på {duration:.2f} sekunder", level=1)
            log(f"Downloadet: {downloadet}, Sprunget over: {sprunget_over}, Fejlet: {fejlet}", level=1, is_important=True)
            
            return downloadet, sprunget_over, fejlet
        else:
            log(f"Ingen 'Alle hændelser' links fundet for {liga_name}.", level=1, is_important=True)
            return 0, 0, 0
    
    except Exception as e:
        log(f"Fejl ved download af {liga_name} PDF-filer: {str(e)}", level=1, is_important=True)
        return 0, 0, 0

#---------------------------
# HJÆLPEFUNKTIONER - Diverse værktøjer
#---------------------------

def count_files_in_dir(directory, extension):
    """
    Tæller filer med en bestemt extension i en mappe
    
    Args:
        directory: Mappen der skal tælles i
        extension: Filtypen der skal tælles
        
    Returns:
        int: Antal filer
    """
    if not os.path.exists(directory):
        return 0
    
    count = 0
    for file in os.listdir(directory):
        if file.lower().endswith(extension.lower()):
            count += 1
    
    return count

#---------------------------
# HOVEDFUNKTIONER - Procesering af ligaer
#---------------------------

def process_liga(args, liga_name, tracking_data):
    """
    Behandler en enkelt liga
    
    Args:
        args: Kommandolinje-argumenter
        liga_name: Liga der skal behandles
        tracking_data: Tracking data
        
    Returns:
        tuple: (results, invalid_removed) - statistik og antal fjernede filer
    """
    # Vis start af liga processering
    log(f"\n======= STARTER {liga_name.upper()} PROCESSERING =======", is_important=True)
    
    # Hent mapper for denne liga
    pdf_dir, txt_dir, db_dir, _, _ = setup_configuration(args, liga_name) 
    
    # Tæl filer før processering
    pdf_count_before = count_files_in_dir(pdf_dir, '.pdf')
    txt_count_before = count_files_in_dir(txt_dir, '.txt')
    db_count_before = count_files_in_dir(db_dir, '.db')
    
    log(f"Filer før processering:", level=1)
    log(f"  PDF-filer: {pdf_count_before}", level=1)
    log(f"  TXT-filer: {txt_count_before}", level=1)
    log(f"  DB-filer: {db_count_before}", level=1)
    
    liga_start_time = time.time()
    
    # Resultater dictionary
    results = {
        "pdf_downloaded": 0,
        "pdf_skipped": 0,
        "pdf_failed": 0,
        "txt_converted": 0,
        "txt_skipped": 0,
        "db_processed": 0,
        "db_skipped": 0
    }
    
    # 1. Find filer der ikke er fuldt proceseret
    log("Analyserer eksisterende filer for at finde manglende processeringstrin...", level=1)
    unprocessed_info = find_unprocessed_files(pdf_dir, txt_dir, db_dir, tracking_data)
    
    log(f"Fandt:", level=1)
    log(f"  {len(unprocessed_info['invalid_pdfs'])} ugyldige PDF-filer", level=2)
    log(f"  {len(unprocessed_info['pdfs_need_txt'])} PDF-filer der mangler TXT-konvertering", level=2)
    log(f"  {len(unprocessed_info['txts_need_db'])} TXT-filer der mangler DB-konvertering", level=2)
    
    # 2. Behandl disse filer først
    processing_stats = process_unfinished_files(unprocessed_info, args, tracking_data)
    invalid_pdfs_removed = processing_stats["invalid_pdfs_removed"]
    results["txt_converted"] = processing_stats["txt_converted"]
    results["db_processed"] = processing_stats["db_processed"]
    
    # 3. Download nye PDF-filer
    pdf_downloaded, pdf_skipped, pdf_failed = download_liga_pdf_files(args, liga_name, tracking_data)
    results["pdf_downloaded"] = pdf_downloaded
    results["pdf_skipped"] = pdf_skipped
    results["pdf_failed"] = pdf_failed
    
    # 4. Kontroller igen om der er nye filer der mangler processing
    log("Kontrollerer om der er nye filer, der mangler processeringstrin...", level=1)
    unprocessed_info = find_unprocessed_files(pdf_dir, txt_dir, db_dir, tracking_data)
    
    log(f"Fandt efter download:", level=1)
    log(f"  {len(unprocessed_info['invalid_pdfs'])} ugyldige PDF-filer", level=2)
    log(f"  {len(unprocessed_info['pdfs_need_txt'])} PDF-filer der mangler TXT-konvertering", level=2)
    log(f"  {len(unprocessed_info['txts_need_db'])} TXT-filer der mangler DB-konvertering", level=2)
    
    # 5. Behandl de nye filer
    if unprocessed_info['pdfs_need_txt'] or unprocessed_info['txts_need_db'] or unprocessed_info['invalid_pdfs']:
        log("Behandler nye filer der mangler processeringstrin...", level=1)
        new_processing_stats = process_unfinished_files(unprocessed_info, args, tracking_data)
        
        # Opdater statistik
        invalid_pdfs_removed += new_processing_stats["invalid_pdfs_removed"]
        results["txt_converted"] += new_processing_stats["txt_converted"]
        results["db_processed"] += new_processing_stats["db_processed"]
    
    # Tæl filer efter processering
    pdf_count_after = count_files_in_dir(pdf_dir, '.pdf')
    txt_count_after = count_files_in_dir(txt_dir, '.txt')
    db_count_after = count_files_in_dir(db_dir, '.db')
    
    liga_end_time = time.time()
    liga_duration = liga_end_time - liga_start_time
    
    # Vis opsummering for denne liga
    log(f"\n======= {liga_name.upper()} PROCESSERING AFSLUTTET =======", is_important=True)
    log(f"Total køretid: {liga_duration:.2f} sekunder", level=1)
    
    log(f"Filer efter processering:", level=1)
    log(f"  PDF-filer: {pdf_count_after} ({pdf_count_after - pdf_count_before:+d})", level=1)
    log(f"  TXT-filer: {txt_count_after} ({txt_count_after - txt_count_before:+d})", level=1)
    log(f"  DB-filer: {db_count_after} ({db_count_after - db_count_before:+d})", level=1)
    
    log(f"Opsummering:", level=1, is_important=True)
    log(f"  PDF: {results['pdf_downloaded']} downloadet, {results['pdf_skipped']} sprunget over, {results['pdf_failed']} fejlet, {invalid_pdfs_removed} ugyldige fjernet", level=1)
    log(f"  TXT: {results['txt_converted']} konverteret, {results['txt_skipped']} sprunget over", level=1)
    log(f"  DB: {results['db_processed']} behandlet, {results['db_skipped']} sprunget over", level=1)
    
    # Gem tracking data
    save_tracking_data(tracking_data)
    
    return results, invalid_pdfs_removed

#---------------------------
# HOVEDFUNKTION - Main entry point
#---------------------------

def main():
    """
    Kører hele workflowet i rækkefølge for de valgte ligaer
    """
    # Vis velkomst
    log("=" * 80, is_important=True)
    log("HÅNDBOLDHÆNDELSER WORKFLOW", is_important=True)
    log(f"Dato og tid: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", is_important=True)
    log(f"Script version: 2.2 (forbedret processeringskæde-tracking)", is_important=True)
    log("=" * 80, is_important=True)
    
    # Parse argumenter
    args = parse_arguments()
    
    # Indlæs tracking data
    tracking_data = load_tracking_data()
    log(f"Indlæst tracking data for {len(tracking_data['pdf_files'])} PDF-filer, " +
        f"{len(tracking_data['txt_files'])} TXT-filer og {len(tracking_data['db_files'])} DB-filer", level=1)
    
    workflow_start = time.time()
    
    # Total resultater
    total_results = {
        "pdf_downloaded": 0,
        "pdf_skipped": 0,
        "pdf_failed": 0,
        "pdf_invalid_removed": 0,
        "txt_converted": 0,
        "txt_skipped": 0,
        "db_processed": 0,
        "db_skipped": 0
    }
    
    # Proces de valgte ligaer
    if args.liga == 'herreligaen' or args.liga == 'begge':
        log("\n\n" + "=" * 80, is_important=True)
        log("PROCESSERER HERRELIGAEN", is_important=True)
        log("=" * 80, is_important=True)
        
        herreliga_results, invalid_removed = process_liga(args, 'herreligaen', tracking_data)
        # Opdater total resultater
        for key in herreliga_results:
            total_results[key] += herreliga_results[key]
        total_results["pdf_invalid_removed"] += invalid_removed
    
    if args.liga == 'kvindeligaen' or args.liga == 'begge':
        log("\n\n" + "=" * 80, is_important=True)
        log("PROCESSERER KVINDELIGAEN", is_important=True)
        log("=" * 80, is_important=True)
        
        kvindeliga_results, invalid_removed = process_liga(args, 'kvindeligaen', tracking_data)
        # Opdater total resultater
        for key in kvindeliga_results:
            total_results[key] += kvindeliga_results[key]
        total_results["pdf_invalid_removed"] += invalid_removed
    
    workflow_end = time.time()
    duration = workflow_end - workflow_start
    
    # Gem tracking data en sidste gang
    save_tracking_data(tracking_data)
    
    # Vis samlet opsummering
    log("\n\n" + "=" * 80, is_important=True)
    log("WORKFLOW AFSLUTTET", is_important=True)
    log("=" * 80, is_important=True)
    
    log(f"Liga: {args.liga}, Sæson: {args.sæson}", level=1)
    log(f"Total køretid: {duration:.2f} sekunder ({duration/60:.2f} minutter)", level=1)
    
    log(f"Samlet resultat:", level=1, is_important=True)
    log(f"  PDF: {total_results['pdf_downloaded']} downloadet, {total_results['pdf_skipped']} sprunget over, {total_results['pdf_failed']} fejlet", level=1)
    log(f"  PDF Validering: {total_results['pdf_invalid_removed']} ugyldige PDF-filer fjernet", level=1)
    log(f"  TXT: {total_results['txt_converted']} konverteret, {total_results['txt_skipped']} sprunget over", level=1)
    log(f"  DB: {total_results['db_processed']} behandlet, {total_results['db_skipped']} sprunget over", level=1)
    
    log(f"\nAlle filer er nu behandlet gennem hele processerings-kæden (PDF→TXT→DB).", level=0, is_important=True)
    
    # Returnér 0 for succes
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)