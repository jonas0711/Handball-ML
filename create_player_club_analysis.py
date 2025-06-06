#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 SPILLER-KLUB ANALYSE GENERATOR
===============================

Genererer CSV filer med spillere organiseret efter klubber baseret på:
1. Player-based team ELO system resultater  
2. Database analyse af spilleres holdtilknytning
3. Separate filer for Herreliga og Kvindeliga
4. Detaljerede klubstatistikker

Jonas' Analysis Tool - December 2024
"""

import pandas as pd
import numpy as np
import sqlite3
import os
from collections import defaultdict, Counter
from typing import Dict, List

# Import team mappings from player_based_team_elo_system
from player_based_team_elo_system import (
    HERRELIGA_TEAMS, KVINDELIGA_TEAMS, ALL_TEAMS, 
    TEAM_NAME_MAPPINGS, MIN_GAMES_FOR_TEAM_INCLUSION
)

class PlayerClubAnalyzer:
    """
    🏆 ANALYSERER SPILLERE ORGANISERET EFTER KLUBBER
    """
    
    def __init__(self, base_dir: str = "."):
        print("🏆 SPILLER-KLUB ANALYSE GENERATOR")
        print("=" * 70)
        
        self.base_dir = base_dir
        self.herreliga_dir = os.path.join(base_dir, "Herreliga-database")
        self.kvindeliga_dir = os.path.join(base_dir, "Kvindeliga-database")
        self.player_csv_dir = os.path.join(base_dir, "ELO_Results", "Player_Seasonal_CSV")
        
        # Available seasons
        self.seasons = [
            "2017-2018", "2018-2019", "2019-2020", "2020-2021",
            "2021-2022", "2022-2023", "2023-2024", "2024-2025"
        ]
        
        print("✅ Player-Club analyzer initialiseret")
        print(f"📅 Tilgængelige sæsoner: {len(self.seasons)}")
        
    def get_team_code_from_name(self, team_name: str) -> str:
        """Mapper holdnavn til holdkode - duplikeret fra player_based_team_elo_system"""
        if not team_name:
            return "UNK"
            
        team_name_lower = team_name.lower().strip()
        
        # SPECIAL HANDLING for SønderjyskE
        if 'sønderjyske' in team_name_lower or 'sønderjyskE' in team_name:
            if any(keyword in team_name_lower for keyword in ['kvinde', 'women', 'damer']):
                return 'SJK'  # Kvindeliga
            elif any(keyword in team_name_lower for keyword in ['herre', 'men', 'herrer']):
                return 'SJH'  # Herreliga
            else:
                return 'SJE'  # Legacy code
        
        # First try exact mapping
        if team_name_lower in TEAM_NAME_MAPPINGS:
            return TEAM_NAME_MAPPINGS[team_name_lower]
            
        # Then try partial matching
        for mapping_name, code in TEAM_NAME_MAPPINGS.items():
            if mapping_name in team_name_lower or team_name_lower in mapping_name:
                return code
                
        # Legacy fallback
        for code, name in ALL_TEAMS.items():
            if name.lower() in team_name_lower or team_name_lower in name.lower():
                return code
                
        return team_name[:3].upper()
        
    def determine_player_teams_from_database(self, season: str) -> Dict[str, str]:
        """Bestemmer spillerens holdtilknytning baseret på database data"""
        print(f"  🔍 Analyserer spilleres holdtilknytning fra database for {season}")
        
        player_team_games = defaultdict(lambda: defaultdict(int))
        
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
                    
                    # Process match events
                    cursor.execute("SELECT * FROM match_events")
                    events = cursor.fetchall()
                    
                    for event in events:
                        try:
                            _, _, tid, maal, hold, haendelse_1, pos, nr_1, navn_1, haendelse_2, nr_2, navn_2, nr_mv, mv = event
                            
                            # Primary player
                            if navn_1 and navn_1.strip() and navn_1 not in ["Retur", "Bold erobret", "Assist"]:
                                if hold == hjemme_code or hold == hold_hjemme:
                                    team_code = hjemme_code
                                elif hold == ude_code or hold == hold_ude:
                                    team_code = ude_code
                                else:
                                    team_code = self.get_team_code_from_name(hold) if hold else "UNK"
                                    
                                player_team_games[navn_1.strip()][team_code] += 1
                                
                            # Goalkeeper  
                            if mv and mv.strip():
                                if hold == hjemme_code or hold == hold_hjemme:
                                    gk_team_code = ude_code
                                elif hold == ude_code or hold == hold_ude:
                                    gk_team_code = hjemme_code
                                else:
                                    gk_team_code = hjemme_code if hold != hjemme_code else ude_code
                                    
                                player_team_games[mv.strip()][gk_team_code] += 1
                                
                        except Exception as e:
                            continue
                            
                    conn.close()
                    
                except Exception as e:
                    print(f"    ⚠️ Fejl i {db_file}: {e}")
                    continue
                    
        # Determine primary team for each player
        player_teams = {}
        
        for player_name, team_games in player_team_games.items():
            if team_games:
                primary_team = max(team_games.items(), key=lambda x: x[1])
                
                if primary_team[1] >= MIN_GAMES_FOR_TEAM_INCLUSION:
                    player_teams[player_name] = primary_team[0]
                    
        print(f"    ✅ Fundet {len(player_teams)} spillere med holdtilknytning")
        return player_teams
        
    def load_player_ratings_for_season(self, season: str) -> pd.DataFrame:
        """Loader spillernes ELO ratings for en given sæson"""
        season_formatted = season.replace("-", "_")
        
        # Try different player data files
        combined_file = os.path.join(self.player_csv_dir, f"seasonal_elo_{season_formatted}.csv")
        herreliga_file = os.path.join(self.player_csv_dir, f"herreliga_seasonal_elo_{season_formatted}.csv")
        kvindeliga_file = os.path.join(self.player_csv_dir, f"kvindeliga_seasonal_elo_{season_formatted}.csv")
        
        dfs = []
        
        if os.path.exists(combined_file):
            df_combined = pd.read_csv(combined_file)
            dfs.append(df_combined)
            
        if os.path.exists(herreliga_file):
            df_herreliga = pd.read_csv(herreliga_file)
            dfs.append(df_herreliga)
            
        if os.path.exists(kvindeliga_file):
            df_kvindeliga = pd.read_csv(kvindeliga_file)
            dfs.append(df_kvindeliga)
            
        if not dfs:
            print(f"  ❌ Ingen spillerdata for {season}")
            return pd.DataFrame()
            
        # Combine and remove duplicates
        df_all = pd.concat(dfs, ignore_index=True)
        df_all = df_all.drop_duplicates(subset=['player'], keep='first')
        
        return df_all
        
    def create_club_analysis_for_season(self, season: str) -> Dict:
        """Laver klub analyse for en enkelt sæson"""
        print(f"\n🏐 ANALYSERER KLUB STRUKTUR FOR {season}")
        print("-" * 50)
        
        # Load player ratings
        player_df = self.load_player_ratings_for_season(season)
        
        if player_df.empty:
            print(f"  ❌ Ingen spillerdata for {season}")
            return {}
            
        # Determine player-team associations
        player_teams = self.determine_player_teams_from_database(season)
        
        if not player_teams:
            print(f"  ❌ Ingen holdtilknytninger fundet for {season}")
            return {}
            
        # Create club data
        club_data = {
            'herreliga': defaultdict(list),
            'kvindeliga': defaultdict(list),
            'unknown': defaultdict(list)
        }
        
        for _, player_row in player_df.iterrows():
            player_name = player_row['player']
            
            if player_name in player_teams:
                team_code = player_teams[player_name]
                
                # Handle legacy SJE code
                if team_code == 'SJE':
                    # Check if this is a women's team based on player data or context
                    # For now, we'll put it in a special category
                    team_code = 'SJK'  # Assume women's based on our analysis
                
                # Determine league
                if team_code in HERRELIGA_TEAMS:
                    league = 'herreliga'
                elif team_code in KVINDELIGA_TEAMS:
                    league = 'kvindeliga'
                else:
                    league = 'unknown'
                
                player_data = {
                    'player': player_name,
                    'team_code': team_code,
                    'team_name': ALL_TEAMS.get(team_code, team_code),
                    'final_rating': player_row['final_rating'],
                    'games': player_row['games'],
                    'primary_position': player_row['primary_position'],
                    'is_goalkeeper': player_row['is_goalkeeper'],
                    'elite_status': player_row['elite_status'],
                    'rating_change': player_row['rating_change']
                }
                
                club_data[league][team_code].append(player_data)
                
        return club_data
        
    def generate_club_csv_files(self, season: str, club_data: Dict):
        """Genererer CSV filer organiseret efter klubber"""
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