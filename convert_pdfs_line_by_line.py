#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dette script konverterer alle PDF-filer i Kvindeliga/2024-2025/-mappen til TXT-filer
og gemmer dem i en separat mappe 'Kvindeliga-txt/2024-2025/'.
Scriptet prioriterer at bevare linjestrukturen fra PDF'erne.
"""

import os
import glob
import fitz  # PyMuPDF
import time

# Definer stier
PDF_DIR = os.path.join("Kvindeliga", "2024-2025")
TXT_BASE_DIR = "Kvindeliga-txt"
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

def convert_pdf_to_txt_line_by_line(pdf_path, txt_path):
    """
    Konverterer en PDF-fil til tekst og gemmer den i en tekstfil med bevarelse af linjestruktur
    
    Args:
        pdf_path (str): Sti til PDF-filen
        txt_path (str): Sti, hvor tekstfilen skal gemmes
    
    Returns:
        bool: True hvis konverteringen er vellykket
    """
    try:
        # Åbn PDF-dokumentet
        doc = fitz.open(pdf_path)
        
        # Opsamler alt tekst
        all_text = []
        
        # Gennemgå hver side
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            
            # Udskriv sidenummer for at se fremskridt
            print(f"  Behandler side {page_num + 1}/{len(doc)} i {os.path.basename(pdf_path)}...")
            
            # Udtrækker blokke for at bevare layout og tekststruktur
            # Sorter blokkene efter vertikale koordinater
            blocks = page.get_text("blocks")
            blocks.sort(key=lambda b: (b[1], b[0]))  # Sorter efter y, derefter x
            
            # Behandl hver blok
            for block in blocks:
                # Få teksten fra blokken
                text = block[4]
                
                # Opdel teksten i linjer og tilføj hver linje til resultatet
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    if line:
                        all_text.append(line)
            
            # Tilføj en ekstra tom linje mellem sider
            all_text.append("")
        
        # Luk dokumentet
        doc.close()
        
        # Kontrollér om der faktisk er tekst at gemme
        if not all_text:
            print(f"Ingen tekst fundet i {pdf_path}. Springer over.")
            return False
        
        # Skriv alle linjer til tekstfilen
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(all_text))
        
        print(f"Konverteret: {pdf_path} -> {txt_path} ({len(all_text)} linjer)")
        return True
    
    except Exception as e:
        print(f"Fejl ved konvertering af {pdf_path}: {e}")
        return False

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
        
        # Konverter PDF-filen til tekst linje for linje
        if convert_pdf_to_txt_line_by_line(pdf_path, txt_path):
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