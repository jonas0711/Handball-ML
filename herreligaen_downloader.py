#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script til at downloade alle PDF-filer under "Alle hændelser" fra herreligaen på tophaandbold.dk
Filerne gemmes i en mappestruktur baseret på sæson.

Brug:
    python herreligaen_downloader.py --sæson=2024-2025
"""

import os
import requests
from bs4 import BeautifulSoup
import re
import argparse
import sys
import time

def parse_arguments():
    """Parse kommandolinje-argumenter"""
    parser = argparse.ArgumentParser(description='Download håndbold PDF-filer fra herreligaen')
    
    # Sæson parameter (default: 2024-2025)
    parser.add_argument('--sæson', type=str, default='2024-2025',
                      help='Sæsonen der skal behandles (f.eks. 2024-2025)')
    
    # Valider sæson-format (YYYY-YYYY)
    args = parser.parse_args()
    if not re.match(r'^\d{4}-\d{4}$', args.sæson):
        print(f"Fejl: Ugyldig sæson: {args.sæson}. Formatet skal være YYYY-YYYY, f.eks. 2024-2025")
        sys.exit(1)
    
    return args

def setup_directories(sæson):
    """Opsætter nødvendige mapper baseret på sæson"""
    # Definer mappe-struktur
    output_dir = os.path.join("Herreliga", sæson)
    
    # Sørg for at output-mappen eksisterer
    os.makedirs(output_dir, exist_ok=True)
    
    return output_dir

def download_pdf(url, output_file):
    """Download PDF fra URL og gem den med det givne filnavn"""
    # Tjek om filen allerede findes og har indhold
    if os.path.exists(output_file) and os.path.getsize(output_file) > 1024:
        print(f"Filen {output_file} findes allerede. Springer over.")
        return True
    
    print(f"Downloader: {url} -> {output_file}")
    
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
            print(f"Fejl ved download: Status kode {response.status_code}")
            return False
        
        # Tjek at indholdet ligner en PDF
        is_pdf = response.content.startswith(b'%PDF-') or 'application/pdf' in response.headers.get('Content-Type', '')
        if not is_pdf:
            print(f"Advarsel: Indholdet ligner ikke en PDF-fil. Content-Type: {response.headers.get('Content-Type')}")
        
        # Gem filen under alle omstændigheder
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        # Verificer filstørrelsen
        file_size = os.path.getsize(output_file)
        if file_size < 1024:
            print(f"Advarsel: Filen {output_file} er meget lille ({file_size} bytes). Det kan være at den ikke er en gyldig PDF.")
            # Vi beholder filen men markerer den som fejlet
            with open(output_file + ".failed", "w") as f:
                f.write(f"Download fejlet: Filstørrelse for lille ({file_size} bytes)")
            return False
        
        print(f"PDF-fil gemt som: {output_file} ({file_size} bytes)")
        return True
    except Exception as e:
        print(f"Fejl ved download af {url}: {str(e)}")
        # Skriv fejlbesked til en fil for at hjælpe med fejlsøgning
        try:
            with open(output_file + ".error", "w") as f:
                f.write(f"Download fejlet: {str(e)}")
        except:
            pass
        return False

def main():
    """Hovedfunktion"""
    args = parse_arguments()
    sæson = args.sæson
    
    # Første år i sæsonen, bruges i URL
    year = sæson.split('-')[0]
    
    # Opsæt mappe
    output_dir = setup_directories(sæson)
    
    # Base URL
    base_url = "https://tophaandbold.dk"
    kampprogram_url = f"{base_url}/kampprogram/herreligaen?year={year}&team=&home_game=0&home_game=1&away_game=0&away_game=1"
    
    print(f"Starter download af PDF-filer fra herreligaen for sæson {sæson}")
    print(f"Henter data fra: {kampprogram_url}")
    print(f"Filer vil blive gemt i: {os.path.abspath(output_dir)}")
    
    # Hent kampprogram-siden
    try:
        response = requests.get(kampprogram_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Gem en kopi af HTML for debugging
        with open('debug_page.html', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print("Kampprogram-siden gemt som debug_page.html for debugging")
    except Exception as e:
        print(f"Fejl ved hentning af kampprogram-siden: {str(e)}")
        return
    
    # Find alle links med teksten "Alle hændelser"
    alle_links = []
    
    # Søg i dropdown-items specifikt (baseret på den faktiske HTML)
    for link in soup.find_all('a', class_='dropdown-item'):
        text = link.get_text(strip=True)
        href = link.get('href')
        
        if href and text and ("Alle hændelser" in text or "alle hændelser" in text.lower()):
            print(f"Fandt 'Alle hændelser' link: {href}")
            
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
            else:
                print(f"  Advarsel: Kunne ikke ekstrahere match_id og match_type fra {href}")
    
    # Hvis vi ikke fandt nogen links via dropdown-items, prøv generelt søgning som backup
    if not alle_links:
        print("Ingen links fundet via dropdown-items, prøver generel søgning...")
        for link in soup.find_all('a'):
            text = link.get_text(strip=True)
            href = link.get('href')
            
            if href and text and ("Alle hændelser" in text or "alle hændelser" in text.lower()):
                print(f"Fandt 'Alle hændelser' link via generel søgning: {href}")
                
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
                else:
                    print(f"  Advarsel: Kunne ikke ekstrahere match_id og match_type fra {href}")
    
    if alle_links:
        print(f"Fandt {len(alle_links)} 'Alle hændelser' links")
        
        downloaded = 0
        failed = 0
        for url, match_id, match_type in alle_links:
            output_file = os.path.join(output_dir, f"match_{match_id}_{match_type}.pdf")
            if download_pdf(url, output_file):
                downloaded += 1
            else:
                failed += 1
            # Lille pause mellem downloads for at undgå at blive begrænset af serveren
            time.sleep(1)
        
        print(f"Download afsluttet. {downloaded} filer blev downloadet, {failed} fejlede.")
        print(f"Se {output_dir} for downloadede filer og eventuelle .failed/.error filer for fejlinformation.")
    else:
        print("Ingen 'Alle hændelser' links fundet på kampprogram-siden.")
        
        # Vis nogle eksempler på links på siden for debugging
        print("\nHer er nogle eksempler på links der blev fundet på siden:")
        for i, link in enumerate(soup.find_all('a')[:10]):
            print(f"Link {i+1}: {link.get_text(strip=True)} - {link.get('href')}")

if __name__ == "__main__":
    main() 