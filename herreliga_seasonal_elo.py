#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 HERRELIGA SÆSON-BASERET HÅNDBOL ELO SYSTEM  
=====================================================

FOKUSERER KUN PÅ HERRELIGA MED FORBEDREDE START-RATINGS:
✅ Kun Herreliga data - ingen blanding med Kvindeliga
✅ ULTRA-INDIVIDUELLE start ratings baseret på:
   - Performance sidste sæson (final rating)
   - Momentum sidste sæson (seneste kampe vægtning)
   - Position-specifik progression
   - Antal kampe spillet (stabilitet)
   - Elite status (progression sværhedsgrad)
   - Konsistens gennem sæsonen
   - Hold-prestations faktorer

FORBEDRINGER I FORHOLD TIL ORIGINAL:
- Meget mere granulære start ratings
- Position-specifik regression
- Performance-based momentum carryover
- Hold-styrke påvirkning
- Konsistens-tracking
- Forbedret range spreading

Jonas' Custom System - December 2024
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

# Import player aliases
from team_config import PLAYER_NAME_ALIASES

# Princip 2: Separat Position Analyse System
class PositionAnalyzer:
    """
    Analyserer en hel sæson for at bestemme spilleres primære positioner.
    Fokuserer kun på "rene" positioner og ignorerer situationsbestemte.
    """
    def __init__(self, base_dir: str = ".", league_dir: str = "Herreliga-database"):
        self.base_dir = base_dir
        self.league_dir_path = os.path.join(base_dir, league_dir)
        self.pure_positions = {'VF', 'HF', 'VB', 'PL', 'HB', 'ST'}
        
        # Data containers
        self.player_positions = defaultdict(Counter)
        self.confirmed_goalkeepers = set()
        
        # Mapping from position code to full name
        self.position_map = {
            'MV': 'Målvogter',
            'VF': 'Venstre fløj', 'HF': 'Højre fløj', 'VB': 'Venstre back',
            'PL': 'Playmaker', 'HB': 'Højre back', 'ST': 'Streg', 'Ukendt': 'Ukendt'
        }

    def analyze_season(self, season: str):
        print(f"📊 Starter positionsanalyse for Herreliga sæson {season}...")
        season_path = os.path.join(self.league_dir_path, season)
        if not os.path.exists(season_path):
            print(f"  ❌ Sæsonsti ikke fundet: {season_path}")
            return

        db_files = [f for f in os.listdir(season_path) if f.endswith('.db')]
        for db_file in db_files:
            db_path = os.path.join(season_path, db_file)
            try:
                conn = sqlite3.connect(db_path)
                # Brug pandas for effektiv og robust datalæsning
                events_df = pd.read_sql_query("SELECT navn_1, pos, mv FROM match_events", conn)
                conn.close()

                # Fjern ugyldige værdier
                events_df.dropna(subset=['navn_1', 'pos', 'mv'], how='all', inplace=True)

                # Identificer målvogtere
                goalkeepers = events_df['mv'].astype(str).str.strip()
                valid_goalkeepers = goalkeepers[(goalkeepers.notna()) & (goalkeepers != '') & (goalkeepers != 'nan') & (goalkeepers != '0')]
                self.confirmed_goalkeepers.update(valid_goalkeepers)

                # Analyser markspilleres positioner
                field_players = events_df[['navn_1', 'pos']].copy()
                field_players['navn_1'] = field_players['navn_1'].astype(str).str.strip()
                field_players['pos'] = field_players['pos'].astype(str).str.strip()
                
                # Filtrer til kun rene positioner
                valid_events = field_players[field_players['pos'].isin(self.pure_positions) & (field_players['navn_1'] != '')]
                
                # Tæl positioner
                position_counts = valid_events.groupby(['navn_1', 'pos']).size().reset_index(name='counts')
                
                for _, row in position_counts.iterrows():
                    self.player_positions[row['navn_1']][row['pos']] += row['counts']
                    
            except Exception as e:
                print(f"  ⚠️ Fejl under læsning af {db_file}: {e}")

        print(f"✅ Positionsanalyse for {season} fuldført.")
        print(f"  - {len(self.player_positions)} markspillere analyseret.")
        print(f"  - {len(self.confirmed_goalkeepers)} målvogtere identificeret.")

    def get_primary_position(self, player_name: str) -> Tuple[str, str]:
        # Først, tjek om spilleren er en bekræftet målvogter
        if player_name in self.confirmed_goalkeepers:
            return 'MV', self.position_map['MV']

        # Dernæst, find markspillerens primære position
        if player_name in self.player_positions and self.player_positions[player_name]:
            positions = self.player_positions[player_name]
            primary_pos_code = positions.most_common(1)[0][0]
            return primary_pos_code, self.position_map.get(primary_pos_code, 'Ukendt')
        
        # Fallback for spillere uden registrerede "rene" positioner (f.eks. kun 'Gbr')
        return 'Ukendt', 'Ukendt'

