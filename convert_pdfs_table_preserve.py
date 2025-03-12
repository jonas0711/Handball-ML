#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dette script konverterer alle PDF-filer i Kvindeliga/2024-2025/-mappen til TXT-filer
og gemmer dem i en separat mappe 'Kvindeliga-txt-tabel/2024-2025/'.

Scriptet fokuserer på at bevare tabelstrukturen fra kamprapporterne,
så kolonner og rækker er korrekt justeret og let læsbare.
"""

import os
import glob
import fitz  # PyMuPDF
import time
import re

# Definer stier
PDF_DIR = os.path.join("Kvindeliga", "2024-2025")
TXT_BASE_DIR = "Kvindeliga-txt-tabel"
TXT_DIR = os.path.join(TXT_BASE_DIR, "2024-2025")

# Mindste acceptable PDF-størrelse i bytes
MIN_PDF_SIZE = 1024

# Sørg for at output-mappen eksisterer
os.makedirs(TXT_DIR, exist_ok=True)

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
            print(f"Filen {pdf_path} har ikke gyldig PDF signatur. Springer over.")
            return False
    
    return True

def extract_match_info(pdf_path):
    """
    Udtrækker kamp-information fra PDF-filen
    
    Args:
        pdf_path (str): Sti til PDF-filen
    
    Returns:
        dict: Ordbog med kampinformation
    """
    info = {
        "hold_hjemme": "",
        "hold_ude": "",
        "resultat": "",
        "dato": "",
        "sted": ""
    }
    
    try:
        # Åbn PDF-dokumentet
        doc = fitz.open(pdf_path)
        
        # Vi kigger kun på første side for matchinfo
        page = doc.load_page(0)
        
        # Få teksten fra første side
        text = page.get_text()
        
        # Prøv at finde holdnavne og resultat
        teams_result = re.search(r'([A-Za-zÆØÅæøå\s]+)\s*-\s*([A-Za-zÆØÅæøå\s]+)\s*(\d+)\s*-\s*(\d+)', text)
        if teams_result:
            info["hold_hjemme"] = teams_result.group(1).strip()
            info["hold_ude"] = teams_result.group(2).strip()
            info["resultat"] = f"{teams_result.group(3)}-{teams_result.group(4)}"
        
        # Prøv at finde dato og sted
        date_venue = re.search(r'(\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4})[^\n]*?([A-Za-zÆØÅæøå\s]+)', text)
        if date_venue:
            info["dato"] = date_venue.group(1)
            info["sted"] = date_venue.group(2).strip()
        
        # Luk dokumentet
        doc.close()
    
    except Exception as e:
        print(f"Fejl ved udtrækning af kampinformation: {e}")
    
    return info

def convert_pdf_to_txt_preserve_table(pdf_path, txt_path):
    """
    Konverterer en PDF-fil til tekst med bevarelse af tabelstruktur
    
    Args:
        pdf_path (str): Sti til PDF-filen
        txt_path (str): Sti, hvor tekstfilen skal gemmes
    
    Returns:
        bool: True hvis konverteringen er vellykket
    """
    try:
        # Åbn PDF-dokumentet
        doc = fitz.open(pdf_path)
        
        # Udtrække kampen information til brug i header
        match_info = extract_match_info(pdf_path)
        
        # Start med at inkludere kampinfo
        all_text = []
        header = []
        if match_info["hold_hjemme"] and match_info["hold_ude"]:
            header.append(f"Kamp: {match_info['hold_hjemme']} - {match_info['hold_ude']}")
        if match_info["resultat"]:
            header.append(f"Resultat: {match_info['resultat']}")
        if match_info["dato"]:
            header.append(f"Dato: {match_info['dato']}")
        if match_info["sted"]:
            header.append(f"Sted: {match_info['sted']}")
        
        # Hvis vi har header information, tilføj det til output
        if header:
            all_text.append("="*80)
            all_text.extend(header)
            all_text.append("="*80)
            all_text.append("")
        
        # Gennemgå hver side
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Udskriv sidenummer for at se fremskridt
            print(f"  Behandler side {page_num + 1}/{len(doc)} i {os.path.basename(pdf_path)}...")
            
            # Tilføj sidenummer til output
            all_text.append(f"--- Side {page_num + 1} ---")
            all_text.append("")
            
            # Udtrækker tekst med rawDict-metoden for at bevare koordinater
            # Dette hjælper med at identificere tabeller og kolonner
            raw_dict = page.get_text("rawdict")
            
            # Organisér blokkene efter vertikale koordinater (y)
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0]))  # Sorter efter y, derefter x
            
            # Behandl hver blok
            for block in blocks:
                # Få teksten fra blokken
                text = block[4]
                
                # Hvis der er tabeller, forsøg at justere kolonner
                if '\n' in text and '\t' in text:
                    # Opdel i linjer og juster tabellen
                    table_lines = []
                    for line in text.split('\n'):
                        if line.strip():
                            # Erstatter flere mellemrum med et enkelt tab for bedre kolonnejustering
                            line = re.sub(r'\s{2,}', '\t', line)
                            table_lines.append(line)
                    
                    # Tilføj den justerede tabel
                    all_text.extend(table_lines)
                else:
                    # For almindelig tekst, bare opdel i linjer
                    for line in text.split('\n'):
                        line = line.strip()
                        if line:
                            all_text.append(line)
                
                # Tilføj en tom linje efter hver blok for bedre læsbarhed
                all_text.append("")
            
            # Tilføj en ekstra tom linje mellem sider
            all_text.append("")
        
        # Luk dokumentet
        doc.close()
        
        # For tabelindhold prøv at se, om vi kan optimere kolonnebredder
        # Dette er et forsøg på at gøre tabeloutput mere læsbart
        optimized_text = []
        table_mode = False
        table_lines = []
        
        for line in all_text:
            if '\t' in line:
                # Vi er i tabelmode
                if not table_mode:
                    table_mode = True
                    table_lines = []
                table_lines.append(line)
            else:
                # Vi er ikke i tabelmode
                if table_mode:
                    # Format tidligere tabellinjer
                    if table_lines:
                        optimized_text.extend(format_table(table_lines))
                        optimized_text.append("")
                    table_mode = False
                    table_lines = []
                
                optimized_text.append(line)
        
        # Tjek om vi sluttede i tabelmode
        if table_mode and table_lines:
            optimized_text.extend(format_table(table_lines))
        
        # Kontrollér om der faktisk er tekst at gemme
        if not optimized_text:
            print(f"Ingen tekst fundet i {pdf_path}. Springer over.")
            return False
        
        # Skriv alle linjer til tekstfilen
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(optimized_text))
        
        print(f"Konverteret: {pdf_path} -> {txt_path} ({len(optimized_text)} linjer)")
        return True
    
    except Exception as e:
        print(f"Fejl ved konvertering af {pdf_path}: {e}")
        return False

def format_table(table_lines):
    """
    Formatterer en tabel for at få pæne kolonner
    
    Args:
        table_lines (list): Liste af tabellinjer med tab-separerede værdier
    
    Returns:
        list: Liste af formatterede tabellinjer
    """
    # Hvis der er mindre end 2 linjer, betragter vi det ikke som en tabel
    if len(table_lines) < 2:
        return table_lines
    
    # Find maksimalt antal kolonner
    max_cols = 0
    for line in table_lines:
        cols = line.split('\t')
        max_cols = max(max_cols, len(cols))
    
    # Hvis vi kun har én kolonne, brug ikke tabelformattering
    if max_cols <= 1:
        return table_lines
    
    # Find maksimal bredde for hver kolonne
    col_widths = [0] * max_cols
    
    # Opdel alle linjer i kolonner og find maksimal bredde
    split_lines = []
    for line in table_lines:
        cols = line.split('\t')
        # Pad med tomme strenge, hvis linjen har færre kolonner
        cols = cols + [''] * (max_cols - len(cols))
        split_lines.append(cols)
        
        # Opdater kolonnebredde
        for i, col in enumerate(cols):
            col_widths[i] = max(col_widths[i], len(col))
    
    # Formatér hver linje med fast kolonnebredde
    formatted_lines = []
    for cols in split_lines:
        # Formatér hver kolonne til den krævede bredde
        formatted_cols = []
        for i, col in enumerate(cols):
            # Venstrejustér tekst og pad med mellemrum
            formatted_cols.append(col.ljust(col_widths[i]))
        
        # Sammensæt kolonner til en linje
        formatted_lines.append('  '.join(formatted_cols))
    
    return formatted_lines

def main():
    """
    Hovedfunktion til at konvertere PDF-filer til tekstfiler
    """
    print(f"Starter konvertering af PDF-filer fra {PDF_DIR}")
    print(f"Tekstfiler vil blive gemt i: {os.path.abspath(TXT_DIR)}")
    
    # Find alle PDF-filer i mappen
    pdf_files = glob.glob(os.path.join(PDF_DIR, "*.pdf"))
    
    if not pdf_files:
        print(f"Ingen PDF-filer fundet i {PDF_DIR}")
        return
    
    print(f"Fandt {len(pdf_files)} PDF-filer")
    
    # Statistik
    successful = 0
    failed = 0
    skipped = 0
    
    # Konverter hver PDF-fil
    for pdf_path in pdf_files:
        # Få filnavnet uden sti og filtype
        base_name = os.path.basename(pdf_path)
        file_name = os.path.splitext(base_name)[0]
        txt_path = os.path.join(TXT_DIR, f"{file_name}.txt")
        
        # Tjek om tekstfilen allerede eksisterer
        if os.path.exists(txt_path):
            print(f"Filen {txt_path} findes allerede. Springer over.")
            skipped += 1
            continue
        
        # Tjek om PDF-filen er gyldig
        if not is_valid_pdf(pdf_path):
            print(f"Springer over ugyldig PDF: {pdf_path}")
            skipped += 1
            continue
        
        print(f"Konverterer: {pdf_path}")
        
        # Konverter PDF-filen til tekst med tabelbevarelse
        if convert_pdf_to_txt_preserve_table(pdf_path, txt_path):
            successful += 1
        else:
            failed += 1
    
    # Vis opsummering
    print("\nKonvertering afsluttet!")
    print(f"Vellykket: {successful}")
    print(f"Mislykkedes: {failed}")
    print(f"Sprunget over: {skipped}")
    print(f"Total: {len(pdf_files)}")
    print(f"Tekstfiler blev gemt i: {os.path.abspath(TXT_DIR)}")

if __name__ == "__main__":
    start_time = time.time()
    main()
    elapsed_time = time.time() - start_time
    print(f"\nKøretid: {elapsed_time:.2f} sekunder") 