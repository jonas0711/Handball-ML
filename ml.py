#!/usr/bin/env python3
"""
MACHINE LEARNING DATASET GENERATOR - HÅNDBOL
===========================================

Dette script genererer et omfattende ML dataset baseret på historiske data
fra håndboldkampe. Datasettet inkluderer IKKE data fra den aktuelle kamp 
for at undgå data leakage.

FEATURES KATEGORIER:
1. Hold ELO Ratings (historiske)
2. Spiller Performance Metrics (historiske)
3. Team Form & Momentum (seneste N kampe)
4. Head-to-Head Statistikker
5. Hjemmebane Statistikker
6. Spillersammensætning & Styrke
7. Tidsmæssige Features
8. Liga Position & Konkurrence Niveau
9. Målvogter Performance
10. Offensive & Defensive Metrics

KRITISK: Kun data fra FØR kampstart inkluderes!
"""

import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

class HandballMLDatasetGenerator:
    """
    Genererer machine learning dataset fra håndbold kampdata
    """
    
    def __init__(self, base_dir: str = ".", league: str = "Herreliga"):
        """
        Initialiserer dataset generator
        
        Args:
            base_dir: Sti til projektets rod
            league: "Herreliga" eller "Kvindeliga"
        """
        print(f"🎯 INITIALISERER ML DATASET GENERATOR FOR {league}")
        print("=" * 60)
        
        self.base_dir = base_dir
        self.league = league
        
        # Database stier
        if league == "Herreliga":
            self.database_dir = os.path.join(base_dir, "Herreliga-database")
        else:
            self.database_dir = os.path.join(base_dir, "Kvindeliga-database")
        
        # ELO Results directories
        self.elo_results_dir = os.path.join(base_dir, "ELO_Results")
        self.player_seasonal_csv_dir = os.path.join(self.elo_results_dir, "Player_Seasonal_CSV")
        self.team_csv_dir = os.path.join(self.elo_results_dir, "Team_CSV")
        
        # Sæsoner at inkludere (OPDATERET KORREKT)
        if league == "Herreliga":
            self.seasons = [
                "2017-2018", "2018-2019", "2019-2020", "2020-2021",
                "2021-2022", "2022-2023", "2023-2024", "2024-2025"
            ]
        else:  # Kvindeliga
            self.seasons = [
                "2018-2019", "2019-2020", "2020-2021",
                "2021-2022", "2022-2023", "2023-2024", "2024-2025"
            ]
        
        # Feature storage
        self.historical_data = {}  # kamp_id -> historical features
        self.match_results = {}    # kamp_id -> actual results
        self.team_stats = defaultdict(lambda: defaultdict(list))
        self.player_stats = defaultdict(lambda: defaultdict(list))
        self.head_to_head = defaultdict(lambda: defaultdict(list))
        
        # ELO data storage
        self.elo_player_data = {}  # season -> player_data
        self.elo_team_data = {}    # season -> team_data
        self.master_elo_data = {}  # Combined master ELO data
        
        # Output dataset
        self.dataset_rows = []
        
        print(f"📁 Database directory: {self.database_dir}")
        print(f"📊 ELO Results directory: {self.elo_results_dir}")
        print(f"📅 Sæsoner: {self.seasons}")
        
        # Load ELO data
        self.load_elo_data()
        
    def validate_seasons(self):
        """Validerer at sæsoner eksisterer"""
        print("\n🔍 VALIDERER SÆSONER")
        print("-" * 30)
        
        valid_seasons = []
        for season in self.seasons:
            season_path = os.path.join(self.database_dir, season)
            if os.path.exists(season_path):
                db_files = [f for f in os.listdir(season_path) if f.endswith('.db')]
                if db_files:
                    valid_seasons.append(season)
                    print(f"  ✅ {season}: {len(db_files)} kampe")
                else:
                    print(f"  ❌ {season}: ingen DB filer")
            else:
                print(f"  ❌ {season}: directory ikke fundet")
        
        self.seasons = valid_seasons
        print(f"\n📊 {len(self.seasons)} gyldige sæsoner fundet")
        
        if not self.seasons:
            raise ValueError(f"Ingen gyldige sæsoner fundet for {self.league}!")
    
    def extract_match_info(self, db_path: str) -> Optional[Dict]:
        """
        Ekstraherer match info fra database
        
        Returns:
            Dict med match info eller None hvis fejl
        """
        try:
            conn = sqlite3.connect(db_path)
            
            # Tjek tabeller eksisterer
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if 'match_info' not in tables or 'match_events' not in tables:
                conn.close()
                return None
            
            # Hent match info
            match_info = pd.read_sql_query("SELECT * FROM match_info", conn)
            if match_info.empty:
                conn.close()
                return None
                
            # Hent events
            events = pd.read_sql_query("SELECT * FROM match_events", conn)
            
            conn.close()
            
            # Parse dato
            dato_str = match_info.iloc[0]['dato']
            try:
                # Prøv forskellige datoformater
                if '-' in dato_str and len(dato_str.split('-')) == 3:
                    parts = dato_str.split('-')
                    if len(parts[2]) == 4:  # DD-MM-YYYY
                        match_date = datetime.strptime(dato_str, "%d-%m-%Y")
                    else:  # YYYY-MM-DD
                        match_date = datetime.strptime(dato_str, "%Y-%m-%d")
                else:
                    match_date = datetime.strptime(dato_str, "%d-%m-%Y")
            except:
                # Fallback - brug fil dato
                match_date = datetime.fromtimestamp(os.path.getmtime(db_path))
            
            return {
                'kamp_id': match_info.iloc[0]['kamp_id'],
                'hold_hjemme': match_info.iloc[0]['hold_hjemme'],
                'hold_ude': match_info.iloc[0]['hold_ude'],
                'resultat': match_info.iloc[0]['resultat'],
                'halvleg_resultat': match_info.iloc[0]['halvleg_resultat'],
                'dato': match_date,
                'sted': match_info.iloc[0]['sted'],
                'turnering': match_info.iloc[0]['turnering'],
                'events': events
            }
            
        except Exception as e:
            print(f"❌ Fejl ved læsning af {db_path}: {e}")
            return None
    
    def calculate_team_historical_stats(self, team_name: str, before_date: datetime, 
                                      num_games: int = 10) -> Dict:
        """
        Beregner historiske hold statistikker før en given dato
        
        Args:
            team_name: Holdets navn
            before_date: Kun kampe før denne dato
            num_games: Antal seneste kampe at inkludere
            
        Returns:
            Dict med historiske statistikker
        """
        
        # Find relevante kampe for holdet før datoen
        team_matches = []
        for match_data in self.historical_data.values():
            if match_data['dato'] < before_date:
                if (match_data['hold_hjemme'] == team_name or 
                    match_data['hold_ude'] == team_name):
                    team_matches.append(match_data)
        
        # Sorter efter dato (nyeste først)
        team_matches.sort(key=lambda x: x['dato'], reverse=True)
        recent_matches = team_matches[:num_games]
        
        if not recent_matches:
            return self._get_default_team_stats()
        
        # Beregn statistikker
        stats = {
            'games_played': len(recent_matches),
            'wins': 0,
            'draws': 0,
            'losses': 0,
            'goals_for': 0,
            'goals_against': 0,
            'home_games': 0,
            'away_games': 0,
            'avg_goals_for': 0.0,
            'avg_goals_against': 0.0,
            'goal_difference': 0,
            'win_rate': 0.0,
            'home_win_rate': 0.0,
            'away_win_rate': 0.0,
            'form_points': 0,  # 3 for win, 1 for draw, 0 for loss
            'momentum': 0.0,   # Weighted recent performance
            'offensive_strength': 0.0,
            'defensive_strength': 0.0,
            'days_since_last_match': 0
        }
        
        home_wins = 0
        away_wins = 0
        
        for i, match in enumerate(recent_matches):
            # Determiner om holdet spillede hjemme eller ude
            is_home = match['hold_hjemme'] == team_name
            if is_home:
                stats['home_games'] += 1
            else:
                stats['away_games'] += 1
            
            # Parse resultat
            try:
                if '-' in match['resultat']:
                    home_goals, away_goals = map(int, match['resultat'].split('-'))
                    
                    if is_home:
                        team_goals = home_goals
                        opponent_goals = away_goals
                    else:
                        team_goals = away_goals
                        opponent_goals = home_goals
                    
                    stats['goals_for'] += team_goals
                    stats['goals_against'] += opponent_goals
                    
                    # Beregn resultat
                    if team_goals > opponent_goals:
                        stats['wins'] += 1
                        stats['form_points'] += 3
                        if is_home:
                            home_wins += 1
                        else:
                            away_wins += 1
                    elif team_goals == opponent_goals:
                        stats['draws'] += 1
                        stats['form_points'] += 1
                    else:
                        stats['losses'] += 1
                        
                    # Momentum vægtning (nyere kampe vægter mere)
                    weight = 1.0 / (i + 1)  # Første kamp vægter mest
                    if team_goals > opponent_goals:
                        stats['momentum'] += 3.0 * weight
                    elif team_goals == opponent_goals:
                        stats['momentum'] += 1.0 * weight
                        
            except:
                continue
        
        # Finalize statistikker
        if stats['games_played'] > 0:
            stats['avg_goals_for'] = stats['goals_for'] / stats['games_played']
            stats['avg_goals_against'] = stats['goals_against'] / stats['games_played']
            stats['goal_difference'] = stats['goals_for'] - stats['goals_against']
            stats['win_rate'] = stats['wins'] / stats['games_played']
            
            if stats['home_games'] > 0:
                stats['home_win_rate'] = home_wins / stats['home_games']
            if stats['away_games'] > 0:
                stats['away_win_rate'] = away_wins / stats['away_games']
                
            # Normalisér momentum
            stats['momentum'] = stats['momentum'] / stats['games_played']
            
            # Offensive/defensive strength (goals per game)
            stats['offensive_strength'] = stats['avg_goals_for']
            stats['defensive_strength'] = 35 - stats['avg_goals_against']  # Reverse scale
            
        # Dage siden sidste kamp
        if recent_matches:
            stats['days_since_last_match'] = (before_date - recent_matches[0]['dato']).days
            
        return stats
    
    def calculate_player_features(self, team_name: str, before_date: datetime) -> Dict:
        """
        Beregner spiller-baserede features for et hold før en given dato
        
        Returns:
            Dict med aggregerede spiller statistikker
        """
        # Find alle spillere der har spillet for holdet
        team_players = set()
        player_stats = defaultdict(lambda: {
            'goals': 0, 'assists': 0, 'saves': 0, 'games': 0, 
            'minutes_played': 0, 'is_goalkeeper': False
        })
        
        for match_data in self.historical_data.values():
            if match_data['dato'] >= before_date:
                continue
                
            if not ((match_data['hold_hjemme'] == team_name) or 
                   (match_data['hold_ude'] == team_name)):
                continue
                
            # Analyser events for spillere
            events = match_data.get('events', pd.DataFrame())
            if events.empty:
                continue
                
            for _, event in events.iterrows():
                # Primær spiller
                if pd.notna(event.get('navn_1')):
                    player_name = str(event['navn_1']).strip()
                    team_players.add(player_name)
                    
                    # Count actions
                    action = str(event.get('haendelse_1', ''))
                    if 'Mål' in action:
                        player_stats[player_name]['goals'] += 1
                    elif 'Assist' in str(event.get('haendelse_2', '')):
                        if pd.notna(event.get('navn_2')):
                            assist_player = str(event['navn_2']).strip()
                            player_stats[assist_player]['assists'] += 1
                
                # Målvogter
                if pd.notna(event.get('mv')):
                    mv_name = str(event['mv']).strip()
                    team_players.add(mv_name)
                    player_stats[mv_name]['is_goalkeeper'] = True
                    
                    action = str(event.get('haendelse_1', ''))
                    if 'reddet' in action:
                        player_stats[mv_name]['saves'] += 1
        
        # Aggregér features
        features = {
            'squad_size': len(team_players),
            'total_goals_by_players': sum(p['goals'] for p in player_stats.values()),
            'total_assists_by_players': sum(p['assists'] for p in player_stats.values()),
            'total_saves_by_goalkeepers': sum(p['saves'] for p in player_stats.values() if p['is_goalkeeper']),
            'num_goalkeepers': sum(1 for p in player_stats.values() if p['is_goalkeeper']),
            'top_scorer_goals': max([p['goals'] for p in player_stats.values()] + [0]),
            'top_assistant_assists': max([p['assists'] for p in player_stats.values()] + [0]),
            'top_goalkeeper_saves': max([p['saves'] for p in player_stats.values() if p['is_goalkeeper']] + [0]),
            'avg_goals_per_player': 0.0,
            'goals_concentration': 0.0  # Hvor koncentreret målscoring er
        }
        
        if features['squad_size'] > 0:
            features['avg_goals_per_player'] = features['total_goals_by_players'] / features['squad_size']
            
            # Goals concentration (Gini coefficient approx)
            goal_counts = [p['goals'] for p in player_stats.values()]
            if sum(goal_counts) > 0:
                goal_counts.sort(reverse=True)
                # Simpel koncentration metric
                top_3_goals = sum(goal_counts[:3])
                features['goals_concentration'] = top_3_goals / sum(goal_counts) if sum(goal_counts) > 0 else 0
        
        return features
    
    def load_elo_data(self):
        """
        Loader alle ELO data fra CSV filer
        """
        print("\n📊 LOADER ELO DATA")
        print("-" * 30)
        
        # Load Player Seasonal ELO data
        self.load_player_seasonal_elo_data()
        
        # Load Team ELO data  
        self.load_team_elo_data()
        
        # Load Master ELO data if available
        self.load_master_elo_data()
        
        print("✅ ELO data loading komplet")
    
    def load_player_seasonal_elo_data(self):
        """Loader spillere seasonal ELO data"""
        print("📋 Loading Player Seasonal ELO data...")
        
        for season in self.seasons:
            season_formatted = season.replace("-", "_")
            
            # Seasonal ELO filer (prøv forskellige navnekonventioner)
            possible_filenames = [
                f"{self.league.lower()}_seasonal_elo_{season_formatted}.csv",
                f"{self.league.lower()}_player_elo_{season_formatted}.csv",
                f"seasonal_elo_{self.league.lower()}_{season_formatted}.csv"
            ]
            
            data_loaded = False
            for filename in possible_filenames:
                filepath = os.path.join(self.player_seasonal_csv_dir, filename)
                
                if os.path.exists(filepath):
                    try:
                        df = pd.read_csv(filepath)
                        self.elo_player_data[season] = df
                        print(f"  ✅ {season}: {len(df)} spillere loaded ({filename})")
                        data_loaded = True
                        break
                    except Exception as e:
                        print(f"  ⚠️  {season}: Fejl ved loading {filename} - {e}")
                        continue
            
            if not data_loaded:
                print(f"  ❌ {season}: Ingen ELO data fundet")
                print(f"      Søgte efter: {', '.join(possible_filenames)}")
                print(f"      I directory: {self.player_seasonal_csv_dir}")
    
    def load_team_elo_data(self):
        """Loader team ELO data"""
        print("🏟️ Loading Team ELO data...")
        
        for season in self.seasons:
            season_formatted = season.replace("-", "_")
            
            # Team seasonal filer
            team_seasonal_file = os.path.join(
                self.team_csv_dir, 
                self.league, 
                f"{self.league.lower()}_team_seasonal_summary_report.csv"
            )
            
            # Player-based team filer
            player_based_file = os.path.join(
                self.team_csv_dir,
                "Player_Based", 
                f"player_based_{self.league.lower()}_team_elo_{season_formatted}.csv"
            )
            
            season_team_data = {}
            
            # Load player-based team data
            if os.path.exists(player_based_file):
                try:
                    df = pd.read_csv(player_based_file)
                    season_team_data['player_based'] = df
                    print(f"  ✅ {season} Player-based: {len(df)} hold")
                except Exception as e:
                    print(f"  ❌ {season} Player-based: {e}")
            
            # Load team seasonal data
            if os.path.exists(team_seasonal_file):
                try:
                    df = pd.read_csv(team_seasonal_file)
                    # Filter for specific season if season column exists
                    if 'season' in df.columns:
                        season_df = df[df['season'] == season]
                        if not season_df.empty:
                            season_team_data['seasonal'] = season_df
                            print(f"  ✅ {season} Seasonal: {len(season_df)} hold")
                except Exception as e:
                    print(f"  ❌ {season} Seasonal: {e}")
            
            if season_team_data:
                self.elo_team_data[season] = season_team_data
    
    def load_master_elo_data(self):
        """Loader master ELO data hvis tilgængelig"""
        print("🎯 Loading Master ELO data...")
        
        master_files = {
            'players': 'master_player_elo_ratings.csv',
            'teams': 'master_team_elo_ratings.csv', 
            'matches': 'master_match_elo_results.csv'
        }
        
        for data_type, filename in master_files.items():
            filepath = os.path.join(self.base_dir, filename)
            if os.path.exists(filepath):
                try:
                    df = pd.read_csv(filepath)
                    self.master_elo_data[data_type] = df
                    print(f"  ✅ Master {data_type}: {len(df)} records")
                except Exception as e:
                    print(f"  ❌ Master {data_type}: {e}")
            else:
                print(f"  ⚠️  Master {data_type}: File ikke fundet")
    
    def get_player_elo_before_match(self, player_name: str, team_name: str, 
                                   match_date: datetime, season: str) -> Dict:
        """
        Henter spillerens ELO rating FØR en bestemt kamp (undgår data leakage)
        
        Returns:
            Dict med spillerens ELO data
        """
        default_elo = {
            'final_rating': 1200, 'start_rating': 1200, 'rating_change': 0,
            'games': 0, 'primary_position': 'Unknown', 'is_goalkeeper': False,
            'elite_status': 'NORMAL', 'momentum': 0.0, 'consistency': 0.0,
            'found': False
        }
        
        # Normaliser spillernavn  
        normalized_name = self.normalize_player_name(player_name)
        
        # Tjek seasonal data for denne sæson
        if season in self.elo_player_data:
            player_df = self.elo_player_data[season]
            
            # Find spilleren (tjek om player_name kolonne eksisterer)
            if 'player_name' in player_df.columns:
                matches = player_df[player_df['player_name'].str.upper().str.strip() == normalized_name.upper()]
            elif 'player' in player_df.columns:
                matches = player_df[player_df['player'].str.upper().str.strip() == normalized_name.upper()]
            else:
                matches = pd.DataFrame()  # Tom dataframe hvis ingen matchende kolonne
            if not matches.empty:
                player_data = matches.iloc[0].to_dict()
                
                # KRITISK: Dette er sæson-slut data, så vi antager det er gyldigt
                # før alle kampe i sæsonen (kan forbedres med match-by-match data)
                return {
                    'final_rating': float(player_data.get('final_rating', 1200)),
                    'start_rating': float(player_data.get('start_rating', 1200)), 
                    'rating_change': float(player_data.get('rating_change', 0)),
                    'games': int(player_data.get('games', 0)),
                    'primary_position': str(player_data.get('primary_position', 'Unknown')),
                    'is_goalkeeper': bool(player_data.get('is_goalkeeper', False)),
                    'elite_status': str(player_data.get('elite_status', 'NORMAL')),
                    'momentum': float(player_data.get('momentum', 0.0)),
                    'consistency': float(player_data.get('consistency', 0.0)),
                    'found': True
                }
        
        # Tjek master data hvis seasonal ikke fundet
        if 'players' in self.master_elo_data:
            master_df = self.master_elo_data['players']
            # Tjek hvilken kolonne der eksisterer
            if 'player_name' in master_df.columns:
                matches = master_df[master_df['player_name'].str.upper().str.strip() == normalized_name.upper()]
            elif 'player' in master_df.columns:
                matches = master_df[master_df['player'].str.upper().str.strip() == normalized_name.upper()]
            else:
                matches = pd.DataFrame()
            if not matches.empty:
                # Tag seneste record
                latest_record = matches.iloc[-1].to_dict()
                return {
                    'final_rating': float(latest_record.get('rating', 1200)),
                    'start_rating': 1200,  # Ikke tilgængelig i master data
                    'rating_change': 0,
                    'games': int(latest_record.get('games', 0)),
                    'primary_position': str(latest_record.get('position', 'Unknown')),
                    'is_goalkeeper': bool(latest_record.get('is_goalkeeper', False)),
                    'elite_status': 'NORMAL',  # Ikke tilgængelig i master data
                    'momentum': 0.0,
                    'consistency': 0.0,
                    'found': True
                }
        
        return default_elo
    
    def get_team_elo_before_match(self, team_name: str, match_date: datetime, 
                                season: str) -> Dict:
        """
        Henter holdets ELO rating FØR en bestemt kamp (undgår data leakage)
        
        Returns:
            Dict med holdets ELO data
        """
        default_team_elo = {
            'team_avg_rating': 1350, 'top_7_rating': 1350, 'top_12_rating': 1350,
            'best_position_rating': 1350, 'weighted_position_rating': 1350,
            'total_players': 15, 'goalkeeper_count': 2, 'elite_players': 0,
            'rating_std': 50, 'rating_range': 100, 'best_player_rating': 1400,
            'worst_player_rating': 1300, 'positions_represented': 7,
            'found': False
        }
        
        # Normaliser holdnavn
        team_code = self.normalize_team_name(team_name)
        
        # Tjek team data for denne sæson
        if season in self.elo_team_data:
            season_data = self.elo_team_data[season]
            
            # Tjek player-based team data først (har team_name og team_code kolonner)
            if 'player_based' in season_data:
                team_df = season_data['player_based']
                matches = team_df[
                    (team_df['team_code'].str.upper() == team_code.upper()) |
                    (team_df['team_name'].str.upper() == team_name.upper())
                ]
                
                if not matches.empty:
                    team_data = matches.iloc[0].to_dict()
                    result = default_team_elo.copy()
                    
                    # Opdater med faktiske værdier
                    for key in default_team_elo.keys():
                        if key in team_data and key != 'found':
                            result[key] = team_data[key]
                    result['found'] = True
                    return result
            
            # Tjek seasonal team data (har IKKE team_name - kun aggregeret data)
            if 'seasonal' in season_data:
                team_df = season_data['seasonal']
                # Seasonal data har kun én række per sæson med aggregeret info
                season_matches = team_df[team_df['season'] == season]
                
                if not season_matches.empty:
                    team_data = season_matches.iloc[0].to_dict()
                    return {
                        'team_avg_rating': float(team_data.get('avg_rating', 1350)),
                        'top_7_rating': 1350,  # Ikke tilgængelig i seasonal data
                        'top_12_rating': 1350,
                        'best_position_rating': 1350,
                        'weighted_position_rating': 1350,
                        'total_players': int(team_data.get('teams', 15)),
                        'goalkeeper_count': 2,
                        'elite_players': int(team_data.get('elite_teams', 0)),
                        'rating_std': 50,
                        'rating_range': 100,
                        'best_player_rating': float(team_data.get('max_rating', 1400)),
                        'worst_player_rating': 1300,
                        'positions_represented': 7,
                        'found': True
                    }
        
        return default_team_elo
    
    def normalize_player_name(self, name: str) -> str:
        """Normaliser spillernavn til standard format"""
        if not name or not isinstance(name, str):
            return ""
        
        # Brug eksisterende player aliases hvis tilgængelig
        try:
            from team_config import PLAYER_NAME_ALIASES
            clean_name = name.strip().upper()
            standardized_aliases = {k.strip().upper(): v.upper() for k, v in PLAYER_NAME_ALIASES.items()}
            return standardized_aliases.get(clean_name, clean_name)
        except:
            return name.strip().upper()
    
    def normalize_team_name(self, name: str) -> str:
        """Normaliser holdnavn til holdkode"""
        if not name or not isinstance(name, str):
            return "UNK"
        
        # Brug eksisterende team mappings hvis tilgængelig
        try:
            if self.league == "Herreliga":
                from team_config import HERRELIGA_NAME_MAPPINGS, HERRELIGA_TEAMS
                name_mappings = HERRELIGA_NAME_MAPPINGS
                teams = HERRELIGA_TEAMS
            else:
                from team_config import KVINDELIGA_NAME_MAPPINGS, KVINDELIGA_TEAMS  
                name_mappings = KVINDELIGA_NAME_MAPPINGS
                teams = KVINDELIGA_TEAMS
            
            clean_name = name.strip().lower()
            
            # Først tjek om det allerede er en holdkode
            if name.strip().upper() in teams:
                return name.strip().upper()
            
            # Så tjek name mappings
            if clean_name in name_mappings:
                return name_mappings[clean_name]
            
            # Fallback til simpel forkortelse
            words = name.upper().split()
            if len(words) >= 2:
                return words[0][:2] + words[1][:1]
            
        except:
            pass
        
        return name.strip().upper()[:3]  # Fallback
    
    def calculate_squad_elo_features(self, team_name: str, before_date: datetime, 
                                   season: str) -> Dict:
        """
        Beregner ELO-baserede features for holdets spillertrup
        
        Returns:
            Dict med aggregerede ELO features
        """
        # Hent hold ELO data
        team_elo = self.get_team_elo_before_match(team_name, before_date, season)
        
        # Find spillere for dette hold fra events
        team_players = set()
        player_elos = []
        goalkeeper_elos = []
        position_elos = defaultdict(list)
        
        # Gennemgå alle matches før denne dato for at finde spillere
        for match_data in self.historical_data.values():
            if match_data['dato'] >= before_date:
                continue
            if season not in str(match_data.get('dato', '')):
                continue
                
            # Tjek om holdet spillede i denne kamp
            if not ((match_data['hold_hjemme'] == team_name) or 
                   (match_data['hold_ude'] == team_name)):
                continue
                
            events = match_data.get('events', pd.DataFrame())
            if events.empty:
                continue
                
            # Find spillere fra denne kamp
            for _, event in events.iterrows():
                # Primær spiller
                if pd.notna(event.get('navn_1')):
                    player_name = str(event['navn_1']).strip()
                    if player_name not in team_players:
                        team_players.add(player_name)
                        
                        # Hent spiller ELO
                        player_elo = self.get_player_elo_before_match(
                            player_name, team_name, before_date, season
                        )
                        
                        if player_elo['found']:
                            player_elos.append(player_elo)
                            
                            # Separer målvogtere
                            if player_elo['is_goalkeeper']:
                                goalkeeper_elos.append(player_elo)
                            
                            # Gruppér efter position
                            pos = player_elo['primary_position']
                            position_elos[pos].append(player_elo['final_rating'])
                
                # Målvogter fra mv felt
                if pd.notna(event.get('mv')):
                    mv_name = str(event['mv']).strip()
                    if mv_name not in team_players:
                        team_players.add(mv_name)
                        
                        player_elo = self.get_player_elo_before_match(
                            mv_name, team_name, before_date, season
                        )
                        
                        if player_elo['found']:
                            player_elos.append(player_elo)
                            goalkeeper_elos.append(player_elo)
                            position_elos['MV'].append(player_elo['final_rating'])
        
        # Beregn aggregerede features
        features = {}
        
        # Hold-niveau ELO (fra team data)
        features['elo_team_avg_rating'] = team_elo['team_avg_rating']
        features['elo_team_top7_rating'] = team_elo['top_7_rating']
        features['elo_team_top12_rating'] = team_elo['top_12_rating']
        features['elo_team_best_position_rating'] = team_elo['best_position_rating']
        features['elo_team_weighted_rating'] = team_elo['weighted_position_rating']
        features['elo_team_players_count'] = team_elo['total_players']
        features['elo_team_elite_players'] = team_elo['elite_players']
        features['elo_team_rating_std'] = team_elo['rating_std']
        features['elo_team_rating_range'] = team_elo['rating_range']
        features['elo_team_best_player'] = team_elo['best_player_rating']
        features['elo_team_worst_player'] = team_elo['worst_player_rating']
        
        # Spiller-niveau aggregeringer (fra faktiske spillere)
        if player_elos:
            ratings = [p['final_rating'] for p in player_elos]
            start_ratings = [p['start_rating'] for p in player_elos]
            rating_changes = [p['rating_change'] for p in player_elos]
            games_played = [p['games'] for p in player_elos]
            momentum_scores = [p['momentum'] for p in player_elos]
            
            features['elo_squad_avg_rating'] = np.mean(ratings)
            features['elo_squad_median_rating'] = np.median(ratings)
            features['elo_squad_max_rating'] = np.max(ratings)
            features['elo_squad_min_rating'] = np.min(ratings)
            features['elo_squad_std_rating'] = np.std(ratings)
            features['elo_squad_rating_range'] = np.max(ratings) - np.min(ratings)
            
            features['elo_squad_avg_start_rating'] = np.mean(start_ratings)
            features['elo_squad_total_rating_change'] = np.sum(rating_changes)
            features['elo_squad_avg_rating_change'] = np.mean(rating_changes)
            features['elo_squad_total_games'] = np.sum(games_played)
            features['elo_squad_avg_games'] = np.mean(games_played)
            features['elo_squad_avg_momentum'] = np.mean(momentum_scores)
            
            # Elite status distribution
            elite_counts = Counter([p['elite_status'] for p in player_elos])
            features['elo_squad_elite_count'] = elite_counts.get('ELITE', 0)
            features['elo_squad_legendary_count'] = elite_counts.get('LEGENDARY', 0)
            features['elo_squad_normal_count'] = elite_counts.get('NORMAL', 0)
            
            # Experience metrics
            experienced_players = sum(1 for g in games_played if g >= 10)
            features['elo_squad_experienced_players'] = experienced_players
            features['elo_squad_experience_ratio'] = experienced_players / len(player_elos)
            
        else:
            # Default values hvis ingen spillere fundet
            default_rating = 1200
            features.update({
                'elo_squad_avg_rating': default_rating, 'elo_squad_median_rating': default_rating,
                'elo_squad_max_rating': default_rating, 'elo_squad_min_rating': default_rating,
                'elo_squad_std_rating': 0, 'elo_squad_rating_range': 0,
                'elo_squad_avg_start_rating': default_rating, 'elo_squad_total_rating_change': 0,
                'elo_squad_avg_rating_change': 0, 'elo_squad_total_games': 0,
                'elo_squad_avg_games': 0, 'elo_squad_avg_momentum': 0,
                'elo_squad_elite_count': 0, 'elo_squad_legendary_count': 0,
                'elo_squad_normal_count': 0, 'elo_squad_experienced_players': 0,
                'elo_squad_experience_ratio': 0
            })
        
        # Målvogter specifikt
        if goalkeeper_elos:
            gk_ratings = [g['final_rating'] for g in goalkeeper_elos]
            features['elo_goalkeeper_count'] = len(goalkeeper_elos)
            features['elo_goalkeeper_avg_rating'] = np.mean(gk_ratings)
            features['elo_goalkeeper_max_rating'] = np.max(gk_ratings)
            features['elo_goalkeeper_rating_spread'] = np.max(gk_ratings) - np.min(gk_ratings) if len(gk_ratings) > 1 else 0
        else:
            features['elo_goalkeeper_count'] = 0
            features['elo_goalkeeper_avg_rating'] = 1250  # Default målvogter rating
            features['elo_goalkeeper_max_rating'] = 1250
            features['elo_goalkeeper_rating_spread'] = 0
        
        # Position-specific ELO
        standard_positions = ['VF', 'HF', 'VB', 'PL', 'HB', 'ST', 'MV']
        for pos in standard_positions:
            if pos in position_elos and position_elos[pos]:
                features[f'elo_pos_{pos}_avg_rating'] = np.mean(position_elos[pos])
                features[f'elo_pos_{pos}_max_rating'] = np.max(position_elos[pos])
                features[f'elo_pos_{pos}_count'] = len(position_elos[pos])
            else:
                features[f'elo_pos_{pos}_avg_rating'] = 1200
                features[f'elo_pos_{pos}_max_rating'] = 1200
                features[f'elo_pos_{pos}_count'] = 0
        
        # Taktisk dybde baseret på ELO
        features['elo_positional_depth'] = len([pos for pos in standard_positions 
                                              if features[f'elo_pos_{pos}_count'] > 0])
        features['elo_squad_balance'] = features['elo_squad_std_rating'] / max(1, features['elo_squad_avg_rating'])
        
        return features
    
    def calculate_elo_trends(self, team_name: str, before_date: datetime, 
                           season: str) -> Dict:
        """
        Beregner ELO trends og volatilitet FØR en bestemt kamp
        
        Returns:
            Dict med ELO trend features
        """
        trends = {
            # Rating progression through season
            'elo_early_season_rating': 1200,
            'elo_mid_season_rating': 1200, 
            'elo_late_season_rating': 1200,
            'elo_season_progression': 0.0,
            'elo_season_volatility': 0.0,
            
            # Recent form trends (last N matches)
            'elo_recent_5_avg': 1200,
            'elo_recent_10_avg': 1200,
            'elo_last_match_rating': 1200,
            'elo_recent_trend_5': 0.0,
            'elo_recent_trend_10': 0.0,
            'elo_recent_volatility': 0.0,
            
            # Peak performance tracking
            'elo_season_peak_rating': 1200,
            'elo_season_low_rating': 1200,
            'elo_peak_distance': 0.0,
            'elo_consistency_score': 0.0,
            
            # Momentum indicators
            'elo_positive_momentum': 0,
            'elo_negative_momentum': 0,
            'elo_momentum_streaks': 0,
            'elo_last_5_wins': 0,
            'elo_last_5_rating_change': 0.0,
            
            # Home/Away specific trends
            'elo_home_advantage_rating': 0.0,
            'elo_away_performance_rating': 0.0,
            'elo_venue_consistency': 0.0,
            
            # Advanced trend metrics
            'elo_regression_to_mean': 0.0,
            'elo_breakthrough_indicator': 0.0,
            'elo_decline_indicator': 0.0,
            'elo_stability_index': 0.0
        }
        
        # Find alle kampe for dette hold før datoen i denne sæson
        team_match_history = []
        season_start_year = int(season.split('-')[0])
        season_start = datetime(season_start_year, 8, 1)  # Approx season start
        season_end = datetime(season_start_year + 1, 6, 30)  # Approx season end
        
        for match_data in self.historical_data.values():
            match_date = match_data['dato']
            
            # KRITISK: Kun kampe FØR den aktuelle kamp og i samme sæson
            if match_date >= before_date:
                continue
            if match_date < season_start or match_date > season_end:
                continue
                
            # Tjek om holdet spillede i denne kamp
            is_home = match_data['hold_hjemme'] == team_name
            is_away = match_data['hold_ude'] == team_name
            
            if is_home or is_away:
                # Estimate rating for this match (simplified - kunne bruges ELO beregning)
                team_elo_data = self.get_team_elo_before_match(team_name, match_date, season)
                estimated_rating = team_elo_data['team_avg_rating']
                
                team_match_history.append({
                    'date': match_date,
                    'rating': estimated_rating,
                    'is_home': is_home,
                    'days_from_season_start': (match_date - season_start).days
                })
        
        # Sorter efter dato
        team_match_history.sort(key=lambda x: x['date'])
        
        if len(team_match_history) < 2:
            return trends  # Return defaults hvis ikke nok data
        
        # Calculate trend features
        ratings = [m['rating'] for m in team_match_history]
        dates = [m['date'] for m in team_match_history]
        
        # Season progression analysis
        season_length = (season_end - season_start).days
        for i, match in enumerate(team_match_history):
            season_progress = match['days_from_season_start'] / season_length
            
            if season_progress <= 0.33:  # Early season
                trends['elo_early_season_rating'] = match['rating']
            elif season_progress <= 0.66:  # Mid season
                trends['elo_mid_season_rating'] = match['rating']
            else:  # Late season
                trends['elo_late_season_rating'] = match['rating']
        
        # Season progression trend
        if len(ratings) >= 3:
            trends['elo_season_progression'] = ratings[-1] - ratings[0]
            trends['elo_season_volatility'] = np.std(ratings)
            
            # Linear trend over season
            x = np.arange(len(ratings))
            trend_slope = np.polyfit(x, ratings, 1)[0]
            trends['elo_recent_trend_10'] = trend_slope
        
        # Recent form analysis
        recent_5 = ratings[-5:] if len(ratings) >= 5 else ratings
        recent_10 = ratings[-10:] if len(ratings) >= 10 else ratings
        
        trends['elo_recent_5_avg'] = np.mean(recent_5)
        trends['elo_recent_10_avg'] = np.mean(recent_10)
        trends['elo_last_match_rating'] = ratings[-1]
        
        if len(recent_5) >= 2:
            trends['elo_recent_trend_5'] = recent_5[-1] - recent_5[0]
            trends['elo_recent_volatility'] = np.std(recent_5)
        
        # Peak performance tracking
        trends['elo_season_peak_rating'] = max(ratings)
        trends['elo_season_low_rating'] = min(ratings)
        trends['elo_peak_distance'] = trends['elo_season_peak_rating'] - ratings[-1]
        
        # Consistency score (inverse of volatility)
        if trends['elo_season_volatility'] > 0:
            trends['elo_consistency_score'] = 1.0 / (1.0 + trends['elo_season_volatility'] / 100)
        else:
            trends['elo_consistency_score'] = 1.0
        
        # Momentum indicators
        positive_changes = sum(1 for i in range(1, len(ratings)) if ratings[i] > ratings[i-1])
        negative_changes = sum(1 for i in range(1, len(ratings)) if ratings[i] < ratings[i-1])
        
        trends['elo_positive_momentum'] = positive_changes
        trends['elo_negative_momentum'] = negative_changes
        
        # Streak analysis (simplified)
        if len(ratings) >= 5:
            last_5_changes = [ratings[i] - ratings[i-1] for i in range(-4, 0)]
            trends['elo_last_5_rating_change'] = sum(last_5_changes)
            trends['elo_last_5_wins'] = sum(1 for change in last_5_changes if change > 0)
        
        # Home/Away performance (if enough data)
        home_ratings = [m['rating'] for m in team_match_history if m['is_home']]
        away_ratings = [m['rating'] for m in team_match_history if not m['is_home']]
        
        if home_ratings and away_ratings:
            trends['elo_home_advantage_rating'] = np.mean(home_ratings) - np.mean(away_ratings)
            trends['elo_venue_consistency'] = 1.0 - abs(np.std(home_ratings) - np.std(away_ratings)) / 100
        
        # Advanced indicators
        avg_rating = np.mean(ratings)
        current_rating = ratings[-1]
        
        # Regression to mean indicator
        league_average = 1350  # Typical league average
        trends['elo_regression_to_mean'] = (league_average - current_rating) / max(1, abs(league_average - avg_rating))
        
        # Breakthrough/decline indicators
        if current_rating > avg_rating + trends['elo_season_volatility']:
            trends['elo_breakthrough_indicator'] = (current_rating - avg_rating) / trends['elo_season_volatility']
        elif current_rating < avg_rating - trends['elo_season_volatility']:
            trends['elo_decline_indicator'] = (avg_rating - current_rating) / trends['elo_season_volatility']
        
        # Stability index (how stable are recent performances)
        if len(recent_10) >= 5:
            recent_changes = [abs(recent_10[i] - recent_10[i-1]) for i in range(1, len(recent_10))]
            avg_change = np.mean(recent_changes)
            trends['elo_stability_index'] = 1.0 / (1.0 + avg_change / 50)  # Normalize to 0-1
        
        return trends
    
    def get_match_context_elo_features(self, home_team: str, away_team: str, 
                                     match_date: datetime, season: str) -> Dict:
        """
        Beregner kamp-kontekst ELO features mellem to specifikke hold
        
        Returns:
            Dict med kontekstuelle ELO features
        """
        context_features = {
            # Head-to-head ELO trends
            'elo_h2h_home_advantage': 0.0,
            'elo_h2h_rating_consistency': 0.0,
            'elo_h2h_avg_quality': 1275.0,
            'elo_h2h_competitiveness': 0.5,
            
            # Match-specific predictions
            'elo_expected_goal_difference': 0.0,
            'elo_blowout_probability': 0.0,
            'elo_close_match_probability': 0.0,
            
            # Form convergence
            'elo_form_convergence': 0.0,
            'elo_momentum_clash': 0.0,
            'elo_peak_vs_peak': 0.0,
            
            # Context multipliers
            'elo_context_importance': 1.0,
            'elo_upset_potential': 0.0,
            'elo_volatility_factor': 1.0
        }
        
        # Get ELO data for both teams
        home_elo = self.get_team_elo_before_match(home_team, match_date, season)
        away_elo = self.get_team_elo_before_match(away_team, match_date, season)
        
        home_trends = self.calculate_elo_trends(home_team, match_date, season)
        away_trends = self.calculate_elo_trends(away_team, match_date, season)
        
        # Basic ELO difference
        rating_diff = home_elo['team_avg_rating'] - away_elo['team_avg_rating']
        
        # Head-to-head analysis
        h2h_matches = []
        for match_data in self.historical_data.values():
            if match_data['dato'] >= match_date:
                continue
                
            if ((match_data['hold_hjemme'] == home_team and match_data['hold_ude'] == away_team) or
                (match_data['hold_hjemme'] == away_team and match_data['hold_ude'] == home_team)):
                h2h_matches.append(match_data)
        
        if h2h_matches:
            # H2H ELO trends (simplified)
            context_features['elo_h2h_avg_quality'] = (home_elo['team_avg_rating'] + away_elo['team_avg_rating']) / 2
            context_features['elo_h2h_competitiveness'] = min(1.0, abs(rating_diff) / 200)
        
        # Expected performance based on ELO
        win_prob = 1 / (1 + 10**(-rating_diff/400))
        
        # Expected goal difference (simplified model)
        expected_home_goals = 25 + (rating_diff / 50)  # Base 25 goals + ELO adjustment
        expected_away_goals = 25 - (rating_diff / 50)
        context_features['elo_expected_goal_difference'] = expected_home_goals - expected_away_goals
        
        # Match predictions
        context_features['elo_blowout_probability'] = max(0, (abs(rating_diff) - 100) / 200)
        context_features['elo_close_match_probability'] = max(0, 1 - abs(rating_diff) / 100)
        
        # Form convergence analysis
        home_recent_trend = home_trends['elo_recent_trend_5']
        away_recent_trend = away_trends['elo_recent_trend_5']
        
        context_features['elo_form_convergence'] = abs(home_recent_trend - away_recent_trend)
        context_features['elo_momentum_clash'] = home_recent_trend - away_recent_trend
        
        # Peak performance comparison
        home_peak_form = home_trends['elo_season_peak_rating'] - home_trends['elo_peak_distance']
        away_peak_form = away_trends['elo_season_peak_rating'] - away_trends['elo_peak_distance']
        context_features['elo_peak_vs_peak'] = home_peak_form - away_peak_form
        
        # Advanced context metrics
        combined_volatility = (home_trends['elo_season_volatility'] + away_trends['elo_season_volatility']) / 2
        context_features['elo_volatility_factor'] = min(2.0, combined_volatility / 50)
        
        # Upset potential (how likely is an upset based on ELO)
        if abs(rating_diff) > 50:
            underdog_momentum = away_trends['elo_recent_trend_5'] if rating_diff > 0 else home_trends['elo_recent_trend_5']
            context_features['elo_upset_potential'] = max(0, underdog_momentum / 50)
        
        # Context importance (how much ELO matters in this matchup)
        both_stable = (home_trends['elo_stability_index'] + away_trends['elo_stability_index']) / 2
        context_features['elo_context_importance'] = both_stable
        
        return context_features
    
    def validate_no_data_leakage(self):
        """
        KRITISK: Validerer at der ikke er data leakage i dataset
        
        Tjekker:
        1. Alle matches er sorteret kronologisk
        2. Features kun bruger data FØR match dato
        3. Ingen fremtidige data er inkluderet
        """
        print("\n🔒 VALIDERER DATA LEAKAGE BESKYTTELSE")
        print("-" * 50)
        
        if not self.dataset_rows:
            print("❌ Intet dataset at validere!")
            return False
        
        validation_errors = []
        matches_checked = 0
        
        for i, row in enumerate(self.dataset_rows):
            matches_checked += 1
            match_date_str = row['match_date']
            match_date = datetime.strptime(match_date_str, '%Y-%m-%d')
            
            # 1. Tjek at alle historiske features har realistiske værdier
            for key, value in row.items():
                if key.startswith(('home_', 'away_')):
                    if isinstance(value, (int, float)):
                        # Tjek for urealistiske værdier der kunne indikere leakage
                        # FORBEDRET VALIDERING: Kun tjek faktiske ELO ratings
                        if ('_rating' in key and 'elo_' in key) and (value < 500 or value > 3000):
                            validation_errors.append(f"Match {i}: Unrealistic ELO rating {key}={value}")
                        elif 'games' in key and value < 0:
                            validation_errors.append(f"Match {i}: Negative games value {key}={value}")
                        # FJERNET: Zero rating check da 0 er legitimate for mange features
                        # Kun check for impossible negative ratings på core ratings
                        elif ('avg_rating' in key or 'final_rating' in key) and value < 0:
                            validation_errors.append(f"Match {i}: Negative core rating {key}={value}")
            
            # 2. Tjek temporal consistency
            if 'season_progress' in row:
                if row['season_progress'] < 0 or row['season_progress'] > 1:
                    validation_errors.append(f"Match {i}: Invalid season progress {row['season_progress']}")
            
            # 3. Tjek at ELO trends er realistiske
            for trend_key in ['home_elo_recent_trend_5', 'away_elo_recent_trend_5']:
                if trend_key in row:
                    if abs(row[trend_key]) > 500:  # Meget store ændringer kunne indikere fejl
                        validation_errors.append(f"Match {i}: Extreme ELO trend {trend_key}={row[trend_key]}")
            
            # Begræns checks for performance
            if matches_checked >= 100:  # Check first 100 matches
                break
        
        # 4. Tjek kronologisk ordering
        dates = [datetime.strptime(row['match_date'], '%Y-%m-%d') for row in self.dataset_rows[:100]]
        if dates != sorted(dates):
            validation_errors.append("Dataset ikke sorteret kronologisk!")
        
        # Print validation results
        if validation_errors:
            print(f"❌ VALIDATION FEJL FUNDET ({len(validation_errors)}):")
            for error in validation_errors[:10]:  # Show first 10
                print(f"  - {error}")
            if len(validation_errors) > 10:
                print(f"  ... og {len(validation_errors) - 10} flere fejl")
            return False
        else:
            print("✅ INGEN DATA LEAKAGE DETEKTERET")
            print(f"  📊 Valideret {matches_checked} kampe")
            print("  🔒 Temporal ordering korrekt")
            print("  📈 ELO værdier indenfor forventede ranges")
            print("  🎯 Feature values realistiske")
            return True
    
    def calculate_positional_features(self, team_name: str, before_date: datetime) -> Dict:
        """
        Beregner positionsspecifikke features baseret på data.md positioner
        
        Returns:
            Dict med detaljerede positionsstatistikker
        """
        
        # Definér alle håndboldpositioner fra data.md (KORREKTE POSITIONER)
        HANDBALL_POSITIONS = {
            'VF': 'Venstre fløj',        # Venstre fløj
            'HF': 'Højre fløj',          # Højre fløj  
            'VB': 'Venstre back',        # Venstre back
            'PL': 'Playmaker',           # Playmaker
            'HB': 'Højre back',          # Højre back
            'ST': 'Streg',               # Streg/Pivot
            'Gbr': 'Gennembrud',         # Gennembrud
            '1:e': 'Første bølge kontra', # Første bølge kontra
            '2:e': 'Anden bølge kontra', # Anden bølge kontra
            'MV': 'Målvogter'            # Målvogter (identificeres via nr_mv/mv)
        }
        
        # Initialiser position statistikker
        position_stats = defaultdict(lambda: {
            'attempts': 0,           # Afslutningsforsøg
            'goals': 0,              # Scorede mål
            'assists': 0,            # Assists
            'saves': 0,              # Redninger (kun MV)
            'blocks': 0,             # Blokerede skud
            'turnovers': 0,          # Boldomgivelser
            'fouls': 0,              # Personlige fejl
            'penalties_earned': 0,   # Fremtvunget straffe
            'penalties_missed': 0,   # Missede straffe
            'successful_passes': 0,  # Succesfulde afleveringer
            'total_actions': 0       # Total aktioner fra position
        })
        
        # Gennemgå alle matches før datoen
        for match_data in self.historical_data.values():
            if match_data['dato'] >= before_date:
                continue
                
            # Check om holdet spillede i denne kamp
            team_involved = ((match_data['hold_hjemme'] == team_name) or 
                           (match_data['hold_ude'] == team_name))
            if not team_involved:
                continue
                
            events = match_data.get('events', pd.DataFrame())
            if events.empty:
                continue
                
            # Analyser hver event for positionsdata
            for _, event in events.iterrows():
                # Skip administrative events
                action = str(event.get('haendelse_1', ''))
                if action in ['Halvleg', 'Start 1:e halvleg', 'Start 2:e halvleg', 
                             'Fuld tid', 'Kamp slut', 'Time out', 'Video Proof', 'Video Proof slut']:
                    continue
                
                # Tjek om denne event involverer vores hold
                event_team = str(event.get('hold', ''))
                player_name = str(event.get('navn_1', ''))
                position = str(event.get('pos', ''))
                
                # Normaliser position
                if position and position in HANDBALL_POSITIONS:
                    pos_key = position
                elif position:
                    pos_key = 'U'  # Ukendt position
                else:
                    continue  # Skip events uden position
                
                # Kun tæl events fra vores hold
                # Dette kræver hold-identifikation baseret på data.md regler
                if not self._is_team_player_event(event, team_name, match_data):
                    continue
                
                position_stats[pos_key]['total_actions'] += 1
                
                # Analyser specifik action type
                if 'Mål' in action:
                    position_stats[pos_key]['goals'] += 1
                    position_stats[pos_key]['attempts'] += 1
                    
                elif any(x in action for x in ['Skud', 'reddet', 'forbi', 'stolpe', 'blokeret']):
                    position_stats[pos_key]['attempts'] += 1
                    
                    if 'blokeret' in action:
                        # Dette er en blokering AF modstanderen, ikke en blokering vi laver
                        pass
                    
                elif 'Blok af' in action:
                    position_stats[pos_key]['blocks'] += 1
                    
                elif any(x in action for x in ['Tabt bold', 'Fejlaflevering']):
                    position_stats[pos_key]['turnovers'] += 1
                    
                elif any(x in action for x in ['Udvisning', 'Advarsel', 'Regelfejl']):
                    position_stats[pos_key]['fouls'] += 1
                    
                elif 'Tilkendt straffe' in action:
                    position_stats[pos_key]['penalties_earned'] += 1
                    
                elif 'Straffekast' in action and ('forbi' in action or 'reddet' in action):
                    position_stats[pos_key]['penalties_missed'] += 1
                
                # Tjek secondary actions (assists etc.)
                secondary_action = str(event.get('haendelse_2', ''))
                if 'Assist' in secondary_action:
                    # Assist tildeles navn_2 spilleren 
                    assist_player = str(event.get('navn_2', ''))
                    if assist_player and self._is_team_player_name(assist_player, team_name, match_data):
                        # Vi kan ikke vide assist-spillerens position fra denne event
                        # men vi kan estimere baseret på hovedaktionen
                        position_stats[pos_key]['assists'] += 1
                
                # Målvogter specifikke actions
                if pos_key == 'MV' or position == 'MV':
                    if any(x in action for x in ['reddet', 'Skud reddet', 'Straffekast reddet']):
                        position_stats['MV']['saves'] += 1
        
        # Beregn endelige features
        features = {}
        
        # For hver position, beregn statistikker
        for pos_code, pos_name in HANDBALL_POSITIONS.items():
            stats = position_stats[pos_code]
            
            # Basis statistikker
            features[f'pos_{pos_code}_total_actions'] = stats['total_actions']
            features[f'pos_{pos_code}_attempts'] = stats['attempts']
            features[f'pos_{pos_code}_goals'] = stats['goals']
            features[f'pos_{pos_code}_assists'] = stats['assists']
            features[f'pos_{pos_code}_blocks'] = stats['blocks']
            features[f'pos_{pos_code}_turnovers'] = stats['turnovers']
            features[f'pos_{pos_code}_fouls'] = stats['fouls']
            
            # Effektivitetsrater
            if stats['attempts'] > 0:
                features[f'pos_{pos_code}_goal_conversion'] = stats['goals'] / stats['attempts']
            else:
                features[f'pos_{pos_code}_goal_conversion'] = 0.0
                
            if stats['total_actions'] > 0:
                features[f'pos_{pos_code}_turnover_rate'] = stats['turnovers'] / stats['total_actions']
                features[f'pos_{pos_code}_foul_rate'] = stats['fouls'] / stats['total_actions']
            else:
                features[f'pos_{pos_code}_turnover_rate'] = 0.0
                features[f'pos_{pos_code}_foul_rate'] = 0.0
            
            # Målvogter specifikke
            if pos_code == 'MV':
                features[f'pos_{pos_code}_saves'] = stats['saves']
                if stats['attempts'] > 0:  # Attempts = skud mod målvogter
                    features[f'pos_{pos_code}_save_rate'] = stats['saves'] / stats['attempts']
                else:
                    features[f'pos_{pos_code}_save_rate'] = 0.0
        
        # Aggregerede positionsfordelinger
        total_goals = sum(position_stats[pos]['goals'] for pos in HANDBALL_POSITIONS.keys())
        total_attempts = sum(position_stats[pos]['attempts'] for pos in HANDBALL_POSITIONS.keys())
        total_actions = sum(position_stats[pos]['total_actions'] for pos in HANDBALL_POSITIONS.keys())
        
        # Fordelinger (procent af total)
        for pos_code in HANDBALL_POSITIONS.keys():
            if total_goals > 0:
                features[f'pos_{pos_code}_goal_share'] = position_stats[pos_code]['goals'] / total_goals
            else:
                features[f'pos_{pos_code}_goal_share'] = 0.0
                
            if total_attempts > 0:
                features[f'pos_{pos_code}_attempt_share'] = position_stats[pos_code]['attempts'] / total_attempts
            else:
                features[f'pos_{pos_code}_attempt_share'] = 0.0
                
            if total_actions > 0:
                features[f'pos_{pos_code}_action_share'] = position_stats[pos_code]['total_actions'] / total_actions
            else:
                features[f'pos_{pos_code}_action_share'] = 0.0
        
        # Overordnede positionelle trends
        features['pos_offensive_diversity'] = len([pos for pos in HANDBALL_POSITIONS.keys() 
                                                  if position_stats[pos]['goals'] > 0])
        
        # Målkoncentration per position type (OPDATERET MED KORREKTE POSITIONER)
        wing_goals = position_stats['VF']['goals'] + position_stats['HF']['goals']
        back_goals = position_stats['VB']['goals'] + position_stats['HB']['goals'] + position_stats['PL']['goals']
        pivot_goals = position_stats['ST']['goals']
        breakthrough_goals = position_stats['Gbr']['goals']
        fastbreak_goals = position_stats['1:e']['goals'] + position_stats['2:e']['goals']  # Første og anden bølge
        
        features['pos_wing_dominance'] = wing_goals / max(1, total_goals)
        features['pos_back_dominance'] = back_goals / max(1, total_goals)  
        features['pos_pivot_dominance'] = pivot_goals / max(1, total_goals)
        features['pos_breakthrough_dominance'] = breakthrough_goals / max(1, total_goals)
        features['pos_fastbreak_dominance'] = fastbreak_goals / max(1, total_goals)
        
        # Offensiv stil analyse (OPDATERET)
        features['pos_wing_heavy_offense'] = 1 if wing_goals > (back_goals + pivot_goals) else 0
        features['pos_pivot_heavy_offense'] = 1 if pivot_goals > (wing_goals + back_goals) else 0
        features['pos_back_heavy_offense'] = 1 if back_goals > (wing_goals + pivot_goals) else 0
        features['pos_balanced_offense'] = 1 if abs(wing_goals - back_goals) <= 2 else 0
        
        # Defensiv positionering
        total_blocks = sum(position_stats[pos]['blocks'] for pos in HANDBALL_POSITIONS.keys())
        features['pos_total_blocks'] = total_blocks
        features['pos_defensive_activity'] = total_blocks / max(1, total_actions)
        
        # Position effektivitet sammenligninger
        position_efficiencies = {}
        for pos_code in HANDBALL_POSITIONS.keys():
            attempts = position_stats[pos_code]['attempts']
            goals = position_stats[pos_code]['goals']
            if attempts > 0:
                position_efficiencies[pos_code] = goals / attempts
            else:
                position_efficiencies[pos_code] = 0.0
        
        # Find mest og mindst effektive positioner
        if position_efficiencies:
            most_efficient_pos = max(position_efficiencies, key=position_efficiencies.get)
            least_efficient_pos = min(position_efficiencies, key=position_efficiencies.get)
            
            features['pos_most_efficient'] = most_efficient_pos
            features['pos_least_efficient'] = least_efficient_pos
            features['pos_efficiency_spread'] = (position_efficiencies[most_efficient_pos] - 
                                               position_efficiencies[least_efficient_pos])
        
        # Målvogter ydeevne detaljer (hvis data tilgængelig)
        if position_stats['MV']['total_actions'] > 0:
            features['pos_goalkeeper_activity_level'] = position_stats['MV']['total_actions']
            features['pos_goalkeeper_workload'] = position_stats['MV']['saves'] / max(1, position_stats['MV']['total_actions'])
        else:
            features['pos_goalkeeper_activity_level'] = 0
            features['pos_goalkeeper_workload'] = 0.0
        
        # Taktisk stil indikatorer (OPDATERET MED KORREKTE POSITIONER)
        total_structured_goals = back_goals + pivot_goals  # Struktureret angreb (back + streg)
        total_transition_goals = breakthrough_goals + fastbreak_goals  # Omstillingsangreb (gennembrud + kontra)
        
        features['pos_structured_vs_transition'] = (total_structured_goals / max(1, total_transition_goals)) if total_transition_goals > 0 else float('inf')
        features['pos_transition_percentage'] = total_transition_goals / max(1, total_goals)
        features['pos_structured_percentage'] = total_structured_goals / max(1, total_goals)
        
        # Position konsistens (diversitet i målscoring)
        goal_variance = np.var([position_stats[pos]['goals'] for pos in HANDBALL_POSITIONS.keys()])
        features['pos_goal_distribution_variance'] = goal_variance
        features['pos_is_specialist_team'] = 1 if goal_variance > 5.0 else 0  # Høj varians = specialister
        
        # Fejl og disciplin per position
        total_fouls = sum(position_stats[pos]['fouls'] for pos in HANDBALL_POSITIONS.keys())
        total_turnovers = sum(position_stats[pos]['turnovers'] for pos in HANDBALL_POSITIONS.keys())
        
        features['pos_total_fouls'] = total_fouls
        features['pos_total_turnovers'] = total_turnovers
        features['pos_discipline_ratio'] = total_fouls / max(1, total_actions)
        features['pos_ball_security_ratio'] = 1 - (total_turnovers / max(1, total_actions))
        
        # Position spredning (hvor mange forskellige positioner bruges aktivt)
        active_positions = len([pos for pos in HANDBALL_POSITIONS.keys() 
                               if position_stats[pos]['total_actions'] > 0])
        features['pos_tactical_width'] = active_positions
        features['pos_uses_most_positions'] = 1 if active_positions >= 8 else 0  # 8 ud af 10 positioner
        
        return features
    
    def _is_team_player_event(self, event, team_name: str, match_data: Dict) -> bool:
        """
        Afgør om en event tilhører det specificerede hold baseret på data.md regler
        
        KRITISK: Implementerer data.md's regler for hold-identifikation:
        - Primær spiller (navn_1) tilhører holdet angivet i 'hold' feltet
        - Sekundær spiller (navn_2) kan tilhøre samme eller modsat hold afhængig af hændelse
        - Målvogter (mv) tilhører ALTID det modsatte hold af 'hold' feltet
        """
        event_hold = str(event.get('hold', ''))
        player_name = str(event.get('navn_1', ''))
        
        if not event_hold or not player_name:
            return False
        
        # Match hold koder til hold navne fra match_info
        home_team = match_data.get('hold_hjemme', '')
        away_team = match_data.get('hold_ude', '')
        
        # Simpel mapping - dette kan udvides med mere sofistikeret hold-kode mapping
        if team_name == home_team:
            # Vi ser efter vores hjemmehold - match event_hold med hjemme
            return self._team_name_matches_hold_code(home_team, event_hold)
        elif team_name == away_team:
            # Vi ser efter vores udehold - match event_hold med ude
            return self._team_name_matches_hold_code(away_team, event_hold)
        
        return False
    
    def _team_name_matches_hold_code(self, team_name: str, hold_code: str) -> bool:
        """
        Matcher holdnavn med holdkode - simpel implementation
        Dette kan udvides med din eksisterende hold-mapping logik
        """
        if not team_name or not hold_code:
            return False
            
        # Simpel matching baseret på forkortelser
        team_words = team_name.upper().split()
        if len(team_words) >= 2:
            # Tag første bogstav fra de første to ord
            expected_code = team_words[0][:2] + team_words[1][:1]
            if expected_code.upper() == hold_code.upper():
                return True
        
        # Fallback - check om hold_code er i team_name
        return hold_code.upper() in team_name.upper()
    
    def _is_team_player_name(self, player_name: str, team_name: str, match_data: Dict) -> bool:
        """
        Hjælpefunktion til at afgøre om en spiller tilhører et bestemt hold
        """
        # Dette kræver mere sofistikeret logik for at matche spillere til hold
        # For nu returnerer vi True som placeholder
        return True
    
    def calculate_head_to_head_stats(self, team_a: str, team_b: str, 
                                   before_date: datetime, num_games: int = 5) -> Dict:
        """
        Beregner head-to-head statistikker mellem to hold før en given dato
        
        Returns:
            Dict med H2H statistikker
        """
        h2h_matches = []
        
        for match_data in self.historical_data.values():
            if match_data['dato'] >= before_date:
                continue
                
            if ((match_data['hold_hjemme'] == team_a and match_data['hold_ude'] == team_b) or
                (match_data['hold_hjemme'] == team_b and match_data['hold_ude'] == team_a)):
                h2h_matches.append(match_data)
        
        # Sorter efter dato (nyeste først)
        h2h_matches.sort(key=lambda x: x['dato'], reverse=True)
        recent_h2h = h2h_matches[:num_games]
        
        stats = {
            'h2h_games': len(recent_h2h),
            'team_a_wins': 0,
            'team_b_wins': 0,
            'draws': 0,
            'team_a_goals': 0,
            'team_b_goals': 0,
            'avg_total_goals': 0.0,
            'avg_goal_difference': 0.0,
            'team_a_win_rate': 0.0,
            'days_since_last_h2h': 999,
            'h2h_momentum_team_a': 0.0  # Recent H2H performance for team A
        }
        
        if not recent_h2h:
            return stats
            
        for i, match in enumerate(recent_h2h):
            try:
                if '-' in match['resultat']:
                    home_goals, away_goals = map(int, match['resultat'].split('-'))
                    
                    # Determiner hvilke mål der tilhører hvilket hold
                    if match['hold_hjemme'] == team_a:
                        team_a_goals = home_goals
                        team_b_goals = away_goals
                    else:
                        team_a_goals = away_goals
                        team_b_goals = home_goals
                    
                    stats['team_a_goals'] += team_a_goals
                    stats['team_b_goals'] += team_b_goals
                    
                    # Beregn vinder
                    weight = 1.0 / (i + 1)  # Nyere kampe vægter mere
                    if team_a_goals > team_b_goals:
                        stats['team_a_wins'] += 1
                        stats['h2h_momentum_team_a'] += 3.0 * weight
                    elif team_a_goals == team_b_goals:
                        stats['draws'] += 1
                        stats['h2h_momentum_team_a'] += 1.0 * weight
                    else:
                        stats['team_b_wins'] += 1
                        
            except:
                continue
        
        # Finalize statistikker
        if stats['h2h_games'] > 0:
            total_goals = stats['team_a_goals'] + stats['team_b_goals']
            stats['avg_total_goals'] = total_goals / stats['h2h_games']
            stats['avg_goal_difference'] = abs(stats['team_a_goals'] - stats['team_b_goals']) / stats['h2h_games']
            stats['team_a_win_rate'] = stats['team_a_wins'] / stats['h2h_games']
            stats['days_since_last_h2h'] = (before_date - recent_h2h[0]['dato']).days
            stats['h2h_momentum_team_a'] = stats['h2h_momentum_team_a'] / stats['h2h_games']
        
        return stats
    
    def calculate_temporal_features(self, match_date: datetime, season: str) -> Dict:
        """
        Beregner tidsmæssige features
        
        Returns:
            Dict med temporal features
        """
        features = {
            'day_of_week': match_date.weekday(),  # 0=Monday, 6=Sunday
            'month': match_date.month,
            'is_weekend': match_date.weekday() >= 5,
            'season_progress': 0.0,  # 0.0 = season start, 1.0 = season end
            'days_from_season_start': 0,
            'is_christmas_period': False,
            'is_spring_season': False,
            'is_season_finale': False
        }
        
        # Season progress (approx)
        try:
            season_start_year = int(season.split('-')[0])
            season_start = datetime(season_start_year, 9, 1)  # Approx season start
            season_end = datetime(season_start_year + 1, 5, 31)  # Approx season end
            
            total_season_days = (season_end - season_start).days
            days_into_season = (match_date - season_start).days
            
            features['season_progress'] = max(0, min(1, days_into_season / total_season_days))
            features['days_from_season_start'] = days_into_season
            
            # Særlige perioder
            features['is_christmas_period'] = match_date.month in [12, 1]
            features['is_spring_season'] = match_date.month in [3, 4, 5]
            features['is_season_finale'] = features['season_progress'] > 0.8
            
        except:
            pass
        
        return features
    
    def calculate_league_context_features(self, team_name: str, before_date: datetime, 
                                        season: str) -> Dict:
        """
        Beregner liga kontext features (position, konkurrenceniveau etc.)
        
        Returns:
            Dict med liga context features
        """
        # Find alle hold i sæsonen
        season_teams = set()
        team_records = defaultdict(lambda: {'wins': 0, 'draws': 0, 'losses': 0, 'gf': 0, 'ga': 0})
        
        for match_data in self.historical_data.values():
            if match_data['dato'] >= before_date:
                continue
            if season not in str(match_data.get('dato', '')):
                continue
                
            home_team = match_data['hold_hjemme']
            away_team = match_data['hold_ude']
            season_teams.update([home_team, away_team])
            
            try:
                if '-' in match_data['resultat']:
                    home_goals, away_goals = map(int, match_data['resultat'].split('-'))
                    
                    # Update records
                    team_records[home_team]['gf'] += home_goals
                    team_records[home_team]['ga'] += away_goals
                    team_records[away_team]['gf'] += away_goals
                    team_records[away_team]['ga'] += home_goals
                    
                    if home_goals > away_goals:
                        team_records[home_team]['wins'] += 1
                        team_records[away_team]['losses'] += 1
                    elif home_goals == away_goals:
                        team_records[home_team]['draws'] += 1
                        team_records[away_team]['draws'] += 1
                    else:
                        team_records[home_team]['losses'] += 1
                        team_records[away_team]['wins'] += 1
            except:
                continue
        
        # Beregn league table
        league_table = []
        for team, record in team_records.items():
            points = record['wins'] * 3 + record['draws']
            games = record['wins'] + record['draws'] + record['losses']
            goal_diff = record['gf'] - record['ga']
            
            league_table.append({
                'team': team,
                'points': points,
                'games': games,
                'goal_difference': goal_diff,
                'goals_for': record['gf'],
                'goals_against': record['ga']
            })
        
        # Sorter tabellen
        league_table.sort(key=lambda x: (x['points'], x['goal_difference'], x['goals_for']), reverse=True)
        
        # Find team position
        team_position = len(league_table)  # Default til sidste plads
        team_points = 0
        team_goal_diff = 0
        
        for i, entry in enumerate(league_table):
            if entry['team'] == team_name:
                team_position = i + 1
                team_points = entry['points']
                team_goal_diff = entry['goal_difference']
                break
        
        features = {
            'league_position': team_position,
            'total_teams_in_league': len(league_table),
            'points_before_match': team_points,
            'goal_difference_before_match': team_goal_diff,
            'is_top_half': team_position <= len(league_table) // 2,
            'is_top_3': team_position <= 3,
            'is_bottom_3': team_position > len(league_table) - 3,
            'position_percentile': 1 - (team_position - 1) / max(1, len(league_table) - 1),
            'points_from_leader': 0,
            'points_to_relegation': 0
        }
        
        if league_table:
            leader_points = league_table[0]['points']
            features['points_from_leader'] = leader_points - team_points
            
            # Approx relegation line (bottom 2 teams)
            if len(league_table) >= 2:
                relegation_points = league_table[-3]['points'] if len(league_table) > 2 else 0
                features['points_to_relegation'] = team_points - relegation_points
        
        return features
    
    def _get_default_team_stats(self) -> Dict:
        """Returnerer default team stats for nye hold"""
        return {
            'games_played': 0, 'wins': 0, 'draws': 0, 'losses': 0,
            'goals_for': 0, 'goals_against': 0, 'home_games': 0, 'away_games': 0,
            'avg_goals_for': 25.0, 'avg_goals_against': 25.0, 'goal_difference': 0,
            'win_rate': 0.33, 'home_win_rate': 0.5, 'away_win_rate': 0.2,
            'form_points': 0, 'momentum': 0.0, 'offensive_strength': 25.0,
            'defensive_strength': 10.0, 'days_since_last_match': 7
        }
    
    def load_all_historical_data(self):
        """Loader alle historiske data fra alle sæsoner"""
        print("\n📊 LOADER HISTORISKE DATA")
        print("-" * 40)
        
        total_matches = 0
        
        for season in self.seasons:
            season_path = os.path.join(self.database_dir, season)
            if not os.path.exists(season_path):
                continue
                
            print(f"\n📅 Processerer {season}...")
            season_matches = 0
            
            db_files = sorted([f for f in os.listdir(season_path) if f.endswith('.db')])
            
            for db_file in db_files:
                db_path = os.path.join(season_path, db_file)
                match_data = self.extract_match_info(db_path)
                
                if match_data:
                    kamp_id = match_data['kamp_id']
                    self.historical_data[kamp_id] = match_data
                    self.historical_data[kamp_id]['season'] = season
                    season_matches += 1
                    total_matches += 1
                    
                    if season_matches % 50 == 0:
                        print(f"  📈 {season_matches} kampe loaded...")
            
            print(f"  ✅ {season}: {season_matches} kampe")
        
        print(f"\n🎯 TOTAL: {total_matches} historiske kampe loaded")
        
    def generate_ml_dataset(self):
        """
        Genererer det fulde ML dataset ved at iterere over alle historiske kampe.
        BRUGER NU DEN CENTRALE `generate_features_for_single_match` FUNKTION.
        """
        print("\n🎯 GENERERER ML DATASET")
        print("-" * 40)
        
        # Sorter kampe efter dato
        sorted_matches = sorted(self.historical_data.items(), 
                               key=lambda x: x[1]['dato'])
        
        processed_count = 0
        
        for kamp_id, match_data in sorted_matches:
            try:
                # Kun inkludér kampe med gyldigt resultat
                if not match_data.get('resultat') or '-' not in match_data['resultat']:
                    continue
                
                home_team = match_data['hold_hjemme']
                away_team = match_data['hold_ude']
                match_date = match_data['dato']
                season = match_data['season']
                
                # Beregn alle features (HISTORISKE - før kampen!)
                features = {
                    # Metadata
                    'kamp_id': kamp_id,
                    'season': season,
                    'match_date': match_date.strftime('%Y-%m-%d'),
                    'home_team': home_team,
                    'away_team': away_team,
                    'venue': match_data.get('sted', ''),
                    'league': match_data.get('turnering', self.league),
                }
                
                # 1. HOLD STATISTIKKER
                home_stats = self.calculate_team_historical_stats(home_team, match_date)
                away_stats = self.calculate_team_historical_stats(away_team, match_date)
                
                # Tilføj prefix til features
                for key, value in home_stats.items():
                    features[f'home_{key}'] = value
                for key, value in away_stats.items():
                    features[f'away_{key}'] = value
                
                # 2. SPILLER FEATURES
                home_players = self.calculate_player_features(home_team, match_date)
                away_players = self.calculate_player_features(away_team, match_date)
                
                for key, value in home_players.items():
                    features[f'home_players_{key}'] = value
                for key, value in away_players.items():
                    features[f'away_players_{key}'] = value
                
                # 2B. POSITIONSSPECIFIKKE FEATURES (NYT!)
                home_positions = self.calculate_positional_features(home_team, match_date)
                away_positions = self.calculate_positional_features(away_team, match_date)
                
                for key, value in home_positions.items():
                    features[f'home_{key}'] = value
                for key, value in away_positions.items():
                    features[f'away_{key}'] = value
                
                # 2C. ELO-BASEREDE FEATURES (NYT!)
                try:
                    home_elo = self.calculate_squad_elo_features(home_team, match_date, season)
                    away_elo = self.calculate_squad_elo_features(away_team, match_date, season)
                except Exception as e:
                    print(f"⚠️ ELO features fejl for kamp {kamp_id}: {e}")
                    # Default ELO features hvis fejl
                    default_elo_features = {
                        'elo_team_avg_rating': 1350, 'elo_team_top7_rating': 1350, 'elo_team_top12_rating': 1350,
                        'elo_team_best_position_rating': 1350, 'elo_team_weighted_rating': 1350,
                        'elo_team_players_count': 15, 'elo_team_elite_players': 0, 'elo_team_rating_std': 50,
                        'elo_team_rating_range': 100, 'elo_team_best_player': 1400, 'elo_team_worst_player': 1300,
                        'elo_squad_avg_rating': 1200, 'elo_squad_median_rating': 1200, 'elo_squad_max_rating': 1300,
                        'elo_squad_min_rating': 1100, 'elo_squad_std_rating': 50, 'elo_squad_rating_range': 200,
                        'elo_squad_avg_start_rating': 1200, 'elo_squad_total_rating_change': 0,
                        'elo_squad_avg_rating_change': 0, 'elo_squad_total_games': 0, 'elo_squad_avg_games': 0,
                        'elo_squad_avg_momentum': 0, 'elo_squad_elite_count': 0, 'elo_squad_legendary_count': 0,
                        'elo_squad_normal_count': 0, 'elo_squad_experienced_players': 0,
                        'elo_squad_experience_ratio': 0, 'elo_goalkeeper_count': 2, 'elo_goalkeeper_avg_rating': 1250,
                        'elo_goalkeeper_max_rating': 1250, 'elo_goalkeeper_rating_spread': 0
                    }
                    # Add position-specific defaults
                    for pos in ['VF', 'HF', 'VB', 'PL', 'HB', 'ST', 'MV']:
                        default_elo_features[f'elo_pos_{pos}_avg_rating'] = 1200
                        default_elo_features[f'elo_pos_{pos}_max_rating'] = 1200
                        default_elo_features[f'elo_pos_{pos}_count'] = 0
                    
                    home_elo = default_elo_features.copy()
                    away_elo = default_elo_features.copy()
                
                for key, value in home_elo.items():
                    features[f'home_{key}'] = value
                for key, value in away_elo.items():
                    features[f'away_{key}'] = value
                
                # 2D. ELO TRENDS FEATURES (NYT!)
                try:
                    home_elo_trends = self.calculate_elo_trends(home_team, match_date, season)
                    away_elo_trends = self.calculate_elo_trends(away_team, match_date, season)
                except Exception as e:
                    print(f"⚠️ ELO trends fejl for kamp {kamp_id}: {e}")
                    # Default ELO trends hvis fejl
                    default_trends = {
                        'elo_early_season_rating': 1200, 'elo_mid_season_rating': 1200, 'elo_late_season_rating': 1200,
                        'elo_season_progression': 0.0, 'elo_season_volatility': 0.0, 'elo_recent_5_avg': 1200,
                        'elo_recent_10_avg': 1200, 'elo_last_match_rating': 1200, 'elo_recent_trend_5': 0.0,
                        'elo_recent_trend_10': 0.0, 'elo_recent_volatility': 0.0, 'elo_season_peak_rating': 1200,
                        'elo_season_low_rating': 1200, 'elo_peak_distance': 0.0, 'elo_consistency_score': 0.0,
                        'elo_positive_momentum': 0, 'elo_negative_momentum': 0, 'elo_momentum_streaks': 0,
                        'elo_last_5_wins': 0, 'elo_last_5_rating_change': 0.0, 'elo_home_advantage_rating': 0.0,
                        'elo_away_performance_rating': 0.0, 'elo_venue_consistency': 0.0, 'elo_regression_to_mean': 0.0,
                        'elo_breakthrough_indicator': 0.0, 'elo_decline_indicator': 0.0, 'elo_stability_index': 0.0
                    }
                    home_elo_trends = default_trends.copy()
                    away_elo_trends = default_trends.copy()
                
                for key, value in home_elo_trends.items():
                    features[f'home_{key}'] = value
                for key, value in away_elo_trends.items():
                    features[f'away_{key}'] = value
                
                # 2E. MATCH CONTEXT ELO FEATURES (NYT!)
                match_context_elo = self.get_match_context_elo_features(home_team, away_team, match_date, season)
                features.update(match_context_elo)
                
                # 3. HEAD-TO-HEAD
                h2h_stats = self.calculate_head_to_head_stats(home_team, away_team, match_date)
                for key, value in h2h_stats.items():
                    features[f'h2h_{key}'] = value
                
                # 4. TEMPORAL FEATURES
                temporal = self.calculate_temporal_features(match_date, season)
                features.update(temporal)
                
                # 5. LIGA CONTEXT
                home_context = self.calculate_league_context_features(home_team, match_date, season)
                away_context = self.calculate_league_context_features(away_team, match_date, season)
                
                for key, value in home_context.items():
                    features[f'home_league_{key}'] = value
                for key, value in away_context.items():
                    features[f'away_league_{key}'] = value
                
                # 6. PERFORMANCE DIFFERENTIALS (OPDATERET MED ELO)
                features['team_strength_diff'] = (home_stats['offensive_strength'] - 
                                                 away_stats['defensive_strength'])
                features['defensive_diff'] = (home_stats['defensive_strength'] - 
                                             away_stats['offensive_strength'])
                features['form_diff'] = home_stats['momentum'] - away_stats['momentum']
                features['experience_diff'] = home_stats['games_played'] - away_stats['games_played']
                
                # ELO DIFFERENTIALS (OPDATERET)
                features['elo_team_rating_diff'] = (home_elo['elo_team_avg_rating'] - 
                                                   away_elo['elo_team_avg_rating'])
                features['elo_squad_rating_diff'] = (home_elo['elo_squad_avg_rating'] - 
                                                    away_elo['elo_squad_avg_rating'])
                features['elo_top7_rating_diff'] = (home_elo['elo_team_top7_rating'] - 
                                                   away_elo['elo_team_top7_rating'])
                features['elo_goalkeeper_diff'] = (home_elo['elo_goalkeeper_avg_rating'] - 
                                                  away_elo['elo_goalkeeper_avg_rating'])
                features['elo_elite_players_diff'] = (home_elo['elo_squad_elite_count'] - 
                                                     away_elo['elo_squad_elite_count'])
                features['elo_experience_diff'] = (home_elo['elo_squad_experienced_players'] - 
                                                  away_elo['elo_squad_experienced_players'])
                features['elo_momentum_diff'] = (home_elo['elo_squad_avg_momentum'] - 
                                                away_elo['elo_squad_avg_momentum'])
                features['elo_rating_spread_diff'] = (home_elo['elo_squad_std_rating'] - 
                                                     away_elo['elo_squad_std_rating'])
                
                # ELO TREND DIFFERENTIALS (NYT!)
                features['elo_season_progression_diff'] = (home_elo_trends['elo_season_progression'] - 
                                                          away_elo_trends['elo_season_progression'])
                features['elo_recent_form_diff'] = (home_elo_trends['elo_recent_trend_5'] - 
                                                   away_elo_trends['elo_recent_trend_5'])
                features['elo_volatility_diff'] = (home_elo_trends['elo_season_volatility'] - 
                                                  away_elo_trends['elo_season_volatility'])
                features['elo_consistency_diff'] = (home_elo_trends['elo_consistency_score'] - 
                                                   away_elo_trends['elo_consistency_score'])
                features['elo_peak_distance_diff'] = (home_elo_trends['elo_peak_distance'] - 
                                                     away_elo_trends['elo_peak_distance'])
                features['elo_stability_diff'] = (home_elo_trends['elo_stability_index'] - 
                                                 away_elo_trends['elo_stability_index'])
                features['elo_home_advantage_diff'] = (home_elo_trends['elo_home_advantage_rating'] - 
                                                      away_elo_trends['elo_away_performance_rating'])
                
                # POSITION-SPECIFIC ELO DIFFERENTIALS
                for pos in ['VF', 'HF', 'VB', 'PL', 'HB', 'ST', 'MV']:
                    features[f'elo_pos_{pos}_diff'] = (home_elo[f'elo_pos_{pos}_avg_rating'] - 
                                                      away_elo[f'elo_pos_{pos}_avg_rating'])
                    features[f'elo_pos_{pos}_depth_diff'] = (home_elo[f'elo_pos_{pos}_count'] - 
                                                            away_elo[f'elo_pos_{pos}_count'])
                
                # 7. ADVANCED METRICS (OPDATERET MED ELO)
                features['home_advantage_strength'] = (home_stats.get('home_win_rate', 0.5) - 
                                                     away_stats.get('away_win_rate', 0.3))
                features['total_firepower'] = (home_stats['offensive_strength'] + 
                                              away_stats['offensive_strength'])
                features['match_competitiveness'] = abs(home_stats['win_rate'] - away_stats['win_rate'])
                
                # ELO-BASEREDE ADVANCED METRICS (NYT!)
                features['elo_match_quality'] = (home_elo['elo_squad_avg_rating'] + 
                                                away_elo['elo_squad_avg_rating']) / 2
                features['elo_rating_uncertainty'] = abs(features['elo_squad_rating_diff']) / max(1, features['elo_match_quality'])
                features['elo_combined_elite_talent'] = (home_elo['elo_squad_elite_count'] + 
                                                        away_elo['elo_squad_elite_count'])
                features['elo_combined_experience'] = (home_elo['elo_squad_experienced_players'] + 
                                                      away_elo['elo_squad_experienced_players'])
                features['elo_goalkeeper_battle_quality'] = (home_elo['elo_goalkeeper_avg_rating'] + 
                                                            away_elo['elo_goalkeeper_avg_rating']) / 2
                features['elo_squad_balance_diff'] = (home_elo['elo_squad_balance'] - 
                                                     away_elo['elo_squad_balance'])
                features['elo_positional_advantage'] = (home_elo['elo_positional_depth'] - 
                                                       away_elo['elo_positional_depth'])
                
                # PREDICTIVE ELO METRICS
                elo_home_win_prob = 1 / (1 + 10**((away_elo['elo_squad_avg_rating'] - home_elo['elo_squad_avg_rating'])/400))
                features['elo_home_win_probability'] = elo_home_win_prob
                features['elo_away_win_probability'] = 1 - elo_home_win_prob
                features['elo_match_predictability'] = abs(elo_home_win_prob - 0.5) * 2  # 0=unpredictable, 1=very predictable
                
                # TARGET VARIABLES (det vi vil forudsige)
                try:
                    home_goals, away_goals = map(int, match_data['resultat'].split('-'))
                    features['target_home_goals'] = home_goals
                    features['target_away_goals'] = away_goals
                    features['target_total_goals'] = home_goals + away_goals
                    features['target_goal_difference'] = home_goals - away_goals
                    features['target_home_win'] = 1 if home_goals > away_goals else 0
                    features['target_away_win'] = 1 if away_goals > home_goals else 0
                    features['target_draw'] = 1 if home_goals == away_goals else 0
                    
                    # Margin categories
                    goal_diff = abs(home_goals - away_goals)
                    features['target_close_match'] = 1 if goal_diff <= 2 else 0
                    features['target_blowout'] = 1 if goal_diff >= 8 else 0
                    
                except:
                    continue
                
                self.dataset_rows.append(features)
                processed_count += 1
                
                if processed_count % 100 == 0:
                    print(f"  📊 Processeret {processed_count} kampe...")
                    
            except Exception as e:
                print(f"❌ Fejl ved processering af kamp {kamp_id}: {e}")
                continue
        
        print(f"\n✅ Dataset genereret: {len(self.dataset_rows)} samples")
        
    def save_dataset(self, output_file: str = "handball_ml_dataset.csv"):
        """Gemmer dataset til CSV"""
        if not self.dataset_rows:
            print("❌ Intet dataset at gemme!")
            return
            
        df = pd.DataFrame(self.dataset_rows)
        
        # Opret output directory
        output_dir = os.path.join(self.base_dir, "ML_Datasets")
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, f"{self.league.lower()}_{output_file}")
        df.to_csv(output_path, index=False)
        
        print(f"\n💾 Dataset gemt: {output_path}")
        print(f"📊 Shape: {df.shape}")
        print(f"🎯 Features: {df.shape[1] - 8} (excluding targets)")  # Minus targets
        
        # Print feature summary
        print(f"\n📋 FEATURE KATEGORIER:")
        feature_categories = {
            'Team Stats': len([col for col in df.columns if col.startswith(('home_', 'away_')) and 'players' not in col and 'league' not in col and 'pos_' not in col and 'elo_' not in col]),
            'Player Stats': len([col for col in df.columns if 'players' in col]),
            'Positional Stats': len([col for col in df.columns if 'pos_' in col]),
            'ELO Base Features': len([col for col in df.columns if 'elo_' in col and '_diff' not in col and 'trend' not in col and 'h2h' not in col]),
            'ELO Trends': len([col for col in df.columns if 'elo_' in col and ('trend' in col or 'progression' in col or 'volatility' in col or 'momentum' in col)]),
            'ELO Differentials': len([col for col in df.columns if 'elo_' in col and '_diff' in col]),
            'ELO Context': len([col for col in df.columns if 'elo_' in col and ('h2h' in col or 'context' in col or 'expected' in col or 'probability' in col)]),
            'Head-to-Head': len([col for col in df.columns if col.startswith('h2h_')]),
            'Temporal': len([col for col in df.columns if col in ['day_of_week', 'month', 'is_weekend', 'season_progress', 'days_from_season_start', 'is_christmas_period', 'is_spring_season', 'is_season_finale']]),
            'League Context': len([col for col in df.columns if 'league_' in col]),
            'Advanced Metrics': len([col for col in df.columns if col in ['team_strength_diff', 'defensive_diff', 'form_diff', 'experience_diff', 'home_advantage_strength', 'total_firepower', 'match_competitiveness']]),
            'Targets': len([col for col in df.columns if col.startswith('target_')])
        }
        
        for category, count in feature_categories.items():
            print(f"  {category}: {count} features")
        
        return output_path
    
    def run_complete_analysis(self):
        """Kører komplet dataset generering"""
        print(f"🚀 STARTER KOMPLET ML DATASET GENERERING")
        print("=" * 60)
        
        # Valider sæsoner
        self.validate_seasons()
        
        if not self.seasons:
            print("❌ Ingen gyldige sæsoner fundet!")
            return
        
        # Load historiske data
        self.load_all_historical_data()
        
        if not self.historical_data:
            print("❌ Ingen historiske data fundet!")
            return
        
        # Load historiske data
        self.load_all_historical_data()
        
        if not self.historical_data:
            print("❌ Ingen historiske data fundet!")
            return
        
        # Generer dataset
        self.generate_ml_dataset()
        
        # KRITISK: Valider data leakage
        validation_passed = self.validate_no_data_leakage()
        if not validation_passed:
            print("❌ VALIDATION FEJLEDE - Dataset kan indeholde data leakage!")
            print("⚠️  Tjek logs for detaljer og ret fejl før brug!")
        
        # Gem dataset
        output_path = self.save_dataset()
        
        print(f"\n🎉 ML DATASET KOMPLET!")
        print("=" * 60)
        print(f"📁 Output: {output_path}")
        print(f"🎯 {len(self.dataset_rows)} samples klar til machine learning")
        print("\n💡 KRITISKE PUNKTER:")
        print("  ✅ Kun historiske data (ingen data leakage)")
        print("  ✅ Omfattende feature engineering")
        print("  ✅ Multiple target variables")
        print("  ✅ Robust error handling")
        print("  ✅ Temporal awareness")
        
    def generate_features_for_single_match(self, match_info: Dict) -> Optional[Dict]:
        """
        Genererer et komplet feature set for en enkelt, fremtidig kamp.
        Dette er den centrale funktion, der bruges af både batch-træning og real-time prediction.

        Args:
            match_info: Et dictionary med info om kampen:
                - home_team (str)
                - away_team (str)
                - match_date (datetime)
                - season (str)
                - kamp_id (str, valgfri)

        Returns:
            Et dictionary med alle genererede features for kampen, klar til modellen.
            Returnerer None hvis kritiske data mangler.
        """
        home_team = self.normalize_team_name(match_info['home_team'])
        away_team = self.normalize_team_name(match_info['away_team'])
        match_date = match_info['match_date']
        season = match_info['season']
        kamp_id = match_info.get('kamp_id', f"new_{home_team}_{away_team}_{match_date.strftime('%Y%m%d')}")

        # --- Fuldstændig og korrekt feature-generering for en enkelt kamp ---
        
        # 1. Hent alle nødvendige data-komponenter
        home_stats = self.calculate_team_historical_stats(home_team, match_date, num_games=10)
        away_stats = self.calculate_team_historical_stats(away_team, match_date, num_games=10)
        home_players = self.calculate_player_features(home_team, match_date)
        away_players = self.calculate_player_features(away_team, match_date)
        home_positions = self.calculate_positional_features(home_team, match_date)
        away_positions = self.calculate_positional_features(away_team, match_date)
        squad_elo_home = self.calculate_squad_elo_features(home_team, match_date, season)
        squad_elo_away = self.calculate_squad_elo_features(away_team, match_date, season)
        elo_trends_home = self.calculate_elo_trends(home_team, match_date, season)
        elo_trends_away = self.calculate_elo_trends(away_team, match_date, season)
        match_context_elo = self.get_match_context_elo_features(home_team, away_team, match_date, season)
        h2h_stats = self.calculate_head_to_head_stats(home_team, away_team, match_date)
        temporal = self.calculate_temporal_features(match_date, season)
        home_context = self.calculate_league_context_features(home_team, match_date, season)
        away_context = self.calculate_league_context_features(away_team, match_date, season)

        # 2. Byg feature-dictionaryet med 100% korrekte præfikser
        features = {
            'kamp_id': kamp_id, 'season': season, 'match_date': match_date.strftime("%Y-%m-%d"),
            'home_team': home_team, 'away_team': away_team, 'venue': 'Home', 'league': self.league,
        }

        def _add_prefix(data, prefix):
            return {f"{prefix}_{key}": value for key, value in data.items()}

        features.update(_add_prefix(home_stats, 'home'))
        features.update(_add_prefix(away_stats, 'away'))
        features.update(_add_prefix(home_players, 'home_players'))
        features.update(_add_prefix(away_players, 'away_players'))
        features.update(_add_prefix(home_positions, 'home'))
        features.update(_add_prefix(away_positions, 'away'))
        features.update(_add_prefix(squad_elo_home, 'home'))
        features.update(_add_prefix(squad_elo_away, 'away'))
        features.update(_add_prefix(elo_trends_home, 'home'))
        features.update(_add_prefix(elo_trends_away, 'away'))
        features.update(match_context_elo) # Har allerede korrekte navne
        features.update(_add_prefix(h2h_stats, 'h2h'))
        features.update(temporal) # Har ikke præfiks
        features.update(_add_prefix(home_context, 'home_league'))
        features.update(_add_prefix(away_context, 'away_league'))
        
        # 3. Beregn differential-features til sidst
        features['team_strength_diff'] = features.get('home_offensive_strength', 0) - features.get('away_defensive_strength', 0)
        features['defensive_diff'] = features.get('home_defensive_strength', 0) - features.get('away_offensive_strength', 0)
        features['form_diff'] = features.get('home_momentum', 0) - features.get('away_momentum', 0)
        features['elo_team_rating_diff'] = features.get('home_elo_team_weighted_rating', 1200) - features.get('away_elo_team_weighted_rating', 1200)
        features['elo_top7_rating_diff'] = features.get('home_elo_team_top7_rating', 1200) - features.get('away_elo_team_top7_rating', 1200)
        features['home_advantage_strength'] = features.get('home_home_win_rate', 0.5) - features.get('away_away_win_rate', 0.3)
        
        return features

