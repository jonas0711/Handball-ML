#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database til CSV konvertering

Dette script konverterer alle SQLite-databasefiler fra Kvindeliga-database og
Herreliga-database mapperne til CSV-filer baseret på match_events tabellen.
CSV-filerne gemmes i en ny mappestruktur under 'csv' mappen.

Brug:
    python db_to_csv_converter.py
"""

import os
import sqlite3
import csv
import glob
import sys
from pathlib import Path

# Konstanter
INPUT_DIRECTORIES = [
    "Kvindeliga-database",
    "Herreliga-database"
]
OUTPUT_DIRECTORY = "csv"

def create_output_directories():
    """
    Opretter output-mappestrukturen, hvis den ikke eksisterer.
    """
    # Opret hovedmappen, hvis den ikke eksisterer
    if not os.path.exists(OUTPUT_DIRECTORY):
        os.makedirs(OUTPUT_DIRECTORY)
        print(f"Oprettet hovedmappe: {OUTPUT_DIRECTORY}")

    # Opret undermapper for hver liga
    for input_dir in INPUT_DIRECTORIES:
        # Uddrag liganavn (fjerner '-database' delen)
        liga_name = input_dir.split('-')[0]
        liga_output_dir = os.path.join(OUTPUT_DIRECTORY, liga_name)
        
        # Opret liga-mappen, hvis den ikke eksisterer
        if not os.path.exists(liga_output_dir):
            os.makedirs(liga_output_dir)
            print(f"Oprettet liga-mappe: {liga_output_dir}")
        
        # Find alle sæsonmapper i input-mappen
        for season_dir in glob.glob(os.path.join(input_dir, "*/")):
            # Uddrag sæsonnavnet (f.eks. "2024-2025")
            season_name = os.path.basename(os.path.normpath(season_dir))
            
            # Opret sæson-mappen under output-liga-mappen
            season_output_dir = os.path.join(liga_output_dir, season_name)
            if not os.path.exists(season_output_dir):
                os.makedirs(season_output_dir)
                print(f"Oprettet sæson-mappe: {season_output_dir}")

def convert_db_to_csv(db_file, csv_file):
    """
    Konverterer en SQLite-databasefil til en CSV-fil baseret på match_events tabellen.
    
    Args:
        db_file (str): Sti til SQLite-databasefilen
        csv_file (str): Sti til output CSV-filen
    
    Returns:
        bool: True hvis konverteringen lykkedes, ellers False
    """
    try:
        # Opret forbindelse til databasen
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Tjek om match_events tabellen eksisterer
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_events';")
        if not cursor.fetchone():
            print(f"Fejl: match_events tabellen findes ikke i {db_file}")
            conn.close()
            return False
        
        # Hent kolonneinformation
        cursor.execute("PRAGMA table_info(match_events)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Hent alle data fra match_events tabellen
        cursor.execute("SELECT * FROM match_events")
        data = cursor.fetchall()
        
        # Luk databaseforbindelsen
        conn.close()
        
        # Skriv data til CSV-fil
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            # Skriv kolonnenavne
            writer.writerow(columns)
            # Skriv data
            writer.writerows(data)
        
        print(f"Konverteret: {db_file} -> {csv_file}")
        return True
    
    except Exception as e:
        print(f"Fejl ved konvertering af {db_file}: {str(e)}")
        return False

def get_match_info(db_file):
    """
    Henter match_info fra databasefilen til brug i CSV-filnavnet.
    
    Args:
        db_file (str): Sti til SQLite-databasefilen
    
    Returns:
        dict: Ordbog med match_info data eller tom ordbog hvis der opstod en fejl
    """
    try:
        # Opret forbindelse til databasen
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Tjek om match_info tabellen eksisterer
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_info';")
        if not cursor.fetchone():
            print(f"Advarsel: match_info tabellen findes ikke i {db_file}")
            conn.close()
            return {}
        
        # Hent match_info
        cursor.execute("SELECT kamp_id, hold_hjemme, hold_ude, dato FROM match_info")
        info = cursor.fetchone()
        
        # Luk databaseforbindelsen
        conn.close()
        
        if info:
            return {
                'kamp_id': info[0],
                'hold_hjemme': info[1],
                'hold_ude': info[2],
                'dato': info[3]
            }
        else:
            return {}
    
    except Exception as e:
        print(f"Fejl ved hentning af match_info fra {db_file}: {str(e)}")
        return {}

def process_all_databases():
    """
    Behandler alle databasefiler i input-mapperne og konverterer dem til CSV-filer.
    """
    total_files = 0
    success_count = 0
    error_count = 0
    
    # Gennemgå alle input-mapper
    for input_dir in INPUT_DIRECTORIES:
        # Uddrag liganavn (fjerner '-database' delen)
        liga_name = input_dir.split('-')[0]
        
        # Find alle sæsonmapper i input-mappen
        for season_dir in glob.glob(os.path.join(input_dir, "*/")):
            # Uddrag sæsonnavnet (f.eks. "2024-2025")
            season_name = os.path.basename(os.path.normpath(season_dir))
            
            # Definer output-mappen for denne sæson
            output_season_dir = os.path.join(OUTPUT_DIRECTORY, liga_name, season_name)
            
            # Find alle .db filer i denne sæson-mappe
            db_files = glob.glob(os.path.join(season_dir, "*.db"))
            
            print(f"\nBehandler {len(db_files)} databasefiler i {input_dir}/{season_name}...")
            
            # Gennemgå hver databasefil
            for db_file in db_files:
                total_files += 1
                
                # Hent match_info til filnavnet
                match_info = get_match_info(db_file)
                
                # Opret CSV-filnavn
                if match_info and 'kamp_id' in match_info:
                    # Brug kamp_id og hold-navne til at skabe et beskrivende filnavn
                    base_name = f"kamp_{match_info['kamp_id']}_{match_info['hold_hjemme']}_vs_{match_info['hold_ude']}"
                    # Fjern ugyldige filnavnskarakterer
                    base_name = "".join(c if c.isalnum() or c in ['_', '-'] else '_' for c in base_name)
                else:
                    # Fallback til at bruge det oprindelige databasefilnavn
                    base_name = os.path.splitext(os.path.basename(db_file))[0]
                
                csv_file = os.path.join(output_season_dir, f"{base_name}.csv")
                
                # Konverter databasen til CSV
                if convert_db_to_csv(db_file, csv_file):
                    success_count += 1
                else:
                    error_count += 1
    
    # Rapporter resultater
    print(f"\nKonvertering færdig!")
    print(f"Total antal filer behandlet: {total_files}")
    print(f"Succes: {success_count}")
    print(f"Fejl: {error_count}")

def main():
    """
    Hovedfunktion der kører hele konverteringsprocessen.
    """
    print("=== Håndboldhændelser - Database til CSV Konvertering ===")
    
    # Tjek om input-mapperne eksisterer
    for input_dir in INPUT_DIRECTORIES:
        if not os.path.exists(input_dir):
            print(f"Fejl: Input-mappen '{input_dir}' eksisterer ikke.")
            return
    
    # Opret output-mappestrukturen
    create_output_directories()
    
    # Behandl alle databasefiler
    process_all_databases()

if __name__ == "__main__":
    main() 