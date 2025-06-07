#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SPECIFIK DEBUG SCRIPT - Niklas Landin Kamp-tracking
==================================================

Dette script sporer specifikt Niklas Landins deltagelse gennem hele
ELO-systemet for at finde ud af, hvorfor han kun registreres med 10 kampe.
"""

import sqlite3
import os
import sys
from collections import defaultdict

# === KONFIGURATION ===
BASE_DIR = "."
HERRELIGA_DB_DIR = os.path.join(BASE_DIR, "Herreliga-database")
TARGET_PLAYER = "NIKLAS LANDIN"
SEASONS_TO_CHECK = ["2023-2024"]

def debug_landin_games():
    """Spor Niklas Landins kamp-deltagelse detaljeret"""
    print(f"🔍 SPORING AF {TARGET_PLAYER} KAMP-DELTAGELSE")
    print("=" * 60)
    
    total_files_found = 0
    total_events_found = 0
    actual_matches_participated = set()
    
    # Først: Find den korrekte database struktur
    sample_checked = False
    correct_columns = None
    
    for season in SEASONS_TO_CHECK:
        season_path = os.path.join(HERRELIGA_DB_DIR, season)
        
        if not os.path.exists(season_path):
            print(f"❌ Sæson ikke fundet: {season_path}")
            continue
            
        print(f"\n📅 ANALYSERER SÆSON: {season}")
        print("-" * 40)
        
        db_files = [f for f in os.listdir(season_path) if f.endswith('.db')]
        db_files.sort()
        
        print(f"📁 Fundet {len(db_files)} database filer")
        
        for db_file in db_files[:3]:  # Check kun de første 3 filer for struktur
            if sample_checked and correct_columns:
                break
                
            db_path = os.path.join(season_path, db_file)
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check specifikt for match_events tabellen
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_events'")
                if not cursor.fetchone():
                    conn.close()
                    continue
                
                # Få kolonnenavne fra match_events
                cursor.execute("PRAGMA table_info(match_events)")
                columns_info = cursor.fetchall()
                column_names = [col[1] for col in columns_info]
                
                print(f"  📊 Kolonner i match_events: {column_names}")
                
                # Find spillerkolonner
                player_columns = []
                for col in column_names:
                    if any(term in col.lower() for term in ['spiller', 'player', 'navn']):
                        player_columns.append(col)
                
                if player_columns:
                    correct_columns = {
                        'table': 'match_events',
                        'player_cols': player_columns,
                        'all_cols': column_names
                    }
                    sample_checked = True
                    print(f"  ✅ Fundet spillerkolonner: {player_columns}")
                    break
                else:
                    # Hvis ingen spillerkolonner fundet, vis alle kolonner
                    print(f"  ⚠️  Ingen spillerkolonner fundet. Alle kolonner: {column_names}")
                    # Test med alle tekstkolonner
                    text_columns = []
                    for col in column_names:
                        # Test om det er en tekstkolonne ved at tjekke datatype
                        cursor.execute(f"SELECT {col} FROM match_events LIMIT 1")
                        sample = cursor.fetchone()
                        if sample and sample[0] and isinstance(sample[0], str):
                            text_columns.append(col)
                    
                    if text_columns:
                        correct_columns = {
                            'table': 'match_events',
                            'player_cols': text_columns,  # Brug alle tekstkolonner
                            'all_cols': column_names
                        }
                        sample_checked = True
                        print(f"  💡 Bruger tekstkolonner som spillerkolonner: {text_columns}")
                        break
                
                conn.close()
                
            except Exception as e:
                print(f"    ❌ Fejl i {db_file}: {e}")
                continue
        
        if not sample_checked:
            print("❌ Kunne ikke finde korrekt database struktur!")
            return
        
        print(f"\n🔍 BRUGER STRUKTUR: {correct_columns}")
        print("=" * 40)
        
        # Nu søg efter Landin med korrekte kolonner
        checked_files = 0
        for db_file in db_files:
            db_path = os.path.join(season_path, db_file)
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check om match_events findes
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_events'")
                if not cursor.fetchone():
                    conn.close()
                    continue
                
                table_name = correct_columns['table']
                player_cols = correct_columns['player_cols']
                
                # Byg query dynamisk
                where_conditions = []
                for col in player_cols:
                    where_conditions.append(f"UPPER({col}) LIKE '%LANDIN%'")
                
                where_clause = " OR ".join(where_conditions)
                
                query = f"""
                SELECT * FROM {table_name} 
                WHERE {where_clause}
                """
                
                cursor.execute(query)
                events = cursor.fetchall()
                
                checked_files += 1
                
                if events:
                    total_files_found += 1
                    total_events_found += len(events)
                    actual_matches_participated.add(db_file)
                    
                    print(f"  🎯 {db_file}: {len(events)} events fundet")
                    
                    # Vis nogle eksempler med kolonnenavne
                    for i, event in enumerate(events[:2]):  # Vis kun første 2
                        event_dict = dict(zip(correct_columns['all_cols'], event))
                        print(f"    - Event {i+1}: {event_dict}")
                
                conn.close()
                
            except Exception as e:
                print(f"    ❌ Fejl i {db_file}: {e}")
                continue
        
        print(f"\n📊 GENNEMSØGNING KOMPLET:")
        print(f"   Undersøgte {checked_files} filer")
        
    print(f"\n🏁 SAMMENFATNING FOR {TARGET_PLAYER}")
    print("=" * 60)
    print(f"🎯 Total kampe med Landin events: {len(actual_matches_participated)}")
    print(f"📊 Total events fundet: {total_events_found}")
    
    if actual_matches_participated:
        print(f"\n✅ Kampe med Landin:")
        for match in sorted(actual_matches_participated):
            print(f"  - {match}")
    else:
        print("\n❌ INGEN KAMPE FUNDET! Dette forklarer hvorfor han kun har 10 kampe.")
        print("   Problemet er i database søgningen eller navnematching.")
    
    return {
        'total_matches': len(actual_matches_participated),
        'total_events': total_events_found,
        'structure': correct_columns
    }

if __name__ == "__main__":
    results = debug_landin_games() 