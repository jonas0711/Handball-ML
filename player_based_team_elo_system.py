#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 SPILLERBASERET HOLD ELO SYSTEM (FIXED VERSION)
=================================================

BYGGER HOLD RATINGS BASERET PÅ SPILLERNES INDIVIDUELLE RATINGS:
✅ FIXED: Korrekt indlæsning af spillernes ELO ratings fra CSV filer
✅ FIXED: Korrekt holdtilknytning baseret på database analyse  
✅ FIXED: Separate processer for Herreliga og Kvindeliga
✅ Forskellige beregningsmetoder: gennemsnit, top 7, top 12, bedste pr. position
✅ Genererer detaljerede CSV rapporter

KRITISKE FIXES:
- Bruger ikke længere MasterHandballEloSystem (som gav problemer)
- Indlæser direkte fra eksisterende CSV filer fra seasonal ELO systemer
- Korrekt team mapping med kontekst-aware funktioner
- Robust fejlhåndtering og logging

Jonas' Fixed System - December 2024
"""

import pandas as pd
import numpy as np
import sqlite3
import os
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Import central team configuration
from team_config import (
    HERRELIGA_TEAMS, KVINDELIGA_TEAMS, ALL_TEAMS,
    HERRELIGA_NAME_MAPPINGS, KVINDELIGA_NAME_MAPPINGS,
    SKIP_TEAMS, MIN_GAMES_FOR_TEAM_INCLUSION,
    PLAYER_NAME_ALIASES
)

# === SYSTEM PARAMETRE ===
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

class PlayerBasedTeamEloSystem:
    """
    🏆 SPILLERBASERET HOLD ELO SYSTEM (FIXED)
    Beregner hold ratings baseret på spillernes individuelle ELO ratings
    """
    
    def __init__(self, base_dir: str = "."):
        print("🏆 SPILLERBASERET HOLD ELO SYSTEM (FIXED VERSION)")
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
        
        # Validate data availability
        self.validate_data_availability()
        
        print("✅ Player-Based Team ELO system initialiseret (FIXED)")
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
            season_formatted = season.replace("-", "_")
            
            # Check for league-specific files first, then combined
            herreliga_file = os.path.join(self.player_csv_dir, f"herreliga_seasonal_elo_{season_formatted}.csv")
            kvindeliga_file = os.path.join(self.player_csv_dir, f"kvindeliga_seasonal_elo_{season_formatted}.csv")
            combined_file = os.path.join(self.player_csv_dir, f"seasonal_elo_{season_formatted}.csv")
            
            has_csv = os.path.exists(herreliga_file) or os.path.exists(kvindeliga_file) or os.path.exists(combined_file)
            
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
            
            if has_csv and total_db_files > 0:
                valid_seasons.append(season)
                csv_info = []
                if os.path.exists(herreliga_file): csv_info.append("herreliga")
                if os.path.exists(kvindeliga_file): csv_info.append("kvindeliga") 
                if os.path.exists(combined_file): csv_info.append("combined")
                print(f"  ✅ {season}: {', '.join(csv_info)} CSV, {total_db_files} DB filer")
            else:
                print(f"  ❌ {season}: mangler data (CSV: {has_csv}, DB: {total_db_files})")
                
        self.seasons = valid_seasons
        print(f"\n📊 {len(self.seasons)} gyldige sæsoner klar til processering")

    def _normalize_and_get_canonical_name(self, name: str) -> str:
        """Normaliserer et spillernavn og oversætter det til dets kanoniske version"""
        if not isinstance(name, str):
            return ""
        
        # Standardiser input-navnet (STORE BOGSTAVER, trimmet)
        processed_name = " ".join(name.strip().upper().split())
        
        # Opret standardiseret version af alias-mappen
        standardized_aliases = { 
            " ".join(k.strip().upper().split()): v.upper() 
            for k, v in PLAYER_NAME_ALIASES.items() 
        }

        # Slå det standardiserede navn op
        return standardized_aliases.get(processed_name, processed_name)

    def get_team_code_from_name(self, team_name: str, league_context: str) -> str:
        """
        FIXED: Korrekt team mapping med league kontekst
        """
        if not team_name:
            return "UNK"

        # Choose the correct mapping dictionary and valid team set
        if league_context == 'herre':
            mapping_dict = HERRELIGA_NAME_MAPPINGS
            valid_teams = HERRELIGA_TEAMS
        elif league_context == 'kvinde':
            mapping_dict = KVINDELIGA_NAME_MAPPINGS
            valid_teams = KVINDELIGA_TEAMS
        else:
            print(f"⚠️ Invalid league context: '{league_context}'")
            return "UNK"

        clean_name = team_name.strip().lower()

        # Direct lookup
        if clean_name in mapping_dict:
            code = mapping_dict[clean_name]
            if code in valid_teams:
                return code

        # Fallback search
        for key, code in mapping_dict.items():
            if key in clean_name and code in valid_teams:
                return code

        return "UNK"
        
    def determine_player_teams_from_database(self, season: str) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        FIXED: Bestemmer spillerens holdtilknytning SEPARAT for hver liga
        Returns: (herreliga_player_teams, kvindeliga_player_teams)
        """
        print(f"  🔍 Analyserer spilleres holdtilknytning fra database for {season}")
        
        herreliga_player_teams = {}
        kvindeliga_player_teams = {}
        
        # Process Herreliga
        herreliga_player_games = defaultdict(lambda: defaultdict(set))
        herreliga_path = os.path.join(self.herreliga_dir, season)
        
        if os.path.exists(herreliga_path):
            db_files = [f for f in os.listdir(herreliga_path) if f.endswith('.db')]
            
            for db_file in db_files:
                db_path = os.path.join(herreliga_path, db_file)
                
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Check if tables exist
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_info'")
                    if cursor.fetchone() is None:
                        conn.close()
                        continue

                    # Get match info for team names
                    cursor.execute("SELECT * FROM match_info LIMIT 1")
                    match_info = cursor.fetchone()
                    
                    if not match_info:
                        conn.close()
                        continue
                        
                    kamp_id, hold_hjemme, hold_ude, resultat, halvleg_resultat, dato, sted, turnering = match_info
                    
                    # Get team codes WITH HERRELIGA CONTEXT
                    hjemme_code = self.get_team_code_from_name(hold_hjemme, "herre")
                    ude_code = self.get_team_code_from_name(hold_ude, "herre")
                    
                    # Skip if teams are not valid Herreliga teams
                    if hjemme_code not in HERRELIGA_TEAMS or ude_code not in HERRELIGA_TEAMS:
                        conn.close()
                        continue
                    
                    # Process match events
                    cursor.execute("SELECT * FROM match_events")
                    events = cursor.fetchall()
                    
                    for event in events:
                        try:
                            _, _, tid, maal, hold, haendelse_1, pos, nr_1, navn_1, haendelse_2, nr_2, navn_2, nr_mv, mv = event
                            
                            # Primary player
                            if navn_1 and navn_1.strip() and navn_1 not in ["Retur", "Bold erobret", "Assist"]:
                                canonical_navn_1 = self._normalize_and_get_canonical_name(navn_1)
                                
                                if hold == hjemme_code or hold == hold_hjemme:
                                    team_code = hjemme_code
                                elif hold == ude_code or hold == hold_ude:
                                    team_code = ude_code
                                else:
                                    team_code = self.get_team_code_from_name(hold, "herre") if hold else "UNK"
                                    
                                if team_code in HERRELIGA_TEAMS:
                                    herreliga_player_games[canonical_navn_1][team_code].add(db_file)
                                    
                            # Secondary player (assists)
                            if navn_2 and navn_2.strip() and haendelse_2 and navn_2 not in ["Retur", "Bold erobret", "Forårs. str."]:
                                canonical_navn_2 = self._normalize_and_get_canonical_name(navn_2)
                                
                                if haendelse_2 == "Assist":
                                    if hold == hjemme_code or hold == hold_hjemme:
                                        assist_team_code = hjemme_code
                                    elif hold == ude_code or hold == hold_ude:
                                        assist_team_code = ude_code
                                    else:
                                        assist_team_code = self.get_team_code_from_name(hold, "herre") if hold else "UNK"
                                        
                                    if assist_team_code in HERRELIGA_TEAMS:
                                        herreliga_player_games[canonical_navn_2][assist_team_code].add(db_file)
                                
                            # Goalkeeper  
                            if mv and mv.strip():
                                canonical_mv = self._normalize_and_get_canonical_name(mv)
                                
                                if hold == hjemme_code or hold == hold_hjemme:
                                    gk_team_code = ude_code
                                elif hold == ude_code or hold == hold_ude:
                                    gk_team_code = hjemme_code
                                else:
                                    gk_team_code = hjemme_code if hold != hjemme_code else ude_code
                                    
                                if gk_team_code in HERRELIGA_TEAMS:
                                    herreliga_player_games[canonical_mv][gk_team_code].add(db_file)
                                
                        except Exception as e:
                            continue
                            
                    conn.close()
                    
                except Exception as e:
                    print(f"      ⚠️ Fejl i Herreliga {db_file}: {e}")
                    continue
        
        # Determine primary team for Herreliga players
        for player_name, team_games in herreliga_player_games.items():
            if team_games:
                valid_teams = {team: games for team, games in team_games.items() if team != "UNK"}
                if not valid_teams:
                    continue

                primary_team = max(valid_teams.items(), key=lambda x: len(x[1]))
                
                if len(primary_team[1]) >= MIN_GAMES_FOR_TEAM_INCLUSION and primary_team[0] in HERRELIGA_TEAMS:
                    herreliga_player_teams[player_name] = primary_team[0]
        
        # Process Kvindeliga (similar logic)
        kvindeliga_player_games = defaultdict(lambda: defaultdict(set))
        kvindeliga_path = os.path.join(self.kvindeliga_dir, season)
        
        if os.path.exists(kvindeliga_path):
            db_files = [f for f in os.listdir(kvindeliga_path) if f.endswith('.db')]
            
            for db_file in db_files:
                db_path = os.path.join(kvindeliga_path, db_file)
                
                try:
                    conn = sqlite3.connect(db_path)
                    cursor = conn.cursor()
                    
                    # Check if tables exist
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_info'")
                    if cursor.fetchone() is None:
                        conn.close()
                        continue

                    # Get match info for team names
                    cursor.execute("SELECT * FROM match_info LIMIT 1")
                    match_info = cursor.fetchone()
                    
                    if not match_info:
                        conn.close()
                        continue
                        
                    kamp_id, hold_hjemme, hold_ude, resultat, halvleg_resultat, dato, sted, turnering = match_info
                    
                    # Get team codes WITH KVINDELIGA CONTEXT
                    hjemme_code = self.get_team_code_from_name(hold_hjemme, "kvinde")
                    ude_code = self.get_team_code_from_name(hold_ude, "kvinde")
                    
                    # Skip if teams are not valid Kvindeliga teams
                    if hjemme_code not in KVINDELIGA_TEAMS or ude_code not in KVINDELIGA_TEAMS:
                        conn.close()
                        continue
                    
                    # Process match events (same logic as Herreliga but with kvinde context)
                    cursor.execute("SELECT * FROM match_events")
                    events = cursor.fetchall()
                    
                    for event in events:
                        try:
                            _, _, tid, maal, hold, haendelse_1, pos, nr_1, navn_1, haendelse_2, nr_2, navn_2, nr_mv, mv = event
                            
                            # Primary player
                            if navn_1 and navn_1.strip() and navn_1 not in ["Retur", "Bold erobret", "Assist"]:
                                canonical_navn_1 = self._normalize_and_get_canonical_name(navn_1)
                                
                                if hold == hjemme_code or hold == hold_hjemme:
                                    team_code = hjemme_code
                                elif hold == ude_code or hold == hold_ude:
                                    team_code = ude_code
                                else:
                                    team_code = self.get_team_code_from_name(hold, "kvinde") if hold else "UNK"
                                    
                                if team_code in KVINDELIGA_TEAMS:
                                    kvindeliga_player_games[canonical_navn_1][team_code].add(db_file)
                                    
                            # Secondary player (assists)
                            if navn_2 and navn_2.strip() and haendelse_2 and navn_2 not in ["Retur", "Bold erobret", "Forårs. str."]:
                                canonical_navn_2 = self._normalize_and_get_canonical_name(navn_2)
                                
                                if haendelse_2 == "Assist":
                                    if hold == hjemme_code or hold == hold_hjemme:
                                        assist_team_code = hjemme_code
                                    elif hold == ude_code or hold == hold_ude:
                                        assist_team_code = ude_code
                                    else:
                                        assist_team_code = self.get_team_code_from_name(hold, "kvinde") if hold else "UNK"
                                        
                                    if assist_team_code in KVINDELIGA_TEAMS:
                                        kvindeliga_player_games[canonical_navn_2][assist_team_code].add(db_file)
                                
                            # Goalkeeper  
                            if mv and mv.strip():
                                canonical_mv = self._normalize_and_get_canonical_name(mv)
                                
                                if hold == hjemme_code or hold == hold_hjemme:
                                    gk_team_code = ude_code
                                elif hold == ude_code or hold == hold_ude:
                                    gk_team_code = hjemme_code
                                else:
                                    gk_team_code = hjemme_code if hold != hjemme_code else ude_code
                                    
                                if gk_team_code in KVINDELIGA_TEAMS:
                                    kvindeliga_player_games[canonical_mv][gk_team_code].add(db_file)
                                
                        except Exception as e:
                            continue
                            
                    conn.close()
                    
                except Exception as e:
                    print(f"      ⚠️ Fejl i Kvindeliga {db_file}: {e}")
                    continue
        
        # Determine primary team for Kvindeliga players
        for player_name, team_games in kvindeliga_player_games.items():
            if team_games:
                valid_teams = {team: games for team, games in team_games.items() if team != "UNK"}
                if not valid_teams:
                    continue
                    
                primary_team = max(valid_teams.items(), key=lambda x: len(x[1]))
                
                if len(primary_team[1]) >= MIN_GAMES_FOR_TEAM_INCLUSION and primary_team[0] in KVINDELIGA_TEAMS:
                    kvindeliga_player_teams[player_name] = primary_team[0]
        
        print(f"    ✅ Herreliga: {len(herreliga_player_teams)} spillere")
        print(f"    ✅ Kvindeliga: {len(kvindeliga_player_teams)} spillere")
        
        return herreliga_player_teams, kvindeliga_player_teams
        
    def load_player_ratings_for_season(self, season: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        FIXED: Loader spillernes ELO ratings SEPARAT for hver liga
        Returns: (herreliga_df, kvindeliga_df)
        """
        season_formatted = season.replace("-", "_")
        
        # Try to load separate files for each league
        herreliga_file = os.path.join(self.player_csv_dir, f"herreliga_seasonal_elo_{season_formatted}.csv")
        kvindeliga_file = os.path.join(self.player_csv_dir, f"kvindeliga_seasonal_elo_{season_formatted}.csv")
        combined_file = os.path.join(self.player_csv_dir, f"seasonal_elo_{season_formatted}.csv")
        
        herreliga_df = pd.DataFrame()
        kvindeliga_df = pd.DataFrame()
        
        # Load Herreliga data
        if os.path.exists(herreliga_file):
            herreliga_df = pd.read_csv(herreliga_file)
            print(f"    📊 Herreliga: {len(herreliga_df)} spillere indlæst fra dedikeret fil")
        
        # Load Kvindeliga data  
        if os.path.exists(kvindeliga_file):
            kvindeliga_df = pd.read_csv(kvindeliga_file)
            print(f"    📊 Kvindeliga: {len(kvindeliga_df)} spillere indlæst fra dedikeret fil")
        
        # If no separate files exist, try to split combined file
        if herreliga_df.empty and kvindeliga_df.empty and os.path.exists(combined_file):
            print(f"    🔄 Splitter combined fil baseret på holdtilknytninger...")
            combined_df = pd.read_csv(combined_file)
            
            # Get player-team associations for separation
            herreliga_player_teams, kvindeliga_player_teams = self.determine_player_teams_from_database(season)
            
            # Split based on player team associations
            herreliga_players = []
            kvindeliga_players = []
            
            for _, player_row in combined_df.iterrows():
                player_name = self._normalize_and_get_canonical_name(player_row['player'])
                
                if player_name in herreliga_player_teams:
                    herreliga_players.append(player_row)
                elif player_name in kvindeliga_player_teams:
                    kvindeliga_players.append(player_row)
                # Skip players without clear team association
                    
            if herreliga_players:
                herreliga_df = pd.DataFrame(herreliga_players)
                print(f"    ✅ Herreliga fra combined: {len(herreliga_df)} spillere")
                
            if kvindeliga_players:
                kvindeliga_df = pd.DataFrame(kvindeliga_players)
                print(f"    ✅ Kvindeliga fra combined: {len(kvindeliga_df)} spillere")
                
        return herreliga_df, kvindeliga_df
        
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
            
            # 4. BEST POSITION AVERAGE
            specific_positions = ['MV', 'VF', 'HF', 'ST']  # Specifikke positioner
            dynamic_positions = ['VB', 'PL', 'HB']        # Dynamiske positioner
            
            selected_players = []
            
            # Bedste fra hver specifik position
            for pos in specific_positions:
                pos_players = [p for p in players if p['primary_position'] == pos]
                if pos_players:
                    best_player = max(pos_players, key=lambda x: x['final_rating'])
                    selected_players.append(best_player)
                    
            # De 3 bedste fra dynamiske positioner
            dynamic_players = [p for p in players if p['primary_position'] in dynamic_positions]
            if dynamic_players:
                dynamic_players.sort(key=lambda x: x['final_rating'], reverse=True)
                selected_players.extend(dynamic_players[:3])
                
            if len(selected_players) >= 3:
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
        """FIXED: Processerer en enkelt sæson og returnerer hold ratings"""
        print(f"\n🏐 PROCESSERER SÆSON {season}")
        print("-" * 50)
        
        # Load player ratings SEPARATELY for each league
        herreliga_df, kvindeliga_df = self.load_player_ratings_for_season(season)
        
        if herreliga_df.empty and kvindeliga_df.empty:
            print(f"  ❌ Ingen spillerdata for {season}")
            return {}
            
        # Determine player-team associations from database SEPARATELY
        herreliga_player_teams, kvindeliga_player_teams = self.determine_player_teams_from_database(season)
        
        if not herreliga_player_teams and not kvindeliga_player_teams:
            print(f"  ❌ Ingen holdtilknytninger fundet for {season}")
            return {}
            
        # Group players by team
        team_players = defaultdict(list)
        
        # Process Herreliga players
        if not herreliga_df.empty and herreliga_player_teams:
            print(f"    🔵 Processerer {len(herreliga_df)} Herreliga spillere...")
            
            for _, player_row in herreliga_df.iterrows():
                player_name = self._normalize_and_get_canonical_name(player_row['player'])
                
                if player_name in herreliga_player_teams:
                    team_code = herreliga_player_teams[player_name]
                    
                    # Validation: Only accept Herreliga teams
                    if team_code not in HERRELIGA_TEAMS:
                        print(f"      ⚠️ FEJL: Herreliga spiller {player_name} tildelt ikke-Herreliga hold {team_code}")
                        continue
                    
                    player_data = {
                        'player': player_name,
                        'team_code': team_code,
                        'team_name': HERRELIGA_TEAMS[team_code],
                        'final_rating': player_row['final_rating'],
                        'games': player_row['games'],
                        'primary_position': player_row['primary_position'],
                        'is_goalkeeper': player_row['is_goalkeeper'],
                        'elite_status': player_row['elite_status'],
                        'rating_change': player_row.get('rating_change', 0)
                    }
                    
                    team_players[team_code].append(player_data)
        
        # Process Kvindeliga players
        if not kvindeliga_df.empty and kvindeliga_player_teams:
            print(f"    🔴 Processerer {len(kvindeliga_df)} Kvindeliga spillere...")
            
            for _, player_row in kvindeliga_df.iterrows():
                player_name = self._normalize_and_get_canonical_name(player_row['player'])
                
                if player_name in kvindeliga_player_teams:
                    team_code = kvindeliga_player_teams[player_name]
                    
                    # Validation: Only accept Kvindeliga teams
                    if team_code not in KVINDELIGA_TEAMS:
                        print(f"      ⚠️ FEJL: Kvindeliga spiller {player_name} tildelt ikke-Kvindeliga hold {team_code}")
                        continue
                    
                    player_data = {
                        'player': player_name,
                        'team_code': team_code,
                        'team_name': KVINDELIGA_TEAMS[team_code],
                        'final_rating': player_row['final_rating'],
                        'games': player_row['games'],
                        'primary_position': player_row['primary_position'],
                        'is_goalkeeper': player_row['is_goalkeeper'],
                        'elite_status': player_row['elite_status'],
                        'rating_change': player_row.get('rating_change', 0)
                    }
                    
                    team_players[team_code].append(player_data)
        
        print(f"  👥 Fordelt {sum(len(players) for players in team_players.values())} spillere på {len(team_players)} hold")
        
        # Calculate team ratings
        team_ratings = self.calculate_team_ratings(team_players)
            
        # Add season info and determine league
        for team_code, team_data in team_ratings.items():
            team_data['season'] = season
            
            # Determine league
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
                          
        # Save career analysis
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
        🚀 FIXED: Kører komplet spillerbaseret team analyse for alle sæsoner
        """
        print("🏐 STARTER SPILLERBASERET TEAM ELO ANALYSE (FIXED)")
        print("=" * 70)
        
        # Validate data first
        self.validate_data_availability()
        
        # Process each season
        self.all_season_results = {}
        
        for season in self.seasons:
            print(f"\n📅 === SÆSON {season} ===")
            season_results = self.process_season(season)
            
            if season_results:
                self.all_season_results[season] = season_results
                self.save_season_csv(season_results, season)
            
        # Generate comparative analysis
        if self.all_season_results:
            self.generate_comparative_analysis()
            
        print(f"\n\n✅ SPILLERBASERET TEAM ANALYSE KOMPLET (FIXED)!")
        print("=" * 70)
        print("📁 Genererede filer:")
        for season in self.seasons:
            print(f"  • player_based_herreliga_team_elo_{season.replace('-', '_')}.csv")
            print(f"  • player_based_kvindeliga_team_elo_{season.replace('-', '_')}.csv")
        print("  • player_based_team_career_analysis.csv")
        print("  • player_based_herreliga_career_analysis.csv")
        print("  • player_based_kvindeliga_career_analysis.csv")
        
        print("\n🎯 FIXED implementerede beregningsmetoder:")
        print("  ✅ Team Average Rating - Gennemsnit af alle spillere")
        print("  ✅ Top 7 Players Rating - De 7 bedste spillere") 
        print("  ✅ Top 12 Players Rating - De 12 bedste spillere")
        print("  ✅ Best Position Rating - Bedste fra hver position")
        print("  ✅ Weighted Position Rating - Positionsvægtet gennemsnit")
        print("  ✅ Playing Time Weighted - Vægtet efter spilletid")
        
        print("\n🔧 KRITISKE FIXES IMPLEMENTERET:")
        print("  ✅ Korrekt indlæsning af spillernes ELO ratings fra CSV filer")
        print("  ✅ Separat processering af Herreliga og Kvindeliga")
        print("  ✅ Robust team mapping med kontekst-aware funktioner")
        print("  ✅ Fjernet afhængighed af MasterHandballEloSystem")
        print("  ✅ Forbedret fejlhåndtering og logging")


# === MAIN EXECUTION ===
if __name__ == "__main__":
    print("🏆 STARTER SPILLERBASERET HOLD ELO SYSTEM (FIXED)")
    print("=" * 80)
    
    # Create system instance
    player_team_system = PlayerBasedTeamEloSystem()
    
    # Run complete analysis
    player_team_system.run_complete_analysis()
    
    print("\n🎉 SPILLERBASERET TEAM SYSTEM KOMPLET (FIXED)!")
    print("=" * 80)
    print("🎯 Hold ratings bygget fra spillernes individuelle ELO ratings")
    print("🔄 Automatisk transfer tracking baseret på database analyse") 
    print("📊 Seks forskellige beregningsmetoder implementeret")
    print("🏆 Detaljeret sæson- og karriere analyse genereret")