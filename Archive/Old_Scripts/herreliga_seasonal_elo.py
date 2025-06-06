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
        self.player_career_data = defaultdict(list)
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
        
    def run_herreliga_season(self, season: str, start_ratings: Dict = None) -> Dict:
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
            herreliga_matches = master_system.process_season_database(season)
            
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
                    
                    # Find primary position
                    positions = master_system.player_positions[player_name]
                    primary_position = positions.most_common(1)[0][0] if positions else 'PL'
                    
                    # Position info
                    position_name = master_system.standard_positions.get(primary_position, 'Unknown')
                    is_goalkeeper = player_name in master_system.confirmed_goalkeepers
                    
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
                        'total_actions': sum(positions.values()) if positions else 0,
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
        
        # Save CSV
        filename = f"herreliga_seasonal_elo_{season.replace('-', '_')}.csv"
        df.to_csv(filename, index=False, encoding='utf-8')
        
        # Print statistics
        avg_rating = df['final_rating'].mean()
        rating_spread = df['final_rating'].max() - df['final_rating'].min()
        elite_count = len(df[df['elite_status'] == 'ELITE'])
        legendary_count = len(df[df['elite_status'] == 'LEGENDARY'])
        
        print(f"💾 Gemt: {filename}")
        print(f"📊 {len(df)} Herreliga spillere, avg rating: {avg_rating:.1f}")
        print(f"📏 Rating spread: {rating_spread:.0f} points")
        print(f"🏆 Elite spillere: {elite_count}, Legendary: {legendary_count}")
        
    def run_complete_herreliga_analysis(self):
        """
        🚀 HOVEDFUNKTION - Kører komplet Herreliga sæson-baseret analyse
        """
        print("\n🚀 STARTER KOMPLET HERRELIGA SÆSON-BASERET ANALYSE")
        print("=" * 70)
        print("🎯 KUN HERRELIGA - ULTRA-INDIVIDUELLE START RATINGS")
        
        previous_season_data = None
        
        for season in self.seasons:
            print(f"\n📅 === HERRELIGA SÆSON {season} ===")
            
            # Calculate start ratings from previous season
            start_ratings = {}
            
            if previous_season_data:
                print(f"📈 Beregner ultra-individuelle start ratings fra {len(previous_season_data)} spillere")
                
                # Calculate league statistics for reference
                prev_ratings = [data['final_rating'] for data in previous_season_data.values()]
                league_stats = {
                    'avg_rating': np.mean(prev_ratings) if prev_ratings else BASE_RATING,
                    'median_rating': np.median(prev_ratings) if prev_ratings else BASE_RATING,
                    'std_rating': np.std(prev_ratings) if prev_ratings else 50
                }
                
                print(f"📊 Forrige sæson Herreliga stats:")
                print(f"   🎯 Gennemsnit: {league_stats['avg_rating']:.1f}")
                print(f"   📊 Median: {league_stats['median_rating']:.1f}")
                print(f"   📏 Standardafvigelse: {league_stats['std_rating']:.1f}")
                
                regression_stats = {'bonus': 0, 'penalty': 0, 'significant': 0, 'ultra_bonus': 0}
                
                for player_name, player_data in previous_season_data.items():
                    start_rating = self.calculate_ultra_individual_start_rating(
                        player_name, player_data, None, league_stats
                    )
                    start_ratings[player_name] = start_rating
                    
                    # Track regression statistics  
                    if start_rating > BASE_RATING + 100:
                        regression_stats['ultra_bonus'] += 1
                    elif start_rating > BASE_RATING:
                        regression_stats['bonus'] += 1
                    elif start_rating < BASE_RATING:
                        regression_stats['penalty'] += 1
                        
                    if abs(start_rating - player_data['final_rating']) > 75:
                        regression_stats['significant'] += 1
                        
                # Calculate final spread
                if start_ratings:
                    min_start = min(start_ratings.values())
                    max_start = max(start_ratings.values())
                    start_spread = max_start - min_start
                    
                    print(f"📊 Ultra-individuelle start ratings oversigt:")
                    print(f"   🚀 {regression_stats['ultra_bonus']} spillere med ultra bonus (>+100)")
                    print(f"   ⬆️ {regression_stats['bonus']} spillere med bonus start")
                    print(f"   ⬇️ {regression_stats['penalty']} spillere med penalty start")
                    print(f"   🔄 {regression_stats['significant']} spillere med betydelig regression")
                    print(f"   📏 Start rating spread: {start_spread:.0f} points ({min_start:.0f} - {max_start:.0f})")
            else:
                print("📊 Første sæson - alle starter på base rating med positions-justeringer")
                
            # Run master system for this Herreliga season
            season_results = self.run_herreliga_season(season, start_ratings)
            
            if not season_results:
                print(f"⚠️ Springer over Herreliga {season} - ingen resultater")
                continue
                
            # Store results
            self.all_season_results[season] = season_results
            
            # Update player career data
            for player_name, player_data in season_results.items():
                self.player_career_data[player_name].append({
                    'season': season,
                    'final_rating': player_data['final_rating'],
                    'games': player_data['games'],
                    'position': player_data['primary_position'],
                    'rating_change': player_data['rating_change']
                })
            
            # Save season CSV
            self.save_herreliga_season_csv(season_results, season)
            
            # Set up for next season
            previous_season_data = season_results
            
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