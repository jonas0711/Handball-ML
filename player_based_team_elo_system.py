#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 SPILLERBASERET HOLD ELO SYSTEM
=================================

BYGGER HOLD RATINGS BASERET PÅ SPILLERNES INDIVIDUELLE RATINGS:
✅ Spillere tilknyttes hold baseret på flest kampe i sæsonen
✅ Hold rating beregnes fra spillernes ELO ratings
✅ Forskellige beregningsmetoder: gennemsnit, top 7, top 12, bedste pr. position
✅ Sæson-for-sæson processering med transfers/skift
✅ Bruger team mappings fra eksisterende team ELO systemer
✅ Genererer detaljerede CSV rapporter
✅ Både Herreliga og Kvindeliga support

BEREGNINGSMETODER FOR HOLD RATING:
1. Team Average Rating - Gennemsnit af alle spillere
2. Top 7 Players Rating - Gennemsnit af de 7 bedste spillere
3. Top 12 Players Rating - Gennemsnit af de 12 bedste spillere
4. Best Position Average - Bedste spiller fra hver position gennemsnit
5. Weighted Position Average - Positionsvægtet gennemsnit
6. Playing Time Weighted - Vægtet efter spilletid

Jonas' Custom System - December 2024
"""

import pandas as pd
import numpy as np
import sqlite3
import os
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# === SYSTEM PARAMETRE ===
MIN_GAMES_FOR_TEAM_INCLUSION = 3    # Mindst 3 kampe for at tælle med på holdet
MIN_PLAYERS_FOR_TEAM_RATING = 5     # Mindst 5 spillere for at beregne hold rating

# VÆGTNINGSFAKTORER FOR POSITIONER
POSITION_WEIGHTS = {
    'MV': 1.2,   # Målvogter - vigtigste position
    'PL': 1.15,  # Playmaker - meget vigtig
    'ST': 1.1,   # Streg - scorende position
    'VF': 1.0,   # Venstre fløj
    'HF': 1.0,   # Højre fløj  
    'VB': 0.95,  # Venstre back
    'HB': 0.95   # Højre back
}

# === TEAM MAPPINGS ===
# Extended team mappings from existing team ELO systems

# Teams to skip during processing (problematic or invalid codes)
SKIP_TEAMS = {
    'UNKNOWN',  # Generic unknown team entries
    'NULL',     # Null entries
    'N/A',      # Not applicable entries
    'HIH',      # Unknown team code appearing in older data
    'OHC',      # Unknown team code appearing in older data  
    'RHK'       # Unknown team code appearing in older data
}

# Herreliga team mappings - FIXED: SJE removed, separate codes added
HERRELIGA_TEAMS = {
    'AAH': 'Aalborg Håndbold',
    'BSH': 'Bjerringbro-Silkeborg',
    'FHK': 'Fredericia Håndbold Klub',
    'GIF': 'Grindsted GIF Håndbold',
    'GOG': 'GOG',
    'KIF': 'KIF Kolding',
    'MTH': 'Mors-Thy Håndbold',
    'NSH': 'Nordsjælland Håndbold',
    'REH': 'Ribe-Esbjerg HH',
    'SAH': 'SAH - Skanderborg AGF',
    'SKH': 'Skjern Håndbold',
    'SJH': 'SønderjyskE Herrehåndbold',    # FIXED: New code for men's team
    'TTH': 'TTH Holstebro',
    'TMH': 'TMS Ringsted',                # FIXED: New code for men's team
    'LTH': 'Lemvig-Thyborøn Håndbold',
    'ARH': 'Århus Håndbold',
    'SKI': 'Skive fH',
    'AJH': 'Ajax København',              # FIXED: New code for men's team
    'HØJ': 'HØJ Elite',
    'HCM': 'HC Midtjylland',
    'TSY': 'Team Sydhavsøerne',
    'TMT': 'TM Tønder Håndbold',
    # NEW MAPPINGS FOR UNMAPPED TEAMS
    'AAU': 'Aalborg Universitet Håndbold',  # Aalborg Universitet
    'AJX': 'Ajax København',                # Ajax København (forkortelse)
    'SFH': 'Silkeborg fH',                  # Silkeborg fH
    'VF': 'Vendsyssel F',                   # Vendsyssel F (forkortelse)
}

# Kvindeliga team mappings - FIXED: SJE changed to SJK, separate codes added
KVINDELIGA_TEAMS = {
    'AHB': 'Aarhus Håndbold Kvinder',
    'BFH': 'Bjerringbro FH',
    'EHA': 'EH Aalborg',
    'HHE': 'Horsens Håndbold Elite',
    'IKA': 'Ikast Håndbold',
    'KBH': 'København Håndbold',
    'NFH': 'Nykøbing F. Håndbold',
    'ODE': 'Odense Håndbold',
    'RIN': 'Ringkøbing Håndbold',
    'SVK': 'Silkeborg-Voel KFUM',
    'SKB': 'Skanderborg Håndbold',
    'SJK': 'SønderjyskE Kvindehåndbold',    # FIXED: New code for women's team
    'TES': 'Team Esbjerg',
    'VHK': 'Viborg HK',
    'TMK': 'TMS Ringsted',                 # FIXED: New code for women's team
    'VEN': 'Vendsyssel Håndbold',
    'RAN': 'Randers HK',
    'HOL': 'Holstebro Håndbold',
    'AJK': 'Ajax København',               # FIXED: New code for women's team
    # NEW MAPPINGS FOR UNMAPPED TEAMS
    'AAU': 'Aalborg Universitet Håndbold',  # Aalborg Universitet
    'SFH': 'Silkeborg fH',                  # Silkeborg fH  
    'VF': 'Vendsyssel F',                   # Vendsyssel F (forkortelse)
}

# Combined teams dictionary for lookup
ALL_TEAMS = {**HERRELIGA_TEAMS, **KVINDELIGA_TEAMS}

# EXTENSIVE TEAM NAME MAPPINGS for database analysis
TEAM_NAME_MAPPINGS = {
    # === HERRELIGA MAPPINGS ===
    # Aalborg variationer
    'aalborg håndbold': 'AAH',
    'aalborg': 'AAH',
    'aalborg universitet håndbold': 'AAU',    # NEW: Aalborg Universitet
    'aalborg universitet': 'AAU',             # NEW
    'aau håndbold': 'AAU',                    # NEW
    
    # Ajax variationer - FIXED: Gender-specific mappings
    'ajax københavn': 'AJH',                 # Default to men's team
    'ajax': 'AJH',                           # Default to men's team
    'ajx': 'AJX',                            # NEW: Ajax forkortelse
    'ajax kvindehåndbold': 'AJK',            # FIXED: Women's team
    'ajax kvinder': 'AJK',                   # FIXED: Women's team
    'ajax kbh kvinder': 'AJK',               # FIXED: Women's team
    'ajax københavn kvinder': 'AJK',         # FIXED: Women's team
    
    # Bjerringbro-Silkeborg variationer
    'bjerringbro-silkeborg': 'BSH',
    'bjerringbro silkeborg': 'BSH',
    
    # Fredericia variationer
    'fredericia hk': 'FHK',
    'fredericia håndbold klub': 'FHK',
    'fredericia håndboldklub': 'FHK',
    'fredericia': 'FHK',
    
    # Grindsted variationer
    'grindsted gif håndbold': 'GIF',
    'grindsted gif, håndbold': 'GIF',
    'grindsted gif': 'GIF',
    'grindsted': 'GIF',
    
    # GOG
    'gog': 'GOG',
    
    # KIF Kolding variationer
    'kif kolding': 'KIF',
    'kif kolding københavn': 'KIF',
    'kif': 'KIF',
    
    # Mors-Thy Håndbold
    'mors-thy håndbold': 'MTH',
    'mors thy': 'MTH',
    
    # Nordsjælland Håndbold
    'nordsjælland håndbold': 'NSH',
    'nordsjælland': 'NSH',
    
    # Ribe-Esbjerg HH
    'ribe-esbjerg hh': 'REH',
    'ribe esbjerg': 'REH',
    
    # SAH variationer
    'sah - skjern håndbold': 'SKH',
    'sah – skanderborg agf': 'SAH',
    'sah - skanderborg agf': 'SAH',
    'skanderborg agf': 'SAH',
    'skanderborg': 'SAH',
    
    # Silkeborg variationer
    'silkeborg fh': 'SFH',                    # NEW: Silkeborg fH
    'silkeborg': 'SFH',                       # NEW
    'sfh': 'SFH',                             # NEW
    
    # Skjern Håndbold
    'skjern håndbold': 'SKH',
    'skjern': 'SKH',
    
    # SønderjyskE legacy fix - CRITICAL: Always map SJE to SJK 
    'sje': 'SJK',                             # FIXED: Legacy SJE code always goes to Kvindeliga
    
    # SønderjyskE variationer - FIXED: Gender-specific mappings
    'sønderjyske': 'SJH',                     # Default to men's team
    'sønderjyske herrer': 'SJH',
    'sønderjyske herrehåndbold': 'SJH', 
    'sønderjyske håndbold': 'SJH',            # Default to men's team
    'sønderjyskE herrehåndbold': 'SJH',       # FIXED: New men's code
    'sønderjyskE håndbold': 'SJH',            # Default to men's team
    'sønderjyskE kvindehåndbold': 'SJK',      # FIXED: New women's code
    'sønderjyskE kvinder': 'SJK',             # FIXED: New women's code
    'sønderjyske kvindehåndbold': 'SJK',      # FIXED: New women's code
    'sønderjyske kvinder': 'SJK',             # FIXED: New women's code
    
    # TTH Holstebro
    'tth holstebro': 'TTH',
    'tth': 'TTH',
    'holstebro': 'TTH',
    
    # Vendsyssel variationer
    'vendsyssel håndbold': 'VEN',
    'vendsyssel': 'VEN',
    'vendsyssel f': 'VF',                     # NEW: Vendsyssel F
    'vf': 'VF',                               # NEW
    
    # TMS Ringsted - FIXED: Gender-specific mappings
    'tms ringsted': 'TMH',                    # Default to men's team
    'tms': 'TMH',                             # Default to men's team
    'tms ringsted kvinder': 'TMK',            # FIXED: Women's team
    'tms kvinder': 'TMK',                     # FIXED: Women's team
    
    # Lemvig-Thyborøn Håndbold
    'lemvig-thyborøn håndbold': 'LTH',
    'lemvig thyborøn': 'LTH',
    'lemvig': 'LTH',
    
    # Århus Håndbold
    'århus håndbold': 'ARH',
    'aarhus håndbold': 'ARH',
    
    # Skive fH
    'skive fh': 'SKI',
    'skive': 'SKI',
    
    # HØJ Elite
    'høj elite': 'HØJ',
    'høj': 'HØJ',
    
    # HC Midtjylland
    'hc midtjylland': 'HCM',
    'fc midtjylland': 'HCM',
    'midtjylland': 'HCM',
    
    # Team Sydhavsøerne
    'team sydhavsøerne': 'TSY',
    'sydhavsøerne': 'TSY',
    
    # TM Tønder Håndbold
    'tm tønder håndbold': 'TMT',
    'tm tønder': 'TMT',
    'tønder': 'TMT',
    
    # === KVINDELIGA MAPPINGS ===
    # Aarhus variationer
    'aarhus united': 'AHB',
    'aarhus håndbold kvinder': 'AHB',
    'aarhus håndbold': 'AHB',
    'aarhus': 'AHB',
    
    # Ajax Kvindeliga
    'ajax københavn kvinder': 'AJK',
    'ajax kvinder': 'AJK',
    'ajax kvindehåndbold': 'AJK',
    
    # Bjerringbro FH
    'bjerringbro fh': 'BFH',
    'bjerringbro': 'BFH',
    
    # EH Aalborg
    'eh aalborg': 'EHA',
    'eh aalborg kvinder': 'EHA',
    
    # Horsens Håndbold Elite
    'horsens håndbold elite': 'HHE',
    'horsens': 'HHE',
    
    # Ikast Håndbold
    'ikast håndbold': 'IKA',
    'ikast': 'IKA',
    
    # København variationer
    'københavn håndbold': 'KBH',
    'fc københavn': 'KBH',
    'københavn': 'KBH',
    
    # Nykøbing F. variationer
    'nykøbing f. håndbold': 'NFH',
    'nykøbing f. håndboldklub': 'NFH',
    'nykøbing f.': 'NFH',
    'nykøbing': 'NFH',
    
    # Odense Håndbold
    'odense håndbold': 'ODE',
    'odense': 'ODE',
    
    # Ringkøbing Håndbold
    'ringkøbing håndbold': 'RIN',
    'ringkøbing': 'RIN',
    
    # Silkeborg-Voel KFUM variationer
    'silkeborg-voel kfum': 'SVK',
    'voel kfum': 'SVK',
    'silkeborg voel': 'SVK',
    'voel': 'SVK',
    
    # Skanderborg Håndbold
    'skanderborg håndbold': 'SKB',
    'skanderborg': 'SKB',
    
    # SønderjyskE Kvindeliga variationer
    'sønderjyske kvindehåndbold': 'SJK',
    'sønderjyske kvinder': 'SJK',
    'sønderjyskE kvindehåndbold': 'SJK',
    'sønderjyskE kvinder': 'SJK',
    
    # Team Esbjerg
    'team esbjerg': 'TES',
    'esbjerg': 'TES',
    
    # Viborg HK
    'viborg hk': 'VHK',
    'viborg': 'VHK',
    
    # Randers HK
    'randers hk': 'RAN',
    'randers': 'RAN',
    
    # Holstebro Håndbold
    'holstebro håndbold': 'HOL',
    'holstebro': 'HOL'
}

class PlayerBasedTeamEloSystem:
    """
    🏆 SPILLERBASERET HOLD ELO SYSTEM
    Beregner hold ratings baseret på spillernes individuelle ELO ratings
    """
    
    def __init__(self, base_dir: str = "."):
        print("🏆 SPILLERBASERET HOLD ELO SYSTEM")
        print("=" * 70)
        print("🎯 Bygger hold ratings fra spillernes individuelle ELO ratings")
        
        self.base_dir = base_dir
        
        # Database directories
        self.herreliga_dir = os.path.join(base_dir, "Herreliga-database")
        self.kvindeliga_dir = os.path.join(base_dir, "Kvindeliga-database")
        self.player_csv_dir = os.path.join(base_dir, "ELO_Results", "Player_Seasonal_CSV")
        
        # Storage for results
        self.all_season_results = {}
        self.team_career_data = defaultdict(list)
        
        # Available seasons
        self.seasons = [
            "2017-2018", "2018-2019", "2019-2020", "2020-2021",
            "2021-2022", "2022-2023", "2023-2024", "2024-2025"
        ]
        
        self.validate_data_availability()
        
        print("✅ Player-Based Team ELO system initialiseret")
        print(f"📅 Tilgængelige sæsoner: {len(self.seasons)}")
        print(f"🎯 Min games for team inclusion: {MIN_GAMES_FOR_TEAM_INCLUSION}")
        print(f"👥 Min players for team rating: {MIN_PLAYERS_FOR_TEAM_RATING}")
        
    def validate_data_availability(self):
        """Validerer at nødvendig data er tilgængelig"""
        print(f"\n🔍 VALIDERER DATA TILGÆNGELIGHED")
        print("-" * 50)
        
        valid_seasons = []
        
        for season in self.seasons:
            # Check for player CSV files
            player_csv_files = []
            season_formatted = season.replace("-", "_")
            
            # Check for combined seasonal file
            combined_file = os.path.join(self.player_csv_dir, f"seasonal_elo_{season_formatted}.csv")
            herreliga_file = os.path.join(self.player_csv_dir, f"herreliga_seasonal_elo_{season_formatted}.csv")
            
            if os.path.exists(combined_file):
                player_csv_files.append("combined")
            if os.path.exists(herreliga_file):
                player_csv_files.append("herreliga")
                
            # Check for database files
            herreliga_path = os.path.join(self.herreliga_dir, season)
            kvindeliga_path = os.path.join(self.kvindeliga_dir, season)
            
            herreliga_files = 0
            kvindeliga_files = 0
            
            if os.path.exists(herreliga_path):
                herreliga_files = len([f for f in os.listdir(herreliga_path) if f.endswith('.db')])
            if os.path.exists(kvindeliga_path):
                kvindeliga_files = len([f for f in os.listdir(kvindeliga_path) if f.endswith('.db')])
                
            total_db_files = herreliga_files + kvindeliga_files
            
            if player_csv_files and total_db_files > 0:
                valid_seasons.append(season)
                print(f"  ✅ {season}: {', '.join(player_csv_files)} CSV, {total_db_files} DB filer")
            else:
                print(f"  ❌ {season}: mangler data (CSV: {player_csv_files}, DB: {total_db_files})")
                
        self.seasons = valid_seasons
        print(f"\n📊 {len(self.seasons)} gyldige sæsoner klar til processering")
        
    def get_team_code_from_name(self, team_name: str) -> str:
        """
        FIXED: Mapper holdnavn til holdkode med korrekt SønderjyskE håndtering
        """
        if not team_name:
            return "UNK"
            
        team_name_lower = team_name.lower().strip()
        
        # CRITICAL FIX: Handle exact "SJE" team name from database
        if team_name_lower == 'sje' or team_name.strip() == 'SJE':
            return 'SJK'  # Always map SJE to Kvindeliga
        
        # SPECIAL HANDLING for SønderjyskE - detect if it's men or women
        if 'sønderjyske' in team_name_lower or 'sønderjyskE' in team_name:
            if any(keyword in team_name_lower for keyword in ['kvinde', 'women', 'damer']):
                return 'SJK'  # Kvindeliga
            elif any(keyword in team_name_lower for keyword in ['herre', 'men', 'herrer']):
                return 'SJH'  # Herreliga
            else:
                # Default legacy fallback for sønderjyske without keywords
                return 'SJK'  # Default to women's team for historical data
        
        # First try exact mapping
        if team_name_lower in TEAM_NAME_MAPPINGS:
            code = TEAM_NAME_MAPPINGS[team_name_lower]
            # Check if team should be skipped
            if code in SKIP_TEAMS:
                return "UNK"  # Return unknown for skipped teams
            return code
            
        # Then try partial matching
        for mapping_name, code in TEAM_NAME_MAPPINGS.items():
            if code in SKIP_TEAMS:
                continue  # Skip teams in SKIP_TEAMS
            if mapping_name in team_name_lower or team_name_lower in mapping_name:
                return code
                
        # Legacy fallback
        for code, name in ALL_TEAMS.items():
            if code in SKIP_TEAMS:
                continue  # Skip teams in SKIP_TEAMS
            if name.lower() in team_name_lower or team_name_lower in name.lower():
                return code
                
        # Generate unknown code (but don't spam warnings for known skipped teams)
        potential_code = team_name[:3].upper()
        if potential_code not in SKIP_TEAMS:
            print(f"⚠️ UNMAPPED TEAM: '{team_name}'")
        return potential_code
        
    def determine_player_teams_from_database(self, season: str) -> Dict[str, str]:
        """
        🔍 BESTEMMER SPILLERENS HOLDTILKNYTNING BASERET PÅ DATABASE DATA
        Læser database filer og tæller hvilke hold hver spiller spiller for oftest
        """
        print(f"  🔍 Analyserer spilleres holdtilknytning fra database for {season}")
        
        player_team_games = defaultdict(lambda: defaultdict(int))  # player -> team -> games
        
        # Process both leagues
        for league_dir, league_name in [(self.herreliga_dir, "Herreliga"), 
                                       (self.kvindeliga_dir, "Kvindeliga")]:
            season_path = os.path.join(league_dir, season)
            
            if not os.path.exists(season_path):
                continue
                
            db_files = [f for f in os.listdir(season_path) if f.endswith('.db')]
            
            for db_file in db_files:
                db_path = os.path.join(season_path, db_file)
                
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Get match info for team names
                    cursor.execute("SELECT * FROM match_info LIMIT 1")
                    match_info = cursor.fetchone()
                    
                    if not match_info:
                        conn.close()
                        continue
                        
                    kamp_id, hold_hjemme, hold_ude, resultat, halvleg_resultat, dato, sted, turnering = match_info
                    
                    # Get team codes
                    hjemme_code = self.get_team_code_from_name(hold_hjemme)
                    ude_code = self.get_team_code_from_name(hold_ude)
                    
                    # Process match events to find player-team associations
                    cursor.execute("SELECT * FROM match_events")
                    events = cursor.fetchall()
                    
                    for event in events:
                        # Match events structure: id, kamp_id, tid, maal, hold, haendelse_1, pos, nr_1, navn_1, haendelse_2, nr_2, navn_2, nr_mv, mv
                        try:
                            _, _, tid, maal, hold, haendelse_1, pos, nr_1, navn_1, haendelse_2, nr_2, navn_2, nr_mv, mv = event
                            
                            # Primary player (navn_1)
                            if navn_1 and navn_1.strip() and navn_1 not in ["Retur", "Bold erobret", "Assist"]:
                                # Map hold to team code
                                if hold == hjemme_code or hold == hold_hjemme:
                                    team_code = hjemme_code
                                elif hold == ude_code or hold == hold_ude:
                                    team_code = ude_code
                                else:
                                    team_code = self.get_team_code_from_name(hold) if hold else "UNK"
                                    
                                player_team_games[navn_1.strip()][team_code] += 1
                                
                            # Secondary player (navn_2) - kun hvis det er samme hold
                            if navn_2 and navn_2.strip() and navn_2 not in ["Retur", "Bold erobret", "Assist", "Forårs. str."]:
                                # For sekundære hændelser skal vi være forsigtige med holdtilknytning
                                same_team_events = ["Assist"]
                                if haendelse_2 in same_team_events:
                                    if hold == hjemme_code or hold == hold_hjemme:
                                        team_code = hjemme_code
                                    elif hold == ude_code or hold == hold_ude:
                                        team_code = ude_code
                                    else:
                                        team_code = self.get_team_code_from_name(hold) if hold else "UNK"
                                        
                                    player_team_games[navn_2.strip()][team_code] += 1
                                    
                            # Goalkeeper (mv) - altid modsatte hold af primary action
                            if mv and mv.strip():
                                # Målvogter tilhører det modsatte hold af det angivne i 'hold' feltet
                                if hold == hjemme_code or hold == hold_hjemme:
                                    gk_team_code = ude_code
                                elif hold == ude_code or hold == hold_ude:
                                    gk_team_code = hjemme_code
                                else:
                                    # Fallback
                                    gk_team_code = hjemme_code if hold != hjemme_code else ude_code
                                    
                                player_team_games[mv.strip()][gk_team_code] += 1
                                
                        except Exception as e:
                            continue  # Skip problematic events
                            
                    conn.close()
                    
                except Exception as e:
                    print(f"    ⚠️ Fejl i {db_file}: {e}")
                    continue
                    
        # Determine primary team for each player (team with most games)
        player_teams = {}
        
        for player_name, team_games in player_team_games.items():
            if team_games:
                # Find team with most games
                primary_team = max(team_games.items(), key=lambda x: x[1])
                
                # Only include if player has enough games
                if primary_team[1] >= MIN_GAMES_FOR_TEAM_INCLUSION:
                    player_teams[player_name] = primary_team[0]
                    
        print(f"    ✅ Fundet {len(player_teams)} spillere med holdtilknytning")
        return player_teams
        
    def load_player_ratings_for_season(self, season: str) -> pd.DataFrame:
        """Loader spillernes ELO ratings for en given sæson"""
        season_formatted = season.replace("-", "_")
        
        # Try combined file first, then herreliga file
        combined_file = os.path.join(self.player_csv_dir, f"seasonal_elo_{season_formatted}.csv")
        herreliga_file = os.path.join(self.player_csv_dir, f"herreliga_seasonal_elo_{season_formatted}.csv")
        
        dfs = []
        
        if os.path.exists(combined_file):
            df_combined = pd.read_csv(combined_file)
            dfs.append(df_combined)
            
        if os.path.exists(herreliga_file):
            df_herreliga = pd.read_csv(herreliga_file)
            dfs.append(df_herreliga)
            
        if not dfs:
            print(f"  ❌ Ingen spillerdata for {season}")
            return pd.DataFrame()
            
        # Combine and remove duplicates
        df_all = pd.concat(dfs, ignore_index=True)
        df_all = df_all.drop_duplicates(subset=['player'], keep='first')
        
        print(f"  📊 Indlæst {len(df_all)} spillere for {season}")
        return df_all
        
    def calculate_team_ratings(self, team_players: Dict[str, List[Dict]]) -> Dict[str, Dict]:
        """
        🧮 BEREGNER FORSKELLIGE HOLD RATINGS BASERET PÅ SPILLERNES RATINGS
        """
        team_ratings = {}
        
        for team_code, players in team_players.items():
            if len(players) < MIN_PLAYERS_FOR_TEAM_RATING:
                continue
                
            # Extract ratings and other data
            ratings = [p['final_rating'] for p in players]
            games = [p['games'] for p in players]
            positions = [p['primary_position'] for p in players]
            
            # Sort players by rating (descending)
            sorted_players = sorted(players, key=lambda x: x['final_rating'], reverse=True)
            
            # 1. TEAM AVERAGE RATING
            team_avg_rating = np.mean(ratings)
            
            # 2. TOP 7 PLAYERS RATING
            top_7_players = sorted_players[:7]
            top_7_rating = np.mean([p['final_rating'] for p in top_7_players]) if len(top_7_players) >= 7 else team_avg_rating
            
            # 3. TOP 12 PLAYERS RATING  
            top_12_players = sorted_players[:12]
            top_12_rating = np.mean([p['final_rating'] for p in top_12_players]) if len(top_12_players) >= 10 else team_avg_rating
            
            # 4. BEST POSITION AVERAGE (ÆNDRET LOGIK)
            # For MV, VF, HF, ST: Tag den bedste fra hver position
            # For VB, PL, HB: Tag de 3 bedste på tværs af disse positioner
            
            specific_positions = ['MV', 'VF', 'HF', 'ST']  # Specifikke positioner
            dynamic_positions = ['VB', 'PL', 'HB']        # Dynamiske positioner
            
            selected_players = []
            
            # 1. Bedste fra hver specifik position
            for pos in specific_positions:
                pos_players = [p for p in players if p['primary_position'] == pos]
                if pos_players:
                    best_player = max(pos_players, key=lambda x: x['final_rating'])
                    selected_players.append(best_player)
                    
            # 2. De 3 bedste fra dynamiske positioner (på tværs)
            dynamic_players = [p for p in players if p['primary_position'] in dynamic_positions]
            if dynamic_players:
                # Sort og tag de 3 bedste
                dynamic_players.sort(key=lambda x: x['final_rating'], reverse=True)
                selected_players.extend(dynamic_players[:3])
                
            if len(selected_players) >= 3:  # Need minimum 3 players
                best_pos_rating = np.mean([p['final_rating'] for p in selected_players])
            else:
                best_pos_rating = team_avg_rating
                
            # 5. WEIGHTED POSITION AVERAGE
            weighted_sum = 0
            weight_sum = 0
            for player in players:
                weight = POSITION_WEIGHTS.get(player['primary_position'], 1.0)
                weighted_sum += player['final_rating'] * weight
                weight_sum += weight
                
            weighted_pos_rating = weighted_sum / weight_sum if weight_sum > 0 else team_avg_rating
            
            # 6. PLAYING TIME WEIGHTED
            total_games = sum(games)
            if total_games > 0:
                playing_time_weighted = sum(r * g for r, g in zip(ratings, games)) / total_games
            else:
                playing_time_weighted = team_avg_rating
                
            # Team composition analysis
            goalkeeper_count = sum(1 for p in players if p['is_goalkeeper'])
            elite_count = sum(1 for p in players if p['elite_status'] in ['ELITE', 'LEGENDARY'])
            
            team_ratings[team_code] = {
                'team_code': team_code,
                'team_name': ALL_TEAMS.get(team_code, team_code),
                'total_players': len(players),
                'total_games': sum(games),
                'avg_games_per_player': np.mean(games),
                'goalkeeper_count': goalkeeper_count,
                'elite_players': elite_count,
                
                # Various rating calculations
                'team_avg_rating': round(team_avg_rating, 1),
                'top_7_rating': round(top_7_rating, 1),
                'top_12_rating': round(top_12_rating, 1),
                'best_position_rating': round(best_pos_rating, 1),
                'weighted_position_rating': round(weighted_pos_rating, 1),
                'playing_time_weighted_rating': round(playing_time_weighted, 1),
                
                # Additional metrics
                'rating_std': round(np.std(ratings), 1),
                'rating_range': round(max(ratings) - min(ratings), 1),
                'best_player_rating': round(max(ratings), 1),
                'worst_player_rating': round(min(ratings), 1),
                
                # Position distribution
                'positions_represented': len(set(positions)),
                'position_distribution': dict(Counter(positions))
            }
            
        return team_ratings
        
    def process_season(self, season: str) -> Dict:
        """Processerer en enkelt sæson og returnerer hold ratings"""
        print(f"\n🏐 PROCESSERER SÆSON {season}")
        print("-" * 50)
        
        # Load player ratings
        player_df = self.load_player_ratings_for_season(season)
        
        if player_df.empty:
            print(f"  ❌ Ingen spillerdata for {season}")
            return {}
            
        # Determine player-team associations from database
        player_teams = self.determine_player_teams_from_database(season)
        
        if not player_teams:
            print(f"  ❌ Ingen holdtilknytninger fundet for {season}")
            return {}
            
        # Group players by team
        team_players = defaultdict(list)
        
        for _, player_row in player_df.iterrows():
            player_name = player_row['player']
            
            if player_name in player_teams:
                team_code = player_teams[player_name]
                
                player_data = {
                    'player': player_name,
                    'final_rating': player_row['final_rating'],
                    'games': player_row['games'],
                    'primary_position': player_row['primary_position'],
                    'is_goalkeeper': player_row['is_goalkeeper'],
                    'elite_status': player_row['elite_status'],
                    'rating_change': player_row['rating_change']
                }
                
                team_players[team_code].append(player_data)
                
        print(f"  👥 Fordelt {sum(len(players) for players in team_players.values())} spillere på {len(team_players)} hold")
        
        # Calculate team ratings
        team_ratings = self.calculate_team_ratings(team_players)
            
        # Add season info
        for team_code, team_data in team_ratings.items():
            team_data['season'] = season
            
            # FIXED: Update team names for new codes
            if team_code == 'SJH':
                team_data['team_name'] = HERRELIGA_TEAMS['SJH']
            elif team_code == 'SJK':
                team_data['team_name'] = KVINDELIGA_TEAMS['SJK']
            elif team_code == 'TMH':
                team_data['team_name'] = HERRELIGA_TEAMS['TMH']
            elif team_code == 'TMK':
                team_data['team_name'] = KVINDELIGA_TEAMS['TMK']
            elif team_code == 'AJH':
                team_data['team_name'] = HERRELIGA_TEAMS['AJH']
            elif team_code == 'AJK':
                team_data['team_name'] = KVINDELIGA_TEAMS['AJK']
            
            # Determine league - FIXED: No more legacy SJE handling needed
            if team_code in HERRELIGA_TEAMS:
                team_data['league'] = 'Herreliga'
            elif team_code in KVINDELIGA_TEAMS:
                team_data['league'] = 'Kvindeliga'
            else:
                team_data['league'] = 'Unknown'
                
        print(f"  ✅ Beregnet ratings for {len(team_ratings)} hold")
        
        return team_ratings
        
    def save_season_csv(self, season_results: Dict, season: str):
        """Gemmer sæson resultater til separate CSV filer for hver liga"""
        if not season_results:
            return
            
        # Convert to DataFrame
        df = pd.DataFrame(list(season_results.values()))
        
        # Ensure output directory exists
        output_dir = os.path.join("ELO_Results", "Team_CSV", "Player_Based")
        os.makedirs(output_dir, exist_ok=True)
        
        # Split by league and save separate files
        leagues_saved = []
        
        for league in ['Herreliga', 'Kvindeliga']:
            league_teams = df[df['league'] == league].copy()
            
            if len(league_teams) > 0:
                # Sort by team average rating (descending)
                league_teams = league_teams.sort_values('team_avg_rating', ascending=False)
                
                # Save league-specific CSV
                filename = f'player_based_{league.lower()}_team_elo_{season.replace("-", "_")}.csv'
                filepath = os.path.join(output_dir, filename)
                league_teams.to_csv(filepath, index=False)
                
                print(f"💾 Gemt: {filepath} ({len(league_teams)} {league} hold)")
                leagues_saved.append(league)
                
        # Show top teams by league
        print(f"\n🏆 TOP HOLD BASERET PÅ SPILLERE {season}:")
        
        for league in leagues_saved:
            league_teams = df[df['league'] == league].head(8)
            print(f"  📊 {league}:")
            for i, (_, row) in enumerate(league_teams.iterrows(), 1):
                print(f"    {i}. {row['team_name']}: Avg:{row['team_avg_rating']:.0f}, "
                      f"Top7:{row['top_7_rating']:.0f}, Top12:{row['top_12_rating']:.0f} "
                      f"({row['total_players']} spillere)")
                          
    def generate_comparative_analysis(self):
        """Genererer sammenlignende analyse på tværs af sæsoner"""
        print(f"\n📊 SAMMENLIGNENDE ANALYSE PÅ TVÆRS AF SÆSONER")
        print("=" * 70)
        
        if not self.all_season_results:
            print("❌ Ingen sæsondata til analyse")
            return
            
        # Collect all team career data
        for season, results in self.all_season_results.items():
            for team_code, team_data in results.items():
                self.team_career_data[team_code].append({
                    'season': season,
                    'team_avg_rating': team_data['team_avg_rating'],
                    'top_7_rating': team_data['top_7_rating'],
                    'top_12_rating': team_data['top_12_rating'],
                    'total_players': team_data['total_players'],
                    'elite_players': team_data['elite_players'],
                    'league': team_data['league']
                })
                
        # Generate career statistics
        career_stats = []
        
        for team_code, seasons_data in self.team_career_data.items():
            if len(seasons_data) >= 3:  # Only teams with at least 3 seasons
                team_name = ALL_TEAMS.get(team_code, team_code)
                league = seasons_data[0]['league']
                
                avg_ratings = [s['team_avg_rating'] for s in seasons_data]
                top7_ratings = [s['top_7_rating'] for s in seasons_data]
                elite_counts = [s['elite_players'] for s in seasons_data]
                
                career_stats.append({
                    'team_code': team_code,
                    'team_name': team_name,
                    'league': league,
                    'seasons_played': len(seasons_data),
                    'avg_team_rating': round(np.mean(avg_ratings), 1),
                    'avg_top7_rating': round(np.mean(top7_ratings), 1),
                    'peak_team_rating': round(max(avg_ratings), 1),
                    'avg_elite_players': round(np.mean(elite_counts), 1),
                    'rating_consistency': round(np.std(avg_ratings), 1),
                    'career_development': round(avg_ratings[-1] - avg_ratings[0], 1)
                })
                
        # Sort by average rating within league
        career_stats.sort(key=lambda x: (x['league'], -x['avg_team_rating']))
        
        print(f"📈 Fundet {len(career_stats)} hold med karriere data (≥3 sæsoner)")
        
        # Show top career teams by league
        for league in ['Herreliga', 'Kvindeliga']:
            league_teams = [team for team in career_stats if team['league'] == league][:10]
            if league_teams:
                print(f"\n🏆 TOP {league.upper()} HOLD (KARRIERE):")
                for i, team in enumerate(league_teams, 1):
                    trend = "📈" if team['career_development'] > 20 else "📉" if team['career_development'] < -20 else "➡️"
                    consistency = "🎯" if team['rating_consistency'] < 30 else "📊"
                    
                    print(f"  {i:2d}. {team['team_name']}: Avg:{team['avg_team_rating']:.0f}, "
                          f"Top7:{team['avg_top7_rating']:.0f}, Peak:{team['peak_team_rating']:.0f} "
                          f"({team['seasons_played']} sæsoner) {trend}{team['career_development']:+.0f} {consistency}")
                          
        # Save career analysis - separate files for each league
        career_df = pd.DataFrame(career_stats)
        output_dir = os.path.join("ELO_Results", "Team_CSV", "Player_Based")
        os.makedirs(output_dir, exist_ok=True)
        
        # Save combined career analysis
        combined_filepath = os.path.join(output_dir, 'player_based_team_career_analysis.csv')
        career_df.to_csv(combined_filepath, index=False)
        print(f"\n💾 Samlet karriere analyse gemt: {combined_filepath}")
        
        # Save separate career files for each league
        for league in ['Herreliga', 'Kvindeliga']:
            league_career = career_df[career_df['league'] == league].copy()
            if len(league_career) > 0:
                league_filepath = os.path.join(output_dir, f'player_based_{league.lower()}_career_analysis.csv')
                league_career.to_csv(league_filepath, index=False)
                print(f"💾 {league} karriere analyse gemt: {league_filepath}")
        
    def run_complete_analysis(self):
        """
        🚀 KØRER KOMPLET SPILLERBASERET TEAM ANALYSE FOR ALLE SÆSONER
        """
        print("🏐 STARTER SPILLERBASERET TEAM ELO ANALYSE")
        print("=" * 70)
        
        # Validate data first
        self.validate_data_availability()
        
        # Process each season
        all_season_results = {}
        
        for season in self.seasons:
            print(f"\n📅 === SÆSON {season} ===")
            season_results = self.process_season(season)
            
            if season_results:
                all_season_results[season] = season_results
                self.save_season_csv(season_results, season)
            
        # Generate comparative analysis
        if all_season_results:
            print(f"\n📊 SAMMENLIGNENDE ANALYSE PÅ TVÆRS AF SÆSONER")
            print("=" * 70)
            self.generate_comparative_analysis()
            
        print(f"\n\n✅ SPILLERBASERET TEAM ANALYSE KOMPLET!")
        print("=" * 70)
        print("📁 Genererede filer:")
        for season in self.seasons:
            print(f"  • player_based_herreliga_team_elo_{season.replace('-', '_')}.csv")
            print(f"  • player_based_kvindeliga_team_elo_{season.replace('-', '_')}.csv")
        print("  • player_based_team_career_analysis.csv")
        print("  • player_based_herreliga_career_analysis.csv")
        print("  • player_based_kvindeliga_career_analysis.csv")
        
        print("\n🎯 Implementerede beregningsmetoder:")
        print("  ✅ Team Average Rating - Gennemsnit af alle spillere")
        print("  ✅ Top 7 Players Rating - De 7 bedste spillere") 
        print("  ✅ Top 12 Players Rating - De 12 bedste spillere")
        print("  ✅ Best Position Rating - Bedste fra hver position")
        print("  ✅ Weighted Position Rating - Positionsvægtet gennemsnit")
        print("  ✅ Playing Time Weighted - Vægtet efter spilletid")
        
        print("\n🎉 SPILLERBASERET TEAM SYSTEM KOMPLET!")
        print("=" * 80)
        print("🎯 Hold ratings bygget fra spillernes individuelle ELO ratings")
        print("🔄 Automatisk transfer tracking baseret på database analyse") 
        print("📊 Seks forskellige beregningsmetoder implementeret")
        print("🏆 Detaljeret sæson- og karriere analyse genereret")
        
        # Summary statistics
        total_seasons = len(self.seasons)
        total_teams_processed = sum(len(results) for results in all_season_results.values())
        
        print(f"\n📈 SYSTEM STATISTIKKER:")
        print(f"  • {total_seasons} sæsoner processeret")
        print(f"  • {total_teams_processed} hold analyseret totalt")
        print(f"  • Minimum {MIN_GAMES_FOR_TEAM_INCLUSION} kampe for holdinkludering")  
        print(f"  • Minimum {MIN_PLAYERS_FOR_TEAM_RATING} spillere for holdrating")
        
        skipped_teams = len(SKIP_TEAMS)
        print(f"  • {skipped_teams} problematiske teamkoder ignoreret")
        
        print("\n🔍 NÆSTE TRIN:")
        print("  1. Analyser de genererede CSV filer for detaljerede resultater")
        print("  2. Sammenlign spillerbaserede ratings med traditionelle team ratings")
        print("  3. Brug dataene til at identificere stærke/svage hold baseret på spillerkvalitet")
        print("  4. Analyser transfereffekter ved hjælp af karriere-analysen")


# === MAIN EXECUTION ===
if __name__ == "__main__":
    print("🏆 STARTER SPILLERBASERET HOLD ELO SYSTEM")
    print("=" * 80)
    
    # Create system instance
    player_team_system = PlayerBasedTeamEloSystem()
    
    # Run complete analysis
    player_team_system.run_complete_analysis()
    
    print("\n🎉 SPILLERBASERET TEAM SYSTEM KOMPLET!")
    print("=" * 80)
    print("🎯 Hold ratings bygget fra spillernes individuelle ELO ratings")
    print("🔄 Automatisk transfer tracking baseret på database analyse")
    print("📊 Seks forskellige beregningsmetoder implementeret")
    print("🏆 Detaljeret sæson- og karriere analyse genereret") 