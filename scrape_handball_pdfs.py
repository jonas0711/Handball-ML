#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script til at downloade alle PDF-filer under "Alle hændelser" fra tophaandbold.dk/kampprogram/kvindeligaen
Filerne gemmes i en mappestruktur: Kvindeliga/2024-2025/
"""

import os
import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

# Definer base URL
BASE_URL = "https://tophaandbold.dk"
TARGET_URL = f"{BASE_URL}/kampprogram/kvindeligaen"

# Definer mappe-struktur
OUTPUT_DIR = os.path.join("Kvindeliga", "2024-2025")

# Mindste acceptable PDF-størrelse i bytes (f.eks. 1KB)
MIN_PDF_SIZE = 1024

# Sørg for at output-mappen eksisterer
os.makedirs(OUTPUT_DIR, exist_ok=True)

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

def is_pdf_already_downloaded(filepath):
    """
    Tjekker om en PDF allerede er downloadet og har indhold
    
    Args:
        filepath (str): Sti til PDF-filen
    
    Returns:
        bool: True hvis PDF'en allerede er downloadet og har indhold
    """
    if os.path.exists(filepath):
        # Tjek at filen har et minimum af indhold
        file_size = os.path.getsize(filepath)
        if file_size > MIN_PDF_SIZE:
            print(f"Filen {filepath} findes allerede og har indhold ({file_size} bytes). Springer over.")
            return True
        else:
            print(f"Filen {filepath} findes, men er for lille ({file_size} bytes). Downloader igen.")
            return False
    return False

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

def download_pdf(url, filename):
    """
    Download PDF fra URL og gem den med det givne filnavn
    
    Args:
        url (str): URL til PDF-filen
        filename (str): Filnavn til at gemme PDF'en
    """
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    # Tjek om filen allerede er downloadet og har indhold
    if is_pdf_already_downloaded(filepath):
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
                    filepath = os.path.join(OUTPUT_DIR, filename)
            
            # Tjek Content-Length header
            content_length = response.headers.get('Content-Length')
            if content_length and int(content_length) < MIN_PDF_SIZE:
                print(f"Advarsel: PDF-filen er for lille: {content_length} bytes")
            
            # Indlæs hele indholdet i hukommelsen først for at validere
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    content += chunk
            
            # Valider PDF-indholdet
            if not is_valid_pdf_content(content):
                print(f"Fejl: Indholdet ligner ikke en gyldig PDF-fil!")
                return False
            
            # Gem indholdet til fil
            with open(filepath, 'wb') as f:
                f.write(content)
            
            # Dobbelttjek filstørrelsen efter skrivning
            file_size = os.path.getsize(filepath)
            if file_size < MIN_PDF_SIZE:
                print(f"Fejl: Den gemte PDF-fil er for lille: {file_size} bytes")
                return False
                
            print(f"Gemt: {filepath} ({file_size} bytes)")
            return True
        else:
            print(f"Fejl ved download af {url}. Status kode: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Fejl ved anmodning til {url}: {e}")
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

def main():
    """
    Hovedfunktion til at scrape og downloade PDF-filer
    """
    print(f"Starter download af PDF-filer fra {TARGET_URL}")
    print(f"Filer vil blive gemt i: {os.path.abspath(OUTPUT_DIR)}")
    print(f"Ignorerer PDF-filer mindre end {MIN_PDF_SIZE} bytes")
    
    try:
        # Hent hovedsiden
        response = requests.get(TARGET_URL)
        response.raise_for_status()
        
        # Parse HTML
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
                        download_pdf(pdf_url, filename)
                    else:
                        # Hvis vi ikke kan finde match info, brug en del af URL'en som filnavn
                        parts = pdf_url.split("/")
                        filename = f"match_{parts[-2]}_{parts[-1].split('?')[0]}.pdf"
                        download_pdf(pdf_url, filename)
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
                        download_pdf(pdf_url, filename)
        
        print("Download afsluttet!")
        
    except requests.exceptions.RequestException as e:
        print(f"Fejl ved anmodning til {TARGET_URL}: {e}")
    except Exception as e:
        print(f"Uventet fejl: {e}")

if __name__ == "__main__":
    main() 