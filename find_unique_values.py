#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Find unikke værdier i CSV-filer og tæl deres forekomster

Dette script gennemgår alle CSV-filer i csv-mappen og finder alle unikke værdier
for kolonnerne 'hold', 'haendelse_1', 'pos' og 'haendelse_2', samt tæller antallet
af gange hver værdi forekommer.

Brug:
    python find_unique_values.py
"""

import os
import csv
import glob
from collections import defaultdict, Counter

# Konstant for CSV-mappen
CSV_DIRECTORY = "csv"

def find_unique_values():
    """
    Gennemgår alle CSV-filer og finder unikke værdier for specifikke kolonner,
    samt tæller antallet af gange hver værdi forekommer.
    
    Returns:
        dict: Ordbog med kolonnenavne som nøgler og Counter-objekter som værdier
    """
    # Kolonner vi ønsker at finde unikke værdier for
    target_columns = ['hold', 'haendelse_1', 'pos', 'haendelse_2']
    
    # Ordbog til at holde tællinger for hver kolonne
    value_counts = defaultdict(Counter)
    
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
            with open(file_path, 'r', encoding='utf-8') as f:
                # Læs CSV-filen
                reader = csv.DictReader(f)
                
                # Gennemgå hver række i filen
                for row in reader:
                    total_rows += 1
                    
                    # Tæl forekomster for hver målkolonne
                    for column in target_columns:
                        if column in row and row[column]:  # Kun hvis kolonnen har en værdi
                            value_counts[column][row[column]] += 1
                            
        except Exception as e:
            print(f"Fejl ved læsning af fil {file_path}: {str(e)}")
    
    print(f"Analyse færdig! Behandlede {total_files} filer med i alt {total_rows} rækker.")
    return value_counts

def print_value_counts(value_counts):
    """
    Printer de unikke værdier og deres antal forekomster for hver kolonne.
    
    Args:
        value_counts (dict): Ordbog med kolonnenavne og deres Counter-objekter
    """
    print("\n=== UNIKKE VÆRDIER OG DERES ANTAL ===")
    
    # Gennemgå hver kolonne og print de unikke værdier og tællinger
    for column, counter in value_counts.items():
        # Sorter efter antal forekomster (mest hyppige først)
        sorted_items = counter.most_common()
        
        print(f"\n--- {column.upper()} ---")
        print(f"Antal unikke værdier: {len(sorted_items)}")
        print("Værdier og antal forekomster (sorteret efter hyppighed):")
        
        # Formater resultaterne i en tabel-lignende struktur
        for value, count in sorted_items:
            print(f"'{value}': {count}")

def main():
    """
    Hovedfunktion der kører analysen.
    """
    print("=== Håndboldhændelser - Find Unikke Værdier og Tæl Forekomster ===")
    
    # Tjek om CSV-mappen eksisterer
    if not os.path.exists(CSV_DIRECTORY):
        print(f"Fejl: CSV-mappen '{CSV_DIRECTORY}' eksisterer ikke.")
        return
    
    # Find unikke værdier og deres tællinger
    value_counts = find_unique_values()
    
    # Print resultaterne
    print_value_counts(value_counts)
    
    # Gem resultaterne til en fil
    save_to_file(value_counts)

def save_to_file(value_counts):
    """
    Gemmer de unikke værdier og deres antal forekomster til en tekstfil.
    
    Args:
        value_counts (dict): Ordbog med kolonnenavne og deres Counter-objekter
    """
    output_file = "vaerdier_og_antal.txt"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=== UNIKKE VÆRDIER OG DERES ANTAL ===\n")
        
        # Gennemgå hver kolonne og skriv de unikke værdier og tællinger
        for column, counter in value_counts.items():
            # Sorter efter antal forekomster (mest hyppige først)
            sorted_items = counter.most_common()
            
            f.write(f"\n--- {column.upper()} ---\n")
            f.write(f"Antal unikke værdier: {len(sorted_items)}\n")
            f.write("Værdier og antal forekomster (sorteret efter hyppighed):\n")
            
            # Formater resultaterne i en tabel-lignende struktur
            for value, count in sorted_items:
                f.write(f"'{value}': {count}\n")
        
        # Tilføj ekstra afsnit til CSV-eksport
        f.write("\n\n=== CSV FORMAT ===\n")
        
        # For hver kolonne, generer også en CSV-venlig version
        for column, counter in value_counts.items():
            sorted_items = counter.most_common()
            
            csv_file = f"{column}_counts.csv"
            f.write(f"\nData for '{column}' er også eksporteret til: {csv_file}\n")
            
            # Gem data i separat CSV-fil
            with open(csv_file, 'w', newline='', encoding='utf-8') as csv_f:
                csv_writer = csv.writer(csv_f)
                csv_writer.writerow([column, 'antal'])
                for value, count in sorted_items:
                    csv_writer.writerow([value, count])
    
    print(f"\nResultaterne er gemt i filen: {output_file}")
    print("CSV-filer med tællinger for hver kolonne er også blevet oprettet.")

if __name__ == "__main__":
    main() 