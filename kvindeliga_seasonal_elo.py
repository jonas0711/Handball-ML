#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 ULTIMATIVT SÆSON-BASERET HÅNDBOL ELO SYSTEM
=================================================

BYGGER PÅ MASTER ELO SYSTEMET MED TILFØJELSE AF:
✅ Sæson-for-sæson processering 
✅ Intelligent regression to mean mellem sæsoner
✅ Detaljerede per-sæson CSV filer
✅ Karriere tracking på tværs af sæsoner  
✅ Robust fejlhåndtering og debugging
✅ Positionsbalance analyse per sæson
✅ Elite spillere skal præstere for at bevare rating

REGRESSION TO MEAN FILOSOFI:
- Højtratede spillere får bedre startposition næste sæson
- Men ikke så højt at dårlig performance ikke straffes  
- Progressiv regression baseret på distance fra gennemsnit
- Spillere med få kampe får mere regression
- Sikrer fair konkurrence på tværs af sæsoner

AI Assistant - December 2024
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

# === KONFIGURATION ===
BASE_RATING = 1200
MIN_GAMES_FOR_FULL_CARRY = 15    # Mindst 15 kampe for fuld carry-over
MAX_CARRY_BONUS = 150            # Max +150 bonus fra forrige sæson
MIN_CARRY_PENALTY = -100         # Max -100 straf fra forrige sæson
REGRESSION_STRENGTH = 0.75       # 75% regression to mean

