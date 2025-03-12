#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sikker version af scriptet til at downloade alle PDF-filer under "Alle hændelser" 
fra tophaandbold.dk/kampprogram/kvindeligaen
Denne version har bedre fejlhåndtering og kan genoptage afbrudte downloads.
Filerne gemmes i en mappestruktur: Kvindeliga/2024-2025/
"""

import os
import requests
from bs4 import BeautifulSoup
import time
import re
import json
import sys
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Definer base URL
BASE_URL = "https://tophaandbold.dk"
TARGET_URL = f"{BASE_URL}/kampprogram/kvindeligaen"

# Definer mappe-struktur
OUTPUT_DIR = os.path.join("Kvindeliga", "2024-2025")
LOG_FILE = os.path.join(OUTPUT_DIR, "download_log.json")

# Mindste acceptable PDF-størrelse i bytes (f.eks. 1KB)
MIN_PDF_SIZE = 1024

# Sørg for at output-mappen eksisterer
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Logger for at holde styr på status
class DownloadLogger:
    """
    Klasse til at logge download status og hjælpe med genoptagelse
    """
    def __init__(self, log_file):
        """
        Initialiser logger
        
        Args:
            log_file (str): Sti til log-filen
        """
        self.log_file = log_file
        self.downloads = self._load_log()
    
    def _load_log(self):
        """
        Indlæs log-filen hvis den eksisterer
        
        Returns:
            dict: Ordbog med download status
        """
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print(f"Advarsel: Kunne ikke læse log-filen. Starter med tom log.")
                return {}
        return {}
    
    def save_log(self):
        """
        Gem log-filen
        """
        with open(self.log_file, 'w', encoding='utf-8') as f:
            json.dump(self.downloads, f, indent=2, ensure_ascii=False)
    
    def is_downloaded(self, url):
        """
        Tjek om en URL allerede er downloadet
        
        Args:
            url (str): URL at tjekke
        
        Returns:
            bool: True hvis URL er downloadet
        """
        if url in self.downloads and self.downloads[url]['success']:
            # Tjek at filen også faktisk eksisterer og har indhold
            if 'filename' in self.downloads[url]:
                filepath = os.path.join(OUTPUT_DIR, self.downloads[url]['filename'])
                if os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    if file_size > MIN_PDF_SIZE:
                        return True
                    else:
                        print(f"Filen {filepath} findes, men er for lille ({file_size} bytes). Downloader igen.")
                else:
                    print(f"Filen {filepath} findes ikke længere. Downloader igen.")
            return False
        return False
    
    def mark_success(self, url, filename, file_size):
        """
        Marker en URL som vellykket downloadet
        
        Args:
            url (str): Downloadet URL
            filename (str): Filnavn det blev gemt som
            file_size (int): Størrelsen på den downloadede fil
        """
        self.downloads[url] = {
            'success': True,
            'filename': filename,
            'file_size': file_size,
            'timestamp': time.time()
        }
        self.save_log()
    
    def mark_failure(self, url, error):
        """
        Marker en URL som mislykkedes
        
        Args:
            url (str): Mislykkede URL
            error (str): Fejlbeskrivelse
        """
        # Hvis den allerede er markeret som succes, så bevar det
        if url in self.downloads and self.downloads[url].get('success', False):
            # Men tjek at filen faktisk eksisterer og har indhold
            if 'filename' in self.downloads[url]:
                filepath = os.path.join(OUTPUT_DIR, self.downloads[url]['filename'])
                if os.path.exists(filepath) and os.path.getsize(filepath) > MIN_PDF_SIZE:
                    return
            
        self.downloads[url] = {
            'success': False,
            'error': str(error),
            'timestamp': time.time()
        }
        self.save_log()
    
    def get_failed_urls(self):
        """
        Få en liste over mislykkede URLs
        
        Returns:
            list: Liste over URLs der mislykkedes
        """
        return [url for url, data in self.downloads.items() 
                if not data.get('success', False)]

def ensure_download_param(url):
    """
    Sikrer at URL'en har download=0 parameteren
    
    Args:
        url (str): Original URL
    
    Returns:
        str: URL med download parameter
    """
    # Parse URL
    parsed_url = urlparse(url)
    
    # Parse query parametre
    query_params = parse_qs(parsed_url.query)
    
    # Tilføj eller opdater download parameter
    query_params['download'] = ['0']
    
    # Byg URL igen med opdaterede parametre
    new_query = urlencode(query_params, doseq=True)
    
    # Byg den komplette URL
    new_url = urlunparse((
        parsed_url.scheme,
        parsed_url.netloc,
        parsed_url.path,
        parsed_url.params,
        new_query,
        parsed_url.fragment
    ))
    
    return new_url

def is_valid_pdf_content(content):
    """
    Tjekker om indholdet ligner en gyldig PDF
    
    Args:
        content (bytes): Binært indhold at tjekke
    
    Returns:
        bool: True hvis indholdet ligner en PDF
    """
    # En gyldig PDF-fil starter med "%PDF-"
    return len(content) > MIN_PDF_SIZE and content.startswith(b'%PDF-')

def download_pdf(url, filename, logger):
    """
    Download PDF fra URL og gem den med det givne filnavn
    
    Args:
        url (str): URL til PDF-filen
        filename (str): Filnavn til at gemme PDF'en
        logger (DownloadLogger): Logger til at spore download status
    
    Returns:
        bool: True hvis download er vellykket
    """
    # Tjek om denne URL allerede er downloadet
    if logger.is_downloaded(url):
        print(f"Springer over {url} - Allerede downloadet")
        return True
        
    print(f"Downloader: {filename}")
    
    # Tilføj base URL hvis nødvendigt
    if url.startswith("/"):
        url = f"{BASE_URL}{url}"
    
    # Sikr at download parameteren er sat
    url = ensure_download_param(url)
    
    try:
        # Send anmodning med download parameter
        response = requests.get(url, stream=True, timeout=30)
        
        if response.status_code == 200:
            # Kontroller om indholdet faktisk er en PDF
            content_type = response.headers.get('Content-Type', '').lower()
            if 'application/pdf' not in content_type and not filename.endswith('.pdf'):
                print(f"Advarsel: Indholdet er ikke en PDF: {content_type}")
                # Tilføj .pdf endelse hvis filnavnet ikke har det
                if not filename.endswith('.pdf'):
                    filename = f"{filename}.pdf"
            
            # Tjek Content-Length header
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) < MIN_PDF_SIZE:
                error = f"Advarsel: PDF-filen er for lille: {content_length} bytes"
                print(error)
                logger.mark_failure(url, error)
                return False
            
            # Indlæs hele indholdet i hukommelsen først for at validere
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content += chunk
            
            # Valider PDF-indholdet
            if not is_valid_pdf_content(content):
                error = f"Fejl: Indholdet ligner ikke en gyldig PDF-fil!"
                print(error)
                logger.mark_failure(url, error)
                return False
            
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, 'wb') as f:
                f.write(content)
            
            # Dobbelttjek filstørrelsen efter skrivning
            file_size = os.path.getsize(filepath)
            if file_size < MIN_PDF_SIZE:
                error = f"Fejl: Den gemte PDF-fil er for lille: {file_size} bytes"
                print(error)
                logger.mark_failure(url, error)
                return False
            
            print(f"Gemt: {filepath} ({file_size} bytes)")
            logger.mark_success(url, filename, file_size)
            return True
        else:
            error = f"Fejl ved download af {url}. Status kode: {response.status_code}"
            print(error)
            logger.mark_failure(url, error)
            return False
    except requests.exceptions.RequestException as e:
        error = f"Fejl ved anmodning til {url}: {e}"
        print(error)
        logger.mark_failure(url, error)
        return False
    except Exception as e:
        error = f"Uventet fejl ved download af {url}: {e}"
        print(error)
        logger.mark_failure(url, error)
        return False

def extract_match_info(match_element):
    """
    Udtræk information om kampen fra HTML-elementet
    
    Args:
        match_element: HTML-element der indeholder kampinformation
    
    Returns:
        dict: Ordbog med kampinformation
    """
    # Initialiser med tomme værdier
    match_info = {
        "date": "",
        "time": "",
        "home_team": "",
        "away_team": "",
        "score": ""
    }
    
    try:
        # Find dato og tid (dette er en antagelse baseret på screenshot)
        date_time_elem = match_element.find_previous("div", class_="match-date")
        if date_time_elem:
            date_time_text = date_time_elem.text.strip()
            # Antager format som "03-11-24 15:00"
            if date_time_text:
                parts = date_time_text.split()
                if len(parts) >= 2:
                    match_info["date"] = parts[0]
                    match_info["time"] = parts[1]
        
        # Find hold navne 
        teams = match_element.find_all("div", class_="team-name")
        if len(teams) >= 2:
            match_info["home_team"] = teams[0].text.strip()
            match_info["away_team"] = teams[1].text.strip()
        
        # Find score
        score_elem = match_element.find("div", class_="match-score")
        if score_elem:
            match_info["score"] = score_elem.text.strip()
            
    except Exception as e:
        print(f"Fejl ved udtræk af kampinformation: {e}")
    
    return match_info

def get_filename_from_match(match_info, pdf_url):
    """
    Generer et filnavn baseret på kampinformation og PDF-URL
    
    Args:
        match_info (dict): Ordbog med kampinformation
        pdf_url (str): URL til PDF-filen
    
    Returns:
        str: Genereret filnavn
    """
    # Prøv at udtrække match-id fra URL'en
    match_id = ""
    match = re.search(r'game/(\d+)/(\d+)/(\d+)', pdf_url)
    if match:
        season_id = match.group(1)
        tournament_id = match.group(2)
        game_id = match.group(3)
        match_id = f"{season_id}-{tournament_id}-{game_id}"
    
    # Opret filnavn med dato, hold og match-id
    date = match_info.get("date", "").replace("-", "")
    home = match_info.get("home_team", "").replace(" ", "_")
    away = match_info.get("away_team", "").replace(" ", "_")
    
    if date and home and away:
        return f"{date}_{home}_vs_{away}_{match_id}_alle_haendelser.pdf"
    else:
        # Fallback til et unikt filnavn baseret på tidsstempel hvis vi mangler info
        return f"handball_match_{int(time.time())}.pdf"

def retry_failed_downloads(logger):
    """
    Genoptag tidligere mislykkede downloads
    
    Args:
        logger (DownloadLogger): Logger med information om mislykkede downloads
    """
    failed_urls = logger.get_failed_urls()
    if not failed_urls:
        print("Ingen tidligere mislykkede downloads at genoptage.")
        return
    
    print(f"Genoptager {len(failed_urls)} tidligere mislykkede downloads...")
    
    for url in failed_urls:
        # Generer et simpelt filnavn baseret på URL
        parts = url.split("/")
        filename = f"retry_{parts[-2]}_{parts[-1].split('?')[0]}.pdf"
        
        # Prøv at downloade igen
        download_pdf(url, filename, logger)

def main():
    """
    Hovedfunktion til at scrape og downloade PDF-filer
    """
    print(f"Starter download af PDF-filer fra {TARGET_URL}")
    print(f"Filer vil blive gemt i: {os.path.abspath(OUTPUT_DIR)}")
    print(f"Ignorerer PDF-filer mindre end {MIN_PDF_SIZE} bytes")
    
    # Initialiser logger
    logger = DownloadLogger(LOG_FILE)
    
    # Spørg om vi skal genoptage tidligere downloads først
    retry_mode = len(sys.argv) > 1 and sys.argv[1].lower() == '--retry'
    
    if retry_mode:
        retry_failed_downloads(logger)
        print("Genoptagelse afsluttet!")
        return
    
    try:
        # Hent hovedsiden
        print("Henter hovedsiden...")
        response = requests.get(TARGET_URL, timeout=30)
        response.raise_for_status()
        
        # Parse HTML
        print("Parser HTML...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find alle dropdown menuer med "Alle hændelser" links
        download_sections = soup.find_all("div", class_="match-program_row_download_select")
        
        if not download_sections:
            print("Ingen download sektioner fundet. Prøver alternativ metode...")
            # Alternativ metode: Find direkte alle "Alle hændelser" links
            alle_haendelser_links = soup.find_all("a", string=lambda s: s and "Alle hændelser" in s)
            if alle_haendelser_links:
                print(f"Fandt {len(alle_haendelser_links)} 'Alle hændelser' links")
                for link in alle_haendelser_links:
                    pdf_url = link.get("href")
                    # Find match-sektion for at få kampinfo
                    match_section = link.find_parent("div", class_="match-program_row_download")
                    if not match_section:
                        match_section = link.find_parent("div", class_="match")
                    
                    if match_section:
                        match_info = extract_match_info(match_section)
                        filename = get_filename_from_match(match_info, pdf_url)
                        download_pdf(pdf_url, filename, logger)
                    else:
                        # Hvis vi ikke kan finde match info, brug en del af URL'en som filnavn
                        parts = pdf_url.split("/")
                        filename = f"match_{parts[-2]}_{parts[-1].split('?')[0]}.pdf"
                        download_pdf(pdf_url, filename, logger)
            else:
                print("Ingen 'Alle hændelser' links fundet på siden!")
        else:
            print(f"Fandt {len(download_sections)} download sektioner")
            for section in download_sections:
                # Find den overordnede match-sektion for at få kampinformation
                match_section = section.find_parent("div", class_="match")
                match_info = extract_match_info(match_section) if match_section else {}
                
                # Find alle links i dropdown menuen
                dropdown_menu = section.find("div", class_="dropdown-menu")
                if dropdown_menu:
                    alle_haendelser_link = dropdown_menu.find("a", string=lambda s: s and "Alle hændelser" in s)
                    if alle_haendelser_link:
                        pdf_url = alle_haendelser_link.get("href")
                        filename = get_filename_from_match(match_info, pdf_url)
                        download_pdf(pdf_url, filename, logger)
        
        # Se om vi har nogle mislykkede downloads at genoptage
        failed_count = len(logger.get_failed_urls())
        if failed_count > 0:
            print(f"\n{failed_count} downloads mislykkedes. Kør scriptet med --retry for at genoptage dem.")
        
        print("Download afsluttet!")
        
    except requests.exceptions.RequestException as e:
        print(f"Fejl ved anmodning til {TARGET_URL}: {e}")
    except Exception as e:
        print(f"Uventet fejl: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 