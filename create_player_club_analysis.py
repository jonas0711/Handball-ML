#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 SPILLER-KLUB ANALYSE GENERATOR (FIXED: SEPAREREDE LIGAER)
===========================================================

Genererer CSV filer med spillere organiseret efter klubber baseret på:
1. Player-based team ELO system resultater  
2. Database analyse af spilleres holdtilknytning
3. HELT SEPARATE processer for Herreliga og Kvindeliga
4. Detaljerede klubstatistikker

KRITISK FIX: Herre- og damespillere kan ALDRIG blandes sammen!

Jonas' Analysis Tool - December 2024
"""

import pandas as pd
import numpy as np
import sqlite3
import os
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

# Import central team configuration
from team_config import (
    HERRELIGA_TEAMS, KVINDELIGA_TEAMS, ALL_TEAMS,
    HERRELIGA_NAME_MAPPINGS, KVINDELIGA_NAME_MAPPINGS,
    MIN_GAMES_FOR_TEAM_INCLUSION, SKIP_TEAMS,
    PLAYER_NAME_ALIASES  # NEW: Import player aliases
)

class PlayerClubAnalyzer:
    """
    🏆 ANALYSERER SPILLERE ORGANISERET EFTER KLUBBER MED SEPARATE LIGAER
    """
    
    def __init__(self, base_dir: str = "."):
        print("🏆 SPILLER-KLUB ANALYSE GENERATOR (FIXED: SEPAREREDE LIGAER)")
        print("=" * 70)
        print("🔒 KRITISK FIX: Herre- og damespillere holdes HELT adskilt!")
        
        self.base_dir = base_dir
        self.herreliga_dir = os.path.join(base_dir, "Herreliga-database")
        self.kvindeliga_dir = os.path.join(base_dir, "Kvindeliga-database")
        self.player_csv_dir = os.path.join(base_dir, "ELO_Results", "Player_Seasonal_CSV")
        
        # Available seasons
        self.seasons = [
            "2017-2018", "2018-2019", "2019-2020", "2020-2021",
            "2021-2022", "2022-2023", "2023-2024", "2024-2025"
        ]
        
        print("✅ Player-Club analyzer initialiseret med separate liga-processer")
        print(f"📅 Tilgængelige sæsoner: {len(self.seasons)}")
        
    def _normalize_and_get_canonical_name(self, name: str) -> str:
        """
        NEW: Normalizes a player name and resolves it to its canonical version.
        Mirrors the logic from the ELO systems for consistency.
        """
        if not isinstance(name, str):
            return ""
        # Trim leading/trailing and remove double spaces
        normalized_name = " ".join(name.strip().split())
        
        # Check for an alias
        return PLAYER_NAME_ALIASES.get(normalized_name, normalized_name)

    def get_team_code_from_name(self, team_name: str, league_context: str) -> str:
        """
        FINAL VERSION: Handles both team codes and team names as input to prevent false warnings.
        """
        if not team_name:
            return "UNK"

        # Define primary and secondary contexts
        if league_context == 'herre':
            primary_teams = HERRELIGA_TEAMS
            primary_map = HERRELIGA_NAME_MAPPINGS
            secondary_map = KVINDELIGA_NAME_MAPPINGS
        elif league_context == 'kvinde':
            primary_teams = KVINDELIGA_TEAMS
            primary_map = KVINDELIGA_NAME_MAPPINGS
            secondary_map = HERRELIGA_NAME_MAPPINGS
        else:
            return "UNK" # Invalid context

        # Step 1: Check if the input is already a valid team code
        code_candidate = team_name.strip().upper()
        if code_candidate in ALL_TEAMS:
            if code_candidate in primary_teams:
                return code_candidate # It's a valid code for the correct league
            else:
                return "WRONG_LEAGUE" # It's a valid code, but for the other league

        # Step 2: If not a code, process it as a name
        clean_name = team_name.strip().lower()

        # Check primary context map
        if clean_name in primary_map:
            return primary_map[clean_name]
        for key, code in primary_map.items():
            if key in clean_name:
                return code
        
        # Check secondary context map SILENTLY
        if clean_name in secondary_map:
            return "WRONG_LEAGUE"
        for key in secondary_map.keys():
            if key in clean_name:
                return "WRONG_LEAGUE"

        # 3. If not found anywhere, check skip list and then print warning
        if code_candidate not in SKIP_TEAMS:
             print(f"⚠️ UNMAPPED TEAM in {league_context}: '{team_name}'")
             
        return "UNK"
        
    def determine_player_teams_from_database_separate(self, season: str) -> Tuple[Dict[str, str], Dict[str, str]]:
        """
        FIXED: Bestemmer spillerens holdtilknytning SEPARAT for hver liga
        Returns: (herreliga_player_teams, kvindeliga_player_teams)
        """
        print(f"  🔍 Analyserer spilleres holdtilknytning SEPARAT for hver liga - {season}")
        
        herreliga_player_teams = {}
        kvindeliga_player_teams = {}
        
        # === PROCESS HERRELIGA SEPARATELY ===
        print(f"    🔵 Processerer Herreliga spillere...")
        herreliga_player_games = defaultdict(lambda: defaultdict(set))
        
        herreliga_path = os.path.join(self.herreliga_dir, season)
        if os.path.exists(herreliga_path):
            db_files = [f for f in os.listdir(herreliga_path) if f.endswith('.db')]
            
            for db_file in db_files:
                db_path = os.path.join(herreliga_path, db_file)
                
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
                    
                    # Get team codes WITH HERRELIGA CONTEXT
                    hjemme_code = self.get_team_code_from_name(hold_hjemme, "herre")
                    ude_code = self.get_team_code_from_name(hold_ude, "herre")
                    
                    # VALIDATE: Only process if both teams are valid Herreliga teams and not in SKIP_TEAMS
                    if hjemme_code in SKIP_TEAMS or ude_code in SKIP_TEAMS:
                        conn.close()
                        continue

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
                                canonical_navn_1 = self._normalize_and_get_canonical_name(navn_1) # NORMALIZE
                                if hold == hjemme_code or hold == hold_hjemme:
                                    team_code = hjemme_code
                                elif hold == ude_code or hold == hold_ude:
                                    team_code = ude_code
                                else:
                                    team_code = self.get_team_code_from_name(hold, "herre") if hold else "UNK"
                                    
                                # ARMOR-PLATED VALIDATION: Only accept valid Herreliga teams
                                if team_code in HERRELIGA_TEAMS:
                                    herreliga_player_games[canonical_navn_1][team_code].add(db_file)
                                    
                            # FIXED: Secondary player (assists and other same-team events)
                            if navn_2 and navn_2.strip() and haendelse_2 and navn_2 not in ["Retur", "Bold erobret", "Forårs. str."]:
                                canonical_navn_2 = self._normalize_and_get_canonical_name(navn_2) # NORMALIZE
                                # CRITICAL: Assists belong to SAME team as primary action
                                if haendelse_2 == "Assist":
                                    if hold == hjemme_code or hold == hold_hjemme:
                                        assist_team_code = hjemme_code
                                    elif hold == ude_code or hold == hold_ude:
                                        assist_team_code = ude_code
                                    else:
                                        assist_team_code = self.get_team_code_from_name(hold, "herre") if hold else "UNK"
                                        
                                    # ARMOR-PLATED VALIDATION
                                    if assist_team_code in HERRELIGA_TEAMS:
                                        herreliga_player_games[canonical_navn_2][assist_team_code].add(db_file)
                                
                            # Goalkeeper  
                            if mv and mv.strip():
                                canonical_mv = self._normalize_and_get_canonical_name(mv) # NORMALIZE
                                if hold == hjemme_code or hold == hold_hjemme:
                                    gk_team_code = ude_code
                                elif hold == ude_code or hold == hold_ude:
                                    gk_team_code = hjemme_code
                                else:
                                    gk_team_code = hjemme_code if hold != hjemme_code else ude_code
                                    
                                # ARMOR-PLATED VALIDATION
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
                # Filter out UNK teams before finding the max
                valid_teams = {team: games for team, games in team_games.items() if team != "UNK"}
                if not valid_teams:
                    continue

                primary_team = max(valid_teams.items(), key=lambda x: len(x[1]))
                
                if len(primary_team[1]) >= MIN_GAMES_FOR_TEAM_INCLUSION and primary_team[0] in HERRELIGA_TEAMS:
                    herreliga_player_teams[player_name] = primary_team[0]
        
        print(f"    ✅ Herreliga: {len(herreliga_player_teams)} spillere")
        
        # === PROCESS KVINDELIGA SEPARATELY ===
        print(f"    🔴 Processerer Kvindeliga spillere...")
        kvindeliga_player_games = defaultdict(lambda: defaultdict(set))
        
        kvindeliga_path = os.path.join(self.kvindeliga_dir, season)
        if os.path.exists(kvindeliga_path):
            db_files = [f for f in os.listdir(kvindeliga_path) if f.endswith('.db')]
            
            for db_file in db_files:
                db_path = os.path.join(kvindeliga_path, db_file)
                
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
                    
                    # Get team codes WITH KVINDELIGA CONTEXT
                    hjemme_code = self.get_team_code_from_name(hold_hjemme, "kvinde")
                    ude_code = self.get_team_code_from_name(hold_ude, "kvinde")
                    
                    # VALIDATE: Only process if both teams are valid Kvindeliga teams and not in SKIP_TEAMS
                    if hjemme_code in SKIP_TEAMS or ude_code in SKIP_TEAMS:
                        conn.close()
                        continue

                    if hjemme_code not in KVINDELIGA_TEAMS or ude_code not in KVINDELIGA_TEAMS:
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
                                canonical_navn_1 = self._normalize_and_get_canonical_name(navn_1) # NORMALIZE
                                if hold == hjemme_code or hold == hold_hjemme:
                                    team_code = hjemme_code
                                elif hold == ude_code or hold == hold_ude:
                                    team_code = ude_code
                                else:
                                    team_code = self.get_team_code_from_name(hold, "kvinde") if hold else "UNK"
                                    
                                # ARMOR-PLATED VALIDATION: Only accept valid Kvindeliga teams
                                if team_code in KVINDELIGA_TEAMS:
                                    kvindeliga_player_games[canonical_navn_1][team_code].add(db_file)
                                    
                            # FIXED: Secondary player (assists and other same-team events)
                            if navn_2 and navn_2.strip() and haendelse_2 and navn_2 not in ["Retur", "Bold erobret", "Forårs. str."]:
                                canonical_navn_2 = self._normalize_and_get_canonical_name(navn_2) # NORMALIZE
                                # CRITICAL: Assists belong to SAME team as primary action
                                if haendelse_2 == "Assist":
                                    if hold == hjemme_code or hold == hold_hjemme:
                                        assist_team_code = hjemme_code
                                    elif hold == ude_code or hold == hold_ude:
                                        assist_team_code = ude_code
                                    else:
                                        assist_team_code = self.get_team_code_from_name(hold, "kvinde") if hold else "UNK"
                                        
                                    # ARMOR-PLATED VALIDATION
                                    if assist_team_code in KVINDELIGA_TEAMS:
                                        kvindeliga_player_games[canonical_navn_2][assist_team_code].add(db_file)
                                
                            # Goalkeeper  
                            if mv and mv.strip():
                                canonical_mv = self._normalize_and_get_canonical_name(mv) # NORMALIZE
                                if hold == hjemme_code or hold == hold_hjemme:
                                    gk_team_code = ude_code
                                elif hold == ude_code or hold == hold_ude:
                                    gk_team_code = hjemme_code
                                else:
                                    gk_team_code = hjemme_code if hold != hjemme_code else ude_code
                                    
                                # ARMOR-PLATED VALIDATION
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
                # Filter out UNK teams before finding the max
                valid_teams = {team: games for team, games in team_games.items() if team != "UNK"}
                if not valid_teams:
                    continue
                    
                primary_team = max(valid_teams.items(), key=lambda x: len(x[1]))
                
                if len(primary_team[1]) >= MIN_GAMES_FOR_TEAM_INCLUSION and primary_team[0] in KVINDELIGA_TEAMS:
                    kvindeliga_player_teams[player_name] = primary_team[0]
        
        print(f"    ✅ Kvindeliga: {len(kvindeliga_player_teams)} spillere")
        
        return herreliga_player_teams, kvindeliga_player_teams
        
    def load_player_ratings_for_season_separate(self, season: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        FIXED: Loader spillernes ELO ratings SEPARAT for hver liga
        Splitter combined fil baseret på holdtilknytninger hvis separate filer ikke eksisterer
        Returns: (herreliga_df, kvindeliga_df)
        """
        season_formatted = season.replace("-", "_")
        
        # Load separate files for each league
        combined_file = os.path.join(self.player_csv_dir, f"seasonal_elo_{season_formatted}.csv")
        herreliga_file = os.path.join(self.player_csv_dir, f"herreliga_seasonal_elo_{season_formatted}.csv")
        kvindeliga_file = os.path.join(self.player_csv_dir, f"kvindeliga_seasonal_elo_{season_formatted}.csv")
        
        herreliga_df = pd.DataFrame()
        kvindeliga_df = pd.DataFrame()
        
        # Try to load Herreliga data
        if os.path.exists(herreliga_file):
            herreliga_df = pd.read_csv(herreliga_file)
            print(f"    📊 Herreliga: {len(herreliga_df)} spillere indlæst")
        
        # Try to load Kvindeliga data  
        if os.path.exists(kvindeliga_file):
            kvindeliga_df = pd.read_csv(kvindeliga_file)
            print(f"    📊 Kvindeliga: {len(kvindeliga_df)} spillere indlæst")
        
        # If no separate files exist, split combined file using team mappings
        if herreliga_df.empty and kvindeliga_df.empty and os.path.exists(combined_file):
            print(f"    🔄 Splitter combined fil baseret på holdtilknytninger...")
            combined_df = pd.read_csv(combined_file)
            
            # Get player-team associations for separation
            herreliga_player_teams, kvindeliga_player_teams = self.determine_player_teams_from_database_separate(season)
            
            # Split based on player team associations
            herreliga_players = []
            kvindeliga_players = []
            
            for _, player_row in combined_df.iterrows():
                player_name = player_row['player']
                
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
        
    def create_club_analysis_for_season(self, season: str) -> Dict:
        """FIXED: Laver klub analyse for en enkelt sæson med SEPARATE processer"""
        print(f"\n🏐 ANALYSERER KLUB STRUKTUR FOR {season} (SEPARATE LIGAER)")
        print("-" * 50)
        
        # Load player ratings SEPARATELY
        herreliga_df, kvindeliga_df = self.load_player_ratings_for_season_separate(season)
        
        # Determine player-team associations SEPARATELY
        herreliga_player_teams, kvindeliga_player_teams = self.determine_player_teams_from_database_separate(season)
        
        # Create club data with STRICT separation
        club_data = {
            'herreliga': defaultdict(list),
            'kvindeliga': defaultdict(list),
            'unknown': defaultdict(list)
        }
        
        # === PROCESS HERRELIGA PLAYERS ===
        if not herreliga_df.empty and herreliga_player_teams:
            print(f"    🔵 Processerer {len(herreliga_df)} Herreliga spillere...")
            
            for _, player_row in herreliga_df.iterrows():
                player_name = self._normalize_and_get_canonical_name(player_row['player']) # NORMALIZE
                
                if player_name in herreliga_player_teams:
                    team_code = herreliga_player_teams[player_name]
                    
                    # CRITICAL VALIDATION: Only accept Herreliga teams
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
                        'rating_change': player_row['rating_change']
                    }
                    
                    club_data['herreliga'][team_code].append(player_data)
        
        # === PROCESS KVINDELIGA PLAYERS ===
        if not kvindeliga_df.empty and kvindeliga_player_teams:
            print(f"    🔴 Processerer {len(kvindeliga_df)} Kvindeliga spillere...")
            
            for _, player_row in kvindeliga_df.iterrows():
                player_name = self._normalize_and_get_canonical_name(player_row['player']) # NORMALIZE
                
                if player_name in kvindeliga_player_teams:
                    team_code = kvindeliga_player_teams[player_name]
                    
                    # CRITICAL VALIDATION: Only accept Kvindeliga teams
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
                        'rating_change': player_row['rating_change']
                    }
                    
                    club_data['kvindeliga'][team_code].append(player_data)
        
        # Print results
        herreliga_teams = len(club_data['herreliga'])
        kvindeliga_teams = len(club_data['kvindeliga'])
        herreliga_players = sum(len(players) for players in club_data['herreliga'].values())
        kvindeliga_players = sum(len(players) for players in club_data['kvindeliga'].values())
        
        print(f"    ✅ Resultat: {herreliga_teams} Herreliga hold ({herreliga_players} spillere)")
        print(f"    ✅ Resultat: {kvindeliga_teams} Kvindeliga hold ({kvindeliga_players} spillere)")
        
        return club_data
        
    def generate_club_csv_files(self, season: str, club_data: Dict):
        """FIXED: Genererer CSV filer organiseret efter klubber med korrekte team mappings"""
        if not club_data:
            return
            
        output_dir = os.path.join("ELO_Results", "Player_Club_Analysis")
        os.makedirs(output_dir, exist_ok=True)
        
        season_formatted = season.replace("-", "_")
        
        for league, teams in club_data.items():
            if not teams:
                continue
                
            print(f"\n📊 GENERERER {league.upper()} KLUB FILER:")
            
            # Create league summary
            league_players = []
            club_stats = []
            
            for team_code, players in teams.items():
                if not players:
                    continue
                    
                # FIXED: Use correct team name based on league
                if league == 'herreliga':
                    team_name = HERRELIGA_TEAMS.get(team_code, team_code)
                elif league == 'kvindeliga':
                    team_name = KVINDELIGA_TEAMS.get(team_code, team_code)
                else:
                    team_name = ALL_TEAMS.get(team_code, team_code)
                
                # Player data
                for player in players:
                    league_players.append(player)
                    
                # Club statistics
                ratings = [p['final_rating'] for p in players]
                games = [p['games'] for p in players]
                positions = [p['primary_position'] for p in players]
                elite_count = sum(1 for p in players if p['elite_status'] in ['ELITE', 'LEGENDARY'])
                goalkeeper_count = sum(1 for p in players if p['is_goalkeeper'])
                
                club_stats.append({
                    'team_code': team_code,
                    'team_name': team_name,
                    'total_players': len(players),
                    'avg_rating': round(np.mean(ratings), 1),
                    'max_rating': round(max(ratings), 1),
                    'min_rating': round(min(ratings), 1),
                    'total_games': sum(games),
                    'avg_games_per_player': round(np.mean(games), 1),
                    'elite_players': elite_count,
                    'goalkeepers': goalkeeper_count,
                    'positions_represented': len(set(positions)),
                    'position_distribution': dict(Counter(positions))
                })
                
            # Save individual club files
            for team_code, players in teams.items():
                if not players:
                    continue
                    
                # FIXED: Use correct team name based on league
                if league == 'herreliga':
                    team_name = HERRELIGA_TEAMS.get(team_code, team_code)
                elif league == 'kvindeliga':
                    team_name = KVINDELIGA_TEAMS.get(team_code, team_code)
                else:
                    team_name = ALL_TEAMS.get(team_code, team_code)
                    
                df_team = pd.DataFrame(players)
                df_team = df_team.sort_values('final_rating', ascending=False)
                
                filename = f"{league}_{team_code}_{team_name.replace(' ', '_').replace('-', '_')}_{season_formatted}.csv"
                filepath = os.path.join(output_dir, filename)
                df_team.to_csv(filepath, index=False)
                
                print(f"  💾 {team_code}: {len(players)} spillere → {filename}")
                
            # Save league summary
            if league_players:
                df_league = pd.DataFrame(league_players)
                df_league = df_league.sort_values('final_rating', ascending=False)
                
                league_filename = f"{league}_all_players_{season_formatted}.csv"
                league_filepath = os.path.join(output_dir, league_filename)
                df_league.to_csv(league_filepath, index=False)
                
                print(f"  📊 {league.upper()} Summary: {len(league_players)} spillere → {league_filename}")
                
            # Save club statistics
            if club_stats:
                df_clubs = pd.DataFrame(club_stats)
                df_clubs = df_clubs.sort_values('avg_rating', ascending=False)
                
                clubs_filename = f"{league}_club_statistics_{season_formatted}.csv"
                clubs_filepath = os.path.join(output_dir, clubs_filename)
                df_clubs.to_csv(clubs_filepath, index=False)
                
                print(f"  📈 {league.upper()} Club Stats: {len(club_stats)} klubber → {clubs_filename}")
                
                # Show top clubs
                print(f"    🏆 Top 5 {league.upper()} klubber:")
                for i, (_, club) in enumerate(df_clubs.head(5).iterrows(), 1):
                    print(f"      {i}. {club['team_name']}: {club['avg_rating']:.0f} avg "
                          f"({club['total_players']} spillere, {club['elite_players']} elite)")
        
    def run_complete_analysis(self):
        """Kører komplet klub analyse for alle sæsoner"""
        print("🚀 STARTER KOMPLET KLUB ANALYSE")
        print("=" * 70)
        
        for season in self.seasons:
            club_data = self.create_club_analysis_for_season(season)
            
            if club_data:
                self.generate_club_csv_files(season, club_data)
            else:
                print(f"⚠️ Springer over {season} - ingen klub data")
                
        print(f"\n✅ KLUB ANALYSE KOMPLET!")
        print("=" * 70)
        print("📁 Genererede filer i ELO_Results/Player_Club_Analysis/:")
        print("  • Individuelle hold filer per sæson")
        print("  • Liga sammendrag per sæson") 
        print("  • Klub statistikker per sæson")
        print("\n🎯 Analyse omfatter:")
        print("  ✅ Spillere organiseret efter klubber")
        print("  ✅ Separate Herreliga og Kvindeliga filer")
        print("  ✅ Detaljerede klubstatistikker")
        print("  ✅ ELO ratings og spillerdata")


if __name__ == "__main__":
    print("🏆 STARTER SPILLER-KLUB ANALYSE GENERATOR")
    print("=" * 80)
    
    # Create analyzer instance
    analyzer = PlayerClubAnalyzer()
    
    # Run complete analysis
    analyzer.run_complete_analysis()
    
    print("\n🎉 SPILLER-KLUB ANALYSE KOMPLET!")
    print("=" * 80) 