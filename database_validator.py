#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database Checker til håndbolddata

Dette script undersøger en SQLite-database og viser en oversigt over indholdet.
Anvendes til at validere at konverteringen er sket korrekt.
"""

import os
import sys
import sqlite3
import glob
from tabulate import tabulate

def check_database(db_path):
    """Tjek og vis indhold af en database"""
    print(f"\n===== Tjekker database: {os.path.basename(db_path)} =====")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Hent match_info
        cursor.execute("SELECT * FROM match_info")
        match_info = cursor.fetchone()
        
        if match_info:
            info_columns = [description[0] for description in cursor.description]
            print("\nMatch Info:")
            info_data = dict(zip(info_columns, match_info))
            for key, value in info_data.items():
                print(f"  {key}: {value}")
            
            # Hent antal hændelser
            cursor.execute("SELECT COUNT(*) FROM match_events")
            event_count = cursor.fetchone()[0]
            print(f"\nTotal antal kamphændelser: {event_count}")
            
            # Vis nogle eksempler på hændelser
            print("\nEksempler på kamphændelser:")
            cursor.execute("""
            SELECT tid, maal, hold, haendelse_1, pos, nr_1, navn_1, 
                   haendelse_2, nr_2, navn_2, nr_mv, mv 
            FROM match_events LIMIT 5
            """)
            events = cursor.fetchall()
            event_columns = [description[0] for description in cursor.description]
            
            print(tabulate(events, headers=event_columns, tablefmt='grid'))
            
            # Vis statistik over hændelsestyper
            print("\nStatistik over hændelsestyper:")
            cursor.execute("""
            SELECT haendelse_1, COUNT(*) as antal 
            FROM match_events 
            GROUP BY haendelse_1 
            ORDER BY antal DESC
            """)
            haendelse_stats = cursor.fetchall()
            print(tabulate(haendelse_stats, headers=["Hændelse", "Antal"], tablefmt='grid'))
            
            # Vis statistik over målvogtere
            print("\nStatistik over målvogtere:")
            cursor.execute("""
            SELECT mv, COUNT(*) as antal 
            FROM match_events 
            WHERE mv IS NOT NULL 
            GROUP BY mv 
            ORDER BY antal DESC
            """)
            mv_stats = cursor.fetchall()
            print(tabulate(mv_stats, headers=["Målvogter", "Involveret i antal hændelser"], tablefmt='grid'))
            
            # Tjek efter potentielle problemer
            check_for_problems(conn)
            
        else:
            print("Ingen match_info fundet i databasen")
        
        conn.close()
        
    except Exception as e:
        print(f"Fejl ved tjek af database: {str(e)}")

def check_for_problems(conn):
    """Tjek for potentielle problemer i databasen"""
    cursor = conn.cursor()
    problems_found = False
    
    print("\nTjekker for potentielle problemer:")
    
    # Tjek for målvogtere i nr_2/navn_2 i stedet for nr_mv/mv
    cursor.execute("""
    SELECT COUNT(*) FROM match_events 
    WHERE haendelse_1 IN ('Mål', 'Skud reddet', 'Skud forbi', 'Skud på stolpe', 'Mål på straffe') 
    AND nr_2 IS NOT NULL AND nr_mv IS NULL
    """)
    wrong_goalie_count = cursor.fetchone()[0]
    
    if wrong_goalie_count > 0:
        problems_found = True
        print(f"  ADVARSEL: Fandt {wrong_goalie_count} hændelser hvor målvogteren muligvis er placeret forkert")
        
        cursor.execute("""
        SELECT tid, maal, hold, haendelse_1, nr_1, navn_1, nr_2, navn_2, nr_mv, mv 
        FROM match_events 
        WHERE haendelse_1 IN ('Mål', 'Skud reddet', 'Skud forbi', 'Skud på stolpe', 'Mål på straffe') 
        AND nr_2 IS NOT NULL AND nr_mv IS NULL
        LIMIT 5
        """)
        examples = cursor.fetchall()
        columns = ["tid", "maal", "hold", "haendelse_1", "nr_1", "navn_1", "nr_2", "navn_2", "nr_mv", "mv"]
        print("\nEksempler på mulige fejlplaceringer af målvogter:")
        print(tabulate(examples, headers=columns, tablefmt='grid'))
    
    # Tjek for forkert formaterede resultater (med mellemrum omkring bindestreg)
    cursor.execute("SELECT resultat, halvleg_resultat FROM match_info")
    result = cursor.fetchone()
    
    if result:
        resultat, halvleg_resultat = result
        
        if resultat and ' - ' in resultat:
            problems_found = True
            print(f"  ADVARSEL: Resultat '{resultat}' indeholder mellemrum omkring bindestregen")
        
        if halvleg_resultat and ' - ' in halvleg_resultat:
            problems_found = True
            print(f"  ADVARSEL: Halvlegsresultat '{halvleg_resultat}' indeholder mellemrum omkring bindestregen")
    
    # Tjek for forkert formaterede mål-værdier
    cursor.execute("SELECT COUNT(*) FROM match_events WHERE maal LIKE '% - %'")
    wrong_maal_count = cursor.fetchone()[0]
    
    if wrong_maal_count > 0:
        problems_found = True
        print(f"  ADVARSEL: Fandt {wrong_maal_count} hændelser med forkert formateret målværdi (med mellemrum omkring bindestregen)")
    
    if not problems_found:
        print("  Ingen problemer fundet!")

def main():
    """Hovedfunktion"""
    if len(sys.argv) > 1:
        # Hvis en specifik database er angivet
        db_path = sys.argv[1]
        if os.path.exists(db_path):
            check_database(db_path)
        else:
            print(f"Database ikke fundet: {db_path}")
    else:
        # Tjek alle databaser i output-mappen
        db_dir = "Kvindeliga-database/"
        if not os.path.exists(db_dir):
            print(f"Mappe ikke fundet: {db_dir}")
            return
        
        db_files = glob.glob(os.path.join(db_dir, "*.db"))
        
        if not db_files:
            print(f"Ingen databasefiler fundet i mappen: {db_dir}")
            return
        
        print(f"Fandt {len(db_files)} databasefiler")
        
        for db_file in db_files:
            check_database(db_file)

if __name__ == "__main__":
    main() 