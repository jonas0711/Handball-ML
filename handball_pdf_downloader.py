#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Håndbold PDF Downloader

Dette script downloader PDF-filer med kamphændelser fra tophaandbold.dk
for en given liga og sæson.

Det er designet til at blive kaldt af et master pipeline script og vil:
- Bruge en tracking-fil til at undgå at downloade allerede fuldt behandlede kampe.
- Gemme downloadede PDF'er i den korrekte mappestruktur.
"""

import os
import sys
import time
import logging
import argparse
import re
import requests
from pathlib import Path
from bs4 import BeautifulSoup
import json # Til at læse master tracking fil
from tqdm import tqdm # <--- TILFØJ DENNE LINJE
try:
    import PyPDF2 # For hurtig PDF struktur validering
except ImportError:
    print("❌ FEJL: PyPDF2 ikke installeret. Installer med: pip install PyPDF2")
    sys.exit(1)

try:
    import fitz  # PyMuPDF for PDF til TXT konvertering
except ImportError:
    print("❌ FEJL: PyMuPDF ikke installeret. Installer med: pip install PyMuPDF")
    sys.exit(1)

# --- KONFIGURATION ---
# Disse stier defineres relativt til master scriptets placering
# BASE_PROJECT_PATH vil blive sat i masteren. Her definerer vi relative stier.
# Mappestrukturen antages at være:
# Handball-ML/
# ├── Kvindeliga/
# │   └── 2023-2024/
# │       └── match_xxxxxx_a.pdf
# ├── Herreliga/
# ... etc.

# Logging opsætning (bør matche master scriptets opsætning for konsistens)
LOG_DIR_NAME = "Logs"
DOWNLOADER_LOG_FILE_NAME = "handball_pdf_downloader.log"

# Master tracking fil (læses for at undgå unødvendige downloads)
JSON_DIR_NAME = "JSON"
MASTER_TRACKING_FILE_NAME = "pipeline_tracking_status.json"

# Tophaandbold base URL
BASE_URL = "https://tophaandbold.dk"

# HTTP Headers for at simulere en browser
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Globale variabler til logger og tracking data (initialiseres i main)
logger = None
tracking_data_global = None # Vil indeholde master tracking data

# --- PDF TIL TXT KONVERTERING FUNKTIONER (Baseret på pdf_to_text_converter.py) ---

def setup_txt_output_dir(liga_folder_name, season_str, base_project_path):
    """
    Opretter og returnerer TXT output mappe baseret på samme struktur som pdf_to_text_converter.py
    
    Args:
        liga_folder_name (str): Liga mappe navn (f.eks. "Herreliga")
        season_str (str): Sæson (f.eks. "2024-2025")
        base_project_path (Path): Base project sti
        
    Returns:
        Path: Sti til TXT output mappe
    """
    # Samme struktur som pdf_to_text_converter.py: {Liga}-txt-tabel/{sæson}/
    txt_base_dir_name = f"{liga_folder_name}-txt-tabel"
    txt_output_dir = base_project_path / txt_base_dir_name / season_str
    
    # Opret mapperne hvis de ikke eksisterer
    txt_output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"TXT output mappe: {txt_output_dir}")
    return txt_output_dir

def txt_file_already_exists(pdf_path, txt_output_dir):
    """
    Tjekker om der allerede findes en TXT fil for denne PDF
    Samme logik som pdf_to_text_converter.py
    
    Args:
        pdf_path (Path): Sti til PDF filen
        txt_output_dir (Path): TXT output mappe
        
    Returns:
        bool: True hvis TXT filen allerede eksisterer
    """
    # Beregn TXT filnavn baseret på PDF filnavn
    txt_filename = pdf_path.stem + ".txt"  # .stem fjerner extension
    txt_path = txt_output_dir / txt_filename
    
    if txt_path.exists():
        logger.debug(f"TXT fil eksisterer allerede: {txt_filename}")
        return True
    
    return False

def convert_single_pdf_to_txt(pdf_path, txt_output_dir):
    """
    Konverterer en enkelt PDF fil til TXT format med bevarelse af struktur.
    Samme konvertering logik som pdf_to_text_converter.py
    
    Args:
        pdf_path (Path): Sti til PDF filen
        txt_output_dir (Path): TXT output mappe
        
    Returns:
        tuple: (bool: success, str: txt_filename eller fejlbesked)
    """
    try:
        # Beregn output filnavn
        txt_filename = pdf_path.stem + ".txt"
        txt_path = txt_output_dir / txt_filename
        
        # Tjek om TXT fil allerede eksisterer
        if txt_file_already_exists(pdf_path, txt_output_dir):
            return True, f"TXT fil eksisterer allerede: {txt_filename}"
        
        # Åbn PDF dokumentet med PyMuPDF
        doc = fitz.open(pdf_path)
        text_output = []
        
        # Behandl hver side (samme som pdf_to_text_converter.py)
        for page_num, page in enumerate(doc):
            # Tilføj sidenummer undtagen for første side
            if page_num > 0:
                text_output.append(f"\n--- Side {page_num + 1} ---\n")
            
            # Udtræk tekst med bevarelse af layout
            text = page.get_text("text")
            text_output.append(text)
        
        # Luk dokumentet
        doc.close()
        
        # Gem den ekstraherede tekst til fil
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(''.join(text_output))
        
        logger.debug(f"✅ PDF→TXT konverteret: {pdf_path.name} → {txt_filename}")
        return True, txt_filename
        
    except Exception as e:
        logger.error(f"❌ Fejl ved PDF→TXT konvertering af {pdf_path.name}: {str(e)}")
        return False, f"Konvertering fejl: {str(e)[:50]}"

def convert_downloaded_pdfs_to_txt(downloaded_pdf_files, txt_output_dir):
    """
    Konverterer alle nyligt downloadede PDF filer til TXT format.
    Dette sker EFTER alle downloads er færdige som ønsket.
    
    Args:
        downloaded_pdf_files (list): Liste med stier til nyligt downloadede PDF filer
        txt_output_dir (Path): TXT output mappe
        
    Returns:
        dict: Statistik over konverteringer
    """
    if not downloaded_pdf_files:
        logger.info("📝 Ingen nye PDF filer at konvertere til TXT")
        return {"converted": 0, "already_exists": 0, "failed": 0}
    
    logger.info(f"📝 STARTER PDF→TXT konvertering af {len(downloaded_pdf_files)} nyligt downloadede filer")
    
    stats = {
        "converted": 0,
        "already_exists": 0, 
        "failed": 0
    }
    
    # Konverter hver downloadet PDF fil
    for pdf_path in tqdm(downloaded_pdf_files, desc="Konverterer PDF→TXT"):
        success, result = convert_single_pdf_to_txt(pdf_path, txt_output_dir)
        
        if success:
            if "eksisterer allerede" in result:
                stats["already_exists"] += 1
            else:
                stats["converted"] += 1
                logger.info(f"📄 Konverteret: {pdf_path.name} → {result}")
        else:
            stats["failed"] += 1
            logger.warning(f"❌ Konvertering fejlede: {pdf_path.name} - {result}")
    
    # Log sammendrag
    logger.info(f"📊 PDF→TXT RESULTAT:")
    logger.info(f"   ✅ Nye konverteringer: {stats['converted']}")
    logger.info(f"   ⏭️ Eksisterede allerede: {stats['already_exists']}")
    logger.info(f"   ❌ Fejlede konverteringer: {stats['failed']}")
    
    return stats

# --- HURTIGE PDF VALIDERING FUNKTIONER (Inspireret af complete.py) ---

def quick_pdf_validation(pdf_path):
    """
    Udfører hurtige PDF valideringer for at sikre filen indeholder kampdata.
    Designet til at være meget hurtig men stadig fange de fleste problemer.
    
    Args:
        pdf_path (Path): Sti til PDF filen der skal valideres
        
    Returns:
        tuple: (bool: er_gyldig, str: reason)
    """
    try:
        # HURTIG CHECK 1: Filstørrelse - skal være mindst 40KB (som complete.py)
        file_size = pdf_path.stat().st_size
        if file_size < 40000:  # 40KB minimum
            return False, f"For lille fil ({file_size} bytes, kræver ≥40KB)"
        
        # HURTIG CHECK 2: Basis PDF struktur med PyPDF2
        try:
            with open(pdf_path, 'rb') as f:
                pdf_reader = PyPDF2.PdfReader(f)
                
                # Tjek om PDF har sider
                if len(pdf_reader.pages) == 0:
                    return False, "PDF har ingen sider"
                
                # Prøv at læse første side som quick test
                first_page = pdf_reader.pages[0]
                page_text = first_page.extract_text()
                
                if not page_text or len(page_text.strip()) < 100:
                    return False, f"For lidt tekst på første side ({len(page_text.strip()) if page_text else 0} tegn)"
                
        except Exception as pdf_error:
            return False, f"PDF struktur fejl: {str(pdf_error)[:50]}"
        
        # HURTIG CHECK 3: Simple nøgleords check (hurtig version)
        # Søger efter håndbold-relaterede nøgleord i første del af teksten
        text_sample = page_text[:1000].lower()  # Kun første 1000 tegn for hastighed
        
        # Specifik søgning efter kamphændelser dokumenter
        target_keywords = ['kamphændelser', 'kamprapport']
        
        found_keywords = sum(1 for keyword in target_keywords if keyword in text_sample)
        
        if found_keywords < 1:  # Kræver mindst ét kamphændelser/kamprapport nøgleord
            return False, f"Ikke en kamphændelser/kamprapport fil (fandt {found_keywords} af: {target_keywords})"
        
        # Alle hurtige checks bestået
        logger.debug(f"PDF validering OK: {pdf_path.name} ({file_size/1024:.1f}KB, {found_keywords} nøgleord)")
        return True, f"Gyldig kampdata PDF ({file_size/1024:.1f}KB, {found_keywords} nøgleord)"
        
    except Exception as e:
        return False, f"Validering fejl: {str(e)[:50]}"

def delete_invalid_pdf(pdf_path, reason):
    """
    Sletter en ugyldig PDF fil og logger årsagen.
    
    Args:
        pdf_path (Path): Sti til filen der skal slettes
        reason (str): Årsag til sletning
    """
    try:
        pdf_path.unlink()
        logger.info(f"❌ Slettet ugyldig PDF: {pdf_path.name} - {reason}")
        return True
    except Exception as e:
        logger.error(f"Kunne ikke slette ugyldig PDF {pdf_path.name}: {e}")
        return False

# --- HJÆLPEFUNKTIONER ---
def setup_logging(base_project_path):
    global logger
    log_dir = base_project_path / LOG_DIR_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file_path = log_dir / DOWNLOADER_LOG_FILE_NAME

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)-8s] %(message)s (%(filename)s:%(lineno)d)',
        handlers=[
            logging.FileHandler(log_file_path, mode='a', encoding='utf-8'),
            logging.StreamHandler(sys.stdout) # Også output til konsol
        ]
    )
    logger = logging.getLogger("PDFDownloader")

def load_master_tracking_data(base_project_path):
    global tracking_data_global
    tracking_file_path = base_project_path / JSON_DIR_NAME / MASTER_TRACKING_FILE_NAME
    if tracking_file_path.exists():
        try:
            with open(tracking_file_path, 'r', encoding='utf-8') as f:
                tracking_data_global = json.load(f)
                tracking_data_global.setdefault("file_status", {})
                tracking_data_global.setdefault("kamp_id_to_file_key", {})
                logger.info(f"Master tracking data indlæst fra {tracking_file_path}")
        except json.JSONDecodeError:
            logger.warning(f"Kunne ikke læse master tracking-fil ({tracking_file_path}). Opretter ny struktur i hukommelsen.")
            tracking_data_global = {"file_status": {}, "kamp_id_to_file_key": {}}
    else:
        logger.info(f"Master tracking-fil ({tracking_file_path}) ikke fundet. Opretter ny struktur i hukommelsen.")
        tracking_data_global = {"file_status": {}, "kamp_id_to_file_key": {}}

def get_file_key(liga_folder_name, season_str, pdf_filename):
    return f"{liga_folder_name}/{season_str}/{pdf_filename}"

def is_match_fully_processed(match_id, liga_folder_name, season_str, current_pdf_filename):
    """
    Tjekker om et match_id allerede er fuldt behandlet (db_created)
    enten via denne specifikke PDF-fil eller en anden PDF-fil med samme match_id.
    """
    if not tracking_data_global or not match_id:
        return False

    # Tjek om dette specifikke kamp_id er mappet til en fil, der er 'db_created'
    processed_file_key = tracking_data_global.get("kamp_id_to_file_key", {}).get(str(match_id))
    if processed_file_key:
        processed_file_info = tracking_data_global.get("file_status", {}).get(processed_file_key, {})
        if processed_file_info.get("status") == "db_created":
            # Hvis den processerede fil er den *aktuelle* fil, er den ikke "allerede" fuldt behandlet *af en anden*.
            # Men hvis det er en *anden* fil, så er den allerede behandlet.
            if processed_file_key != get_file_key(liga_folder_name, season_str, current_pdf_filename):
                 logger.info(f"Match ID {match_id} er allerede fuldt behandlet via filen: {processed_file_key}.")
                 return True
            # Hvis det er den aktuelle fil, og den er db_created, så er den også "allerede" behandlet.
            else:
                 logger.info(f"Match ID {match_id} (denne fil: {current_pdf_filename}) er allerede markeret som db_created.")
                 return True


    # Fallback: Tjek status for den aktuelle fil direkte, hvis kamp_id ikke var mappet (eller mappet til denne fil)
    current_file_key = get_file_key(liga_folder_name, season_str, current_pdf_filename)
    current_file_info = tracking_data_global.get("file_status", {}).get(current_file_key, {})
    if current_file_info.get("status") in ["db_created", "pdf_validated", "txt_converted"]: # Hvis den er godt på vej, spring download over
        logger.info(f"Fil {current_pdf_filename} har status '{current_file_info.get('status')}' og springes over for download.")
        return True
        
    return False


def extract_match_id_from_href(href):
    match = re.search(r'/pdfs/game/\d+/\d+/(\d+)/([ab])', href) # Tillad a eller b
    if match:
        return match.group(1), match.group(2)
    return None, None

def download_single_pdf(pdf_url_suffix, output_path, base_toph_url):
    if not pdf_url_suffix.startswith('/'):
        pdf_url_suffix = '/' + pdf_url_suffix
    
    full_pdf_url = base_toph_url + pdf_url_suffix
    # Sørg for at ?download=0 er til stede for direkte download
    if "?download=0" not in full_pdf_url:
        if "?" in full_pdf_url:
            full_pdf_url += "&download=0"
        else:
            full_pdf_url += "?download=0"
            
    logger.debug(f"Forsøger at downloade fra: {full_pdf_url}")
    try:
        response = requests.get(full_pdf_url, headers=HEADERS, timeout=30, stream=True)
        response.raise_for_status() # Hæv HTTPError for dårlige statuskoder (4xx eller 5xx)

        # Tjek content type for at være mere sikker på det er en PDF
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' not in content_type and not response.content.startswith(b'%PDF-'):
            logger.warning(f"Uventet content type '{content_type}' for {full_pdf_url}. Forventede PDF. Størrelse: {len(response.content)} bytes.")
            # Gem indhold for debugging hvis det ikke er for stort
            if len(response.content) < 1024*10: # Mindre end 10KB
                debug_content_path = output_path.with_suffix(".debug_content.html")
                with open(debug_content_path, 'wb') as f_debug:
                    f_debug.write(response.content)
                logger.info(f"Ikke-PDF indhold gemt til {debug_content_path}")
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        file_size = output_path.stat().st_size
        logger.debug(f"Downloadet til validering: {output_path.name} ({file_size / 1024:.2f} KB)")
        
        # FORBEDRET VALIDERING: Hurtig kvalitets-tjek direkte efter download
        is_valid, validation_reason = quick_pdf_validation(output_path)
        
        if not is_valid:
            # Slet ugyldig fil med det samme for at spare plads
            delete_invalid_pdf(output_path, validation_reason)
            logger.warning(f"❌ Ugyldig PDF slettet: {output_path.name} - {validation_reason}")
            return False
        else:
            # Gyldig PDF - log success
            logger.info(f"✅ Gyldig PDF downloadet: {output_path.name} - {validation_reason}")
            return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Fejl ved download af {full_pdf_url}: {e}")
        return False
    except Exception as e:
        logger.error(f"Uventet fejl under download af {full_pdf_url}: {e}", exc_info=True)
        return False

def scan_existing_pdf_files(pdf_output_dir):
    """
    Scanner PDF output mappen og returnerer et sæt med GYLDIGE eksisterende PDF filnavne.
    
    OPTIMERING: Tidligere kaldte koden .exists() for hver PDF fil individuelt i loopet.
    Nu scanner vi mappen én gang og bruger sæt-lookup (O(1)) i stedet for fil-system checks (O(n)).
    
    VALIDERING: Tjekker samtidig om eksisterende filer er gyldige og sletter ugyldige.
    Dette gør processen hurtigere og rydder op i gamle problematiske filer.
    
    Args:
        pdf_output_dir (Path): Sti til PDF output mappen
        
    Returns:
        set: Sæt med GYLDIGE eksisterende PDF filnavne (kun filnavn, ikke fuld sti)
    """
    valid_existing_files = set()
    deleted_invalid_count = 0
    
    # DEBUG: Logger hvilken mappe der scannes
    logger.info(f"Scanner og validerer eksisterende PDF filer: {pdf_output_dir}")
    
    # Tjek om mappen eksisterer
    if not pdf_output_dir.exists():
        logger.info(f"PDF output mappe eksisterer ikke endnu: {pdf_output_dir}")
        return valid_existing_files
    
    # Scan mappen for PDF filer og valider dem
    try:
        pdf_files = list(pdf_output_dir.glob("*.pdf"))
        total_files = len(pdf_files)
        
        if total_files == 0:
            logger.info("Ingen eksisterende PDF filer fundet")
            return valid_existing_files
        
        logger.info(f"Fandt {total_files} eksisterende PDF filer - validerer hver fil...")
        
        for pdf_file in pdf_files:
            if pdf_file.is_file():  # Sørg for det er en fil og ikke en mappe
                # Hurtig validering af eksisterende fil
                is_valid, reason = quick_pdf_validation(pdf_file)
                
                if is_valid:
                    valid_existing_files.add(pdf_file.name)
                    logger.debug(f"✅ Gyldig eksisterende: {pdf_file.name}")
                else:
                    # Slet ugyldig eksisterende fil
                    if delete_invalid_pdf(pdf_file, reason):
                        deleted_invalid_count += 1
                        logger.info(f"🧹 Ryddet op: slettet ugyldig eksisterende fil {pdf_file.name} - {reason}")
        
        # Sammendrag af scanning
        valid_count = len(valid_existing_files)
        logger.info(f"📊 Scanning resultat: {valid_count} gyldige filer bevaret, {deleted_invalid_count} ugyldige filer slettet")
        
        # Log nogle eksempler hvis der er mange gyldige filer
        if valid_count > 0:
            if valid_count <= 5:
                logger.info(f"Gyldige eksisterende filer: {', '.join(sorted(valid_existing_files))}")
            else:
                sample_files = list(sorted(valid_existing_files))[:3]
                logger.info(f"Eksempel på gyldige filer: {', '.join(sample_files)}... (+{valid_count-3} flere)")
        else:
            logger.info("Ingen gyldige eksisterende filer fundet - alle filer vil blive forsøgt downloadet")
                
    except Exception as e:
        logger.error(f"Fejl ved scanning/validering af eksisterende PDF filer i {pdf_output_dir}: {e}")
        # Returner tomt sæt hvis der er fejl - så vil den downloade alle filer
        return set()
    
    return valid_existing_files

# --- HOVEDFUNKTION ---
def main():
    # Brug __file__ til at bestemme base_project_path, hvis scriptet ligger i projektets rod
    # Ellers, hvis det kaldes af master, skal master måske sende stien.
    # For nu antager vi, at det kan køre standalone og BASE_PROJECT_PATH fra master bruges.
    # Hvis dette script kaldes direkte, skal BASE_PROJECT_PATH defineres her.
    # For nu, hent fra argument eller cwd.
    
    parser = argparse.ArgumentParser(description='Download håndbold PDF-filer.')
    parser.add_argument('--liga', required=True, help='Ligaens URL-navn (f.eks. kvindeligaen)')
    parser.add_argument('--sæson', required=True, help='Sæson (format YYYY-YYYY)')
    parser.add_argument('--base_project_dir', default=str(Path(__file__).resolve().parent),
                        help='Sti til rodmappen for projektet (hvor Logs, JSON osv. ligger)')
    args = parser.parse_args()

    base_project_path_obj = Path(args.base_project_dir)
    setup_logging(base_project_path_obj)
    load_master_tracking_data(base_project_path_obj) # Indlæs master tracking

    logger.info(f"Starter PDF Downloader for liga: {args.liga}, sæson: {args.sæson}")

    # Udled folder_name fra liga_url_name med korrekt mapping til eksisterende mappestruktur
    # DEBUG: Logger input liga for at hjælpe med troubleshooting
    logger.info(f"Input liga parameter: '{args.liga}'")
    
    # Korrekt mapping til de eksisterende mapperne i projektet
    # Baseret på de faktiske liga URL parametre fra master scriptet
    if args.liga.lower() == "kvindeligaen":
        liga_folder_name = "Kvindeliga"
    elif args.liga.lower() == "herreligaen":
        liga_folder_name = "Herreliga"
    elif args.liga.lower() == "1-division-damer":
        liga_folder_name = "1-Division-Kvinder"
    elif args.liga.lower() == "1-division-herrer":
        liga_folder_name = "1-Division-Herrer"
    else:
        # Fallback: forsøg den gamle logik for eventuelle andre ligaer
        liga_folder_name = args.liga.replace("-damer", "-Kvinder").replace("-herrer", "-Herrer").replace("-", " ").title().replace(" ", "-")
        logger.warning(f"Bruger fallback mapping for ukendt liga: '{args.liga}' -> '{liga_folder_name}'")
    
    # DEBUG: Logger den afledte mappestien
    logger.info(f"Afledt liga mappe: '{liga_folder_name}'")
    
    pdf_output_dir = base_project_path_obj / liga_folder_name / args.sæson
    
    # DEBUG: Logger den fulde sti der vil bruges
    logger.info(f"PDF output mappe sti: {pdf_output_dir}")
    
    pdf_output_dir.mkdir(parents=True, exist_ok=True)
    
    # Setup TXT output mappe (samme struktur som pdf_to_text_converter.py)
    txt_output_dir = setup_txt_output_dir(liga_folder_name, args.sæson, base_project_path_obj)

    year_start_sæson = args.sæson.split('-')[0]
    kampprogram_url = f"{BASE_URL}/kampprogram/{args.liga}?year={year_start_sæson}&team=&home_game=0&home_game=1&away_game=0&away_game=1"
    
    # DEBUG: Logger mapping mellem liga parameter og mappe for at sikre sammenhæng
    logger.info(f"Liga parameter '{args.liga}' -> Mappe '{liga_folder_name}' -> URL: {kampprogram_url}")
    logger.info(f"Henter kampprogram fra: {kampprogram_url}")
    
    try:
        response = requests.get(kampprogram_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Kunne ikke hente kampprogram-siden {kampprogram_url}: {e}")
        sys.exit(1)

    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find links til "Alle hændelser" PDF'er
    pdf_links_data = [] # (url_suffix, match_id, type_a_or_b)
    
    # Søg i dropdowns
    for link_tag in soup.find_all('a', class_='dropdown-item'):
        if "Alle hændelser" in link_tag.get_text(strip=True):
            href = link_tag.get('href')
            if href:
                match_id, match_type = extract_match_id_from_href(href)
                if match_id:
                    pdf_links_data.append((href, match_id, match_type))

    # Hvis ingen fundet i dropdowns, prøv en bredere søgning (kan give falske positiver)
    if not pdf_links_data:
        logger.info("Ingen PDF links fundet i dropdowns, forsøger bredere søgning...")
        for link_tag in soup.find_all('a', href=True):
             if "Alle hændelser" in link_tag.get_text(strip=True):
                href = link_tag.get('href')
                match_id, match_type = extract_match_id_from_href(href)
                if match_id:
                    pdf_links_data.append((href, match_id, match_type))

    if not pdf_links_data:
        logger.warning(f"Ingen 'Alle hændelser' PDF links fundet for {args.liga} {args.sæson}.")
        sys.exit(0)

    logger.info(f"Fandt {len(pdf_links_data)} potentielle PDF links.")
    
    # OPTIMERING: Scan eksisterende PDF filer og valider dem (slet ugyldige)
    existing_valid_files = scan_existing_pdf_files(pdf_output_dir)
    logger.info(f"📁 Klar til download: {len(existing_valid_files)} gyldige eksisterende filer vil blive sprunget over")
    
    downloaded_count = 0
    validated_count = 0  # Nye gyldige downloads
    invalid_deleted_count = 0  # Ugyldige downloads slettet
    skipped_count = 0
    failed_count = 0
    
    # Track downloadede PDF filer for TXT konvertering
    downloaded_pdf_files = []  # Liste med stier til nyligt downloadede gyldige PDF'er

    for pdf_url_suffix, match_id, match_type in tqdm(pdf_links_data, desc="Downloader PDF'er"):
        pdf_filename = f"match_{match_id}_{match_type}.pdf"
        output_file_path = pdf_output_dir / pdf_filename

        # Tjek mod master tracking om denne kamp (match_id) eller fil allerede er fuldt behandlet
        if is_match_fully_processed(match_id, liga_folder_name, args.sæson, pdf_filename):
            skipped_count += 1
            continue # Næste PDF link

        # OPTIMERING: Tjek mod forud-valideret sæt af gyldige eksisterende filer
        # Dette er meget hurtigere og sikrer kun gyldige filer springes over
        if pdf_filename in existing_valid_files:
            logger.info(f"⏭️ SPRINGER OVER eksisterende: {pdf_filename} (findes i valid set)")
            skipped_count += 1 # Tælles som sprunget over for download-trinnet
            continue
        else:
            logger.debug(f"🆕 Ny fil, forsøger download: {pdf_filename}")

        # Forsøg download med indbygget validering
        download_result = download_single_pdf(pdf_url_suffix, output_file_path, BASE_URL)
        
        if download_result:
            validated_count += 1  # Succesfuld download + validering
            downloaded_count += 1  # Total downloads (for bagudkompatibilitet)
            
            # Track downloadede filer for TXT konvertering
            downloaded_pdf_files.append(output_file_path)
            logger.debug(f"📁 Tilføjet til TXT konvertering liste: {output_file_path.name}")
        else:
            # Download fejlede ELLER fil var ugyldig og blev slettet
            if output_file_path.exists():
                failed_count += 1  # Download OK men anden fejl
            else:
                invalid_deleted_count += 1  # Ugyldig fil blev slettet
        
        time.sleep(0.2) # OPTIMERET: Reduceret fra 0.5s til 0.2s for hurtigere download

    # === PDF→TXT KONVERTERING (sker EFTER alle downloads er færdige) ===
    logger.info(f"\n🔄 Starter PDF→TXT konvertering fase...")
    txt_stats = convert_downloaded_pdfs_to_txt(downloaded_pdf_files, txt_output_dir)

    logger.info(f"🏁 PDF Download + TXT Konvertering proces afsluttet for {args.liga} {args.sæson}")
    logger.info(f"📊 SAMLET RESULTAT:")
    logger.info(f"   📥 PDF DOWNLOAD:")
    logger.info(f"      ✅ Gyldige filer downloadet: {validated_count}")
    logger.info(f"      ⏭️ Sprunget over (gyldige eksisterende): {skipped_count}")
    logger.info(f"      ❌ Ugyldige filer slettet: {invalid_deleted_count}")
    logger.info(f"      🚫 Download fejl: {failed_count}")
    logger.info(f"      📈 Total forsøgt downloads: {downloaded_count}")
    
    logger.info(f"   📝 TXT KONVERTERING:")
    logger.info(f"      ✅ Nye TXT filer: {txt_stats['converted']}")
    logger.info(f"      ⏭️ TXT filer eksisterede: {txt_stats['already_exists']}")
    logger.info(f"      ❌ Konvertering fejl: {txt_stats['failed']}")
    
    # Beregn success rates
    total_pdf_attempts = validated_count + invalid_deleted_count + failed_count
    if total_pdf_attempts > 0:
        pdf_success_rate = (validated_count / total_pdf_attempts) * 100
        logger.info(f"   📊 PDF Success rate: {pdf_success_rate:.1f}% ({validated_count}/{total_pdf_attempts})")
    
    total_txt_attempts = txt_stats['converted'] + txt_stats['failed'] 
    if total_txt_attempts > 0:
        txt_success_rate = (txt_stats['converted'] / total_txt_attempts) * 100
        logger.info(f"   📊 TXT Success rate: {txt_success_rate:.1f}% ({txt_stats['converted']}/{total_txt_attempts})")

    # Exit code baseret på om der var kritiske fejl
    has_critical_pdf_errors = failed_count > validated_count
    has_critical_txt_errors = txt_stats['failed'] > txt_stats['converted'] if total_txt_attempts > 0 else False
    no_activity = validated_count == 0 and skipped_count == 0
    
    if has_critical_pdf_errors:
        logger.warning(f"⚠️  Mange PDF download fejl ({failed_count}) vs succeser ({validated_count})")
        sys.exit(1)
    elif has_critical_txt_errors:
        logger.warning(f"⚠️  Mange TXT konvertering fejl ({txt_stats['failed']}) vs succeser ({txt_stats['converted']})")
        sys.exit(1)
    elif no_activity:
        logger.warning("⚠️  Ingen filer blev behandlet - potentielt problem")
        sys.exit(1)
    else:
        logger.info("🎉 PDF Download + TXT Konvertering proces fuldført succesfuldt!")

if __name__ == "__main__":
    main()