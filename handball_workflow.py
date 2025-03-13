#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Håndboldhændelser - Komplet Workflow Script

Dette script kører hele workflowet fra start til slut:
1. Download PDF-filer fra tophaandbold.dk
2. Konverter PDF-filer til tekstfiler
3. Behandl tekstfiler og opret SQLite-databaser

Scriptet sikrer at filer ikke behandles dobbelt ved at tjekke:
- Om PDF-filerne allerede er downloadet
- Om PDF-filerne allerede er konverteret til TXT
- Om TXT-filerne allerede er behandlet til databaser

Brug:
    python handball_workflow.py --liga=kvindeligaen --sæson=2024-2025
    python handball_workflow.py --liga=herreligaen --sæson=2023-2024
"""

import os
import sys
import time
import subprocess
import logging
import argparse
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Konfigurér logging
LOG_FILE = "handball_workflow.log"

# Opret logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("workflow")

def parse_arguments():
    """
    Parserer kommandolinje-argumenter
    
    Returns:
        argparse.Namespace: De parserede argumenter
    """
    parser = argparse.ArgumentParser(description='Kør håndboldhændelser workflow')
    
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
        logger.error(f"Ugyldig liga: {args.liga}. Gyldige værdier er: {', '.join(valid_leagues)}")
        sys.exit(1)
    
    # Valider sæson-format (YYYY-YYYY)
    if not re.match(r'^\d{4}-\d{4}$', args.sæson):
        logger.error(f"Ugyldig sæson: {args.sæson}. Formatet skal være YYYY-YYYY, f.eks. 2024-2025")
        sys.exit(1)
    
    return args

def run_script(script_name, description, args):
    """
    Kører et Python-script med logging af resultatet og sender liga/sæson som argumenter
    
    Args:
        script_name (str): Navnet på scriptet der skal køres
        description (str): Beskrivelse af hvad scriptet gør
        args (argparse.Namespace): Kommandolinje-argumenter
        
    Returns:
        bool: True hvis scriptet kørte succesfuldt, ellers False
    """
    logger.info(f"===== Starter {description} ({args.liga}, {args.sæson}) =====")
    
    try:
        # Kør scriptet med argumenterne og vent på at det er færdigt
        start_time = time.time()
        result = subprocess.run(
            [sys.executable, script_name, f"--liga={args.liga}", f"--sæson={args.sæson}"], 
            capture_output=True, 
            text=True, 
            check=True
        )
        end_time = time.time()
        
        # Log resultatet
        duration = end_time - start_time
        logger.info(f"Script {script_name} afsluttet med success på {duration:.2f} sekunder")
        logger.info(f"Output fra {script_name}:")
        for line in result.stdout.splitlines():
            logger.info(f"  > {line}")
            
        if result.stderr:
            logger.warning(f"Stderr output fra {script_name}:")
            for line in result.stderr.splitlines():
                logger.warning(f"  > {line}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Fejl ved kørsel af {script_name}: {str(e)}")
        logger.error(f"Returnkode: {e.returncode}")
        logger.error(f"Output:")
        for line in e.stdout.splitlines():
            logger.error(f"  > {line}")
        logger.error(f"Fejl output:")
        for line in e.stderr.splitlines():
            logger.error(f"  > {line}")
        return False
        
    except Exception as e:
        logger.error(f"Uventet fejl ved kørsel af {script_name}: {str(e)}")
        return False

def download_pdf(url, output_file):
    """
    Download PDF fra URL og gem den med det givne filnavn
    
    Args:
        url (str): URL til PDF-filen
        output_file (str): Filnavn PDF'en skal gemmes som
        
    Returns:
        bool: True hvis download var succesfuld, ellers False
    """
    # Tjek om filen allerede findes og har indhold
    if os.path.exists(output_file) and os.path.getsize(output_file) > 1024:
        logger.info(f"Filen {output_file} findes allerede. Springer over.")
        return True
    
    logger.info(f"Downloader: {url} -> {output_file}")
    
    try:
        # Tilføj download=0 parameter hvis den ikke allerede er der
        if "download=" not in url:
            if "?" in url:
                url += "&download=0"
            else:
                url += "?download=0"
        
        # Download filen
        response = requests.get(url, timeout=15)
        
        # Tjek om vi fik et gyldigt svar
        if response.status_code != 200:
            logger.warning(f"Fejl ved download: Status kode {response.status_code}")
            return False
        
        # Tjek at indholdet ligner en PDF
        is_pdf = response.content.startswith(b'%PDF-') or 'application/pdf' in response.headers.get('Content-Type', '')
        if not is_pdf:
            logger.warning(f"Advarsel: Indholdet ligner ikke en PDF-fil. Content-Type: {response.headers.get('Content-Type')}")
        
        # Gem filen under alle omstændigheder
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        # Verificer filstørrelsen
        file_size = os.path.getsize(output_file)
        if file_size < 1024:
            logger.warning(f"Advarsel: Filen {output_file} er meget lille ({file_size} bytes). Det kan være at den ikke er en gyldig PDF.")
            # Vi beholder filen men markerer den som fejlet
            with open(output_file + ".failed", "w") as f:
                f.write(f"Download fejlet: Filstørrelse for lille ({file_size} bytes)")
            return False
        
        logger.info(f"PDF-fil gemt som: {output_file} ({file_size} bytes)")
        return True
    except Exception as e:
        logger.error(f"Fejl ved download af {url}: {str(e)}")
        # Skriv fejlbesked til en fil for at hjælpe med fejlsøgning
        try:
            with open(output_file + ".error", "w") as f:
                f.write(f"Download fejlet: {str(e)}")
        except:
            pass
        return False

def download_herreligaen_pdf_files(args, output_dir):
    """
    Download PDF-filer for herreligaen med den forbedrede metode
    
    Args:
        args (argparse.Namespace): Kommandolinje-argumenter
        output_dir (str): Mappen hvor PDF-filerne skal gemmes
        
    Returns:
        bool: True hvis download var succesfuld, ellers False
    """
    logger.info(f"===== Starter PDF download (herreligaen, {args.sæson}) =====")
    start_time = time.time()
    
    sæson = args.sæson
    year = sæson.split('-')[0]
    
    # Base URL
    base_url = "https://tophaandbold.dk"
    kampprogram_url = f"{base_url}/kampprogram/herreligaen?year={year}&team=&home_game=0&home_game=1&away_game=0&away_game=1"
    
    logger.info(f"Starter download af PDF-filer fra https://tophaandbold.dk/kampprogram/herreligaen?year={year}&team=&home_game=0&home_game=1&away_game=0&away_game=1")
    logger.info(f"Filer vil blive gemt i: {os.path.abspath(output_dir)}")
    logger.info(f"Ignorerer PDF-filer mindre end 1024 bytes")
    
    try:
        # Hent kampprogram-siden
        logger.info(f"Henter kampprogram-siden: {kampprogram_url}")
        response = requests.get(kampprogram_url)
        logger.info(f"Status kode: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Fejl ved hentning af kampprogram-siden: Status kode {response.status_code}")
            return False
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Gem en kopi af HTML for debugging
        debug_file = 'debug_page.html'
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
        logger.info(f"HTML-side gemt som {debug_file} for debugging")
        
        # Find alle direkte links til "Alle hændelser"
        alle_links = []
        
        # Find alle href-links i HTML
        alle_href_links = []
        for link in soup.find_all('a'):
            href = link.get('href')
            if href and '/pdfs/game/' in href:
                alle_href_links.append(href)
        
        logger.info(f"Debug: Fandt {len(alle_href_links)} direkte 'Alle hændelser' links i HTML")
        for i, href in enumerate(alle_href_links[:5]):
            logger.info(f"  Link {i+1}: {href}")
        
        # Søg i dropdown-items (den vigtige del der finder alle links)
        dropdown_links = soup.find_all('a', class_='dropdown-item')
        logger.info(f"Debug: Fandt {len(dropdown_links)} dropdown-menuer")
        
        # Søg efter download sektioner (fra den oprindelige kode)
        download_sections = soup.find_all('div', class_='download-section')
        if not download_sections:
            download_sections = soup.find_all('div', class_='text-right')
        logger.info(f"Debug: Fandt {len(download_sections)} download sektioner")
        
        # Søg i dropdown-items specifikt (baseret på den faktiske HTML)
        for link in soup.find_all('a', class_='dropdown-item'):
            text = link.get_text(strip=True)
            href = link.get('href')
            
            if href and text and ("Alle hændelser" in text or "alle hændelser" in text.lower()):
                # Pattern for links som "/intranet/pdfs/game/2024/9010199/748777/a?download=0"
                match = re.search(r'/pdfs/game/\d+/\d+/(\d+)/([a-z])', href)
                if match:
                    match_id = match.group(1)
                    match_type = match.group(2)
                    
                    # Bygge komplet URL
                    if not href.startswith('http'):
                        if href.startswith('/'):
                            href = base_url + href
                        else:
                            href = base_url + '/' + href
                    
                    alle_links.append((href, match_id, match_type))
        
        if not alle_links:
            logger.warning("Ingen 'Alle hændelser' links fundet via dropdown-items, prøver generel søgning...")
            for link in soup.find_all('a'):
                text = link.get_text(strip=True)
                href = link.get('href')
                
                if href and text and ("Alle hændelser" in text or "alle hændelser" in text.lower()):
                    # Pattern for links som "/intranet/pdfs/game/2024/9010199/748777/a?download=0"
                    match = re.search(r'/pdfs/game/\d+/\d+/(\d+)/([a-z])', href)
                    if match:
                        match_id = match.group(1)
                        match_type = match.group(2)
                        
                        # Bygge komplet URL
                        if not href.startswith('http'):
                            if href.startswith('/'):
                                href = base_url + href
                            else:
                                href = base_url + '/' + href
                        
                        alle_links.append((href, match_id, match_type))
        
        if alle_links:
            logger.info(f"Fandt {len(alle_links)} 'Alle hændelser' links")
            
            downloaded = 0
            skipped = 0
            failed = 0
            for url, match_id, match_type in alle_links:
                output_file = os.path.join(output_dir, f"match_{match_id}_{match_type}.pdf")
                
                # Tjek om filen allerede er downloadet
                if os.path.exists(output_file) and os.path.getsize(output_file) > 1024:
                    logger.info(f"Filen {os.path.basename(output_file)} findes allerede ({os.path.getsize(output_file)} bytes). Springer over.")
                    skipped += 1
                    continue
                
                if download_pdf(url, output_file):
                    downloaded += 1
                else:
                    failed += 1
                
                # Lille pause mellem downloads for at undgå at blive begrænset af serveren
                time.sleep(0.5)
            
            end_time = time.time()
            duration = end_time - start_time
            
            logger.info(f"Download afsluttet. {downloaded} filer blev downloadet, {skipped} sprunget over, {failed} fejlede.")
            logger.info(f"Total tid: {duration:.2f} sekunder")
            return True
        else:
            logger.warning("Ingen 'Alle hændelser' links fundet på kampprogram-siden.")
            return False
    
    except Exception as e:
        logger.error(f"Fejl ved download af herreligaen PDF-filer: {str(e)}")
        return False

def main():
    """
    Kører hele workflowet i rækkefølge
    """
    # Parse argumenter
    args = parse_arguments()
    
    # Konverter liga-navn til mappenavn (fjern 'en' fra slutningen)
    liga_mappe = args.liga
    if liga_mappe.endswith('en'):
        liga_mappe = liga_mappe[:-2]
    liga_mappe = liga_mappe.capitalize()
    
    # Definer forventede mappestrukturer
    pdf_dir = os.path.join(liga_mappe, args.sæson)
    txt_dir = os.path.join(f"{liga_mappe}-txt-tabel", args.sæson)
    db_dir = os.path.join(f"{liga_mappe}-database", args.sæson)
    
    logger.info("======= STARTER HÅNDBOLDHÆNDELSER WORKFLOW =======")
    logger.info(f"Dato og tid: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Liga: {args.liga}, Sæson: {args.sæson}")
    logger.info(f"PDF-mappe: {os.path.abspath(pdf_dir)}")
    logger.info(f"TXT-mappe: {os.path.abspath(txt_dir)}")
    logger.info(f"Database-mappe: {os.path.abspath(db_dir)}")
    
    # Sørg for at alle mapper eksisterer
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(txt_dir, exist_ok=True)
    os.makedirs(db_dir, exist_ok=True)
    
    workflow_start = time.time()
    
    # Trin 1: Download PDF-filer
    if args.liga == 'herreligaen':
        # Brug den nye, forbedrede metode til at downloade herreligaen PDF-filer
        success = download_herreligaen_pdf_files(args, pdf_dir)
        if not success:
            logger.warning("Herreligaen PDF download fejlede, men fortsætter til næste trin")
    else:
        # Brug det oprindelige script til andre ligaer
        success = run_script("handball_pdf_downloader.py", "PDF download", args)
        if not success:
            logger.warning("PDF download fejlede, men fortsætter til næste trin")
    
    # Trin 2: Konverter PDF-filer til TXT
    success = run_script("pdf_to_text_converter.py", "PDF til TXT konvertering", args)
    if not success:
        logger.warning("PDF til TXT konvertering fejlede, men fortsætter til næste trin")
    
    # Trin 3: Behandl TXT-filer til databaser
    success = run_script("handball_data_processor.py", "TXT til database behandling", args)
    if not success:
        logger.warning("TXT til database behandling fejlede")
    
    workflow_end = time.time()
    duration = workflow_end - workflow_start
    
    logger.info("======= WORKFLOW AFSLUTTET =======")
    logger.info(f"Liga: {args.liga}, Sæson: {args.sæson}")
    logger.info(f"Total køretid: {duration:.2f} sekunder ({duration/60:.2f} minutter)")
    logger.info(f"Se separate logfiler for detaljerede resultater")

if __name__ == "__main__":
    main() 