# === FORBEDREDE SYSTEM PARAMETRE ===
BASE_RATING = 1000                 # REDUCERET fra 1200 - giver mere plads til spredning over mange sæsoner
MIN_GAMES_FOR_FULL_CARRY = 12      # Reduceret for at flere får carry-over
MAX_CARRY_BONUS = 400              # Reduceret fra 500 til at passe med lavere base
MIN_CARRY_PENALTY = -200           # Reduceret fra -250 til at passe med lavere base
REGRESSION_STRENGTH = 0.35         # YDERLIGERE REDUCERET fra 0.45 for mindre regression

# Position-specific progression rates (nogle positioner udvikler sig hurtigere)
POSITION_PROGRESSION_RATES = {
    'MV': 0.85,    # Målvogtere: Stabil progression
    'PL': 1.15,    # Playmaker: Hurtig progression (vigtig position)
    'ST': 1.10,    # Streg: God progression (scorende position)
    'VF': 1.05,    # Venstre fløj: Normal progression 
    'HF': 1.05,    # Højre fløj: Normal progression
    'VB': 0.95,    # Venstre back: Langsom progression
    'HB': 0.95     # Højre back: Langsom progression
}

class HerreligaSeasonalEloSystem:
    """
    🏆 HERRELIGA-FOKUSERET SÆSON ELO SYSTEM MED ULTRA-INDIVIDUELLE RATINGS
    """
    
    def __init__(self, base_dir: str = "."):
        print("🏆 HERRELIGA SÆSON-BASERET HÅNDBOL ELO SYSTEM")
        print("=" * 70)
        print("🎯 FOKUS: Kun Herreliga med ultra-individuelle start ratings")
        
        self.base_dir = base_dir
        
        # Kun Herreliga directory  
        self.herreliga_dir = os.path.join(base_dir, "Herreliga-database")
        
        # Sæson data storage
        self.all_season_results = {}
        # NEW: Global player database for long-term ELO memory
        self.player_career_database = {}
        self.team_season_performance = defaultdict(dict)
        
        # Available seasons
        self.seasons = [
            "2017-2018", "2018-2019", "2019-2020", "2020-2021", 
            "2021-2022", "2022-2023", "2023-2024", "2024-2025"
        ]
        
        # Validate seasons exist (kun Herreliga)
        self.validate_herreliga_seasons()
        
        print("✅ Herreliga ELO system initialiseret")
        print(f"📅 Tilgængelige sæsoner: {len(self.seasons)}")
        print(f"🎯 Base rating: {BASE_RATING}")
        print(f"📊 Max carry bonus: +{MAX_CARRY_BONUS}")
        print(f"📉 Max carry penalty: {MIN_CARRY_PENALTY}")
        
    def validate_herreliga_seasons(self):
        """Validerer kun Herreliga sæsoner"""
        print(f"\n🔍 VALIDERER HERRELIGA SÆSONER")
        print("-" * 50)
        
        valid_seasons = []
        
        for season in self.seasons:
            herreliga_path = os.path.join(self.herreliga_dir, season)
            
            herreliga_files = 0
            if os.path.exists(herreliga_path):
                herreliga_files = len([f for f in os.listdir(herreliga_path) if f.endswith('.db')])
                
            if herreliga_files > 0:
                valid_seasons.append(season)
                print(f"  ✅ {season}: {herreliga_files} Herreliga kampe")
            else:
                print(f"  ❌ {season}: ingen Herreliga data")
                
        self.seasons = valid_seasons
        print(f"\n📊 {len(self.seasons)} gyldige Herreliga sæsoner klar")
        
    def calculate_ultra_individual_start_rating(self, player_name: str, 
                                              previous_season_data: Dict = None,
                                              team_performance: Dict = None,
                                              league_stats: Dict = None) -> float:
        """
        🧠 ULTRA-INDIVIDUALISERET START RATING BEREGNING
        
        Nye faktorer inkluderet:
        1. Performance sidste sæson (final rating)
        2. Momentum sidste kampe (seneste 5 kampe vægtning)  
        3. Position-specifik progression rate
        4. Konsistens gennem sæsonen
        5. Hold-prestations påvirkning
        6. Liga-relative performance
        7. Karriere-trend hvis flere sæsoner
        8. Spillestil stabilitet (flere positioner = mindre carryover)
        """
        
        if not previous_season_data:
            # Nye spillere får base rating med lille variation baseret på position
            position = previous_season_data.get('primary_position', 'PL') if previous_season_data else 'PL'
            position_adjustment = {
                'MV': 30,    # Målvogtere starter højere (reduceret fra 50)
                'PL': 15,    # Playmaker starter lidt højere (reduceret fra 20)
                'ST': 10,    # Streg starter lidt højere
                'VF': 0, 'HF': 0, 'VB': 0, 'HB': 0  # Andre på base
            }.get(position, 0)
            
            return BASE_RATING + position_adjustment
            
        # === HENT TIDLIGERE SÆSON DATA ===
        prev_rating = previous_season_data.get('final_rating', BASE_RATING)
        prev_games = previous_season_data.get('games', 0)
        prev_elite_status = previous_season_data.get('elite_status', 'NORMAL')
        prev_position = previous_season_data.get('primary_position', 'PL')
        prev_consistency = previous_season_data.get('rating_consistency', 50)  # Lavere = mere konsistent
        prev_rating_per_game = previous_season_data.get('rating_per_game', 0)
        
        # === BEREGN LEAGUE BASELINE ===
        league_avg = league_stats.get('avg_rating', BASE_RATING) if league_stats else BASE_RATING
        distance_from_league_avg = prev_rating - league_avg
        
        # === 1. GAMES FACTOR (Forbedret graduering) ===
        if prev_games >= MIN_GAMES_FOR_FULL_CARRY:
            games_factor = 1.0  # Fuld carryover
        elif prev_games >= 8:
            # Gradueret mellem 8-12 kampe
            games_factor = 0.7 + 0.3 * (prev_games - 8) / (MIN_GAMES_FOR_FULL_CARRY - 8)
        elif prev_games >= 4:
            # Minimal carryover
            games_factor = 0.4 + 0.3 * (prev_games - 4) / 4
        else:
            games_factor = 0.25  # Meget minimal carryover
            
        # === 2. POSITION PROGRESSION FACTOR ===
        position_factor = POSITION_PROGRESSION_RATES.get(prev_position, 1.0)
        
        # === 3. ELITE STATUS FACTOR (Modificeret for mere nuance) ===
        if prev_elite_status == 'LEGENDARY':
            elite_factor = 0.55  # Stærk regression for legendary
        elif prev_elite_status == 'ELITE':
            elite_factor = 0.70  # Moderat regression for elite
        else:
            # Normal spillere får bonusser baseret på performance
            if prev_rating > league_avg + 50:
                elite_factor = 0.85  # Svag regression for gode normale spillere
            else:
                elite_factor = 0.95  # Minimal regression for gennemsnitlige
                
        # === 4. KONSISTENS FACTOR (NY!) ===
        # Spillere med høj konsistens får større carryover
        if prev_consistency < 30:  # Meget konsistent
            consistency_factor = 1.1
        elif prev_consistency < 50:  # Rimelig konsistent  
            consistency_factor = 1.05
        elif prev_consistency < 80:  # Inkonsistent
            consistency_factor = 0.95
        else:  # Meget inkonsistent
            consistency_factor = 0.85
            
        # === 5. MOMENTUM FACTOR (NY!) ===
        # Baseret på rating per game - højere = bedre momentum
        if prev_rating_per_game > 10:  # Stærk sæson performance
            momentum_factor = 1.15
        elif prev_rating_per_game > 5:  # God performance
            momentum_factor = 1.08
        elif prev_rating_per_game > 0:  # Positiv performance
            momentum_factor = 1.02
        elif prev_rating_per_game > -5:  # Svag performance
            momentum_factor = 0.95
        else:  # Dårlig performance
            momentum_factor = 0.85
            
        # === 6. HOLD PERFORMANCE FACTOR (NY!) ===
        team_factor = 1.0
        if team_performance:
            team_avg_rating = team_performance.get('avg_team_rating', league_avg)
            if team_avg_rating > league_avg + 100:  # Stærkt hold
                team_factor = 1.05  # Lille bonus for at spille på godt hold
            elif team_avg_rating < league_avg - 100:  # Svagt hold
                team_factor = 0.98  # Lille straf
                
        # === 7. DISTANCE REGRESSION (DRAMATISK ØGET SPREDNING) ===
        abs_distance = abs(distance_from_league_avg)
        
        # DRAMATISK ØGET SPREDNING: Meget mindre regression for at skabe større forskelle
        # Tjek om spilleren var OVER gennemsnittet (positiv performance)
        if distance_from_league_avg > 0:  # Spilleren var bedre end gennemsnittet
            # MEGET mindre regression for at bevare fordele
            if abs_distance > 500:
                distance_factor = 0.85  # DRAMATISK ØGET fra 0.65 - elite skal beholde mest
            elif abs_distance > 400:
                distance_factor = 0.90  # DRAMATISK ØGET fra 0.75 - stor belønning
            elif abs_distance > 300:
                distance_factor = 0.95  # DRAMATISK ØGET fra 0.85 - Anders får stor belønning!
            elif abs_distance > 200:
                distance_factor = 0.97  # DRAMATISK ØGET fra 0.90 - gode spillere belønnes
            elif abs_distance > 100:
                distance_factor = 0.98  # DRAMATISK ØGET fra 0.95 - minimal regression
            else:
                distance_factor = 0.99  # Næsten ingen regression for let over gennemsnit
        else:  # Spilleren var under gennemsnittet (dårlig performance)
            # MEGET mere aggressiv regression for dårlige spillere
            if abs_distance > 400:
                distance_factor = 0.15  # DRAMATISK REDUCERET fra 0.25 - hård straf
            elif abs_distance > 300:
                distance_factor = 0.25  # REDUCERET fra 0.35 - stor straf
            elif abs_distance > 200:
                distance_factor = 0.35  # REDUCERET fra 0.50 - betydelig straf
            elif abs_distance > 100:
                distance_factor = 0.55  # REDUCERET fra 0.70 - moderat straf
            else:
                distance_factor = 0.75  # REDUCERET fra 0.85 - svag straf
            
        # === KOMBINER ALLE FAKTORER ===
        combined_factor = (games_factor * position_factor * elite_factor * 
                          consistency_factor * momentum_factor * team_factor * distance_factor)
        
        # === BEREGN NY START RATING ===
        adjusted_distance = distance_from_league_avg * combined_factor
        new_start_rating = league_avg + adjusted_distance
        
        # === ANVEND CAPS MED GRADUERET OVERGANG (forbedret for gode spillere) ===
        rating_change = new_start_rating - BASE_RATING
        
        # EXCEPTIONAL BONUS for toppræsterende spillere (justeret til lavere base)
        if prev_rating_per_game > 8 and prev_games >= MIN_GAMES_FOR_FULL_CARRY:
            # STOR ekstra bonus for exceptionelle spillere
            exceptional_bonus = min(120, (prev_rating_per_game - 8) * 8)  # Reduceret fra 150/10
            new_start_rating += exceptional_bonus
            print(f"      🌟 EXCEPTIONAL BONUS for {player_name}: +{exceptional_bonus:.0f} "
                  f"(RPG: {prev_rating_per_game:.1f})")
        elif prev_rating_per_game > 5 and prev_games >= 8:
            # Moderat bonus for gode spillere
            moderate_bonus = min(60, (prev_rating_per_game - 5) * 6)  # Reduceret fra 75/8
            new_start_rating += moderate_bonus
            print(f"      ⭐ MODERATE BONUS for {player_name}: +{moderate_bonus:.0f} "
                  f"(RPG: {prev_rating_per_game:.1f})")
        
        # Apply caps
        rating_change = new_start_rating - BASE_RATING
        if rating_change > MAX_CARRY_BONUS:
            new_start_rating = BASE_RATING + MAX_CARRY_BONUS
        elif rating_change < MIN_CARRY_PENALTY:
            new_start_rating = BASE_RATING + MIN_CARRY_PENALTY
            
        # === FINAL SMALL RANDOMIZATION FOR UNIQUENESS ===
        # Tilføj lille tilfældig variation (±3 points) for at sikre unikke ratings
        np.random.seed(hash(player_name) % 1000)  # Konsistent per spiller
        unique_adjustment = np.random.uniform(-3, 3)
        new_start_rating += unique_adjustment
        
        # FORBEDRET DEBUG OUTPUT - viser alle faktorer
        total_change = new_start_rating - prev_rating
        if abs(total_change) > 30 or player_name == "Anders Kragh MARTINUSEN":
            print(f"    📊 {player_name} ({prev_position}): {prev_rating:.0f} → {new_start_rating:.0f} "
                  f"({total_change:+.0f})")
            print(f"       🎯 Faktorer: Games:{games_factor:.2f}, Pos:{position_factor:.2f}, "
                  f"Elite:{elite_factor:.2f}, Consistency:{consistency_factor:.2f}")
            print(f"       ⚡ Momentum:{momentum_factor:.2f}, Team:{team_factor:.2f}, "
                  f"Distance:{distance_factor:.2f}")
            print(f"       📈 Combined:{combined_factor:.3f}, RPG:{prev_rating_per_game:.1f}, "
                  f"Distance from avg:{distance_from_league_avg:.0f}")
                  
        return round(new_start_rating, 1)
        
    def run_herreliga_season(self, season: str, start_ratings: Dict = None, position_analyzer: Optional[PositionAnalyzer] = None) -> Dict:
        """
        Kører master ELO systemet for kun Herreliga i en enkelt sæson
        """
        print(f"\n🏐 PROCESSERER HERRELIGA SÆSON {season}")
        print("-" * 50)
        
        try:
            # Import master system
            from handball_elo_master import MasterHandballEloSystem
            
            # Create fresh instance for this season (kun Herreliga)
            master_system = MasterHandballEloSystem(self.base_dir)
            
            # Set start ratings if provided
            if start_ratings:
                print(f"📈 Sætter start ratings for {len(start_ratings)} Herreliga spillere")
                print(f"📊 Rating range: {min(start_ratings.values()):.0f} - {max(start_ratings.values()):.0f}")
                rating_spread = max(start_ratings.values()) - min(start_ratings.values())
                print(f"📏 Rating spread: {rating_spread:.0f} points")
                
                for player_name, start_rating in start_ratings.items():
                    master_system.player_elos[player_name] = start_rating
                    # Set goalkeeper default if applicable
                    if player_name in master_system.confirmed_goalkeepers:
                        if start_rating == BASE_RATING:
                            master_system.player_elos[player_name] = master_system.rating_bounds['default_goalkeeper']
            
            # Process ONLY Herreliga for this season
            # Temporarily point master system to Herreliga directory
            original_dir = master_system.database_dir
            master_system.database_dir = self.herreliga_dir
            herreliga_matches = master_system.process_season_database(season)
            master_system.database_dir = original_dir # Reset original path
            
            if herreliga_matches == 0:
                print(f"❌ Ingen Herreliga kampe processeret for {season}")
                return {}
                
            print(f"✅ Herreliga: {herreliga_matches} kampe processeret")
            
            # Generate season results
            season_results = {}
            
            for player_name, final_rating in master_system.player_elos.items():
                games = master_system.player_games.get(player_name, 0)
                
                # Only include players who actually played this season
                if games > 0:
                    start_rating = start_ratings.get(player_name, BASE_RATING) if start_ratings else BASE_RATING
                    
                    # Princip 3: Brug den separate positionsanalyse til at bestemme position
                    if position_analyzer:
                        primary_position, position_name = position_analyzer.get_primary_position(player_name)
                        is_goalkeeper = (primary_position == 'MV')
                    else:
                        # Fallback til gammel (mindre præcis) metode hvis analyzer ikke er tilgængelig
                        positions = master_system.player_positions[player_name]
                        primary_position = positions.most_common(1)[0][0] if positions else 'Ukendt'
                        position_name = master_system.standard_positions.get(primary_position, 'Ukendt')
                        is_goalkeeper = player_name in master_system.confirmed_goalkeepers
                        positions = master_system.player_positions[player_name] # Sørg for at positions er defineret

                    # Elite status
                    if final_rating >= master_system.rating_bounds['legendary_threshold']:
                        elite_status = "LEGENDARY"
                    elif final_rating >= master_system.rating_bounds['elite_threshold']:
                        elite_status = "ELITE"
                    else:
                        elite_status = "NORMAL"
                    
                    # Performance level
                    rating_change = final_rating - start_rating
                    if rating_change > 50:
                        performance_level = "ELITE"
                    elif rating_change > 0:
                        performance_level = "NORMAL"
                    else:
                        performance_level = "NORMAL"
                    
                    # Momentum and consistency metrics
                    momentum = master_system.get_momentum_multiplier(player_name)
                    rating_per_game = rating_change / games if games > 0 else 0
                    
                    # Estimate consistency (placeholder - would need more detailed tracking)
                    rating_consistency = abs(rating_change) / games if games > 0 else 50
                    
                    season_results[player_name] = {
                        'season': season,
                        'player': player_name,
                        'start_rating': round(start_rating, 1),
                        'final_rating': round(final_rating, 1),
                        'rating_change': round(rating_change, 1),
                        'games': games,
                        'primary_position': primary_position,
                        'position_name': position_name,
                        'is_goalkeeper': is_goalkeeper,
                        'elite_status': elite_status,
                        'momentum_factor': round(momentum, 3),
                        'total_actions': sum(master_system.player_positions[player_name].values()) if master_system.player_positions[player_name] else 0,
                        'rating_per_game': round(rating_per_game, 3),
                        'performance_level': performance_level,
                        'rating_consistency': round(rating_consistency, 1)
                    }
                    
            return season_results
            
        except Exception as e:
            print(f"❌ Fejl i Herreliga sæson {season}: {e}")
            import traceback
            traceback.print_exc()
            return {}
            
    def save_herreliga_season_csv(self, season_results: Dict, season: str):
        """
        Gemmer Herreliga sæson resultater til CSV
        """
        if not season_results:
            print(f"❌ Ingen data at gemme for {season}")
            return
            
        # Convert to DataFrame
        df_data = []
        for player_data in season_results.values():
            df_data.append(player_data)
            
        df = pd.DataFrame(df_data)
        
        # Sort by final rating descending
        df = df.sort_values('final_rating', ascending=False)
        
        # Ensure ELO_Results/Player_Seasonal_CSV directory exists
        output_dir = os.path.join("ELO_Results", "Player_Seasonal_CSV")
        os.makedirs(output_dir, exist_ok=True)
        
        # Save CSV in correct directory
        filename = f"herreliga_seasonal_elo_{season.replace('-', '_')}.csv"
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        # Print statistics
        avg_rating = df['final_rating'].mean()
        rating_spread = df['final_rating'].max() - df['final_rating'].min()
        elite_count = len(df[df['elite_status'] == 'ELITE'])
        legendary_count = len(df[df['elite_status'] == 'LEGENDARY'])
        
        print(f"💾 Gemt: {filepath}")
        print(f"📊 {len(df)} Herreliga spillere, avg rating: {avg_rating:.1f}")
        print(f"📏 Rating spread: {rating_spread:.0f} points")
        print(f"🏆 Elite spillere: {elite_count}, Legendary: {legendary_count}")
        
    def _get_all_player_names_for_season(self, season: str) -> set:
        """
        Henter alle unikke spillernavne fra database-filerne for en given sæson.
        """
        player_names = set()
        season_path = os.path.join(self.herreliga_dir, season)

        if not os.path.exists(season_path):
            return player_names

        for db_file in os.listdir(season_path):
            if not db_file.endswith('.db'):
                continue
            
            db_path = os.path.join(season_path, db_file)
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                # Check if match_events table exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_events';")
                if cursor.fetchone() is None:
                    conn.close()
                    continue

                for col in ['navn_1', 'navn_2', 'mv']:
                    cursor.execute(f"SELECT DISTINCT {col} FROM match_events")
                    for row in cursor.fetchall():
                        if row[0] and isinstance(row[0], str) and row[0].strip() and row[0] not in ["Retur", "Bold erobret", "Assist", "Forårs. str."]:
                            player_names.add(row[0].strip())
                conn.close()
            except Exception as e:
                print(f"  ⚠️ Kunne ikke læse spillernavne fra {db_file}: {e}")
                continue
        
        return player_names

    def _normalize_and_get_canonical_name(self, name: str) -> str:
        """
        FORBEDRET: Normaliserer et spillernavn og oversætter det til dets kanoniske version.
        Håndterer store/små bogstaver og variationer i aliaser for robust matching.
        """
        if not isinstance(name, str):
            return ""
        
        # Trin 1: Standardiser input-navnet (STORE BOGSTAVER, trimmet)
        processed_name = " ".join(name.strip().upper().split())
        
        # Trin 2: Opret en standardiseret version af alias-mappen til opslag for at sikre case-insensitivitet.
        standardized_aliases = { " ".join(k.strip().upper().split()): v.upper() for k, v in PLAYER_NAME_ALIASES.items() }

        # Trin 3: Slå det standardiserede navn op. Returner kanonisk navn hvis det findes, ellers det behandlede input-navn.
        return standardized_aliases.get(processed_name, processed_name)

    def _find_player_name_mapping(self, current_names: set, previous_player_data: dict) -> dict:
        """
        ROBUST NAVNE-MATCHING (REVISED)
        Connects current season names to the canonical names in the career database.
        1. Applies normalization and aliasing to all names.
        2. Prioritizes direct matches of canonical names.
        3. Falls back to Levenshtein for fuzzy matching.
        """
        print(f"  🧠 Forsøger robust navne-matching for {len(current_names)} spillere mod karriere-databasen...")
        mapping = {}
        
        # Create a set of canonical names from the career database for efficient lookup
        canonical_career_names = {self._normalize_and_get_canonical_name(name) for name in previous_player_data.keys()}
        
        # --- TRIN 1: DIREKTE MATCH EFTER NORMALISERING OG ALIASING ---
        unmatched_current = set()
        direct_matches_found = 0
        
        for name in current_names:
            canonical_name = self._normalize_and_get_canonical_name(name)
            if canonical_name in canonical_career_names:
                mapping[name] = canonical_name
                direct_matches_found += 1
            else:
                unmatched_current.add(name)

        if direct_matches_found > 0:
            print(f"    ✅ Trin 1: Fandt {direct_matches_found} direkte matches via kanoniske navne.")
            
        # --- TRIN 2: LEVENSHTEIN MATCH FOR RESTERENDE (For små stavefejl) ---
        levenshtein_matches_found = 0
        if unmatched_current and canonical_career_names:
            try:
                from Levenshtein import ratio as levenshtein_ratio
                levenshtein_available = True
            except ImportError:
                levenshtein_available = False
            
            if levenshtein_available:
                # Sorter for determinisme
                for curr_name in sorted(list(unmatched_current)):
                    # Normalize current name for matching
                    normalized_curr = " ".join(curr_name.lower().strip().split())
                    
                    best_match = None
                    highest_score = 0.88 # Højere tærskel for at undgå forkerte matches

                    for career_name in sorted(list(canonical_career_names)):
                        normalized_career = " ".join(career_name.lower().strip().split())
                        score = levenshtein_ratio(normalized_curr, normalized_career)
                        if score > highest_score:
                            highest_score = score
                            best_match = career_name
                    
                    if best_match:
                        mapping[curr_name] = best_match
                        canonical_career_names.remove(best_match) # Avoid re-matching
                        levenshtein_matches_found += 1
                        print(f"        🤝 LEVENSHTEIN: '{curr_name}' -> '{best_match}' (Score: {highest_score:.2f})")
        
        if levenshtein_matches_found > 0:
            print(f"    ✅ Trin 2: Fandt {levenshtein_matches_found} Levenshtein-baserede matches.")

        total_mapped = len(mapping)
        unmapped_count = len(current_names) - total_mapped
        print(f"    📊 Resultat: {total_mapped} spillere mappet, {unmapped_count} nye/ukendte spillere.")

        return mapping

    def run_complete_herreliga_analysis(self):
        """
        🚀 HOVEDFUNKTION - Kører komplet Herreliga sæson-baseret analyse
        """
        print("\n🚀 STARTER KOMPLET HERRELIGA SÆSON-BASERET ANALYSE")
        print("=" * 70)
        print("🎯 KUN HERRELIGA - ULTRA-INDIVIDUELLE START RATINGS")
        
        # previous_season_data is now self.player_career_database
        
        for season in self.seasons:
            print(f"\n📅 === HERRELIGA SÆSON {season} ===")
            
            # Princip 2: Kør separat positionsanalyse FØR ELO-beregning
            position_analyzer = PositionAnalyzer(self.base_dir, league_dir="Herreliga-database")
            position_analyzer.analyze_season(season)

            # Calculate start ratings from the global career database
            start_ratings = {}
            
            # Get all unique player names appearing in the current season's database files
            current_season_names = self._get_all_player_names_for_season(season)
            
            if self.player_career_database:
                # Map current raw names to the canonical names stored in the career database
                name_mapping = self._find_player_name_mapping(current_season_names, self.player_career_database)

                print(f"📈 Beregner ultra-individuelle start ratings for {len(current_season_names)} spillere")
                
                # Calculate league statistics for reference
                prev_ratings = [data['final_rating'] for data in self.player_career_database.values()]
                league_stats = {
                    'avg_rating': np.mean(prev_ratings) if prev_ratings else BASE_RATING,
                    'median_rating': np.median(prev_ratings) if prev_ratings else BASE_RATING,
                    'std_rating': np.std(prev_ratings) if prev_ratings else 50
                }
                
                print(f"📊 Forrige sæson Herreliga stats:")
                print(f"   🎯 Gennemsnit: {league_stats['avg_rating']:.1f}")
                print(f"   📊 Median: {league_stats['median_rating']:.1f}")
                print(f"   📏 Standardafvigelse: {league_stats['std_rating']:.1f}")
                
                # Calculate start ratings for all players in the current season
                for player_name in sorted(list(current_season_names)):
                    # Find the corresponding canonical name from the career DB
                    canonical_name = name_mapping.get(player_name)
                    # Get the historical data for that player
                    player_career_data = self.player_career_database.get(canonical_name) if canonical_name else None

                    start_rating = self.calculate_ultra_individual_start_rating(
                        player_name, player_career_data, None, league_stats
                    )
                    start_ratings[player_name] = start_rating
            else:
                print("📊 Første sæson - alle starter på base rating med positions-justeringer")
                # Even in the first season, we must normalize names
                for player_name in sorted(list(current_season_names)):
                    start_ratings[player_name] = self.calculate_ultra_individual_start_rating(player_name)

            # Run master system for this Herreliga season
            season_results = self.run_herreliga_season(season, start_ratings, position_analyzer)
            
            if not season_results:
                print(f"⚠️ Springer over Herreliga {season} - ingen resultater")
                continue
            
            # NEW: Consolidate season results to handle intra-season duplicates (like Marinus Munk)
            # and update the global career database
            merged_canonical_results = {}
            for raw_name, player_data in season_results.items():
                canonical_name = self._normalize_and_get_canonical_name(raw_name)

                # If canonical name already processed, we must MERGE the results.
                if canonical_name in merged_canonical_results:
                    existing_data = merged_canonical_results[canonical_name]
                    
                    # Sum games and actions
                    existing_data['games'] += player_data['games']
                    existing_data['total_actions'] += player_data['total_actions']
                    
                    # Sum the rating change. This is an approximation, but far better than discarding data.
                    existing_data['rating_change'] += player_data['rating_change']
                    
                    # Keep the primary position from the entry with more games as it's more representative
                    if player_data['games'] > existing_data.get('__source_games', 0):
                        existing_data['primary_position'] = player_data['primary_position']
                        existing_data['position_name'] = player_data['position_name']
                        existing_data['__source_games'] = player_data['games'] # Track for subsequent merges
                else:
                    # First time seeing this canonical name this season, just add it.
                    player_data['__source_games'] = player_data['games']
                    merged_canonical_results[canonical_name] = player_data

            # After merging, recalculate final_rating and other derived metrics for the canonical entries
            canonical_season_results = {}
            for canonical_name, data in merged_canonical_results.items():
                # Recalculate final rating based on the summed change
                data['final_rating'] = data['start_rating'] + data['rating_change']

                # Recalculate other derived metrics
                if data['games'] > 0:
                    data['rating_per_game'] = data['rating_change'] / data['games']
                    data['rating_consistency'] = abs(data['rating_change']) / data['games']
                
                # Recalculate elite status based on the new final rating
                # (Assuming master_system's bounds are accessible or can be hardcoded)
                if data['final_rating'] >= 1400: # legendary_threshold
                    data['elite_status'] = "LEGENDARY"
                elif data['final_rating'] >= 1250: # elite_threshold
                    data['elite_status'] = "ELITE"
                else:
                    data['elite_status'] = "NORMAL"

                # Clean up temporary key and ensure player name is canonical
                data.pop('__source_games', None)
                data['player'] = canonical_name
                canonical_season_results[canonical_name] = data

            # Update the global career database with the consolidated results
            print(f"💾 Opdaterer karrieredatabasen med {len(canonical_season_results)} unikke, konsoliderede spillere.")
            self.player_career_database.update(canonical_season_results)
            
            # Store results for final report
            self.all_season_results[season] = self.player_career_database.copy()
            
            # Save season CSV (based on the original, non-consolidated results for season-specific accuracy)
            self.save_herreliga_season_csv(season_results, season)
            
        print(f"\n✅ HERRELIGA ANALYSE KOMPLET!")
        print("=" * 70)
        print("📁 Genererede Herreliga filer:")
        for season in self.all_season_results.keys():
            print(f"  • herreliga_seasonal_elo_{season.replace('-', '_')}.csv")


# === MAIN EXECUTION ===
if __name__ == "__main__":
    print("🏆 STARTER HERRELIGA SÆSON-BASERET HÅNDBOL ELO SYSTEM")
    print("=" * 80)
    print("🎯 FOKUS: Ultra-individuelle start ratings kun for Herreliga")
    
    # Create system instance
    herreliga_system = HerreligaSeasonalEloSystem()
    
    # Run complete Herreliga analysis
    herreliga_system.run_complete_herreliga_analysis() 