#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DEBUG SCRIPT - Find Player Name Variations & Detailed Analysis
==============================================================

Dette script gennemsøger alle Herreliga-databasefiler for at finde variationer
af specifikke spillernavne og laver detaljeret analyse af kampantal.
"""

import sqlite3
import os
import pandas as pd
from collections import defaultdict

# === KONFIGURATION ===
BASE_DIR = "."
HERRELIGA_DB_DIR = os.path.join(BASE_DIR, "Herreliga-database")
SEASONS_TO_CHECK = [
    "2017-2018", "2018-2019", "2019-2020", "2020-2021",
    "2021-2022", "2022-2023", "2023-2024", "2024-2025"
]
PLAYERS_TO_FIND = ["LANDIN", "JOHANNESSON", "NORSTEN", "MØLLGAARD"]

def detailed_player_analysis():
    """
    Laver detaljeret analyse af specifikke spillere for at forstå kampantal problemet.
    """
    print("🕵️  DETALJERET SPILLERANALYSE - FOKUS PÅ KAMPANTAL")
    print("=" * 70)
    
    # Dictionary til at holde styr på alle kampe for hver spiller
    player_game_details = defaultdict(list)

    # Gennemgå hver sæson
    for season in SEASONS_TO_CHECK:
        season_path = os.path.join(HERRELIGA_DB_DIR, season)
        if not os.path.exists(season_path):
            continue

        print(f"\n🔍 Scanning season: {season}")
        
        # Gennemgå hver databasefil i sæsonmappen
        db_files = [f for f in os.listdir(season_path) if f.endswith('.db')]
        for db_file in db_files:
            db_path = os.path.join(season_path, db_file)
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Tjek om 'match_events' tabellen eksisterer
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_events'")
                if cursor.fetchone() is None:
                    conn.close()
                    continue

                # Hent match info for kontekst
                cursor.execute("SELECT * FROM match_info LIMIT 1")
                match_info = cursor.fetchone()
                if match_info:
                    _, hold_hjemme, hold_ude, resultat, _, dato, _, _ = match_info

                # Søg i de relevante kolonner for spillernavne
                for col in ['navn_1', 'navn_2', 'mv']:
                    cursor.execute(f"SELECT DISTINCT {col} FROM match_events")
                    all_names = cursor.fetchall()

                    for name_tuple in all_names:
                        name = name_tuple[0]
                        if name and isinstance(name, str):
                            # Sammenlign med hver spiller, vi leder efter (case-insensitivt)
                            for target_player in PLAYERS_TO_FIND:
                                if target_player in name.upper():
                                    # Registrer denne kamp for spilleren
                                    player_game_details[name.strip()].append({
                                        'season': season,
                                        'db_file': db_file,
                                        'column': col,
                                        'match_info': f"{hold_hjemme} vs {hold_ude} ({resultat})" if match_info else "N/A",
                                        'date': dato if match_info else "N/A"
                                    })
                
                conn.close()

            except Exception as e:
                print(f"  ❌ Fejl under læsning af {db_file}: {e}")
                continue

    # Analyser og print resultater
    print("\n\n✅ DETALJERET SPILLERANALYSE RESULTATER:")
    print("=" * 70)
    
    for player_name, game_details in player_game_details.items():
        print(f"\n--- {player_name} ---")
        
        # Gruppe kampe per sæson
        games_per_season = defaultdict(set)
        for detail in game_details:
            games_per_season[detail['season']].add(detail['db_file'])
        
        total_unique_games = 0
        for season, db_files in games_per_season.items():
            unique_games = len(db_files)
            total_unique_games += unique_games
            print(f"  📅 {season}: {unique_games} unikke kampe")
            
            # Vis de første 3 kampe som eksempler
            for i, detail in enumerate([d for d in game_details if d['season'] == season][:3]):
                print(f"    🏐 {detail['match_info']} [{detail['column']}]")
        
        print(f"  🎯 TOTAL UNIKKE KAMPE: {total_unique_games}")
        
        # Sammenlign med CSV-fil hvis tilgængelig
        try:
            csv_path = f"ELO_Results/Player_Seasonal_CSV/herreliga_seasonal_elo_2023_2024.csv"
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                # Søg efter spilleren i CSV (case-insensitive)
                player_rows = df[df['player'].str.upper().str.contains(player_name.upper(), na=False)]
                if not player_rows.empty:
                    csv_games = player_rows.iloc[0]['games']
                    print(f"  📊 CSV-fil viser: {csv_games} kampe")
                    print(f"  ⚠️  DIFFERENCE: {total_unique_games - csv_games} kampe mangler!")
                else:
                    print(f"  ❌ Ikke fundet i CSV-fil")
        except Exception as e:
            print(f"  ⚠️  Kunne ikke læse CSV: {e}")

def find_player_name_variations():
    """
    Gennemsøger databasefilerne og finder unikke navnevariationer for de specificerede spillere.
    """
    print("🕵️  Starter søgning efter spillernavne-variationer i Herreliga databaser...")
    print("=" * 70)
    
    # En dictionary til at holde styr på alle fundne variationer for hver spiller
    found_variations = defaultdict(set)

    # Gennemgå hver sæson
    for season in SEASONS_TO_CHECK:
        season_path = os.path.join(HERRELIGA_DB_DIR, season)
        if not os.path.exists(season_path):
            print(f"🟡 Sæson '{season}' ikke fundet, springer over.")
            continue

        print(f"\nScanning season: {season}")
        
        # Gennemgå hver databasefil i sæsonmappen
        db_files = [f for f in os.listdir(season_path) if f.endswith('.db')]
        for db_file in db_files:
            db_path = os.path.join(season_path, db_file)
            
            try:
                # Opret forbindelse til databasen
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                # Tjek om 'match_events' tabellen eksisterer
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_events'")
                if cursor.fetchone() is None:
                    conn.close()
                    continue

                # Søg i de relevante kolonner for spillernavne
                for col in ['navn_1', 'navn_2', 'mv']:
                    # Hent alle unikke navne fra kolonnen
                    cursor.execute(f"SELECT DISTINCT {col} FROM match_events")
                    all_names = cursor.fetchall()

                    for name_tuple in all_names:
                        name = name_tuple[0]
                        if name and isinstance(name, str):
                            # Sammenlign med hver spiller, vi leder efter (case-insensitivt)
                            for target_player in PLAYERS_TO_FIND:
                                if target_player in name.upper():
                                    found_variations[target_player].add(name.strip())
                
                conn.close()

            except Exception as e:
                print(f"  ❌ Fejl under læsning af {db_file}: {e}")
                continue

    # Print de endelige resultater
    print("\n\n✅ Søgning afsluttet. Fundne variationer:")
    print("=" * 70)
    if not found_variations:
        print("Ingen variationer fundet for de specificerede spillere.")
    else:
        for player, variations in found_variations.items():
            print(f"--- {player} ---")
            if variations:
                for variation in sorted(list(variations)):
                    print(f"  - '{variation}'")
            else:
                print("  Ingen variationer fundet.")

if __name__ == "__main__":
    print("🚀 STARTER UDVIDET DEBUG ANALYSE")
    print("=" * 80)
    
    # Kør begge analyser
    find_player_name_variations()
    print("\n" + "="*80 + "\n")
    detailed_player_analysis()
    
    print("\n🎉 DEBUG ANALYSE KOMPLET!")
    print("=" * 80) 