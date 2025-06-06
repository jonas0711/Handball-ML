#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 HOLD SÆSON-BASERET HÅNDBOL ELO SYSTEM
========================================

BYGGER PÅ DET AVANCEREDE SPILLER ELO SYSTEM MEN FOKUSERER PÅ HOLD:
✅ Sæson-for-sæson processering af hold
✅ Intelligent regression to mean mellem sæsoner
✅ Detaljerede per-sæson CSV filer for hold
✅ Karriere tracking på tværs af sæsoner for hold
✅ Robust fejlhåndtering og debugging
✅ Elite hold skal præstere for at bevare rating
✅ Hjemme/ude fordel og venue tracking
✅ Målforskels påvirkning på ELO ændringer
✅ Momentum tracking for hold
✅ Liga-specifik analyse (Herreliga/Kvindeliga separat)

HOLD ELO FILOSOFI:
- Store sejre giver mere ELO end knappe sejre
- Hjemmebane fordel indregnet
- Hold der spiller mange kampe får stabilere ratings
- Elite hold skal præstere konsistent for at beholde høj rating
- Regression to mean sikrer fair konkurrence på tværs af sæsoner

Jonas' Team ELO System - December 2024
"""

import pandas as pd
import numpy as np
import sqlite3
import os
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# === TEAM ELO SYSTEM PARAMETRE ===
BASE_TEAM_RATING = 1400           # Højere base rating for hold end spillere
MIN_GAMES_FOR_FULL_CARRY = 10    # Mindst 10 kampe for fuld carry-over
MAX_CARRY_BONUS = 300            # Max +300 bonus fra forrige sæson  
MIN_CARRY_PENALTY = -200         # Max -200 straf fra forrige sæson
REGRESSION_STRENGTH = 0.55       # 55% regression to mean mellem sæsoner

# K-FACTOR FOR ELO BEREGNINGER
K_FACTOR_BASE = 25               # Base K-factor for ELO ændringer
K_FACTOR_NEW_TEAM = 40           # Højere K-factor for nye hold
K_FACTOR_ELITE = 15              # Lavere K-factor for elite hold

# HJEMME/UDE FORDEL
HOME_ADVANTAGE = 75              # Hjemmebane fordel i ELO beregning

# MÅLFORSKELS MULTIPLIKATORER
GOAL_DIFF_MULTIPLIERS = {
    1: 1.0,    # Knap sejr/nederlag
    2: 1.1,    # Tæt sejr/nederlag  
    3: 1.2,    # Klar sejr/nederlag
    4: 1.3,    # Stor sejr/nederlag
    5: 1.4,    # Meget stor sejr/nederlag
    10: 1.8,   # Massiv sejr/nederlag
    15: 2.0    # Historisk sejr/nederlag
}

# TEAM CODE MAPPING fra eksisterende system
TEAM_CODE_MAP = {
    # Kvindeligaen
    "AHB": "Aarhus Håndbold Kvinder", "BFH": "Bjerringbro FH", "EHA": "EH Aalborg",
    "HHE": "Horsens Håndbold Elite", "IKA": "Ikast Håndbold", "KBH": "København Håndbold",
    "NFH": "Nykøbing F. Håndbold", "ODE": "Odense Håndbold", "RIN": "Ringkøbing Håndbold",
    "SVK": "Silkeborg-Voel KFUM", "SKB": "Skanderborg Håndbold", "SJE": "SønderjyskE Kvindehåndbold",
    "TES": "Team Esbjerg", "VHK": "Viborg HK", "TMS": "TMS Ringsted",
    # Herreligaen
    "AAH": "Aalborg Håndbold", "BSH": "Bjerringbro-Silkeborg", "FHK": "Fredericia Håndbold Klub",
    "GIF": "Grindsted GIF Håndbold", "GOG": "GOG", "KIF": "KIF Kolding",
    "MTH": "Mors-Thy Håndbold", "NSH": "Nordsjælland Håndbold", "REH": "Ribe-Esbjerg HH",
    "SAH": "SAH - Skanderborg AGF", "SKH": "Skjern Håndbold", "SJE": "SønderjyskE Herrehåndbold",
    "TTH": "TTH Holstebro"
}

class TeamSeasonalEloSystem:
    """
    🏆 HOLD SÆSON-BASERET ELO SYSTEM
    """
    
    def __init__(self, base_dir: str = "."):
        print("🏆 HOLD SÆSON-BASERET HÅNDBOL ELO SYSTEM")
        print("=" * 70)
        
        self.base_dir = base_dir
        
        # Hold data storage
        self.all_season_results = {}
        self.team_career_data = defaultdict(list)
        self.team_elos = defaultdict(lambda: BASE_TEAM_RATING)
        self.team_momentum = defaultdict(list)  # Seneste kampe for momentum
        
        # Database directories
        self.herreliga_dir = os.path.join(base_dir, "Herreliga-database")
        self.kvindeliga_dir = os.path.join(base_dir, "Kvindeliga-database")
        
        # Available seasons
        self.seasons = [
            "2017-2018", "2018-2019", "2019-2020", "2020-2021", 
            "2021-2022", "2022-2023", "2023-2024", "2024-2025"
        ]
        
        # Validate seasons exist
        self.validate_season_availability()
        
        # Team code to name mapping
        self.team_code_to_name = TEAM_CODE_MAP
        self.team_name_to_code = {v: k for k, v in TEAM_CODE_MAP.items()}
        
        print("✅ Team ELO system initialiseret")
        print(f"📅 Tilgængelige sæsoner: {len(self.seasons)}")
        print(f"🎯 Base team rating: {BASE_TEAM_RATING}")
        print(f"🏠 Hjemmebane fordel: +{HOME_ADVANTAGE}")
        print(f"⚖️ K-factor base: {K_FACTOR_BASE}")
        
    def validate_season_availability(self):
        """Validerer at sæsoner findes i begge ligaer"""
        print(f"\n🔍 VALIDERER SÆSON TILGÆNGELIGHED")
        print("-" * 50)
        
        valid_seasons = []
        
        for season in self.seasons:
            herreliga_path = os.path.join(self.herreliga_dir, season)
            kvindeliga_path = os.path.join(self.kvindeliga_dir, season)
            
            herreliga_files = 0
            kvindeliga_files = 0
            
            if os.path.exists(herreliga_path):
                herreliga_files = len([f for f in os.listdir(herreliga_path) if f.endswith('.db')])
                
            if os.path.exists(kvindeliga_path):
                kvindeliga_files = len([f for f in os.listdir(kvindeliga_path) if f.endswith('.db')])
                
            total_files = herreliga_files + kvindeliga_files
            
            if total_files > 0:
                valid_seasons.append(season)
                print(f"  ✅ {season}: {total_files} kampe (H:{herreliga_files}, K:{kvindeliga_files})")
            else:
                print(f"  ❌ {season}: ingen data")
                
        self.seasons = valid_seasons
        print(f"\n📊 {len(self.seasons)} gyldige sæsoner klar til hold processering")
        
    def normalize_team_name(self, team_name: str) -> str:
        """Normaliserer holdnavn til standard format"""
        if not team_name:
            return ""
        
        team_clean = str(team_name).strip()
        
        # Check hvis det er en holdkode
        if team_clean in self.team_code_to_name:
            return self.team_code_to_name[team_clean]
            
        # Check varianter og returner direkte hvis det matcher
        for code, name in self.team_code_to_name.items():
            if team_clean == name:
                return name
                
        return team_clean
        
    def get_team_code(self, team_name: str) -> str:
        """Henter holdkode fra holdnavn"""
        normalized = self.normalize_team_name(team_name)
        return self.team_name_to_code.get(normalized, team_name[:3].upper())
        
    def calculate_elo_change(self, team_rating: float, opponent_rating: float, 
                           result: int, goal_diff: int, is_home: bool, 
                           team_games: int) -> float:
        """
        🧮 BEREGNER ELO ÆNDRING FOR ET HOLD
        
        Args:
            team_rating: Holdets aktuelle ELO rating
            opponent_rating: Modstanderens ELO rating
            result: 1 for sejr, 0.5 for uafgjort, 0 for nederlag
            goal_diff: Målforskellen (absolut værdi)
            is_home: True hvis holdet spiller hjemme
            team_games: Antal kampe holdet har spillet (påvirker K-factor)
        """
        
        # Juster modstander rating for hjemmebane fordel
        adjusted_opponent = opponent_rating
        if is_home:
            adjusted_opponent -= HOME_ADVANTAGE
        else:
            adjusted_opponent += HOME_ADVANTAGE
            
        # Forventet resultat baseret på ELO difference
        rating_diff = team_rating - adjusted_opponent
        expected_score = 1 / (1 + 10 ** (-rating_diff / 400))
        
        # K-factor baseret på holdets erfaring og rating niveau
        if team_games < 5:
            k_factor = K_FACTOR_NEW_TEAM
        elif team_rating >= BASE_TEAM_RATING + 400:  # Elite hold
            k_factor = K_FACTOR_ELITE
        else:
            k_factor = K_FACTOR_BASE
            
        # Målforskels multiplikator
        goal_diff = abs(goal_diff)
        multiplier = 1.0
        
        for diff_threshold in sorted(GOAL_DIFF_MULTIPLIERS.keys()):
            if goal_diff >= diff_threshold:
                multiplier = GOAL_DIFF_MULTIPLIERS[diff_threshold]
                
        # Beregn ELO ændring
        elo_change = k_factor * multiplier * (result - expected_score)
        
        return round(elo_change, 1)
        
    def update_team_momentum(self, team_code: str, elo_change: float):
        """Opdaterer momentum tracking for et hold"""
        if team_code not in self.team_momentum:
            self.team_momentum[team_code] = []
            
        self.team_momentum[team_code].append(elo_change)
        
        # Behold kun de seneste 5 kampe
        if len(self.team_momentum[team_code]) > 5:
            self.team_momentum[team_code].pop(0)
            
    def get_team_momentum_factor(self, team_code: str) -> float:
        """Beregner momentum faktor baseret på seneste kampe"""
        if team_code not in self.team_momentum or not self.team_momentum[team_code]:
            return 1.0
            
        recent_changes = self.team_momentum[team_code]
        avg_change = sum(recent_changes) / len(recent_changes)
        
        # Konverter til momentum faktor mellem 0.8 og 1.2
        momentum_factor = 1.0 + (avg_change / 100)  # Normaliseret ændring
        return max(0.8, min(1.2, momentum_factor))
        
    def process_match(self, match_info: dict, season: str, league: str) -> bool:
        """
        🏐 PROCESSERER EN ENKELT KAMP FOR HOLD ELO BEREGNING
        """
        try:
            # Hent kamp information
            home_team = str(match_info.get('hold_hjemme', '')).strip()
            away_team = str(match_info.get('hold_ude', '')).strip()
            result_str = str(match_info.get('resultat', '')).strip()
            
            if not home_team or not away_team or not result_str:
                return False
                
            # Parser resultatet
            try:
                home_goals, away_goals = map(int, result_str.split('-'))
            except (ValueError, AttributeError):
                return False
                
            # Normaliser holdnavne og få koder
            home_normalized = self.normalize_team_name(home_team)
            away_normalized = self.normalize_team_name(away_team)
            home_code = self.get_team_code(home_normalized)
            away_code = self.get_team_code(away_normalized)
            
            # Hent aktuelle ratings
            home_rating = self.team_elos[home_code]
            away_rating = self.team_elos[away_code]
            
            # Beregn målforskellen
            goal_diff = abs(home_goals - away_goals)
            
            # Bestem resultat (1 for sejr, 0.5 for uafgjort, 0 for nederlag)
            if home_goals > away_goals:
                home_result = 1.0
                away_result = 0.0
            elif home_goals < away_goals:
                home_result = 0.0
                away_result = 1.0
            else:
                home_result = 0.5
                away_result = 0.5
                
            # Hent antal kampe for hold (estimeret baseret på sæson progression)
            home_games = len([s for s in self.team_career_data[home_code] if s['season'] == season])
            away_games = len([s for s in self.team_career_data[away_code] if s['season'] == season])
            
            # Beregn ELO ændringer
            home_elo_change = self.calculate_elo_change(
                home_rating, away_rating, home_result, goal_diff, True, home_games
            )
            away_elo_change = self.calculate_elo_change(
                away_rating, home_rating, away_result, goal_diff, False, away_games
            )
            
            # Opdater ratings
            self.team_elos[home_code] += home_elo_change
            self.team_elos[away_code] += away_elo_change
            
            # Opdater momentum
            self.update_team_momentum(home_code, home_elo_change)
            self.update_team_momentum(away_code, away_elo_change)
            
            # Log betydelige ændringer
            if abs(home_elo_change) > 30 or abs(away_elo_change) > 30:
                print(f"    🔥 Stor ELO ændring: {home_normalized} {home_elo_change:+.1f}, "
                      f"{away_normalized} {away_elo_change:+.1f} "
                      f"({home_goals}-{away_goals}, diff:{goal_diff})")
                      
            return True
            
        except Exception as e:
            print(f"❌ Fejl ved processering af kamp: {e}")
            return False
            
    def process_season_database(self, season: str, league_dir: str, league_name: str) -> int:
        """
        Processerer alle kampe i en sæson for en specifik liga
        """
        season_path = os.path.join(league_dir, season)
        
        if not os.path.exists(season_path):
            return 0
            
        db_files = [f for f in os.listdir(season_path) if f.endswith('.db')]
        matches_processed = 0
        
        print(f"  📂 Processerer {len(db_files)} {league_name} kampe for {season}")
        
        for db_file in db_files:
            db_path = os.path.join(season_path, db_file)
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Hent match info
                cursor.execute("SELECT * FROM match_info")
                match_info_raw = cursor.fetchone()
                
                if match_info_raw:
                    # Konverter til dictionary (antager standard kolonner)
                    columns = ['kamp_id', 'hold_hjemme', 'hold_ude', 'resultat', 
                              'halvleg_resultat', 'dato', 'sted', 'turnering']
                    match_info = dict(zip(columns, match_info_raw))
                    
                    if self.process_match(match_info, season, league_name):
                        matches_processed += 1
                        
                conn.close()
                
            except Exception as e:
                print(f"    ❌ Fejl i {db_file}: {e}")
                continue
                
        return matches_processed
        
    def calculate_intelligent_team_start_rating(self, team_code: str, 
                                              previous_season_data: Dict = None,
                                              league_stats: Dict = None) -> float:
        """
        🧠 INTELLIGENT HOLD START RATING BEREGNING MED REGRESSION TO MEAN
        
        Faktorer der påvirker hold start rating:
        1. Forrige sæson final rating
        2. Antal kampe spillet (hold med mange kampe får mindre regression)
        3. Distance fra liga gennemsnit (ekstreme ratings regresses mere)
        4. Elite status (top hold skal arbejde hårdere for at beholde position)
        5. Momentum fra slutningen af forrige sæson
        6. Liga performance relativ til andre hold
        """
        
        if not previous_season_data:
            return BASE_TEAM_RATING
            
        prev_rating = previous_season_data.get('final_rating', BASE_TEAM_RATING)
        prev_games = previous_season_data.get('games', 0)
        prev_momentum = previous_season_data.get('momentum_factor', 1.0)
        prev_elite_status = previous_season_data.get('elite_status', 'NORMAL')
        
        # Hvis ingen tidligere rating, start på base
        if prev_rating == BASE_TEAM_RATING:
            return BASE_TEAM_RATING
            
        # === REGRESSION TARGET ===
        league_avg = league_stats.get('avg_rating', BASE_TEAM_RATING) if league_stats else BASE_TEAM_RATING
        distance_from_mean = prev_rating - league_avg
        
        # === GAMES FACTOR ===
        # Hold med flere kampe får mindre regression
        if prev_games >= MIN_GAMES_FOR_FULL_CARRY:
            games_factor = 1.0  # Fuld carry-over
        elif prev_games >= 8:
            # Gradueret mellem 8-10 kampe
            games_factor = 0.7 + 0.3 * (prev_games - 8) / (MIN_GAMES_FOR_FULL_CARRY - 8)
        elif prev_games >= 4:
            # Minimal carry-over
            games_factor = 0.4 + 0.3 * (prev_games - 4) / 4
        else:
            games_factor = 0.3  # Lav carry-over for få kampe
            
        # === ELITE STATUS FACTOR ===
        # Elite hold skal arbejde hårdere for at beholde høj rating
        if prev_elite_status == 'LEGENDARY':
            elite_factor = 0.6  # Stærk regression for legendary
        elif prev_elite_status == 'ELITE':
            elite_factor = 0.75  # Moderat regression for elite
        else:
            elite_factor = 0.9   # Minimal regression for normale
            
        # === MOMENTUM FACTOR ===
        # Gode momentum på slutningen af sæsonen giver bedre start
        if prev_momentum > 1.1:
            momentum_factor = 1.1   # Positiv momentum bonus
        elif prev_momentum < 0.9:
            momentum_factor = 0.9   # Negativ momentum straf
        else:
            momentum_factor = 1.0   # Neutral
            
        # === DISTANCE FACTOR ===
        # Progressive regression baseret på distance fra gennemsnit
        abs_distance = abs(distance_from_mean)
        if abs_distance > 400:
            distance_factor = 0.5  # Ekstremt stærk regression
        elif abs_distance > 300:
            distance_factor = 0.65  # Stærk regression
        elif abs_distance > 200:
            distance_factor = 0.8   # Moderat regression
        elif abs_distance > 100:
            distance_factor = 0.9   # Svag regression
        else:
            distance_factor = 0.95  # Minimal regression
            
        # === KOMBINER ALLE FAKTORER ===
        combined_factor = games_factor * elite_factor * momentum_factor * distance_factor
        
        # Beregn ny start rating
        regressed_distance = distance_from_mean * combined_factor
        new_start_rating = league_avg + regressed_distance
        
        # === APPLY CAPS ===
        rating_change = new_start_rating - BASE_TEAM_RATING
        
        if rating_change > MAX_CARRY_BONUS:
            new_start_rating = BASE_TEAM_RATING + MAX_CARRY_BONUS
        elif rating_change < MIN_CARRY_PENALTY:
            new_start_rating = BASE_TEAM_RATING + MIN_CARRY_PENALTY
            
        # Debug for betydelige ændringer
        total_change = new_start_rating - prev_rating
        team_name = self.team_code_to_name.get(team_code, team_code)
        
        if abs(total_change) > 75:
            print(f"    📊 {team_name}: {prev_rating:.0f} → {new_start_rating:.0f} "
                  f"({total_change:+.0f}) [{prev_games} kampe, {prev_elite_status}]")
                  
        return round(new_start_rating, 1)
        
    def run_season_analysis(self, season: str, start_ratings: Dict = None) -> Dict:
        """
        Kører hold ELO analyse for en enkelt sæson
        """
        print(f"\n🏐 PROCESSERER HOLD SÆSON {season}")
        print("-" * 50)
        
        # Set start ratings if provided
        if start_ratings:
            print(f"📈 Sætter start ratings for {len(start_ratings)} hold")
            for team_code, start_rating in start_ratings.items():
                self.team_elos[team_code] = start_rating
        else:
            # Reset alle hold til base rating for første sæson
            self.team_elos.clear()
            self.team_elos = defaultdict(lambda: BASE_TEAM_RATING)
            
        # Process begge ligaer for denne sæson
        total_matches = 0
        
        # Herreliga
        herreliga_matches = self.process_season_database(
            season, self.herreliga_dir, "Herreliga"
        )
        total_matches += herreliga_matches
        
        # Kvindeliga  
        kvindeliga_matches = self.process_season_database(
            season, self.kvindeliga_dir, "Kvindeliga"
        )
        total_matches += kvindeliga_matches
        
        if total_matches == 0:
            print(f"❌ Ingen kampe processeret for {season}")
            return {}
            
        print(f"✅ Total: {total_matches} kampe processeret")
        
        # Generate season results
        season_results = {}
        
        for team_code, final_rating in self.team_elos.items():
            # Kun inkluder hold der faktisk har spillet
            team_matches = [s for s in self.team_career_data[team_code] if s['season'] == season]
            games = len(team_matches)
            
            if games > 0 or final_rating != BASE_TEAM_RATING:
                team_name = self.team_code_to_name.get(team_code, team_code)
                start_rating = start_ratings.get(team_code, BASE_TEAM_RATING) if start_ratings else BASE_TEAM_RATING
                
                # Elite status baseret på final rating
                if final_rating >= BASE_TEAM_RATING + 400:
                    elite_status = "LEGENDARY"
                elif final_rating >= BASE_TEAM_RATING + 200:
                    elite_status = "ELITE"
                else:
                    elite_status = "NORMAL"
                    
                # Momentum factor
                momentum_factor = self.get_team_momentum_factor(team_code)
                
                # Bestem liga baseret på team code
                if team_code in ["AAH", "BSH", "FHK", "GIF", "GOG", "KIF", "MTH", "NSH", "REH", "SAH", "SKH", "SJE", "TTH"]:
                    league = "Herreliga"
                else:
                    league = "Kvindeliga"
                
                season_results[team_code] = {
                    'season': season,
                    'team_code': team_code,
                    'team_name': team_name,
                    'league': league,
                    'start_rating': round(start_rating, 1),
                    'final_rating': round(final_rating, 1),
                    'rating_change': round(final_rating - start_rating, 1),
                    'games': games,
                    'elite_status': elite_status,
                    'momentum_factor': round(momentum_factor, 3)
                }
                
        return season_results
        
    def save_season_csv(self, season_results: Dict, season: str):
        """
        Gemmer hold sæson resultater til detaljeret CSV fil
        """
        if not season_results:
            return
            
        # Convert to DataFrame
        df = pd.DataFrame(list(season_results.values()))
        
        # Add additional columns
        df['rating_per_game'] = df.apply(
            lambda row: row['rating_change'] / row['games'] if row['games'] > 0 else 0, axis=1
        )
        
        # Sort by final rating
        df = df.sort_values('final_rating', ascending=False)
        
        # Save to CSV
        filename = f'team_seasonal_elo_{season.replace("-", "_")}.csv'
        df.to_csv(filename, index=False)
        
        print(f"💾 Gemt: {filename} ({len(df)} hold)")
        
        # Show top performers by league
        print(f"\n🏆 TOP HOLD {season}:")
        
        for league in ['Herreliga', 'Kvindeliga']:
            league_teams = df[df['league'] == league].head(5)
            if len(league_teams) > 0:
                print(f"  📊 {league}:")
                for i, (_, row) in enumerate(league_teams.iterrows(), 1):
                    elite_badge = f"[{row['elite_status']}]" if row['elite_status'] != 'NORMAL' else ""
                    print(f"    {i}. {row['team_name']}: {row['final_rating']:.0f} "
                          f"({row['rating_change']:+.0f}) {elite_badge}")
                          
    def run_complete_team_analysis(self):
        """
        🚀 HOVEDFUNKTION - Kører komplet hold sæson-baseret analyse
        """
        print("\n🚀 STARTER KOMPLET HOLD SÆSON-BASERET ANALYSE")
        print("=" * 70)
        
        previous_season_data = None
        
        for season in self.seasons:
            print(f"\n📅 === HOLD SÆSON {season} ===")
            
            # Calculate start ratings from previous season
            start_ratings = {}
            
            if previous_season_data:
                print(f"📈 Beregner start ratings fra {len(previous_season_data)} hold")
                
                # Calculate league statistics
                prev_ratings = [data['final_rating'] for data in previous_season_data.values()]
                league_stats = {
                    'avg_rating': np.mean(prev_ratings) if prev_ratings else BASE_TEAM_RATING,
                    'median_rating': np.median(prev_ratings) if prev_ratings else BASE_TEAM_RATING,
                    'std_rating': np.std(prev_ratings) if prev_ratings else 100
                }
                
                print(f"📊 Forrige sæson liga stats:")
                print(f"   🎯 Gennemsnit: {league_stats['avg_rating']:.1f}")
                print(f"   📊 Median: {league_stats['median_rating']:.1f}")
                print(f"   📏 Standardafvigelse: {league_stats['std_rating']:.1f}")
                
                regression_stats = {'bonus': 0, 'penalty': 0, 'significant': 0}
                
                for team_code, team_data in previous_season_data.items():
                    start_rating = self.calculate_intelligent_team_start_rating(
                        team_code, team_data, league_stats
                    )
                    start_ratings[team_code] = start_rating
                    
                    # Track regression statistics
                    if start_rating > BASE_TEAM_RATING:
                        regression_stats['bonus'] += 1
                    elif start_rating < BASE_TEAM_RATING:
                        regression_stats['penalty'] += 1
                        
                    if abs(start_rating - team_data['final_rating']) > 75:
                        regression_stats['significant'] += 1
                        
                print(f"📊 Hold regression oversigt:")
                print(f"   ⬆️ {regression_stats['bonus']} hold med bonus start")
                print(f"   ⬇️ {regression_stats['penalty']} hold med penalty start")
                print(f"   🔄 {regression_stats['significant']} hold med betydelig regression")
            else:
                print("📊 Første sæson - alle hold starter på base rating")
                
            # Run analysis for this season
            season_results = self.run_season_analysis(season, start_ratings)
            
            if not season_results:
                print(f"⚠️ Springer over {season} - ingen resultater")
                continue
                
            # Store results
            self.all_season_results[season] = season_results
            
            # Update team career data
            for team_code, team_data in season_results.items():
                self.team_career_data[team_code].append({
                    'season': season,
                    'final_rating': team_data['final_rating'],
                    'games': team_data['games'],
                    'rating_change': team_data['rating_change'],
                    'league': team_data['league']
                })
            
            # Save season CSV
            self.save_season_csv(season_results, season)
            
            # Set up for next season
            previous_season_data = season_results
            
        # Generate final analyses
        self.generate_team_career_analysis()
        self.generate_team_summary_report()
        
    def generate_team_career_analysis(self):
        """
        Genererer karriere analyse for hold på tværs af sæsoner
        """
        print(f"\n🏆 HOLD KARRIERE ANALYSE PÅ TVÆRS AF SÆSONER")
        print("=" * 70)
        
        if not self.team_career_data:
            print("❌ Ingen hold karriere data tilgængelig")
            return
            
        # Find hold med mindst 3 sæsoner
        career_teams = []
        
        for team_code, seasons_data in self.team_career_data.items():
            if len(seasons_data) >= 3:
                ratings = [s['final_rating'] for s in seasons_data]
                games = [s['games'] for s in seasons_data]
                
                team_name = self.team_code_to_name.get(team_code, team_code)
                league = seasons_data[0]['league'] if seasons_data else 'Unknown'
                
                career_stats = {
                    'team_code': team_code,
                    'team_name': team_name,
                    'league': league,
                    'seasons_played': len(seasons_data),
                    'avg_rating': round(np.mean(ratings), 1),
                    'peak_rating': round(max(ratings), 1),
                    'total_games': sum(games),
                    'career_change': round(ratings[-1] - ratings[0], 1),
                    'consistency': round(np.std(ratings), 1)
                }
                
                career_teams.append(career_stats)
                
        # Sort by average rating within each league
        career_teams.sort(key=lambda x: (x['league'], -x['avg_rating']))
        
        print(f"📊 Fundet {len(career_teams)} karriere hold (≥3 sæsoner)")
        
        # Show top teams by league
        for league in ['Herreliga', 'Kvindeliga']:
            league_teams = [t for t in career_teams if t['league'] == league][:10]
            if league_teams:
                print(f"\n🏆 TOP 10 {league} KARRIERE HOLD:")
                for i, team in enumerate(league_teams, 1):
                    trend = "📈" if team['career_change'] > 50 else "📉" if team['career_change'] < -50 else "➡️"
                    consistency = "🎯" if team['consistency'] < 50 else "📊"
                    
                    print(f"  {i:2d}. {team['team_name']}: "
                          f"{team['avg_rating']:.0f} avg, peak {team['peak_rating']:.0f} "
                          f"({team['seasons_played']} sæsoner) {trend}{team['career_change']:+.0f} {consistency}")
                          
        # Save career analysis
        career_df = pd.DataFrame(career_teams)
        career_df.to_csv('team_career_analysis.csv', index=False)
        print(f"\n💾 Hold karriere analyse gemt: team_career_analysis.csv")
        
    def generate_team_summary_report(self):
        """
        Genererer samlet rapport over alle hold sæsoner
        """
        print(f"\n📊 SAMLET HOLD RAPPORT - ALLE SÆSONER")
        print("=" * 70)
        
        if not self.all_season_results:
            print("❌ Ingen hold sæsondata til rapport")
            return
            
        total_teams = set()
        total_matches = 0
        season_summary = []
        
        for season, results in self.all_season_results.items():
            total_teams.update(results.keys())
            season_matches = sum(team['games'] for team in results.values())
            
            ratings = [team['final_rating'] for team in results.values()]
            elite_count = sum(1 for r in ratings if r >= BASE_TEAM_RATING + 200)
            legendary_count = sum(1 for r in ratings if r >= BASE_TEAM_RATING + 400)
            
            # Separate by league
            herreliga_teams = [t for t in results.values() if t['league'] == 'Herreliga']
            kvindeliga_teams = [t for t in results.values() if t['league'] == 'Kvindeliga']
            
            season_summary.append({
                'season': season,
                'total_teams': len(results),
                'herreliga_teams': len(herreliga_teams),
                'kvindeliga_teams': len(kvindeliga_teams),
                'total_games': season_matches,
                'avg_rating': round(np.mean(ratings), 1),
                'elite_teams': elite_count,
                'legendary_teams': legendary_count,
                'max_rating': round(max(ratings), 1)
            })
            
            total_matches += season_matches
            
        print(f"🏐 SAMLET HOLD STATISTIK:")
        print(f"  📊 Total unikke hold: {len(total_teams):,}")
        print(f"  🏟️ Total kampe: {total_matches:,}")
        print(f"  📅 Sæsoner processeret: {len(self.all_season_results)}")
        
        print(f"\n📅 SÆSON OVERSIGT:")
        for s in season_summary:
            print(f"  {s['season']}: {s['total_teams']:2d} hold "
                  f"(H:{s['herreliga_teams']}, K:{s['kvindeliga_teams']}), "
                  f"{s['total_games']:3d} kampe, avg {s['avg_rating']:.0f} "
                  f"(E:{s['elite_teams']}, L:{s['legendary_teams']})")
                  
        # Save summary
        summary_df = pd.DataFrame(season_summary)
        summary_df.to_csv('team_seasonal_summary_report.csv', index=False)
        print(f"\n💾 Hold rapport gemt: team_seasonal_summary_report.csv")
        
        print(f"\n✅ HOLD SÆSON-BASERET ANALYSE KOMPLET!")
        print("=" * 70)
        print("📁 Genererede hold filer:")
        for season in self.all_season_results.keys():
            print(f"  • team_seasonal_elo_{season.replace('-', '_')}.csv")
        print("  • team_career_analysis.csv")
        print("  • team_seasonal_summary_report.csv")


# === MAIN EXECUTION ===
if __name__ == "__main__":
    print("🏆 STARTER HOLD SÆSON-BASERET HÅNDBOL ELO SYSTEM")
    print("=" * 80)
    
    # Create system instance
    team_system = TeamSeasonalEloSystem()
    
    # Run complete analysis
    team_system.run_complete_team_analysis()
    
    print("\n🎉 HOLD SÆSON-BASERET SYSTEM KOMPLET!")
    print("=" * 80)
    print("🎯 Implementerede hold features:")
    print("  ✅ Intelligent regression to mean mellem sæsoner")
    print("  ✅ Målforskels påvirkning på ELO ændringer")
    print("  ✅ Hjemme/ude fordel indregnet")
    print("  ✅ Momentum tracking baseret på seneste kampe")
    print("  ✅ Liga-specifik analyse (Herreliga/Kvindeliga)")
    print("  ✅ Elite hold skal præstere for at beholde rating")
    print("  ✅ Per-sæson detaljerede CSV filer for hold")
    print("  ✅ Karriere tracking på tværs af sæsoner")
    print("  ✅ Robust fejlhåndtering og debugging")
    print("\n🏆 HOLD ELO SIKRER FAIR KONKURRENCE MELLEM HOLD!")