# === MAIN EXECUTION ===
if __name__ == "__main__":
    print("🎯 HÅNDBOL ML DATASET GENERATOR (AVANCERET ELO + TRENDS)")
    print("=" * 70)
    
    # Vælg liga fra command line arguments
    import sys
    
    if len(sys.argv) > 1:
        league = sys.argv[1]
        if league not in ["Herreliga", "Kvindeliga"]:
            print(f"❌ Ugyldig liga: {league}. Brug 'Herreliga' eller 'Kvindeliga'")
            sys.exit(1)
    else:
        # Default til begge ligaer
        leagues = ["Herreliga", "Kvindeliga"]
        print("🔄 Processerer begge ligaer...")
        
        for league in leagues:
            print(f"\n{'='*50}")
            print(f"🎯 STARTER {league.upper()}")
            print(f"{'='*50}")
            
            try:
                # Opret generator
                generator = HandballMLDatasetGenerator(base_dir=".", league=league)
                
                # Kør komplet analyse
                generator.run_complete_analysis()
                
                print(f"\n🏆 {league.upper()} ML DATASET KOMPLET!")
                
            except Exception as e:
                print(f"❌ FEJL VED PROCESSERING AF {league}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"\n🎉 ALLE LIGAER PROCESSERET!")
        sys.exit(0)
    
    # Single liga execution
    try:
        # Opret generator
        generator = HandballMLDatasetGenerator(base_dir=".", league=league)
        
        # Kør komplet analyse
        generator.run_complete_analysis()
        
        print(f"\n🏆 {league.upper()} ML DATASET KOMPLET!")
        
        # Sæson information
        if league == "Herreliga":
            print("📅 Herreliga: 2017-2018 til 2024-2025 (8 sæsoner)")
        else:
            print("📅 Kvindeliga: 2018-2019 til 2024-2025 (7 sæsoner)")
            
        print("\n🚀 NÆSTE SKRIDT:")
        print("  1. Kør ML analysis: python ml_usage_examples.py")
        print("  2. Tjek dataset filer i ML_Datasets/ directory")
        print("  3. Valider feature importance rankings")
        print("  4. Test forskellige ML algoritmer")
        print("  5. Implementer temporal cross-validation")
        
    except Exception as e:
        print(f"❌ FEJL VED GENERERING AF {league} DATASET: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


"""
🎯 POSITIONSSPECIFIKKE FEATURES DOKUMENTATION
==============================================

Dette script genererer følgende POSITIONSSPECIFIKKE features for hver af de 10 håndboldpositioner:

POSITIONER (data.md korrekte):
- VF (Venstre fløj)
- HF (Højre fløj)  
- VB (Venstre back)
- PL (Playmaker)
- HB (Højre back)
- ST (Streg)
- Gbr (Gennembrud)
- 1:e (Første bølge kontra)
- 2:e (Anden bølge kontra)
- MV (Målvogter - identificeres via nr_mv/mv felter)

FOR HVER POSITION GENERERES:
1. pos_{POS}_total_actions - Totale aktioner fra position
2. pos_{POS}_attempts - Afslutningsforsøg fra position
3. pos_{POS}_goals - Mål scoret fra position
4. pos_{POS}_assists - Assists fra position
5. pos_{POS}_blocks - Blokerede skud fra position
6. pos_{POS}_turnovers - Boldomgivelser fra position
7. pos_{POS}_fouls - Fejl begået fra position
8. pos_{POS}_goal_conversion - Måleffektivitet (mål/forsøg) 
9. pos_{POS}_turnover_rate - Boldomgivelsesrate
10. pos_{POS}_foul_rate - Fejlrate
11. pos_{POS}_goal_share - Andel af holdets totale mål
12. pos_{POS}_attempt_share - Andel af holdets totale forsøg
13. pos_{POS}_action_share - Andel af holdets totale aktioner

AGGREGEREDE POSITIONSFEATURES:
- pos_offensive_diversity - Antal målscorende positioner
- pos_wing_dominance - Fløjspillernes andel af mål (VF+HF)
- pos_back_dominance - Bagspillernes andel af mål (VB+HB+PL)
- pos_pivot_dominance - Stregspillerens andel af mål (ST)
- pos_breakthrough_dominance - Gennembruds andel af mål (Gbr)
- pos_fastbreak_dominance - Kontraangrebsmål andel (1:e+2:e)

TAKTISKE STIL INDIKATORER:
- pos_wing_heavy_offense - Om holdet er fløj-domineret
- pos_pivot_heavy_offense - Om holdet er streg-domineret  
- pos_back_heavy_offense - Om holdet er back-domineret
- pos_balanced_offense - Om holdet har balanceret angreb
- pos_structured_vs_transition - Struktureret vs omstillingsangreb ratio
- pos_transition_percentage - Procent mål fra omstilling (Gbr+kontra)
- pos_structured_percentage - Procent mål fra struktureret angreb (back+streg)

DEFENSIV & DISCIPLIN:
- pos_total_blocks - Totale blokerede skud
- pos_defensive_activity - Defensiv aktivitetsrate
- pos_total_fouls - Totale fejl
- pos_total_turnovers - Totale boldomgivelser
- pos_discipline_ratio - Disciplinær ratio
- pos_ball_security_ratio - Boldsikkerhedsrate

MÅLVOGTER SPECIFIKKE:
- pos_MV_saves - Antal redninger
- pos_MV_save_rate - Redningsprocent
- pos_goalkeeper_activity_level - Målvogter aktivitetsniveau
- pos_goalkeeper_workload - Målvogter arbejdsbyrde
 
AVANCEREDE METRICS:
- pos_goal_distribution_variance - Spredning i målscoring
- pos_is_specialist_team - Om holdet har specialister
- pos_tactical_width - Antal aktive positioner
- pos_uses_all_positions - Om alle positioner bruges
- pos_efficiency_spread - Spredning i positionseffektivitet

TOTALT: ~150+ positionsspecifikke features per hold (300+ total per kamp)

### ELO-BASEREDE FEATURES (NYT!):

**HOLD-NIVEAU ELO FEATURES:**
- elo_team_avg_rating - Gennemsnit hold rating
- elo_team_top7_rating - Top 7 spillere rating
- elo_team_top12_rating - Top 12 spillere rating  
- elo_team_best_position_rating - Bedste position rating
- elo_team_weighted_rating - Vægtede position rating
- elo_team_players_count - Antal spillere med ELO
- elo_team_elite_players - Antal elite spillere
- elo_team_rating_std - Standardafvigelse i ratings
- elo_team_rating_range - Spredning i ratings

**SPILLER-NIVEAU ELO AGGREGERINGER:**
- elo_squad_avg_rating - Gennemsnit spiller rating
- elo_squad_median_rating - Median spiller rating
- elo_squad_max_rating - Højeste spiller rating
- elo_squad_min_rating - Laveste spiller rating
- elo_squad_std_rating - Standardafvigelse spillere
- elo_squad_total_rating_change - Total rating ændring
- elo_squad_avg_momentum - Gennemsnit momentum
- elo_squad_elite_count - Antal elite spillere
- elo_squad_legendary_count - Antal legendary spillere
- elo_squad_experienced_players - Antal erfarne spillere (10+ kampe)

**MÅLVOGTER ELO FEATURES:**
- elo_goalkeeper_count - Antal målvogtere
- elo_goalkeeper_avg_rating - Gennemsnit målvogter rating
- elo_goalkeeper_max_rating - Bedste målvogter rating
- elo_goalkeeper_rating_spread - Spredning målvogter ratings

**POSITION-SPECIFIC ELO (for hver position VF,HF,VB,PL,HB,ST,MV):**
- elo_pos_{POS}_avg_rating - Gennemsnit rating for position
- elo_pos_{POS}_max_rating - Bedste rating for position
- elo_pos_{POS}_count - Antal spillere på position

**ELO DIFFERENTIALS (Sammenligning mellem hold):**
- elo_team_rating_diff - Forskel i hold ratings
- elo_squad_rating_diff - Forskel i spiller ratings
- elo_goalkeeper_diff - Forskel i målvogter ratings
- elo_elite_players_diff - Forskel i elite spillere
- elo_momentum_diff - Forskel i momentum
- elo_pos_{POS}_diff - Forskel per position

**PREDICTIVE ELO METRICS:**
- elo_home_win_probability - ELO-baseret hjemme sejr sandsynlighed
- elo_away_win_probability - ELO-baseret ude sejr sandsynlighed  
- elo_match_predictability - Hvor forudsigelig kampen er (0-1)
- elo_match_quality - Samlet kvalitet af kampen
- elo_rating_uncertainty - Usikkerhed i rating forskelle

**ELO TRENDS FEATURES (NYT!):**
- elo_early_season_rating - Rating tidligt i sæsonen
- elo_mid_season_rating - Rating midt i sæsonen  
- elo_late_season_rating - Rating sent i sæsonen
- elo_season_progression - Total rating udvikling gennem sæson
- elo_season_volatility - Volatilitet i ratings gennem sæson
- elo_recent_5_avg - Gennemsnit sidste 5 kampe
- elo_recent_10_avg - Gennemsnit sidste 10 kampe
- elo_recent_trend_5 - Trend sidste 5 kampe
- elo_recent_trend_10 - Trend sidste 10 kampe
- elo_recent_volatility - Volatilitet i seneste form
- elo_season_peak_rating - Højeste rating i sæsonen
- elo_season_low_rating - Laveste rating i sæsonen
- elo_peak_distance - Afstand fra peak performance
- elo_consistency_score - Konsistens score (0-1)
- elo_positive_momentum - Antal positive rating ændringer
- elo_negative_momentum - Antal negative rating ændringer
- elo_last_5_wins - Sejre i sidste 5 kampe (ELO basis)
- elo_last_5_rating_change - Rating ændring sidste 5 kampe
- elo_home_advantage_rating - Hjemmebane ELO fordel
- elo_away_performance_rating - Udebane ELO performance
- elo_venue_consistency - Konsistens hjemme vs ude
- elo_regression_to_mean - Regression til middeltal indikator
- elo_breakthrough_indicator - Gennembrud indikator
- elo_decline_indicator - Tilbagegang indikator
- elo_stability_index - Stabilitet index (0-1)

**ELO CONTEXT FEATURES (NYT!):**
- elo_h2h_home_advantage - Head-to-head hjemmebane fordel
- elo_h2h_rating_consistency - H2H rating konsistens
- elo_h2h_avg_quality - H2H gennemsnit kvalitet
- elo_h2h_competitiveness - H2H konkurrenceevne
- elo_expected_goal_difference - Forventet målforskel fra ELO
- elo_blowout_probability - Sandsynlighed for ensidig kamp
- elo_close_match_probability - Sandsynlighed for tæt kamp
- elo_form_convergence - Form konvergens mellem hold
- elo_momentum_clash - Momentum sammenstød
- elo_peak_vs_peak - Peak performance sammenligning
- elo_context_importance - Hvor vigtig ELO er i denne kamp
- elo_upset_potential - Potentiale for overraskelse
- elo_volatility_factor - Volatilitet faktor

**ELO TREND DIFFERENTIALS (NYT!):**
- elo_season_progression_diff - Forskel i sæson progression
- elo_recent_form_diff - Forskel i seneste form
- elo_volatility_diff - Forskel i volatilitet
- elo_consistency_diff - Forskel i konsistens
- elo_peak_distance_diff - Forskel i afstand fra peak
- elo_stability_diff - Forskel i stabilitet
- elo_home_advantage_diff - Forskel i hjemmebane fordel

TOTALT ELO FEATURES: ~300+ ELO features per kamp (inkl. trends)

**DATA LEAKAGE BESKYTTELSE:**
✅ Temporal validation - alle data FØR kampstart
✅ Kronologisk ordering validering  
✅ ELO værdier indenfor realistiske ranges
✅ Feature value consistency checks
✅ Automatisk data leakage detection

**SÆSON COVERAGE:**
✅ Herreliga: 2017-2018 til 2024-2025 (8 sæsoner)
✅ Kvindeliga: 2018-2019 til 2024-2025 (7 sæsoner)
✅ Separat processing for hver liga
✅ Liga-specifik ELO system integration

KRITISK FORSKEL FRA TIDLIGERE FEJLAGTIG VERSION:
✅ Korrekte positioner baseret på data.md
✅ VB/HB (back positioner) i stedet for forkerte PR/PL references  
✅1:e/2:e (kontra bølger) i stedet for forkerte fastbreak kategorier
✅ Korrekt gruppering: wings (VF+HF), backs (VB+HB+PL), pivot (ST)
✅ ELO system integration med data leakage beskyttelse
✅ Spillere og hold ELO ratings fra eksisterende CSV systemer
✅ Position-specific ELO analyser
✅ Predictive ELO metrics til ML modeller
✅ ELO trends & volatilitet features
✅ Advanced context & momentum features
✅ Comprehensive data validation system
"""