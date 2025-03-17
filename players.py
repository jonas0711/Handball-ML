#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Håndboldspiller-ekstrakter (Endelig version med understøttelse af flere spillere per nummer)

Dette script gennemgår alle SQLite-databasefiler i Kvindeliga-database-mappen
og udtrækker information om alle spillere, sorteret efter hold.

Scriptet håndterer:
1. Forhåndsdefineret kortlægning af holdkoder til hold
2. Korrekt identificering af spillere på hvert hold
3. Understøttelse af flere spillere med samme nummer på samme hold
"""

import os
import sqlite3
import glob
from collections import defaultdict

# Liste over værdier der ikke er spillernavne
NOT_PLAYER_NAMES = ["Retur", "Bold erobret", "Assist", "Blokeret af", "Blok af (ret)", "Forårs. str."]

# Hændelser hvor nr_2/navn_2 tilhører det MODSATTE hold af 'hold'
OPPOSITE_TEAM_EVENTS = ["Bold erobret", "Forårs. str.", "Blokeret af", "Blok af (ret)"]

# Hændelser hvor nr_2/navn_2 tilhører SAMME hold som 'hold'
SAME_TEAM_EVENTS = ["Assist"]

# Fast kortlægning af holdkoder til holdnavne baseret på den korrekte liste
TEAM_CODE_MAP = {
    "AHB": "Aarhus Håndbold Kvinder",
    "BFH": "Bjerringbro FH",
    "EHA": "EH Aalborg",
    "HHE": "Horsens Håndbold Elite",
    "IKA": "Ikast Håndbold",
    "KBH": "København Håndbold",
    "NFH": "Nykøbing F. Håndbold",
    "ODE": "Odense Håndbold",
    "RIN": "Ringkøbing Håndbold",
    "SVK": "Silkeborg-Voel KFUM",
    "SKB": "Skanderborg Håndbold",
    "SJE": "SønderjyskE Kvindehåndbold",
    "TES": "Team Esbjerg",
    "VHK": "Viborg HK",
    "TMS": "TMS Ringsted"  # Tilføjet baseret på information
}

# Kombinér mulige varianter af holdnavne (til normalisering)
TEAM_NAME_VARIANTS = {
    "Silkeborg-Voel KFUM": ["Silkeborg-Voel KFUM", "Voel KFUM", "Silkeborg Voel", "Silkeborg-Voel"]
}

def normalize_team_name(team_name):
    """
    Normaliserer et holdnavn til den kanoniske form
    """
    for canonical, variants in TEAM_NAME_VARIANTS.items():
        if team_name in variants:
            return canonical
    return team_name

def extract_players_from_database(db_path):
    """
    Udtrækker spillerinformation fra en enkelt database-fil.
    
    Args:
        db_path: Sti til databasefilen
    
    Returns:
        dict: Ordbog med kamp- og spillerinformation
    """
    # Opret forbindelse til databasen
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Udtrække kampinformation
    cursor.execute("SELECT kamp_id, hold_hjemme, hold_ude, dato FROM match_info")
    match_info = cursor.fetchone()
    
    if not match_info:
        print(f"Ingen kampinfo fundet i {os.path.basename(db_path)}")
        conn.close()
        return None
    
    kamp_id, hold_hjemme, hold_ude, kamp_dato = match_info
    
    # Normaliser holdnavne
    hold_hjemme = normalize_team_name(hold_hjemme)
    hold_ude = normalize_team_name(hold_ude)
    
    # Opret tomme dictionaries til at spore spillere for hvert hold
    # Brug en dictionary af sets for at undgå duplikater
    team_players = {
        hold_hjemme: defaultdict(set),
        hold_ude: defaultdict(set)
    }
    
    # Find alle unikke holdkoder i kampen
    cursor.execute("SELECT DISTINCT hold FROM match_events WHERE hold IS NOT NULL")
    team_codes = [row[0] for row in cursor.fetchall()]
    
    # Find ud af, hvilke holdkoder der svarer til hvilke hold i denne kamp
    match_team_codes = {}
    
    # Koble holdkoder med hold baseret på vores faste kortlægning
    for code in team_codes:
        if code in TEAM_CODE_MAP:
            team_name = TEAM_CODE_MAP[code]
            
            # Tjek om dette hold er et af holdene i kampen
            if team_name == hold_hjemme or team_name == hold_ude:
                match_team_codes[code] = team_name
    
    # Hvis vi ikke kunne bestemme alle koder, prøv at tildele dem baseret på mål
    if len(match_team_codes) < len(team_codes):
        unassigned_codes = [code for code in team_codes if code not in match_team_codes]
        
        if len(unassigned_codes) > 0 and len(match_team_codes) > 0:
            # Find hold, der endnu ikke har en kode
            assigned_teams = set(match_team_codes.values())
            unassigned_teams = []
            if hold_hjemme not in assigned_teams:
                unassigned_teams.append(hold_hjemme)
            if hold_ude not in assigned_teams:
                unassigned_teams.append(hold_ude)
            
            # Tæl mål for hver uassigneret holdkode
            code_goals = {}
            for code in unassigned_codes:
                cursor.execute("""
                SELECT COUNT(*) FROM match_events 
                WHERE hold = ? AND (haendelse_1 = 'Mål' OR haendelse_1 = 'Mål på straffe')
                """, (code,))
                goals = cursor.fetchone()[0]
                code_goals[code] = goals
            
            # Sortér koder efter antal mål
            sorted_codes = sorted(code_goals.items(), key=lambda x: x[1], reverse=True)
            
            # Tildel koder til hold
            if len(sorted_codes) > 0 and len(unassigned_teams) > 0:
                if len(sorted_codes) >= len(unassigned_teams):
                    for i, team in enumerate(unassigned_teams):
                        match_team_codes[sorted_codes[i][0]] = team
    
    print(f"Kamp: {hold_hjemme} vs {hold_ude} (ID: {kamp_id}, Dato: {kamp_dato})")
    print(f"Holdkoder i kamp: {match_team_codes}")
    
    # Hvis vi stadig ikke har holdkoder for begge hold, kan vi ikke fortsætte
    if len(match_team_codes) < 1:
        print(f"ADVARSEL: Kunne ikke identificere holdkoder. Springer over {os.path.basename(db_path)}")
        conn.close()
        return None
    
    # Opret en omvendt kortlægning fra hold til kode
    team_to_code = {team: code for code, team in match_team_codes.items()}
    
    # Hjælpefunktion til at få det modsatte hold
    def get_opposite_team(team_code):
        team = match_team_codes.get(team_code)
        if team == hold_hjemme:
            return hold_ude
        elif team == hold_ude:
            return hold_hjemme
        return None
    
    # 1. Udtrække spillere fra primære hændelser (nr_1, navn_1)
    cursor.execute("""
    SELECT hold, nr_1, navn_1, haendelse_1 FROM match_events 
    WHERE hold IS NOT NULL 
      AND nr_1 IS NOT NULL AND nr_1 > 0 
      AND navn_1 IS NOT NULL AND navn_1 != ''
      AND haendelse_1 NOT IN ('Video Proof', 'Video Proof slut', 'Halvleg', 'Start 1:e halvleg', 'Start 2:e halvleg')
    """)
    
    for team_code, player_number, player_name, event in cursor.fetchall():
        if team_code in match_team_codes and player_name not in NOT_PLAYER_NAMES:
            team_name = match_team_codes[team_code]
            team_players[team_name][int(player_number)].add(player_name)
    
    # 2. Udtrække spillere fra sekundære hændelser (nr_2, navn_2)
    cursor.execute("""
    SELECT hold, nr_2, navn_2, haendelse_2 FROM match_events 
    WHERE hold IS NOT NULL 
      AND nr_2 IS NOT NULL AND nr_2 > 0 
      AND navn_2 IS NOT NULL AND navn_2 != '' 
      AND haendelse_2 IS NOT NULL
    """)
    
    for team_code, player_number, player_name, event in cursor.fetchall():
        if team_code in match_team_codes and player_name not in NOT_PLAYER_NAMES:
            # Bestem hvilket hold spilleren tilhører baseret på hændelsestypen
            if event in OPPOSITE_TEAM_EVENTS:
                # Spilleren tilhører det modsatte hold
                team_name = get_opposite_team(team_code)
            elif event in SAME_TEAM_EVENTS:
                # Spilleren tilhører samme hold
                team_name = match_team_codes[team_code]
            else:
                # For ukendte hændelser, antag samme hold
                team_name = match_team_codes[team_code]
            
            if team_name:
                team_players[team_name][int(player_number)].add(player_name)
    
    # 3. Udtrække målvogtere (nr_mv, mv) - de tilhører det MODSATTE hold
    maal_relaterede_haendelser = ['Mål', 'Skud reddet', 'Skud forbi', 'Skud på stolpe', 'Mål på straffe', 'Straffekast reddet']
    
    cursor.execute("""
    SELECT hold, nr_mv, mv, haendelse_1 FROM match_events 
    WHERE hold IS NOT NULL 
      AND nr_mv IS NOT NULL AND nr_mv > 0
      AND mv IS NOT NULL AND mv != ''
      AND haendelse_1 IN ('Mål', 'Skud reddet', 'Skud forbi', 'Skud på stolpe', 'Mål på straffe', 'Straffekast reddet')
    """)
    
    for team_code, player_number, player_name, event in cursor.fetchall():
        if team_code in match_team_codes:
            # Målvogteren tilhører det MODSATTE hold
            opposite_team = get_opposite_team(team_code)
            if opposite_team:
                team_players[opposite_team][int(player_number)].add(player_name)
    
    conn.close()
    
    # Sammensæt resultatet
    result = {
        'kamp_id': kamp_id,
        'hold_hjemme': hold_hjemme,
        'hold_ude': hold_ude,
        'dato': kamp_dato,
        'team_players': team_players,
        'team_codes': match_team_codes
    }
    
    return result

def main():
    # Sti til databasefiler
    db_dir = r"C:\Users\jonas\Desktop\Handball-ML\Kvindeliga-database\2024-2025"
    db_files = glob.glob(os.path.join(db_dir, "*.db"))
    
    if not db_files:
        print(f"Ingen databasefiler fundet i {db_dir}")
        return
    
    # Ordbog til at gemme information om hvert hold
    all_teams = {}  # hold_navn -> {spiller_nr -> set(spiller_navne)}
    team_match_counts = defaultdict(int)  # hold_navn -> antal kampe
    team_match_dates = defaultdict(set)  # hold_navn -> set(kamp_datoer)
    
    print(f"Behandler {len(db_files)} databasefiler...")
    
    for i, db_file in enumerate(db_files):
        print(f"\nBehandler fil {i+1}/{len(db_files)}: {os.path.basename(db_file)}...")
        result = extract_players_from_database(db_file)
        
        if result:
            # Opdater antal kampe og datoer
            team_match_counts[result['hold_hjemme']] += 1
            team_match_counts[result['hold_ude']] += 1
            if result['dato']:
                team_match_dates[result['hold_hjemme']].add(result['dato'])
                team_match_dates[result['hold_ude']].add(result['dato'])
            
            # Opdater spillerinformation
            for team, players in result['team_players'].items():
                if team not in all_teams:
                    all_teams[team] = defaultdict(set)
                for number, names in players.items():
                    all_teams[team][number].update(names)
    
    # Oprette output-mappe
    output_dir = os.path.join(db_dir, "players")
    os.makedirs(output_dir, exist_ok=True)
    
    # Oprette samlet filtreret spillerliste
    player_count_file = os.path.join(output_dir, "_holdstatistik.txt")
    with open(player_count_file, 'w', encoding='utf-8') as f:
        f.write("=== HOLDSTATISTIK ===\n\n")
        f.write("Hold | Antal spillere | Antal kampe | Holdkode | Forskellige numre\n")
        f.write("-" * 90 + "\n")
        
        # Find holdkoden for hvert hold ud fra det omvendte TEAM_CODE_MAP
        reversed_code_map = {value: key for key, value in TEAM_CODE_MAP.items()}
        
        for team in sorted(all_teams.keys()):
            # Tæl det totale antal unikke spillere (sammenlagt på tværs af alle numre)
            all_players = set()
            for player_set in all_teams[team].values():
                all_players.update(player_set)
            
            player_count = len(all_players)
            number_count = len(all_teams[team])  # Antal forskellige numre
            match_count = team_match_counts[team]
            code = reversed_code_map.get(team, "N/A")
            f.write(f"{team:30} | {player_count:14} | {match_count:11} | {code:8} | {number_count}\n")
    
    # Oprette også en CSV-fil med samme information (for lettere databehandling)
    csv_file = os.path.join(output_dir, "_holdstatistik.csv")
    with open(csv_file, 'w', encoding='utf-8') as f:
        f.write("Hold,AntalSpillere,AntalKampe,Holdkode,ForskNumre,FoersteKamp,SidsteKamp\n")
        
        # Find holdkoden for hvert hold ud fra det omvendte TEAM_CODE_MAP
        reversed_code_map = {value: key for key, value in TEAM_CODE_MAP.items()}
        
        for team in sorted(all_teams.keys()):
            # Tæl det totale antal unikke spillere (sammenlagt på tværs af alle numre)
            all_players = set()
            for player_set in all_teams[team].values():
                all_players.update(player_set)
            
            player_count = len(all_players)
            number_count = len(all_teams[team])  # Antal forskellige numre
            match_count = team_match_counts[team]
            code = reversed_code_map.get(team, "N/A")
            
            # Find først og sidste kampdato
            first_date = min(team_match_dates[team]) if team_match_dates[team] else "N/A"
            last_date = max(team_match_dates[team]) if team_match_dates[team] else "N/A"
            
            f.write(f"{team},{player_count},{match_count},{code},{number_count},{first_date},{last_date}\n")
    
    # Skriv til fil og udskriv til terminal
    for team in sorted(all_teams.keys()):
        # Opret et gyldigt filnavn
        team_filename = "".join(c if c.isalnum() or c in [' ', '_', '-'] else '_' for c in team)
        output_file = os.path.join(output_dir, f"{team_filename}.txt")
        
        # Find holdkoden for dette hold
        team_code = "N/A"
        for code, name in TEAM_CODE_MAP.items():
            if name == team:
                team_code = code
                break
        
        # Hent spillerliste
        players = all_teams[team]
        
        # Tæl det totale antal unikke spillere
        all_player_names = set()
        for player_set in players.values():
            all_player_names.update(player_set)
        
        # Skriv til fil
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Spillere for {team}\n")
            f.write(f"Antal kampe: {team_match_counts[team]}\n")
            f.write(f"Holdkode: {team_code}\n")
            f.write(f"Antal unikke spillere: {len(all_player_names)}\n")
            f.write("=" * 60 + "\n")
            f.write("Nummer | Antal | Spillernavn(e)\n")
            f.write("-" * 60 + "\n")
            
            for nr in sorted(players.keys()):
                names = sorted(players[nr])
                if len(names) == 1:
                    # Kun én spiller med dette nummer
                    f.write(f"{nr:6} |   1   | {names[0]}\n")
                else:
                    # Flere spillere med samme nummer - vis antal og alle navne
                    f.write(f"{nr:6} |   {len(names)}   | {names[0]}\n")
                    for name in names[1:]:
                        f.write(f"       |       | {name}\n")
        
        # Skriv også til CSV for lettere databehandling
        csv_output_file = os.path.join(output_dir, f"{team_filename}.csv")
        with open(csv_output_file, 'w', encoding='utf-8') as f:
            f.write("Nummer,Navn\n")
            for nr in sorted(players.keys()):
                names = sorted(players[nr])
                for name in names:
                    # Sørg for at håndtere kommaer i navne ved at indsætte i citationstegn
                    player_name = f'"{name}"' if ',' in name else name
                    f.write(f"{nr},{player_name}\n")
        
        # Udskriv til terminal
        print(f"\nSpillere for {team}:")
        print(f"Antal kampe: {team_match_counts[team]}")
        print(f"Holdkode: {team_code}")
        print(f"Antal unikke spillere: {len(all_player_names)}")
        print("=" * 60)
        print("Nummer | Antal | Spillernavn(e)")
        print("-" * 60)
        
        for nr in sorted(players.keys()):
            names = sorted(players[nr])
            if len(names) == 1:
                print(f"{nr:6} |   1   | {names[0]}")
            else:
                print(f"{nr:6} |   {len(names)}   | {names[0]}")
                for name in names[1:]:
                    print(f"       |       | {name}")
        
        print(f"\nTotal antal unikke spillere: {len(all_player_names)}")
        print(f"Total antal forskellige numre: {len(players)}")
        print(f"Gemt til {output_file} og {csv_output_file}")
    
    print(f"\nSamlet holdstatistik gemt til {player_count_file} og {csv_file}")

if __name__ == "__main__":
    main()