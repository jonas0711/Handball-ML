#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Håndboldhændelser - Elo Rating System (Samlet Version)

Dette script implementerer et Elo Rating System for individuelle håndboldspillere
baseret på deres præstationer i kampe. Systemet kan behandle både Herreligaen og
Kvindeligaen, og sporer positive og negative hændelser for at justere spillernes
Elo-ratings over tid.

Brug:
    python handball_elo_system.py --liga=herreliga
    python handball_elo_system.py --liga=kvindeliga
    python handball_elo_system.py --liga=begge
"""

import os
import sqlite3
import glob
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
from datetime import datetime
import argparse

# Konstanter
BASE_ELO = 1500  # Startværdi for alle spillere
K_FACTOR = 20    # Basisværdi for hvor meget en enkelt hændelse kan ændre rating
SEASON = "2024-2025"  # Standardsæson

# Vægte for forskellige hændelsestyper (positive værdier = godt, negative = dårligt)
EVENT_WEIGHTS = {
    # Positive hændelser for markspillere
    "Mål": 10.0,
    "Mål på straffe": 8.0,
    "Assist": 7.0,
    "Bold erobret": 5.0,
    "Blokeret af": 5.0,
    "Blok af (ret)": 5.0,
    "Tilkendt straffe": 6.0,
    
    # Negative hændelser for markspillere
    "Fejlaflevering": -4.0,
    "Regelfejl": -3.0,
    "Skud forbi": -2.0,
    "Skud på stolpe": -1.5,
    "Skud blokeret": -2.0,
    "Tabt bold": -4.0,
    "Advarsel": -3.0,
    "Passivt spil": -2.0,
    "Straffekast forbi": -4.0,
    "Straffekast på stolpe": -3.0,
    "Udvisning": -6.0,
    "Rødt kort": -10.0,
    "Rødt kort, direkte": -12.0,
    "Blåt kort": -8.0,
    "Udvisning (2x)": -8.0,
    "Forårs. str.": -5.0,
    
    # Specialtilfælde - disse vil blive vendt for målvogtere
    "Skud reddet": -2.0,       # Negativt for markspiller, positivt for målvogter
    "Straffekast reddet": -4.0  # Negativt for markspiller, positivt for målvogter
}

# Målvogter-specifikke vægte (overskriver standardvægtene for målvogtere)
GOALKEEPER_WEIGHTS = {
    "Skud reddet": 5.0,       # Positivt for målvogter
    "Straffekast reddet": 8.0, # Meget positivt for målvogter
    "Mål": -5.0,              # Negativt for målvogter
    "Mål på straffe": -4.0     # Lidt mindre negativt (sværere at redde)
}

def parse_arguments():
    """
    Parser kommandolinjeargumenter
    
    Returns:
        argparse.Namespace: Parsede argumenter
    """
    parser = argparse.ArgumentParser(description='Beregn Elo ratings for håndboldspillere')
    
    # Liga valg (herreliga, kvindeliga eller begge)
    parser.add_argument('--liga', type=str, default='begge', 
                      choices=['herreliga', 'kvindeliga', 'begge'],
                      help='Hvilken liga der skal behandles (herreliga, kvindeliga, eller begge)')
    
    # Sæson valg
    parser.add_argument('--saeson', type=str, default=SEASON,
                      help=f'Sæson der skal behandles (default: {SEASON})')
    
    return parser.parse_args()

def get_liga_info(liga_name, sæson):
    """
    Returnerer mappe og outputsti for den angivne liga
    
    Args:
        liga_name: Navn på liga ('herreliga' eller 'kvindeliga')
        sæson: Sæson (f.eks. '2024-2025')
        
    Returns:
        tuple: (db_dir, output_dir, display_name)
    """
    if liga_name == 'herreliga':
        return (
            f"Herreliga-database/{sæson}",  # Database mappe
            f"player_ratings_herrer",        # Output mappe
            "Herreligaen"                    # Visningsnavn
        )
    else:  # kvindeliga
        return (
            f"Kvindeliga-database/{sæson}", # Database mappe
            f"player_ratings_kvinder",       # Output mappe
            "Kvindeligaen"                   # Visningsnavn
        )

def find_database_files(db_dir):
    """
    Finder alle databasefiler i den specificerede mappe
    
    Args:
        db_dir: Sti til databasemappen
        
    Returns:
        list: Sorteret liste af databasefiler
    """
    # Tjek at mappen eksisterer
    if not os.path.exists(db_dir):
        print(f"Advarsel: Mappen {db_dir} findes ikke!")
        return []
        
    db_files = glob.glob(os.path.join(db_dir, "*.db"))
    
    # Tjek om vi fandt nogen filer
    if not db_files:
        print(f"Ingen databasefiler fundet i {db_dir}")
        return []
    
    return sorted(db_files)

def get_match_date(conn):
    """
    Henter datoen for en kamp fra databasen
    
    Args:
        conn: SQLite connection
        
    Returns:
        str: Kampdato eller None
    """
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT dato FROM match_info")
        result = cursor.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        print(f"Fejl ved hentning af kampdato: {e}")
        return None

def parse_date(date_str):
    """
    Konverterer en dato-streng til et datetime-objekt
    
    Args:
        date_str: Dato som streng
        
    Returns:
        datetime: Dato som datetime-objekt eller None
    """
    if not date_str:
        return None
    
    # Prøv forskellige datoformater
    formats = ["%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y"]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    print(f"Kunne ikke parse dato: {date_str}")
    return None

def sort_games_by_date(db_files):
    """
    Sorterer kampe kronologisk baseret på datoer
    
    Args:
        db_files: Liste af databasefiler
        
    Returns:
        list: Sorteret liste af (db_file, dato) tupler
    """
    games_with_dates = []
    
    for db_file in db_files:
        try:
            conn = sqlite3.connect(db_file)
            date_str = get_match_date(conn)
            conn.close()
            
            date_obj = parse_date(date_str)
            if date_obj:
                games_with_dates.append((db_file, date_obj))
            else:
                print(f"Ingen gyldig dato fundet for {db_file}, springer over")
        except Exception as e:
            print(f"Fejl ved behandling af {db_file}: {e}")
    
    # Sortér efter dato
    return sorted(games_with_dates, key=lambda x: x[1])

def identify_goalkeepers(conn):
    """
    Identificerer målvogtere i en kamp
    
    Args:
        conn: SQLite connection
        
    Returns:
        set: Set af (trikot_nummer, navn) tupler for målvogtere
    """
    cursor = conn.cursor()
    goalkeepers = set()
    
    try:
        # Find spillere der optræder som målvogtere (nr_mv, mv)
        cursor.execute("""
            SELECT DISTINCT nr_mv, mv 
            FROM match_events 
            WHERE nr_mv IS NOT NULL AND nr_mv > 0 AND mv IS NOT NULL AND mv != ''
        """)
        
        for row in cursor.fetchall():
            if row[0] and row[1]:  # Sikrer at både nummer og navn er gyldige
                goalkeepers.add((row[0], row[1]))
                
        return goalkeepers
        
    except sqlite3.Error as e:
        print(f"Fejl ved identifikation af målvogtere: {e}")
        return set()

def get_player_key(number, name, team=None):
    """
    Genererer en unik nøgle for en spiller
    
    Args:
        number: Trikot nummer
        name: Spillernavn
        team: Hold (hvis kendt)
        
    Returns:
        str: Unik spillernøgle
    """
    if team:
        return f"{team}_{number}_{name}"
    return f"{number}_{name}"

def calculate_rating_change(event_type, is_goalkeeper, game_importance=1.0):
    """
    Beregner ændring i Elo-rating baseret på hændelsestype og spillerrolle
    
    Args:
        event_type: Type af hændelse
        is_goalkeeper: Om spilleren er målvogter
        game_importance: Faktor for kampens vigtighed
        
    Returns:
        float: Ændring i Elo-rating
    """
    # Find den rette vægt baseret på hændelsestype og spillerrolle
    if is_goalkeeper and event_type in GOALKEEPER_WEIGHTS:
        weight = GOALKEEPER_WEIGHTS[event_type]
    elif event_type in EVENT_WEIGHTS:
        weight = EVENT_WEIGHTS[event_type]
    else:
        weight = 0.0  # Hændelse uden vægt
    
    # Beregn ratingændring (en brøkdel af K baseret på hændelsens vægt)
    normalized_weight = weight / 10.0  # Normaliserer til ca. -1.0 til 1.0
    rating_change = K_FACTOR * normalized_weight * game_importance
    
    return rating_change

def process_primary_events(cursor, player_ratings, player_history, match_id, match_date, goalkeepers):
    """
    Behandler primære hændelser (haendelse_1) for alle spillere
    
    Args:
        cursor: Database cursor
        player_ratings: Dict med aktuelle ratings
        player_history: Dict med historik
        match_id: Kamp-ID
        match_date: Kampdato
        goalkeepers: Set af målvogtere
    """
    try:
        # Hent alle primære hændelser med spiller
        cursor.execute("""
            SELECT id, hold, haendelse_1, nr_1, navn_1, maal
            FROM match_events 
            WHERE haendelse_1 IS NOT NULL 
              AND nr_1 IS NOT NULL AND nr_1 > 0 
              AND navn_1 IS NOT NULL AND navn_1 != ''
        """)
        
        for event_id, team, event_type, number, name, score in cursor.fetchall():
            # Spring over hvis det er en hændelse uden spiller (f.eks. halvleg)
            if event_type in ['Video Proof', 'Video Proof slut', 'Halvleg', 'Start 1:e halvleg', 'Start 2:e halvleg']:
                continue
                
            # Generer spillernøgle
            player_key = get_player_key(number, name, team)
            
            # Tjek om spilleren er målvogter
            is_goalkeeper = (number, name) in goalkeepers
            
            # Beregn rating ændring
            rating_change = calculate_rating_change(event_type, is_goalkeeper)
            
            # Hvis spilleren ikke allerede er i systemet, tilføj dem
            if player_key not in player_ratings:
                player_ratings[player_key] = BASE_ELO
                player_history[player_key] = []
            
            # Opdater spillerens rating
            old_rating = player_ratings[player_key]
            player_ratings[player_key] += rating_change
            
            # Registrer denne ændring i historik
            player_history[player_key].append({
                'match_id': match_id,
                'date': match_date,
                'event_id': event_id,
                'event_type': event_type,
                'rating_change': rating_change,
                'old_rating': old_rating,
                'new_rating': player_ratings[player_key],
                'score': score
            })
            
    except sqlite3.Error as e:
        print(f"Fejl ved behandling af primære hændelser: {e}")

def process_secondary_events(cursor, player_ratings, player_history, match_id, match_date, goalkeepers):
    """
    Behandler sekundære hændelser (haendelse_2) for alle spillere
    
    Args:
        cursor: Database cursor
        player_ratings: Dict med aktuelle ratings
        player_history: Dict med historik
        match_id: Kamp-ID
        match_date: Kampdato
        goalkeepers: Set af målvogtere
    """
    try:
        # Hent alle sekundære hændelser med spiller
        cursor.execute("""
            SELECT id, hold, haendelse_2, nr_2, navn_2, maal
            FROM match_events 
            WHERE haendelse_2 IS NOT NULL 
              AND nr_2 IS NOT NULL AND nr_2 > 0 
              AND navn_2 IS NOT NULL AND navn_2 != ''
        """)
        
        for event_id, team, event_type, number, name, score in cursor.fetchall():
            # Generer spillernøgle
            player_key = get_player_key(number, name, team)
            
            # Tjek om spilleren er målvogter
            is_goalkeeper = (number, name) in goalkeepers
            
            # Beregn rating ændring
            rating_change = calculate_rating_change(event_type, is_goalkeeper)
            
            # Hvis spilleren ikke allerede er i systemet, tilføj dem
            if player_key not in player_ratings:
                player_ratings[player_key] = BASE_ELO
                player_history[player_key] = []
            
            # Opdater spillerens rating
            old_rating = player_ratings[player_key]
            player_ratings[player_key] += rating_change
            
            # Registrer denne ændring i historik
            player_history[player_key].append({
                'match_id': match_id,
                'date': match_date,
                'event_id': event_id,
                'event_type': event_type,
                'rating_change': rating_change,
                'old_rating': old_rating,
                'new_rating': player_ratings[player_key],
                'score': score
            })
            
    except sqlite3.Error as e:
        print(f"Fejl ved behandling af sekundære hændelser: {e}")

def process_goalkeeper_events(cursor, player_ratings, player_history, match_id, match_date, goalkeepers):
    """
    Behandler målvogterhændelser (nr_mv, mv) for alle målvogtere
    
    Args:
        cursor: Database cursor
        player_ratings: Dict med aktuelle ratings
        player_history: Dict med historik
        match_id: Kamp-ID
        match_date: Kampdato
        goalkeepers: Set af målvogtere
    """
    try:
        # Hent alle hændelser med målvogter
        cursor.execute("""
            SELECT id, hold, haendelse_1, nr_mv, mv, maal
            FROM match_events 
            WHERE nr_mv IS NOT NULL AND nr_mv > 0 
              AND mv IS NOT NULL AND mv != ''
              AND haendelse_1 IN ('Mål', 'Skud reddet', 'Skud forbi', 'Skud på stolpe', 
                                'Mål på straffe', 'Straffekast reddet')
        """)
        
        for event_id, team, event_type, number, name, score in cursor.fetchall():
            # Generer spillernøgle for målvogteren
            # OBS: Her bruger vi ikke team direkte, da målvogteren er på det modsatte hold
            player_key = get_player_key(number, name)
            
            # Beregn rating ændring - altid målvogterspecifik
            rating_change = calculate_rating_change(event_type, True)
            
            # Hvis målvogteren ikke allerede er i systemet, tilføj dem
            if player_key not in player_ratings:
                player_ratings[player_key] = BASE_ELO
                player_history[player_key] = []
            
            # Opdater målvogterens rating
            old_rating = player_ratings[player_key]
            player_ratings[player_key] += rating_change
            
            # Registrer denne ændring i historik
            player_history[player_key].append({
                'match_id': match_id,
                'date': match_date,
                'event_id': event_id,
                'event_type': event_type,
                'rating_change': rating_change,
                'old_rating': old_rating,
                'new_rating': player_ratings[player_key],
                'score': score
            })
            
    except sqlite3.Error as e:
        print(f"Fejl ved behandling af målvogterhændelser: {e}")

def process_game(db_file, player_ratings, player_history):
    """
    Behandler en enkelt kamp og opdaterer alle spillerratings
    
    Args:
        db_file: Sti til databasefil
        player_ratings: Dict med aktuelle ratings
        player_history: Dict med historik
        
    Returns:
        bool: True hvis behandlingen var succesfuld
    """
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Hent kamp-ID og dato
        cursor.execute("SELECT kamp_id, dato FROM match_info")
        result = cursor.fetchone()
        if not result:
            print(f"Ingen kamp-information fundet i {db_file}")
            conn.close()
            return False
        
        match_id, date_str = result
        match_date = parse_date(date_str)
        
        print(f"Behandler kamp {match_id} fra {date_str}...")
        
        # Identificér målvogtere
        goalkeepers = identify_goalkeepers(conn)
        print(f"Fandt {len(goalkeepers)} målvogtere")
        
        # Behandl hændelser
        process_primary_events(cursor, player_ratings, player_history, match_id, match_date, goalkeepers)
        process_secondary_events(cursor, player_ratings, player_history, match_id, match_date, goalkeepers)
        process_goalkeeper_events(cursor, player_ratings, player_history, match_id, match_date, goalkeepers)
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Fejl ved behandling af kamp {db_file}: {e}")
        return False

def create_player_rating_table(player_history):
    """
    Opretter en tabel med spillerratings efter hver kamp
    
    Args:
        player_history: Dict med historik
        
    Returns:
        DataFrame: Tabel med spillerratings
    """
    # Saml alle kampe og datoer
    all_matches = set()
    for player, events in player_history.items():
        for event in events:
            if 'match_id' in event and 'date' in event and event['date']:
                all_matches.add((event['match_id'], event['date']))
    
    # Sortér kampe kronologisk
    sorted_matches = sorted(all_matches, key=lambda x: x[1])
    
    if not sorted_matches:
        print("Advarsel: Ingen kampe fundet til at generere ratingtabel")
        return pd.DataFrame()
    
    # Opret tabel
    rating_data = []
    
    for player, events in player_history.items():
        # Gruppér events efter kamp
        matches = {}
        for event in events:
            if 'match_id' in event:
                match_id = event['match_id']
                if match_id not in matches:
                    matches[match_id] = []
                matches[match_id].append(event)
        
        # Find slutrating for hver kamp
        current_rating = BASE_ELO
        player_row = {'player': player}
        
        for match_id, date in sorted_matches:
            if match_id in matches:
                # Sortér events efter event_id for at sikre korrekt rækkefølge
                match_events = sorted(matches[match_id], key=lambda x: x['event_id'])
                # Brug den sidste nye rating fra kampen
                current_rating = match_events[-1]['new_rating']
            
            # Gem rating for denne kamp
            player_row[match_id] = current_rating
        
        rating_data.append(player_row)
    
    return pd.DataFrame(rating_data)

def plot_player_rating(player_key, player_history, output_dir):
    """
    Plotter udviklingen i en spillers Elo-rating over tid
    
    Args:
        player_key: Nøgle for spilleren
        player_history: Dict med historik
        output_dir: Sti til output-mappen
    """
    if player_key not in player_history:
        print(f"Ingen historik fundet for spiller {player_key}")
        return
    
    events = player_history[player_key]
    
    # Sortér events efter dato
    sorted_events = [e for e in events if 'date' in e and e['date']]
    sorted_events = sorted(sorted_events, key=lambda x: x['date'])
    
    if not sorted_events:
        print(f"Ingen daterede hændelser for spiller {player_key}")
        return
    
    # Gruppér events efter kamp og find slutrating for hver kamp
    match_ratings = {}
    dates = []
    ratings = []
    
    # Saml sidste rating fra hver unik kamp
    for match_id in set(event['match_id'] for event in sorted_events if 'match_id' in event):
        match_events = [e for e in sorted_events if 'match_id' in e and e['match_id'] == match_id]
        if match_events:
            # Sortér efter event_id og tag den sidste rating for denne kamp
            last_event = sorted(match_events, key=lambda x: x['event_id'])[-1]
            dates.append(last_event['date'])
            ratings.append(last_event['new_rating'])
    
    # Sortér på dato for at sikre korrekt rækkefølge
    date_ratings = sorted(zip(dates, ratings), key=lambda x: x[0])
    dates = [dr[0] for dr in date_ratings]
    ratings = [dr[1] for dr in date_ratings]
    
    # Plot data
    plt.figure(figsize=(12, 6))
    plt.plot(dates, ratings, marker='o', linestyle='-', linewidth=2)
    
    # Formater navnet til visning uden koder
    display_name = player_key.split('_', 1)[-1] if '_' in player_key else player_key
    plt.title(f"Elo Rating Udvikling for {display_name}")
    
    plt.xlabel("Dato")
    plt.ylabel("Elo Rating")
    plt.grid(True)
    plt.tight_layout()
    
    # Gem plot som fil
    os.makedirs(output_dir, exist_ok=True)
    safe_filename = player_key.replace("/", "_").replace("\\", "_").replace(" ", "_")
    plt.savefig(os.path.join(output_dir, f"{safe_filename}_rating.png"))
    plt.close()

def process_league(liga_name, sæson):
    """
    Behandler en enkelt liga
    
    Args:
        liga_name: Navn på liga ('herreliga' eller 'kvindeliga')
        sæson: Sæson
        
    Returns:
        tuple: (player_ratings, player_history) for denne liga
    """
    # Få information om ligaen
    db_dir, output_dir, display_name = get_liga_info(liga_name, sæson)
    
    print(f"\n=== Håndboldhændelser Elo Rating System - {display_name} ===")
    print(f"Behandler data fra: {db_dir}")
    print(f"Resultater gemmes i: {output_dir}")
    
    # Find alle databasefiler
    db_files = find_database_files(db_dir)
    if not db_files:
        print(f"Ingen databasefiler fundet for {display_name}.")
        return {}, {}
    
    print(f"Fandt {len(db_files)} kampdatabaser")
    
    # Sortér kampe efter dato
    games_by_date = sort_games_by_date(db_files)
    if not games_by_date:
        print(f"Ingen kampe med gyldige datoer fundet for {display_name}")
        return {}, {}
    
    print(f"Sorterede {len(games_by_date)} kampe kronologisk")
    
    # Initialiser dictionaries til at holde styr på spillerratings og historik
    player_ratings = {}  # player_key -> current_rating
    player_history = {}  # player_key -> [list of rating changes]
    
    # Behandl hver kamp i kronologisk rækkefølge
    successful_games = 0
    for db_file, date in games_by_date:
        print(f"\nBehandler kamp fra {date.strftime('%d-%m-%Y')}: {os.path.basename(db_file)}")
        if process_game(db_file, player_ratings, player_history):
            successful_games += 1
    
    print(f"\nBehandlede {successful_games} af {len(games_by_date)} kampe succesfuldt")
    print(f"Registrerede {len(player_ratings)} spillere med Elo-ratings")
    
    # Opret output-mappe
    os.makedirs(output_dir, exist_ok=True)
    
    # Gem slutresultater
    with open(os.path.join(output_dir, "final_ratings.csv"), 'w', encoding='utf-8') as f:
        f.write("Player,FinalRating\n")
        for player, rating in sorted(player_ratings.items(), key=lambda x: x[1], reverse=True):
            f.write(f"{player},{rating:.2f}\n")
    
    # Opret tabel med ratings efter hver kamp
    rating_table = create_player_rating_table(player_history)
    if not rating_table.empty:
        rating_table.to_csv(os.path.join(output_dir, "rating_history.csv"), index=False)
    
    # Plot udvikling for top-10 spillere baseret på slutrating
    top_players = sorted(player_ratings.items(), key=lambda x: x[1], reverse=True)[:10]
    for player, rating in top_players:
        print(f"Plotter rating-udvikling for {player} (Rating: {rating:.2f})")
        plot_player_rating(player, player_history, output_dir)
    
    print(f"\nAlle resultater er gemt i mappen '{output_dir}'")
    
    return player_ratings, player_history

def main():
    """
    Hovedfunktion der behandler alle kampe og beregner Elo-ratings
    """
    # Parse argumenter
    args = parse_arguments()
    
    print("=== Håndboldhændelser Elo Rating System ===")
    print(f"Valgt liga: {args.liga}")
    print(f"Valgt sæson: {args.saeson}")
    
    if args.liga == 'herreliga' or args.liga == 'begge':
        # Behandl herreligaen
        process_league('herreliga', args.saeson)
    
    if args.liga == 'kvindeliga' or args.liga == 'begge':
        # Behandl kvindeligaen
        process_league('kvindeliga', args.saeson)
    
    print("\nBehandling afsluttet.")

if __name__ == "__main__":
    main()