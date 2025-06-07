#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 KVINDELIGA SÆSON-BASERET HÅNDBOL ELO SYSTEM
=====================================================

FOKUSERER KUN PÅ KVINDELIGA MED FORBEDREDE START-RATINGS:
✅ Kun Kvindeliga data - ingen blanding med Herreliga
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

# === FORBEDREDE SYSTEM PARAMETRE (Synkroniseret med Herreliga) ===
BASE_RATING = 1000                 # REDUCERET fra 1200 - giver mere plads til spredning
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

class KvindeligaSeasonalEloSystem:
    """
    🏆 KVINDELIGA-FOKUSERET SÆSON ELO SYSTEM MED ULTRA-INDIVIDUELLE RATINGS
    """
    
    def __init__(self, base_dir: str = "."):
        print("🏆 KVINDELIGA SÆSON-BASERET HÅNDBOL ELO SYSTEM")
        print("=" * 70)
        print("🎯 FOKUS: Kun Kvindeliga med ultra-individuelle start ratings")
        
        self.base_dir = base_dir
        
        # Kun Kvindeliga directory  
        self.kvindeliga_dir = os.path.join(base_dir, "Kvindeliga-database")
        
        # Sæson data storage
        self.all_season_results = {}
        self.player_career_data = defaultdict(list)
        self.team_season_performance = defaultdict(dict)
        
        # Available seasons
        self.seasons = [
            "2017-2018", "2018-2019", "2019-2020", "2020-2021", 
            "2021-2022", "2022-2023", "2023-2024", "2024-2025"
        ]
        
        # Validate seasons exist (kun Kvindeliga)
        self.validate_kvindeliga_seasons()
        
        print("✅ Kvindeliga ELO system initialiseret")
        print(f"📅 Tilgængelige sæsoner: {len(self.seasons)}")
        print(f"🎯 Base rating: {BASE_RATING}")
        print(f"📊 Max carry bonus: +{MAX_CARRY_BONUS}")
        print(f"📉 Max carry penalty: {MIN_CARRY_PENALTY}")
        
    def validate_kvindeliga_seasons(self):
        """Validerer kun Kvindeliga sæsoner"""
        print(f"\n🔍 VALIDERER KVINDELIGA SÆSONER")
        print("-" * 50)
        
        valid_seasons = []
        
        for season in self.seasons:
            kvindeliga_path = os.path.join(self.kvindeliga_dir, season)
            
            kvindeliga_files = 0
            if os.path.exists(kvindeliga_path):
                kvindeliga_files = len([f for f in os.listdir(kvindeliga_path) if f.endswith('.db')])
                
            if kvindeliga_files > 0:
                valid_seasons.append(season)
                print(f"  ✅ {season}: {kvindeliga_files} Kvindeliga kampe")
            else:
                print(f"  ❌ {season}: ingen Kvindeliga data")
                
        self.seasons = valid_seasons
        print(f"\n📊 {len(self.seasons)} gyldige Kvindeliga sæsoner klar")
        
    def calculate_ultra_individual_start_rating(self, player_name: str, 
                                              previous_season_data: Dict = None,
                                              team_performance: Dict = None,
                                              league_stats: Dict = None) -> float:
        """
        🧠 ULTRA-INDIVIDUALISERET START RATING BEREGNING (Synkroniseret med Herreliga)
        
        Faktorer inkluderet:
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
        if distance_from_league_avg > 0:  # Spilleren var bedre end gennemsnittet
            if abs_distance > 500: distance_factor = 0.85
            elif abs_distance > 400: distance_factor = 0.90
            elif abs_distance > 300: distance_factor = 0.95
            elif abs_distance > 200: distance_factor = 0.97
            elif abs_distance > 100: distance_factor = 0.98
            else: distance_factor = 0.99
        else:  # Spilleren var under gennemsnittet
            if abs_distance > 400: distance_factor = 0.15
            elif abs_distance > 300: distance_factor = 0.25
            elif abs_distance > 200: distance_factor = 0.35
            elif abs_distance > 100: distance_factor = 0.55
            else: distance_factor = 0.75
            
        # === KOMBINER ALLE FAKTORER ===
        combined_factor = (games_factor * position_factor * elite_factor * 
                          consistency_factor * momentum_factor * team_factor * distance_factor)
        
        # === BEREGN NY START RATING ===
        adjusted_distance = distance_from_league_avg * combined_factor
        new_start_rating = league_avg + adjusted_distance
        
        # === ANVEND CAPS MED GRADUERET OVERGANG (forbedret for gode spillere) ===
        if prev_rating_per_game > 8 and prev_games >= MIN_GAMES_FOR_FULL_CARRY:
            exceptional_bonus = min(120, (prev_rating_per_game - 8) * 8)
            new_start_rating += exceptional_bonus
        elif prev_rating_per_game > 5 and prev_games >= 8:
            moderate_bonus = min(60, (prev_rating_per_game - 5) * 6)
            new_start_rating += moderate_bonus
        
        # Apply caps
        rating_change = new_start_rating - BASE_RATING
        if rating_change > MAX_CARRY_BONUS:
            new_start_rating = BASE_RATING + MAX_CARRY_BONUS
        elif rating_change < MIN_CARRY_PENALTY:
            new_start_rating = BASE_RATING + MIN_CARRY_PENALTY
            
        # === FINAL SMALL RANDOMIZATION FOR UNIQUENESS ===
        np.random.seed(hash(player_name) % 1000)
        unique_adjustment = np.random.uniform(-3, 3)
        new_start_rating += unique_adjustment
                  
        return round(new_start_rating, 1)
        
    def run_kvindeliga_season(self, season: str, start_ratings: Dict = None) -> Dict:
        """
        Kører master ELO systemet for kun Kvindeliga i en enkelt sæson
        """
        print(f"\n🏐 PROCESSERER KVINDELIGA SÆSON {season}")
        print("-" * 50)
        
        try:
            # Import master system
            from handball_elo_master import MasterHandballEloSystem
            
            # Create fresh instance for this season (kun Kvindeliga)
            master_system = MasterHandballEloSystem(self.base_dir)
            
            # Set start ratings if provided
            if start_ratings:
                print(f"📈 Sætter start ratings for {len(start_ratings)} Kvindeliga spillere")
                # Add printouts for rating spread
                if start_ratings.values():
                    print(f"📊 Rating range: {min(start_ratings.values()):.0f} - {max(start_ratings.values()):.0f}")
                    rating_spread = max(start_ratings.values()) - min(start_ratings.values())
                    print(f"📏 Rating spread: {rating_spread:.0f} points")
                
                for player_name, start_rating in start_ratings.items():
                    master_system.player_elos[player_name] = start_rating
                    if player_name in master_system.confirmed_goalkeepers and start_rating == BASE_RATING:
                        master_system.player_elos[player_name] = master_system.rating_bounds['default_goalkeeper']
            
            # Process ONLY Kvindeliga for this season
            # Temporarily point master system to Kvindeliga directory
            original_dir = master_system.database_dir
            master_system.database_dir = self.kvindeliga_dir
            kvindeliga_matches = master_system.process_season_database(season)
            master_system.database_dir = original_dir # Reset original path
            
            if kvindeliga_matches == 0:
                print(f"❌ Ingen Kvindeliga kampe processeret for {season}")
                return {}
                
            print(f"✅ Kvindeliga: {kvindeliga_matches} kampe processeret")
            
            # Generate season results
            season_results = {}
            
            for player_name, final_rating in master_system.player_elos.items():
                games = master_system.player_games.get(player_name, 0)
                
                if games > 0:
                    start_rating = start_ratings.get(player_name, BASE_RATING) if start_ratings else BASE_RATING
                    positions = master_system.player_positions[player_name]
                    primary_position = positions.most_common(1)[0][0] if positions else 'PL'
                    position_name = master_system.standard_positions.get(primary_position, 'Unknown')
                    is_goalkeeper = player_name in master_system.confirmed_goalkeepers
                    
                    if final_rating >= master_system.rating_bounds['legendary_threshold']: elite_status = "LEGENDARY"
                    elif final_rating >= master_system.rating_bounds['elite_threshold']: elite_status = "ELITE"
                    else: elite_status = "NORMAL"
                    
                    rating_change = final_rating - start_rating
                    if rating_change > 50: performance_level = "ELITE"
                    else: performance_level = "NORMAL"
                    
                    momentum = master_system.get_momentum_multiplier(player_name)
                    rating_per_game = rating_change / games if games > 0 else 0
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
                        'total_actions': sum(positions.values()) if positions else 0,
                        'rating_per_game': round(rating_per_game, 3),
                        'performance_level': performance_level,
                        'rating_consistency': round(rating_consistency, 1)
                    }
                    
            return season_results
            
        except Exception as e:
            print(f"❌ Fejl i Kvindeliga sæson {season}: {e}")
            import traceback
            traceback.print_exc()
            return {}
            
    def save_kvindeliga_season_csv(self, season_results: Dict, season: str):
        """
        Gemmer Kvindeliga sæson resultater til CSV
        """
        if not season_results:
            print(f"❌ Ingen data at gemme for {season}")
            return
            
        df = pd.DataFrame(list(season_results.values()))
        df = df.sort_values('final_rating', ascending=False)
        
        output_dir = os.path.join("ELO_Results", "Player_Seasonal_CSV")
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f"kvindeliga_seasonal_elo_{season.replace('-', '_')}.csv"
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        avg_rating = df['final_rating'].mean()
        rating_spread = df['final_rating'].max() - df['final_rating'].min()
        elite_count = len(df[df['elite_status'] == 'ELITE'])
        legendary_count = len(df[df['elite_status'] == 'LEGENDARY'])
        
        print(f"💾 Gemt: {filepath}")
        print(f"📊 {len(df)} Kvindeliga spillere, avg rating: {avg_rating:.1f}")
        print(f"📏 Rating spread: {rating_spread:.0f} points")
        print(f"🏆 Elite spillere: {elite_count}, Legendary: {legendary_count}")
        
    def _get_all_player_names_for_season(self, season: str) -> set:
        """
        Henter alle unikke spillernavne fra Kvindeliga database-filerne for en given sæson.
        """
        player_names = set()
        season_path = os.path.join(self.kvindeliga_dir, season)

        if not os.path.exists(season_path):
            return player_names

        for db_file in os.listdir(season_path):
            if not db_file.endswith('.db'):
                continue
            
            db_path = os.path.join(season_path, db_file)
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
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

    def _find_player_name_mapping(self, current_names: set, previous_data: dict) -> dict:
        """
        ROBUST NAVNE-MATCHING (REGELBASERET)
        Prioriterer matches i en logisk rækkefølge for at sikre stabilitet.
        1. Direkte match efter normalisering.
        2. Subset match (når et navn er en del af et andet).
        3. Levenshtein-baseret match for stavefejl.
        """
        print(f"  🧠 Forsøger robust, regelbaseret navne-matching for {len(current_names)} spillere...")
        mapping = {}
        
        # Kopier forrige navne, så vi kan fjerne dem, når de er matchet
        available_prev_names = set(previous_data.keys())
        
        # --- TRIN 1: NORMALISERING & DIREKTE MATCHES ---
        normalized_prev_map = {' '.join(name.lower().split()): name for name in available_prev_names}
        unmatched_current = set()
        
        direct_matches_found = 0
        for name in current_names:
            normalized_name = ' '.join(name.lower().split())
            if normalized_name in normalized_prev_map:
                original_prev_name = normalized_prev_map[normalized_name]
                mapping[name] = original_prev_name
                available_prev_names.remove(original_prev_name)
                del normalized_prev_map[normalized_name]
                direct_matches_found += 1
            else:
                unmatched_current.add(name)
        
        if direct_matches_found > 0:
            print(f"    ✅ Trin 1: Fandt {direct_matches_found} direkte matches efter normalisering.")

        # --- TRIN 2: SUBSET MATCHES (Højeste prioritet for navneændringer) ---
        subset_matches_found = 0
        still_unmatched = set()
        if unmatched_current and available_prev_names:
            sorted_unmatched = sorted(list(unmatched_current))
            
            for curr_name in sorted_unmatched:
                normalized_curr_parts = set(' '.join(curr_name.lower().split()).split())
                best_match = None
                
                for prev_name in sorted(list(available_prev_names)):
                    normalized_prev_parts = set(' '.join(prev_name.lower().split()).split())
                    
                    if normalized_curr_parts.issubset(normalized_prev_parts) or normalized_prev_parts.issubset(normalized_curr_parts):
                        best_match = prev_name
                        break
                
                if best_match:
                    mapping[curr_name] = best_match
                    available_prev_names.remove(best_match)
                    subset_matches_found += 1
                    print(f"        🤝 SUBSET: '{curr_name}' -> '{best_match}'")
                else:
                    still_unmatched.add(curr_name)
            unmatched_current = still_unmatched

        if subset_matches_found > 0:
            print(f"    ✅ Trin 2: Fandt {subset_matches_found} subset-baserede matches.")
            
        # --- TRIN 3: LEVENSHTEIN MATCH (For små stavefejl) ---
        levenshtein_matches_found = 0
        if unmatched_current and available_prev_names:
            try:
                from Levenshtein import ratio as levenshtein_ratio
                levenshtein_available = True
            except ImportError:
                levenshtein_available = False
            
            if levenshtein_available:
                for curr_name in sorted(list(unmatched_current)):
                    normalized_curr = ' '.join(curr_name.lower().split())
                    best_match = None
                    highest_score = 0.85
                    
                    for prev_name in sorted(list(available_prev_names)):
                        normalized_prev = ' '.join(prev_name.lower().split())
                        score = levenshtein_ratio(normalized_curr, normalized_prev)
                        if score > highest_score:
                            highest_score = score
                            best_match = prev_name
                    
                    if best_match:
                        mapping[curr_name] = best_match
                        available_prev_names.remove(best_match)
                        levenshtein_matches_found += 1
                        print(f"        🤝 LEVENSHTEIN: '{curr_name}' -> '{best_match}' (Score: {highest_score:.2f})")
            
        if levenshtein_matches_found > 0:
            print(f"    ✅ Trin 3: Fandt {levenshtein_matches_found} Levenshtein-baserede matches.")

        total_mapped = len(mapping)
        unmapped_count = len(current_names) - total_mapped
        print(f"    📊 Resultat: {total_mapped} spillere mappet, {unmapped_count} nye/ukendte spillere.")

        return mapping

    def run_complete_kvindeliga_analysis(self):
        """
        🚀 HOVEDFUNKTION - Kører komplet Kvindeliga sæson-baseret analyse
        """
        print("\n🚀 STARTER KOMPLET KVINDELIGA SÆSON-BASERET ANALYSE")
        print("=" * 70)
        print("🎯 KUN KVINDELIGA - ULTRA-INDIVIDUELLE START RATINGS")
        
        previous_season_data = None
        
        for season in self.seasons:
            print(f"\n📅 === KVINDELIGA SÆSON {season} ===")
            
            start_ratings = {}
            if previous_season_data:
                current_season_names = self._get_all_player_names_for_season(season)
                name_mapping = self._find_player_name_mapping(current_season_names, previous_season_data)

                print(f"📈 Beregner ultra-individuelle start ratings for {len(current_season_names)} spillere")
                
                prev_ratings = [data['final_rating'] for data in previous_season_data.values()]
                league_stats = {
                    'avg_rating': np.mean(prev_ratings) if prev_ratings else BASE_RATING,
                    'median_rating': np.median(prev_ratings) if prev_ratings else BASE_RATING,
                    'std_rating': np.std(prev_ratings) if prev_ratings else 50
                }
                
                print(f"📊 Forrige sæson Kvindeliga stats: Avg: {league_stats['avg_rating']:.1f}, "
                      f"Median: {league_stats['median_rating']:.1f}, Std: {league_stats['std_rating']:.1f}")
                
                for player_name in sorted(list(current_season_names)):
                    previous_name = name_mapping.get(player_name)
                    player_data = previous_season_data.get(previous_name) if previous_name else None

                    start_rating = self.calculate_ultra_individual_start_rating(
                        player_name, player_data, None, league_stats
                    )
                    start_ratings[player_name] = start_rating
            else:
                print("📊 Første sæson - alle starter på base rating med positions-justeringer")
                
            season_results = self.run_kvindeliga_season(season, start_ratings)
            
            if not season_results:
                print(f"⚠️ Springer over Kvindeliga {season} - ingen resultater")
                continue
                
            self.all_season_results[season] = season_results
            
            for player_name, player_data in season_results.items():
                self.player_career_data[player_name].append({
                    'season': season, 'final_rating': player_data['final_rating'],
                    'games': player_data['games'], 'position': player_data['primary_position'],
                    'rating_change': player_data['rating_change']
                })
            
            self.save_kvindeliga_season_csv(season_results, season)
            previous_season_data = season_results
            
        print(f"\n✅ KVINDELIGA ANALYSE KOMPLET!")
        print("=" * 70)
        print("📁 Genererede Kvindeliga filer:")
        for season in self.all_season_results.keys():
            print(f"  • kvindeliga_seasonal_elo_{season.replace('-', '_')}.csv")

# === MAIN EXECUTION ===
if __name__ == "__main__":
    print("🏆 STARTER KVINDELIGA SÆSON-BASERET HÅNDBOL ELO SYSTEM")
    print("=" * 80)
    print("🎯 FOKUS: Ultra-individuelle start ratings kun for Kvindeliga")
    
    kvindeliga_system = KvindeligaSeasonalEloSystem()
    kvindeliga_system.run_complete_kvindeliga_analysis() 