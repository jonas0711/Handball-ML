#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script til at downloade alle PDF-filer under "Alle hændelser" fra tophaandbold.dk
Filerne gemmes i en mappestruktur baseret på liga og sæson.

Brug:
    python handball_pdf_downloader.py --liga=kvindeligaen --sæson=2024-2025
    python handball_pdf_downloader.py --liga=herreligaen --sæson=2023-2024
"""

import os
import requests
from bs4 import BeautifulSoup
import time
import re
import argparse
import sys
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

def parse_arguments():
    """
    Parserer kommandolinje-argumenter
    
    Returns:
        argparse.Namespace: De parserede argumenter
    """
    parser = argparse.ArgumentParser(description='Download håndbold PDF-filer')
    
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

# Definer base URL og opsæt mappestruktur baseret på argumenter
def setup_configuration(args):
    """
    Opsætter konfiguration baseret på kommandolinje-argumenter
    
    Args:
        args (argparse.Namespace): Kommandolinje-argumenter
        
    Returns:
        tuple: (base_url, output_dir, target_url, sæson_år)
    """
    # Definer base URL
    BASE_URL = "https://tophaandbold.dk"
    
    # Udled sæson-år for URL (tager første år i sæson-stringen)
    sæson_år = args.sæson.split('-')[0]
    
    # Definer target URL med liga og sæson-år
    TARGET_URL = f"{BASE_URL}/kampprogram/{args.liga}?year={sæson_år}&team=&home_game=0&home_game=1&away_game=0&away_game=1"
    
    # Konverter liga-navn til mappenavn (fjern 'en' fra slutningen)
    liga_mappe = args.liga
    if liga_mappe.endswith('en'):
        liga_mappe = liga_mappe[:-2]
    liga_mappe = liga_mappe.capitalize()
    
    # Definer mappe-struktur
    LIGA_DIR = liga_mappe
    OUTPUT_DIR = os.path.join(LIGA_DIR, args.sæson)
    
    # Sørg for at output-mapperne eksisterer
    os.makedirs(LIGA_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    return BASE_URL, OUTPUT_DIR, TARGET_URL, sæson_år

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
    
    # Lav en ny parsed URL med den opdaterede query
    new_parsed = parsed_url._replace(query=new_query)
    
    # Sammensæt URL'en igen
    new_url = urlunparse(new_parsed)
    
    return new_url

# Mindste acceptable PDF-størrelse i bytes (f.eks. 1KB)
MIN_PDF_SIZE = 1024

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

def download_pdf(url, filename, base_url):
    """
    Download PDF fra URL og gem den med det givne filnavn
    
    Args:
        url (str): URL til PDF-filen
        filename (str): Filnavnet PDF'en skal gemmes som
        base_url (str): Base URL for at sikre at URL'en er absolut
        
    Returns:
        bool: True hvis download var succesfuld, ellers False
    """
    # Tjek om PDF'en allerede er downloadet
    if is_pdf_already_downloaded(filename):
        return True
    
    # Sikr at URL'en er absolut
    if not url.startswith('http'):
        if url.startswith('/'):
            url = base_url + url
        else:
            url = base_url + '/' + url
    
    # Sikr at download=0 parameteren er inkluderet
    url = ensure_download_param(url)
    
    # Download PDF'en
    print(f"Downloader: {os.path.basename(filename)} fra {url}")
    try:
        response = requests.get(url, timeout=10)
        
        # Tjek at responsetypen er PDF
        content_type = response.headers.get('Content-Type', '')
        if 'application/pdf' not in content_type and 'application/octet-stream' not in content_type:
            print(f"Advarsel: Indholdstypen er ikke PDF: {content_type}")
            
            # Hvis indholdstypen ikke er PDF, kan vi stadig forsøge at gemme filen
            if 'text/html' in content_type:
                print("Indholdet er HTML. Dette kan betyde at linket ikke peger direkte til en PDF.")
                print("Forsøger at finde PDF-link i HTML...")
                
                # Parse HTML og forsøg at finde PDF-link
                soup = BeautifulSoup(response.text, 'html.parser')
                pdf_links = soup.find_all('a', href=lambda href: href and '.pdf' in href)
                
                if pdf_links:
                    pdf_url = pdf_links[0].get('href')
                    if not pdf_url.startswith('http'):
                        if pdf_url.startswith('/'):
                            pdf_url = base_url + pdf_url
                        else:
                            pdf_url = base_url + '/' + pdf_url
                    
                    print(f"Fandt PDF-link: {pdf_url}. Forsøger at downloade...")
                    response = requests.get(pdf_url, timeout=10)
        
        # Tjek om indholdet ligner en PDF
        if not is_valid_pdf_content(response.content):
            print("Fejl: Indholdet ligner ikke en gyldig PDF-fil!")
            return False
        
        # Gem PDF-filen
        with open(filename, 'wb') as f:
            f.write(response.content)
        
        print(f"PDF-fil gemt som: {filename}")
        return True
    except Exception as e:
        print(f"Fejl ved download af {url}: {str(e)}")
        return False

def find_download_sections(soup):
    """
    Find download sektioner i HTML
    
    Args:
        soup (BeautifulSoup): Parsed HTML
    
    Returns:
        list: Liste af download sektioner
    """
    # Find alle div-elementer der indeholder "Hent spillerstatistikker" tekst
    download_sections = []
    
    # Metode 1: Find div med 'download-section' klasse
    sections = soup.find_all('div', class_='download-section')
    if sections:
        download_sections.extend(sections)
        return download_sections
    
    # Metode 2: Find div med 'text-right' klasse
    sections = soup.find_all('div', class_='text-right')
    if sections:
        # Filtrer for dem, der indeholder "Hent spillerstatistikker"
        for section in sections:
            if 'Hent spillerstatistikker' in section.get_text():
                download_sections.append(section)
        
        if download_sections:
            return download_sections
    
    # Metode 3: Find div med klassen 'match-program__row__download'
    sections = soup.find_all('div', class_='match-program__row__download')
    if sections:
        download_sections.extend(sections)
        return download_sections
            
    # Metode 4: Find div med klassen 'dropdown-menu'
    sections = soup.find_all('div', class_='dropdown-menu')
    if sections:
        # Filtrer for dem, der indeholder "Alle hændelser"
        for section in sections:
            if 'Alle hændelser' in section.get_text():
                download_sections.append(section)
        
        if download_sections:
            return download_sections
    
    # Hvis ingen sektioner findes, så logger vi det
    print("Ingen download sektioner fundet. Prøver alternativ metode...")
    return []

def extract_match_info(link_text):
    """
    Udtrækker kampinformation fra link-tekst
    
    Args:
        link_text (str): Tekst fra linket
    
    Returns:
        tuple: (match_id, match_type)
    """
    # Pattern for kampnumre som 748182_a, hvor 748182 er kamp_id og _a er typen
    match = re.search(r'(\d+)_([a-z])', link_text)
    if match:
        return match.group(1), match.group(2)
    
    # Nyt pattern for links som "/intranet/pdfs/game/2024/9010199/748777/a?download=0"
    match = re.search(r'/pdfs/game/\d+/\d+/(\d+)/([a-z])', link_text)
    if match:
        return match.group(1), match.group(2)
    
    return None, None

def find_all_hændelser_links(soup, base_url):
    """
    Find "Alle hændelser" links i HTML
    
    Args:
        soup (BeautifulSoup): Parsed HTML
        base_url (str): Base URL for at bygge komplette links
        
    Returns:
        list: Liste af tuples med (url, match_id, match_type)
    """
    result_links = []
    
    # Find alle links med teksten "Alle hændelser" uanset hvor de er i dokumentet
    all_links = soup.find_all('a')
    for link in all_links:
        text = link.get_text(strip=True)
        href = link.get('href')
        
        print(f"Undersøger link: {text} - {href}")
        
        if href and text and "alle hændelser" in text.lower():
            print(f"Fandt et 'Alle hændelser' link: {href}")
            
            # Prøv at udtrække match_id og type
            match_id, match_type = extract_match_info(href)
            
            # Hvis vi ikke kunne ekstrahere match_id og type på normal vis, 
            # prøv en speciel håndtering for links som i eksemplet
            if not match_id and 'game' in href and '?' in href:
                # For links som "/intranet/pdfs/game/2024/9010199/748777/a?download=0"
                parts = href.split('/')
                # Forsøg at finde match_id i delen før ?
                for part in reversed(parts):
                    if part.isdigit() and len(part) >= 6:
                        match_id = part
                        break
                
                # Find match_type (typisk 'a')
                for part in reversed(parts):
                    if len(part) == 1 or (len(part) > 1 and '?' in part and len(part.split('?')[0]) == 1):
                        if '?' in part:
                            match_type = part.split('?')[0]
                        else:
                            match_type = part
                        break
            
            if match_id and match_type:
                print(f"Udtrukket match_id: {match_id}, match_type: {match_type}")
                
                # Bygge komplet URL
                if not href.startswith('http'):
                    if href.startswith('/'):
                        href = base_url + href
                    else:
                        href = base_url + '/' + href
                
                result_links.append((href, match_id, match_type))
    
    return result_links

def main():
    """
    Hovedfunktion for at downloade PDF-filer
    """
    # Parse kommandolinje-argumenter
    args = parse_arguments()
    
    # Opsæt konfiguration baseret på argumenter
    BASE_URL, OUTPUT_DIR, TARGET_URL, sæson_år = setup_configuration(args)
    
    print(f"Starter download af PDF-filer fra {TARGET_URL}")
    print(f"Filer vil blive gemt i: {os.path.abspath(OUTPUT_DIR)}")
    print(f"Ignorerer PDF-filer mindre end {MIN_PDF_SIZE} bytes")
    
    # Hent kampprogram-siden
    try:
        print(f"Henter kampprogram-siden: {TARGET_URL}")
        response = requests.get(TARGET_URL)
        print(f"Status kode: {response.status_code}")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Gem en kopi af HTML for debugging
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("HTML-side gemt som debug_page.html for debugging")
        
    except Exception as e:
        print(f"Fejl ved hentning af siden: {str(e)}")
        return
    
    # Find alle links med "Alle hændelser" for diagnostik
    debug_links = []
    for link in soup.find_all('a'):
        if link.get_text(strip=True) == "Alle hændelser":
            debug_links.append(link.get('href'))
    
    print(f"Debug: Fandt {len(debug_links)} direkte 'Alle hændelser' links i HTML")
    for i, href in enumerate(debug_links[:5]):  # Vis kun de første 5 for overskuelighed
        print(f"  Link {i+1}: {href}")
    
    # Find dropdown-menuer
    dropdown_menus = soup.find_all('div', class_='dropdown-menu')
    print(f"Debug: Fandt {len(dropdown_menus)} dropdown-menuer")
    
    # Find download sektioner
    download_sections = find_download_sections(soup)
    print(f"Debug: Fandt {len(download_sections)} download sektioner")
    
    if download_sections:
        # Behandl hver download sektion
        for section in download_sections:
            # Find alle PDF-links i denne sektion
            pdf_links = section.find_all('a', href=lambda href: href and ('.pdf' in href or '/pdf/' in href))
            print(f"Debug: Fandt {len(pdf_links)} PDF-links i en download sektion")
            
            for link in pdf_links:
                href = link.get('href')
                text = link.get_text(strip=True)
                print(f"Debug: Behandler link: {href} - {text}")
                
                # Udtrække match_id og type
                match_id, match_type = extract_match_info(href)
                print(f"Debug: Udtrukket match_id: {match_id}, match_type: {match_type}")
                
                if match_id and match_type:
                    # Definér output-filnavn
                    output_file = os.path.join(OUTPUT_DIR, f"match_{match_id}_{match_type}.pdf")
                    
                    # Download PDF'en
                    download_pdf(href, output_file, BASE_URL)
    else:
        # Alternativ metode: Find links direkte fra kampsiden
        alle_hændelser_links = find_all_hændelser_links(soup, BASE_URL)
        
        print(f"Fandt {len(alle_hændelser_links)} 'Alle hændelser' links")
        
        for href, match_id, match_type in alle_hændelser_links:
            print(f"Debug: Behandler 'Alle hændelser' link: {href}")
            print(f"Debug: Match ID: {match_id}, Match Type: {match_type}")
            
            # Definér output-filnavn
            output_file = os.path.join(OUTPUT_DIR, f"match_{match_id}_{match_type}.pdf")
            
            # Download PDF'en
            download_pdf(href, output_file, BASE_URL)
    
    print("Download afsluttet!")

if __name__ == "__main__":
    main() 