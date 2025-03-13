#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Find sjældne værdier i CSV-filer og tæl deres forekomster

Dette script gennemgår alle CSV-filer i csv-mappen og finder alle værdier
der forekommer mindre end 10 gange i kolonner 'hold', 'haendelse_1', 'pos' og 'haendelse_2'.
For disse sjældne værdier vises også filnavnene hvor de forekommer.

Brug:
    python find_rare_values.py
"""

import os
import csv
import glob
from collections import defaultdict, Counter

# Konstant for CSV-mappen
CSV_DIRECTORY = "csv"

# Tærskelværdi for hvad der betragtes som en 'sjælden' værdi
RARE_THRESHOLD = 10

def find_rare_values():
    """
    Gennemgår alle CSV-filer og finder sjældne værdier (< 10 forekomster) for specifikke kolonner,
    samt registrerer filnavnene hvor disse værdier forekommer.
    
    Returns:
        tuple: (value_counts, value_files), hvor:
            - value_counts er en ordbog med kolonnenavne som nøgler og Counter-objekter som værdier
            - value_files er en ordbog med (kolonne, værdi) tupler som nøgler og filnavnslister som værdier
    """
    # Kolonner vi ønsker at finde sjældne værdier for
    target_columns = ['hold', 'haendelse_1', 'pos', 'haendelse_2']
    
    # Ordbog til at holde tællinger for hver kolonne
    value_counts = defaultdict(Counter)
    
    # Ordbog til at holde styr på hvilke filer hver værdi forekommer i
    # Nøgle: (kolonne, værdi), Værdi: set af filnavne
    value_files = defaultdict(set)
    
    # Tæl filer og rækker for at give en status
    total_files = 0
    total_rows = 0
    
    # Find alle CSV-filer i csv-mappen (inkl. undermapper)
    csv_files = glob.glob(os.path.join(CSV_DIRECTORY, "**/*.csv"), recursive=True)
    
    print(f"Fandt {len(csv_files)} CSV-filer. Analyserer...")
    
    # Gennemgå hver CSV-fil
    for file_path in csv_files:
        total_files += 1
        
        # Vis fremskridt for hver 10. fil
        if total_files % 10 == 0:
            print(f"Behandler fil #{total_files}...")
        
        try:
            # Gem kun filnavnet, ikke hele stien, for mere læsbare resultater
            file_name = os.path.basename(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                # Læs CSV-filen
                reader = csv.DictReader(f)
                
                # Gennemgå hver række i filen
                for row in reader:
                    total_rows += 1
                    
                    # Tæl forekomster for hver målkolonne
                    for column in target_columns:
                        if column in row and row[column]:  # Kun hvis kolonnen har en værdi
                            value = row[column]
                            value_counts[column][value] += 1
                            
                            # Tilføj filnavnet til sættet af filer for denne værdi
                            value_files[(column, value)].add(file_name)
                            
        except Exception as e:
            print(f"Fejl ved læsning af fil {file_path}: {str(e)}")
    
    print(f"Analyse færdig! Behandlede {total_files} filer med i alt {total_rows} rækker.")
    return value_counts, value_files

def print_rare_values(value_counts, value_files):
    """
    Printer de sjældne værdier (< 10 forekomster) og deres antal forekomster for hver kolonne,
    samt filnavnene hvor disse værdier forekommer.
    
    Args:
        value_counts (dict): Ordbog med kolonnenavne og deres Counter-objekter
        value_files (dict): Ordbog med (kolonne, værdi) tupler og sæt af filnavne
    """
    print("\n=== SJÆLDNE VÆRDIER (< 10 FOREKOMSTER) OG DERES FILER ===")
    
    # For hver kolonne, find værdier med mindre end 10 forekomster
    for column, counter in value_counts.items():
        # Find sjældne værdier
        rare_values = [(value, count) for value, count in counter.items() if count < RARE_THRESHOLD]
        
        if rare_values:
            print(f"\n--- {column.upper()} ---")
            print(f"Antal sjældne værdier: {len(rare_values)}")
            print("Værdier, antal forekomster og filer:")
            
            # Sorter efter antal forekomster (mindst hyppige først)
            for value, count in sorted(rare_values, key=lambda x: x[1]):
                # Hent filer for denne værdi
                files = value_files[(column, value)]
                print(f"'{value}': {count} forekomster i {len(files)} filer:")
                
                # Vis alle filnavne for denne sjældne værdi
                for file_name in sorted(files):
                    print(f"  - {file_name}")
        else:
            print(f"\n--- {column.upper()} ---")
            print(f"Ingen sjældne værdier fundet.")

def main():
    """
    Hovedfunktion der kører analysen.
    """
    print(f"=== Håndboldhændelser - Find Sjældne Værdier (< {RARE_THRESHOLD} forekomster) ===")
    
    # Tjek om CSV-mappen eksisterer
    if not os.path.exists(CSV_DIRECTORY):
        print(f"Fejl: CSV-mappen '{CSV_DIRECTORY}' eksisterer ikke.")
        return
    
    # Find sjældne værdier og deres tællinger samt filer
    value_counts, value_files = find_rare_values()
    
    # Print resultaterne
    print_rare_values(value_counts, value_files)
    
    # Gem resultaterne til en fil
    save_to_file(value_counts, value_files)

def save_to_file(value_counts, value_files):
    """
    Gemmer de sjældne værdier, deres antal forekomster og filnavnene til en tekstfil.
    
    Args:
        value_counts (dict): Ordbog med kolonnenavne og deres Counter-objekter
        value_files (dict): Ordbog med (kolonne, værdi) tupler og sæt af filnavne
    """
    output_file = "sjaeldne_vaerdier.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"=== SJÆLDNE VÆRDIER (< {RARE_THRESHOLD} FOREKOMSTER) OG DERES FILER ===\n")
        
        # For hver kolonne, find værdier med mindre end 10 forekomster
        for column, counter in value_counts.items():
            # Find sjældne værdier
            rare_values = [(value, count) for value, count in counter.items() if count < RARE_THRESHOLD]
            
            if rare_values:
                f.write(f"\n--- {column.upper()} ---\n")
                f.write(f"Antal sjældne værdier: {len(rare_values)}\n")
                f.write("Værdier, antal forekomster og filer:\n")
                
                # Sorter efter antal forekomster (mindst hyppige først)
                for value, count in sorted(rare_values, key=lambda x: x[1]):
                    # Hent filer for denne værdi
                    files = value_files[(column, value)]
                    f.write(f"'{value}': {count} forekomster i {len(files)} filer:\n")
                    
                    # Vis alle filnavne for denne sjældne værdi
                    for file_name in sorted(files):
                        f.write(f"  - {file_name}\n")
            else:
                f.write(f"\n--- {column.upper()} ---\n")
                f.write(f"Ingen sjældne værdier fundet.\n")
    
    print(f"\nResultaterne er gemt i filen: {output_file}")

if __name__ == "__main__":
    main() 