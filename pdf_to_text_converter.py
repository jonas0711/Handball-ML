#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dette script konverterer PDF-filer til TXT-filer og gemmer dem i en separat mappe.
Scriptet fokuserer på at bevare tabelstrukturen fra kamprapporterne,
så kolonner og rækker er korrekt justeret og let læsbare.

Brug:
    python pdf_to_text_converter.py --liga=kvindeligaen --sæson=2024-2025
    python pdf_to_text_converter.py --liga=herreligaen --sæson=2023-2024
"""

import os
import glob
import fitz  # PyMuPDF
import time
import re
import argparse
import sys

def parse_arguments():
    """
    Parserer kommandolinje-argumenter
    
    Returns:
        argparse.Namespace: De parserede argumenter
    """
    parser = argparse.ArgumentParser(description='Konverter håndbold PDF-filer til TXT-filer')
    
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
    Opsætter stier baseret på kommandolinje-argumenter
    
    Args:
        args (argparse.Namespace): Kommandolinje-argumenter
        
    Returns:
        tuple: (pdf_dir, txt_dir)
    """
    # Konverter liga-navn til mappenavn (fjern 'en' fra slutningen)
    liga_mappe = args.liga
    if liga_mappe.endswith('en'):
        liga_mappe = liga_mappe[:-2]
    liga_mappe = liga_mappe.capitalize()
    
    # Definer stier for PDF-filer og TXT-filer
    PDF_DIR = os.path.join(liga_mappe, args.sæson)
    TXT_BASE_DIR = f"{liga_mappe}-txt-tabel"
    TXT_DIR = os.path.join(TXT_BASE_DIR, args.sæson)
    
    # Sørg for at output-mapperne eksisterer
    os.makedirs(TXT_BASE_DIR, exist_ok=True)
    os.makedirs(TXT_DIR, exist_ok=True)
    
    return PDF_DIR, TXT_DIR

# Mindste acceptable PDF-størrelse i bytes
MIN_PDF_SIZE = 1024

def is_valid_pdf(pdf_path):
    """
    Tjekker om PDF-filen er gyldig og har indhold
    
    Args:
        pdf_path (str): Sti til PDF-filen
    
    Returns:
        bool: True hvis PDF'en er gyldig og har indhold
    """
    if not os.path.exists(pdf_path):
        return False
    
    # Tjek at filen har et minimum af indhold
    file_size = os.path.getsize(pdf_path)
    if file_size < MIN_PDF_SIZE:
        print(f"Filen {pdf_path} er for lille ({file_size} bytes). Springer over.")
        return False
    
    # Tjek om filen starter med PDF signatur
    with open(pdf_path, 'rb') as f:
        header = f.read(5)
        if header != b'%PDF-':
            print(f"Filen {pdf_path} er ikke en gyldig PDF-fil. Springer over.")
            return False
    
    return True

def text_already_exists(pdf_path, txt_dir):
    """
    Tjekker om der allerede findes en tekstfil for denne PDF
    
    Args:
        pdf_path (str): Sti til PDF-filen
        txt_dir (str): Sti til output-mappen for tekstfiler
    
    Returns:
        bool: True hvis tekstfilen allerede findes
    """
    # Beregn tekstfilnavn baseret på PDF-filnavn
    pdf_filename = os.path.basename(pdf_path)
    txt_filename = os.path.splitext(pdf_filename)[0] + ".txt"
    txt_path = os.path.join(txt_dir, txt_filename)
    
    # Tjek om filen findes
    if os.path.exists(txt_path):
        print(f"Filen {txt_path} findes allerede. Springer over.")
        return True
    
    return False

def is_row_empty(cells_text):
    """
    Tjekker om en række er tom (ingen celler har indhold)
    
    Args:
        cells_text (list): Liste med tekst fra celler
    
    Returns:
        bool: True hvis rækken er tom
    """
    return all(not cell.strip() for cell in cells_text)

def convert_pdf_to_text(pdf_path, txt_path):
    """
    Konverterer en PDF-fil til tekstformat med bevarelse af tabelstruktur
    
    Args:
        pdf_path (str): Sti til PDF-filen
        txt_path (str): Sti til output tekstfilen
    
    Returns:
        bool: True hvis konverteringen var succesfuld
    """
    try:
        # Åbn PDF-dokumentet
        doc = fitz.open(pdf_path)
        text_output = []
        
        # Behandl hver side
        for page_num, page in enumerate(doc):
            # Tilføj sidenummer undtagen for første side
            if page_num > 0:
                text_output.append(f"\n--- Side {page_num + 1} ---\n")
            
            # Udtræk tekst med bevarelse af layout
            text = page.get_text("text")
            text_output.append(text)
        
        # Luk dokumentet
        doc.close()
        
        # Gem den ekstraherede tekst til en fil
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(''.join(text_output))
        
        return True
    
    except Exception as e:
        print(f"Fejl ved konvertering af {pdf_path}: {str(e)}")
        return False

def main():
    """
    Hovedfunktion til at konvertere alle PDF-filer i PDF_DIR til tekstfiler
    """
    # Parse kommandolinje-argumenter
    args = parse_arguments()
    
    # Opsæt konfiguration baseret på argumenter
    PDF_DIR, TXT_DIR = setup_configuration(args)
    
    start_time = time.time()
    
    print(f"Starter konvertering af PDF-filer fra {PDF_DIR}")
    print(f"Tekstfiler vil blive gemt i: {os.path.abspath(TXT_DIR)}")
    
    # Find alle PDF-filer i mappen
    pdf_pattern = os.path.join(PDF_DIR, "*.pdf")
    pdf_files = glob.glob(pdf_pattern)
    
    if not pdf_files:
        print(f"Ingen PDF-filer fundet i {PDF_DIR}")
        return
    
    print(f"Fandt {len(pdf_files)} PDF-filer")
    
    # Hold styr på statistik
    successful = 0
    failed = 0
    skipped = 0
    
    # Konverter hver PDF-fil
    for pdf_path in pdf_files:
        # Tjek om PDF'en er gyldig
        if not is_valid_pdf(pdf_path):
            failed += 1
            continue
        
        # Beregn tekstfilens sti
        pdf_filename = os.path.basename(pdf_path)
        txt_filename = os.path.splitext(pdf_filename)[0] + ".txt"
        txt_path = os.path.join(TXT_DIR, txt_filename)
        
        # Tjek om tekstfilen allerede findes
        if text_already_exists(pdf_path, TXT_DIR):
            skipped += 1
            continue
        
        # Konverter PDF til tekst
        success = convert_pdf_to_text(pdf_path, txt_path)
        
        if success:
            print(f"Konverteret {pdf_filename} til {txt_filename}")
            successful += 1
        else:
            print(f"Kunne ikke konvertere {pdf_filename}")
            failed += 1
    
    end_time = time.time()
    duration = end_time - start_time
    
    print("\nKonvertering afsluttet!")
    print(f"Vellykket: {successful}")
    print(f"Mislykkedes: {failed}")
    print(f"Sprunget over: {skipped}")
    print(f"Total: {len(pdf_files)}")
    print(f"Tekstfiler blev gemt i: {os.path.abspath(TXT_DIR)}")
    print(f"\nKøretid: {duration:.2f} sekunder")

if __name__ == "__main__":
    main() 