class UltimateSeasonalHandballEloSystem:
    """
    🏆 ULTIMATIVT SÆSON-BASERET ELO SYSTEM
    """
    
    def __init__(self, base_dir: str = "."):
        print("🏆 ULTIMATIVT SÆSON-BASERET HÅNDBOL ELO SYSTEM")
        print("=" * 70)
        
        self.base_dir = base_dir
        
        # Sæson data storage
        self.all_season_results = {}
        self.player_career_data = defaultdict(list)
        
        # Database directories
        self.herreliga_dir = os.path.join(base_dir, "Herreliga-database")
        self.kvindeliga_dir = os.path.join(base_dir, "Kvindeliga-database")
        
        # Available seasons (inkluderer 2017-2018)
        self.seasons = [
            "2017-2018", "2018-2019", "2019-2020", "2020-2021", 
            "2021-2022", "2022-2023", "2023-2024", "2024-2025"
        ]
        
        # Validate seasons exist
        self.validate_season_availability()
        
        print("✅ Ultimate Seasonal ELO system initialiseret")
        print(f"📅 Tilgængelige sæsoner: {len(self.seasons)}")
        print(f"🎯 Base rating: {BASE_RATING}")
        print(f"📊 Regression styrke: {REGRESSION_STRENGTH}")
        print(f"🔄 Min games for full carry: {MIN_GAMES_FOR_FULL_CARRY}")
        
    def validate_season_availability(self):
        """Validerer at sæsoner findes i database"""
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
        print(f"\n📊 {len(self.seasons)} gyldige sæsoner klar til processering")
        
    def calculate_intelligent_start_rating(self, player_name: str, 
                                         previous_season_data: Dict = None,
                                         league_avg: float = None) -> float:
        """
        🧠 INTELLIGENT START RATING BEREGNING MED REGRESSION TO MEAN
        
        Faktorer der påvirker start rating:
        1. Forrige sæson final rating
        2. Antal kampe spillet (spillere med få kampe får mere regression)
        3. Distance fra ligagennemsnit (ekstreme ratings regresses mere)
        4. Elite status (høje ratings skal arbejde hårdere for at beholde dem)
        """
        
        if not previous_season_data:
            return BASE_RATING
            
        prev_rating = previous_season_data.get('final_rating', BASE_RATING)
        prev_games = previous_season_data.get('games', 0)
        prev_elite_status = previous_season_data.get('elite_status', 'NORMAL')
        
        # Hvis ingen tidligere rating, start på base
        if prev_rating == BASE_RATING:
            return BASE_RATING
            
        # === REGRESSION TARGET ===
        mean_rating = league_avg if league_avg else BASE_RATING
        distance_from_mean = prev_rating - mean_rating
        
        # === GAMES FACTOR ===
        # Spillere med flere kampe får mindre regression
        if prev_games >= MIN_GAMES_FOR_FULL_CARRY:
            games_factor = 1.0  # Fuld carry-over
        elif prev_games >= 10:
            # Gradueret mellem 10-15 kampe
            games_factor = 0.6 + 0.4 * (prev_games - 10) / (MIN_GAMES_FOR_FULL_CARRY - 10)
        elif prev_games >= 5:
            # Minimal carry-over
            games_factor = 0.3 + 0.3 * (prev_games - 5) / 5
        else:
            games_factor = 0.2  # Meget lav carry-over for få kampe
            
        # === ELITE STATUS FACTOR ===
        # Elite spillere skal arbejde hårdere for at beholde høj rating
        if prev_elite_status == 'LEGENDARY':
            elite_factor = 0.6  # Stærk regression for legendary
        elif prev_elite_status == 'ELITE':
            elite_factor = 0.75  # Moderat regression for elite
        else:
            elite_factor = 0.9   # Minimal regression for normale
            
        # === DISTANCE FACTOR ===
        # Progressive regression baseret på distance
        abs_distance = abs(distance_from_mean)
        if abs_distance > 500:
            distance_factor = 0.4  # Ekstremt stærk regression
        elif abs_distance > 350:
            distance_factor = 0.55  # Stærk regression
        elif abs_distance > 200:
            distance_factor = 0.7   # Moderat regression
        elif abs_distance > 100:
            distance_factor = 0.85  # Svag regression
        else:
            distance_factor = 0.95  # Minimal regression
            
        # === KOMBINER ALLE FAKTORER ===
        combined_factor = games_factor * elite_factor * distance_factor
        
        # Beregn ny start rating
        regressed_distance = distance_from_mean * combined_factor
        new_start_rating = mean_rating + regressed_distance
        
        # === APPLY CAPS ===
        rating_change = new_start_rating - BASE_RATING
        
        if rating_change > MAX_CARRY_BONUS:
            new_start_rating = BASE_RATING + MAX_CARRY_BONUS
        elif rating_change < MIN_CARRY_PENALTY:
            new_start_rating = BASE_RATING + MIN_CARRY_PENALTY
            
        # Debug for betydelige ændringer
        total_change = new_start_rating - prev_rating
        if abs(total_change) > 75:
            print(f"    📊 {player_name}: {prev_rating:.0f} → {new_start_rating:.0f} "
                  f"({total_change:+.0f}) [{prev_games} kampe, {prev_elite_status}]")
                  
        return round(new_start_rating, 1)
        
    def run_master_for_season(self, season: str, start_ratings: Dict = None) -> Dict:
        """
        Kører master ELO systemet for en enkelt sæson
        """
        print(f"\n🏐 PROCESSERER SÆSON {season}")
        print("-" * 50)
        
        try:
            # Import master system
            from handball_elo_master import MasterHandballEloSystem
            
            # Create fresh instance for this season
            master_system = MasterHandballEloSystem(self.base_dir)
            
            # Set start ratings if provided
            if start_ratings:
                print(f"📈 Sætter start ratings for {len(start_ratings)} spillere")
                for player_name, start_rating in start_ratings.items():
                    master_system.player_elos[player_name] = start_rating
                    # Set goalkeeper default if applicable
                    if player_name in master_system.confirmed_goalkeepers:
                        if start_rating == BASE_RATING:
                            master_system.player_elos[player_name] = master_system.rating_bounds['default_goalkeeper']
            
            # Process both leagues for this season
            total_matches = 0
            
            # Herreliga
            herreliga_matches = master_system.process_season_database(season)
            if herreliga_matches > 0:
                total_matches += herreliga_matches
                print(f"  ✅ Herreliga: {herreliga_matches} kampe")
            
            # Kvindeliga (modify master system to handle kvindeliga)
            kvindeliga_path = os.path.join(self.kvindeliga_dir, season)
            if os.path.exists(kvindeliga_path):
                original_dir = master_system.database_dir
                master_system.database_dir = self.kvindeliga_dir
                kvindeliga_matches = master_system.process_season_database(season)
                master_system.database_dir = original_dir
                
                if kvindeliga_matches > 0:
                    total_matches += kvindeliga_matches
                    print(f"  ✅ Kvindeliga: {kvindeliga_matches} kampe")
            
            if total_matches == 0:
                print(f"❌ Ingen kampe processeret for {season}")
                return {}
                
            print(f"✅ Total: {total_matches} kampe processeret")
            
            # Generate season results
            season_results = {}
            
            for player_name, final_rating in master_system.player_elos.items():
                games = master_system.player_games.get(player_name, 0)
                
                # Only include players who actually played
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
                    
                    # Momentum
                    momentum = master_system.get_momentum_multiplier(player_name)
                    
                    season_results[player_name] = {
                        'season': season,
                        'player': player_name,
                        'start_rating': round(start_rating, 1),
                        'final_rating': round(final_rating, 1),
                        'rating_change': round(final_rating - start_rating, 1),
                        'games': games,
                        'primary_position': primary_position,
                        'position_name': position_name,
                        'is_goalkeeper': is_goalkeeper,
                        'elite_status': elite_status,
                        'momentum_factor': round(momentum, 3),
                        'total_actions': sum(positions.values()) if positions else 0
                    }
                    
            return season_results
            
        except Exception as e:
            print(f"❌ Fejl i sæson {season}: {e}")
            return {}
            
    def analyze_position_balance(self, season_results: Dict, season: str):
        """
        Analyserer position balance for en sæson
        """
        print(f"\n⚖️ POSITION BALANCE ANALYSE - {season}")
        print("-" * 50)
        
        if not season_results:
            print("❌ Ingen data til analyse")
            return
            
        # Group by position
        position_ratings = defaultdict(list)
        
        for player_data in season_results.values():
            position = player_data['primary_position']
            rating = player_data['final_rating']
            position_ratings[position].append(rating)
            
        # Calculate statistics
        position_stats = {}
        
        for position, ratings in position_ratings.items():
            if ratings:
                position_stats[position] = {
                    'count': len(ratings),
                    'mean': np.mean(ratings),
                    'std': np.std(ratings),
                    'min': min(ratings),
                    'max': max(ratings)
                }
        
        # Print analysis
        print("📊 Position statistikker:")
        for position in ['MV', 'VF', 'HF', 'VB', 'PL', 'HB', 'ST']:
            if position in position_stats:
                stats = position_stats[position]
                print(f"  {position} ({stats['count']:3d} spillere): "
                      f"{stats['mean']:6.0f} ±{stats['std']:4.0f} "
                      f"[{stats['min']:4.0f}-{stats['max']:4.0f}]")
        
        # Balance coefficient
        if len(position_stats) >= 3:
            means = [stats['mean'] for stats in position_stats.values()]
            overall_mean = np.mean(means)
            cv = np.std(means) / overall_mean * 100
            
            balance_status = "✅ EXCELLENT" if cv < 8 else "✅ GOOD" if cv < 15 else "⚠️ NEEDS WORK"
            print(f"\n📊 Balance koefficient: {cv:.1f}% ({balance_status})")
            
    def save_season_csv(self, season_results: Dict, season: str):
        """
        Gemmer sæson resultater til detaljeret CSV fil
        """
        if not season_results:
            return
            
        # Convert to DataFrame
        df = pd.DataFrame(list(season_results.values()))
        
        # Add additional columns
        df['rating_per_game'] = df['rating_change'] / df['games']
        df['performance_level'] = df['final_rating'].apply(
            lambda x: 'LEGENDARY' if x >= 2200 else 'ELITE' if x >= 1800 else 'NORMAL'
        )
        
        # Sort by final rating
        df = df.sort_values('final_rating', ascending=False)
        
        # Ensure ELO_Results/Player_Seasonal_CSV directory exists
        output_dir = os.path.join("ELO_Results", "Player_Seasonal_CSV")
        os.makedirs(output_dir, exist_ok=True)
        
        # Save CSV in correct directory
        filename = f'seasonal_elo_{season.replace("-", "_")}.csv'
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False)
        
        print(f"💾 Gemt: {filepath} ({len(df)} spillere)")
        
        # Show top performers
        print(f"\n🏆 TOP 10 SPILLERE {season}:")
        for i, (_, row) in enumerate(df.head(10).iterrows(), 1):
            gk_icon = "🥅" if row['is_goalkeeper'] else ""
            elite_badge = f"[{row['elite_status']}]" if row['elite_status'] != 'NORMAL' else ""
            
            print(f"  {i:2d}. {row['player']} {gk_icon}: {row['final_rating']:.0f} "
                  f"({row['rating_change']:+.0f}) {elite_badge}")
                  
    def run_complete_seasonal_analysis(self):
        """
        🚀 HOVEDFUNKTION - Kører komplet sæson-baseret analyse
        """
        print("\n🚀 STARTER KOMPLET SÆSON-BASERET ANALYSE")
        print("=" * 70)
        
        previous_season_data = None
        
        for season in self.seasons:
            print(f"\n📅 === SÆSON {season} ===")
            
            # Calculate start ratings from previous season
            start_ratings = {}
            
            if previous_season_data:
                print(f"📈 Beregner start ratings fra {len(previous_season_data)} spillere")
                
                # Calculate league average
                prev_ratings = [data['final_rating'] for data in previous_season_data.values()]
                league_avg = np.mean(prev_ratings) if prev_ratings else BASE_RATING
                
                print(f"📊 Forrige sæson gennemsnit: {league_avg:.1f}")
                
                regression_stats = {'bonus': 0, 'penalty': 0, 'significant': 0}
                
                for player_name, player_data in previous_season_data.items():
                    start_rating = self.calculate_intelligent_start_rating(
                        player_name, player_data, league_avg
                    )
                    start_ratings[player_name] = start_rating
                    
                    # Track regression statistics
                    if start_rating > BASE_RATING:
                        regression_stats['bonus'] += 1
                    elif start_rating < BASE_RATING:
                        regression_stats['penalty'] += 1
                        
                    if abs(start_rating - player_data['final_rating']) > 50:
                        regression_stats['significant'] += 1
                        
                print(f"📊 Regression oversigt:")
                print(f"   ⬆️ {regression_stats['bonus']} spillere med bonus start")
                print(f"   ⬇️ {regression_stats['penalty']} spillere med penalty start")
                print(f"   🔄 {regression_stats['significant']} spillere med betydelig regression")
            else:
                print("📊 Første sæson - alle starter på base rating")
                
            # Run master system for this season
            season_results = self.run_master_for_season(season, start_ratings)
            
            if not season_results:
                print(f"⚠️ Springer over {season} - ingen resultater")
                continue
                
            # Store results
            self.all_season_results[season] = season_results
            
            # Update player career data
            for player_name, player_data in season_results.items():
                self.player_career_data[player_name].append({
                    'season': season,
                    'final_rating': player_data['final_rating'],
                    'games': player_data['games'],
                    'position': player_data['primary_position']
                })
            
            # Analyze and save
            self.analyze_position_balance(season_results, season)
            self.save_season_csv(season_results, season)
            
            # Set up for next season
            previous_season_data = season_results
            
        # Generate final analyses
        self.generate_career_analysis()
        self.generate_summary_report()
        
    def generate_career_analysis(self):
        """
        Genererer karriere analyse på tværs af sæsoner
        """
        print(f"\n🏆 KARRIERE ANALYSE PÅ TVÆRS AF SÆSONER")
        print("=" * 70)
        
        if not self.player_career_data:
            print("❌ Ingen karriere data tilgængelig")
            return
            
        # Find spillere med mindst 3 sæsoner
        career_players = []
        
        for player_name, seasons_data in self.player_career_data.items():
            if len(seasons_data) >= 3:
                ratings = [s['final_rating'] for s in seasons_data]
                games = [s['games'] for s in seasons_data]
                
                career_stats = {
                    'player': player_name,
                    'seasons_played': len(seasons_data),
                    'avg_rating': round(np.mean(ratings), 1),
                    'peak_rating': round(max(ratings), 1),
                    'total_games': sum(games),
                    'career_change': round(ratings[-1] - ratings[0], 1),
                    'consistency': round(np.std(ratings), 1),
                    'primary_position': Counter([s['position'] for s in seasons_data]).most_common(1)[0][0]
                }
                
                career_players.append(career_stats)
                
        # Sort by average rating
        career_players.sort(key=lambda x: x['avg_rating'], reverse=True)
        
        print(f"📊 Fundet {len(career_players)} karriere spillere (≥3 sæsoner)")
        
        # Show top 20 career players
        print(f"\n🏆 TOP 20 KARRIERE SPILLERE:")
        for i, player in enumerate(career_players[:20], 1):
            trend = "📈" if player['career_change'] > 50 else "📉" if player['career_change'] < -50 else "➡️"
            consistency = "🎯" if player['consistency'] < 50 else "📊"
            
            print(f"  {i:2d}. {player['player']} ({player['primary_position']}): "
                  f"{player['avg_rating']:.0f} avg, peak {player['peak_rating']:.0f} "
                  f"({player['seasons_played']} sæsoner) {trend}{player['career_change']:+.0f} {consistency}")
                  
        # Save career analysis
        career_df = pd.DataFrame(career_players)
        
        # Ensure Analysis CSV directory exists
        analysis_dir = os.path.join("ELO_Results", "Analysis_CSV")
        os.makedirs(analysis_dir, exist_ok=True)
        
        career_filepath = os.path.join(analysis_dir, 'ultimate_career_analysis.csv')
        career_df.to_csv(career_filepath, index=False)
        print(f"\n💾 Karriere analyse gemt: {career_filepath}")
        
    def generate_summary_report(self):
        """
        Genererer samlet rapport over alle sæsoner
        """
        print(f"\n📊 SAMLET RAPPORT - ALLE SÆSONER")
        print("=" * 70)
        
        if not self.all_season_results:
            print("❌ Ingen sæsondata til rapport")
            return
            
        total_players = set()
        total_matches = 0
        season_summary = []
        
        for season, results in self.all_season_results.items():
            total_players.update(results.keys())
            season_matches = sum(player['games'] for player in results.values())
            
            ratings = [player['final_rating'] for player in results.values()]
            elite_count = sum(1 for r in ratings if r >= 1800)
            legendary_count = sum(1 for r in ratings if r >= 2200)
            
            season_summary.append({
                'season': season,
                'players': len(results),
                'total_games': season_matches,
                'avg_rating': round(np.mean(ratings), 1),
                'elite_players': elite_count,
                'legendary_players': legendary_count,
                'max_rating': round(max(ratings), 1)
            })
            
            total_matches += season_matches
            
        print(f"🏐 SAMLET STATISTIK:")
        print(f"  📊 Total unikke spillere: {len(total_players):,}")
        print(f"  🏟️ Total kampe: {total_matches:,}")
        print(f"  📅 Sæsoner processeret: {len(self.all_season_results)}")
        
        print(f"\n📅 SÆSON OVERSIGT:")
        for s in season_summary:
            print(f"  {s['season']}: {s['players']:3d} spillere, {s['total_games']:3d} kampe, "
                  f"avg {s['avg_rating']:.0f} (E:{s['elite_players']}, L:{s['legendary_players']})")
                  
        # Save summary
        summary_df = pd.DataFrame(season_summary)
        
        # Ensure Analysis CSV directory exists
        analysis_dir = os.path.join("ELO_Results", "Analysis_CSV")
        os.makedirs(analysis_dir, exist_ok=True)
        
        summary_filepath = os.path.join(analysis_dir, 'seasonal_summary_report.csv')
        summary_df.to_csv(summary_filepath, index=False)
        print(f"\n💾 Rapport gemt: {summary_filepath}")
        
        print(f"\n✅ ULTIMATIVT SÆSON-BASERET ANALYSE KOMPLET!")
        print("=" * 70)
        print("📁 Genererede filer:")
        for season in self.all_season_results.keys():
            print(f"  • seasonal_elo_{season.replace('-', '_')}.csv")
        print("  • ultimate_career_analysis.csv")
        print("  • seasonal_summary_report.csv")


# === MAIN EXECUTION ===
if __name__ == "__main__":
    print("🏆 STARTER ULTIMATIVT SÆSON-BASERET HÅNDBOL ELO SYSTEM")
    print("=" * 80)
    
    # Create system instance
    seasonal_system = UltimateSeasonalHandballEloSystem()
    
    # Run complete analysis
    seasonal_system.run_complete_seasonal_analysis()
    
    print("\n🎉 ULTIMATIVT SÆSON-BASERET SYSTEM KOMPLET!")
    print("=" * 80)
    print("🎯 Implementerede features:")
    print("  ✅ Intelligent regression to mean mellem sæsoner")
    print("  ✅ Progressiv regression baseret på elite status")
    print("  ✅ Games-baseret carry-over faktorer")
    print("  ✅ Per-sæson detaljerede CSV filer")
    print("  ✅ Position balance analyse per sæson")
    print("  ✅ Karriere tracking på tværs af sæsoner")
    print("  ✅ Robust fejlhåndtering og debugging")
    print("  ✅ Elite spillere skal præstere for at beholde rating")
    print("  ✅ Support for både Herreliga og Kvindeliga")
    print("\n🏆 SÆSON-BASERET ELO SIKRER FAIR KONKURRENCE!") 