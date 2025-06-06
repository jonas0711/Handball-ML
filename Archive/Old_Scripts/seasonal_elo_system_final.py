#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SÆSON-BASERET HÅNDBOL ELO SYSTEM MED INTELLIGENT REGRESSION TO MEAN
====================================================================

Dette system bygger på det fungerende master ELO system men implementerer:
1. Sæson-for-sæson processering med carry-over ratings
2. Intelligent regression to mean mellem sæsoner
3. Per-sæson CSV output for analyse
4. Sikrer spillere skal præstere for at beholde høj rating

REGRESSION TO MEAN FILOSOFI:
- Højt ratede spillere får bedre start point næste sæson
- Men ikke så højt at dårlig performance ikke straffes
- Progressiv regression baseret på distance fra gennemsnit
- Mere regression for spillere med få kampe

Lavet af: AI Assistant  
Dato: 2024-12-19
"""

import pandas as pd
import sqlite3
import os
import numpy as np
from datetime import datetime
from collections import defaultdict, Counter
import warnings
warnings.filterwarnings('ignore')

# === KONFIGURATION ===
BASE_RATING = 1200
MIN_GAMES_FOR_FULL_CARRY = 15    # Mindst 15 kampe for fuld carry-over
MAX_CARRY_BONUS = 150            # Max +150 bonus fra forrige sæson
MIN_CARRY_PENALTY = -100         # Max -100 straf fra forrige sæson
REGRESSION_STRENGTH = 0.75       # 75% regression to mean mellem sæsoner

class SeasonalHandballEloSystem:
    """
    Sæson-baseret ELO system med intelligent regression to mean
    """
    
    def __init__(self, base_dir: str = "."):
        print("🏐 SÆSON-BASERET HÅNDBOL ELO SYSTEM")
        print("=" * 60)
        
        self.base_dir = base_dir
        
        # Sæson-specifikke data
        self.seasonal_results = {}
        self.player_season_history = defaultdict(dict)
        
        # Available seasons (kronologisk orden)
        self.seasons = [
            "2018-2019", "2019-2020", "2020-2021", "2021-2022", 
            "2022-2023", "2023-2024", "2024-2025"
        ]
        
        print("✅ Seasonal ELO system initialiseret")
        print(f"📅 Tilgængelige sæsoner: {len(self.seasons)}")
        print(f"🎯 Base rating: {BASE_RATING}")
        print(f"📊 Regression styrke: {REGRESSION_STRENGTH}")
        
    def calculate_season_start_rating(self, player_name: str, previous_season_data: dict = None,
                                    league_avg: float = None) -> float:
        """
        🎯 BEREGNER START RATING FOR NÆSTE SÆSON MED INTELLIGENT REGRESSION
        
        Filosofi:
        - Spillere med høj rating får bedre start men skal stadig præstere
        - Progressiv regression - jo højere rating, jo mere regression
        - Spillere med få kampe får mere regression
        - Sikrer at dårlig performance stadig resulterer i rating fald
        """
        
        if not previous_season_data:
            return BASE_RATING
            
        previous_rating = previous_season_data.get('final_rating', BASE_RATING)
        previous_games = previous_season_data.get('games', 0)
        
        # Hvis ingen tidligere rating, start på base
        if previous_rating == BASE_RATING:
            return BASE_RATING
            
        # === BEREGN REGRESSION TO MEAN ===
        
        # Base mean (brug ligagennemsnit hvis tilgængeligt)
        mean_rating = league_avg if league_avg else BASE_RATING
        
        # Distance fra mean
        distance_from_mean = previous_rating - mean_rating
        
        # === GAMES FACTOR ===
        # Spillere med flere kampe får mindre regression
        if previous_games >= MIN_GAMES_FOR_FULL_CARRY:
            games_factor = 1.0  # Fuld carry-over
        elif previous_games >= 5:
            # Gradueret mellem 5-15 kampe
            games_factor = 0.4 + 0.6 * (previous_games - 5) / (MIN_GAMES_FOR_FULL_CARRY - 5)
        else:
            games_factor = 0.2  # Meget lav carry-over for få kampe
            
        # === PROGRESSIVE REGRESSION ===
        # Jo højere rating, jo mere regression
        if abs(distance_from_mean) > 400:
            regression_factor = 0.5  # Stærk regression for ekstreme ratings
        elif abs(distance_from_mean) > 250:
            regression_factor = 0.65  # Moderat regression
        elif abs(distance_from_mean) > 150:
            regression_factor = 0.8  # Svag regression
        else:
            regression_factor = 0.9  # Minimal regression for tæt på mean
            
        # Kombiner regression og games factor
        effective_regression = regression_factor * games_factor
        
        # Beregn ny start rating
        regressed_distance = distance_from_mean * effective_regression
        new_start_rating = mean_rating + regressed_distance
        
        # === APPLY CAPS ===
        rating_change = new_start_rating - BASE_RATING
        
        if rating_change > MAX_CARRY_BONUS:
            new_start_rating = BASE_RATING + MAX_CARRY_BONUS
        elif rating_change < MIN_CARRY_PENALTY:
            new_start_rating = BASE_RATING + MIN_CARRY_PENALTY
            
        # Debug for interessante cases
        if abs(previous_rating - new_start_rating) > 100:
            print(f"    📊 {player_name}: {previous_rating:.0f} → {new_start_rating:.0f} "
                  f"({previous_games} kampe, regression: {effective_regression:.2f})")
                  
        return round(new_start_rating, 1)
        
    def run_master_system_for_season(self, season: str, start_ratings: dict = None) -> dict:
        """
        Kører master ELO systemet for en enkelt sæson med start ratings
        """
        print(f"\n🏐 PROCESSERER SÆSON {season}")
        print("-" * 50)
        
        # Import og konfigurer master systemet
        try:
            from handball_elo_master import MasterHandballEloSystem
        except ImportError:
            print("❌ Kunne ikke importere master system")
            return {}
            
        # Opret master system instance
        master_system = MasterHandballEloSystem(self.base_dir)
        
        # === INDSTIL START RATINGS ===
        if start_ratings:
            print(f"📈 Indstiller start ratings for {len(start_ratings)} spillere")
            for player_name, start_rating in start_ratings.items():
                master_system.player_elos[player_name] = start_rating
                
        # === PROCESS DENNE SÆSON ===
        processed_matches = master_system.process_season_database(season)
        
        if processed_matches == 0:
            print(f"❌ Ingen kampe processeret for {season}")
            return {}
            
        print(f"✅ {processed_matches} kampe processeret")
        
        # === GENERER SÆSON RESULTATER ===
        season_results = {}
        
        for player_name, final_rating in master_system.player_elos.items():
            games_played = master_system.player_games.get(player_name, 0)
            
            # Kun spillere der faktisk spillede kampe
            if games_played > 0:
                start_rating = start_ratings.get(player_name, BASE_RATING) if start_ratings else BASE_RATING
                
                # Find primær position
                positions = master_system.player_positions[player_name]
                primary_position = positions.most_common(1)[0][0] if positions else 'PL'
                
                # Målvogter status
                is_goalkeeper = player_name in master_system.confirmed_goalkeepers
                
                # Elite status
                if final_rating >= 2200:
                    elite_status = "LEGENDARY"
                elif final_rating >= 1800:
                    elite_status = "ELITE" 
                else:
                    elite_status = "NORMAL"
                
                season_results[player_name] = {
                    'season': season,
                    'player': player_name,
                    'start_rating': round(start_rating, 1),
                    'final_rating': round(final_rating, 1),
                    'rating_change': round(final_rating - start_rating, 1),
                    'games': games_played,
                    'primary_position': primary_position,
                    'is_goalkeeper': is_goalkeeper,
                    'elite_status': elite_status,
                    'actions': sum(positions.values()) if positions else 0
                }
                
        print(f"📊 {len(season_results)} spillere med aktivitet i {season}")
        
        return season_results
        
    def analyze_seasonal_position_balance(self, season_results: dict, season: str):
        """
        Analyserer position balance for en sæson
        """
        print(f"\n⚖️ POSITION BALANCE ANALYSE - {season}")
        print("-" * 50)
        
        if not season_results:
            print("❌ Ingen data til analyse")
            return
            
        # Grupper efter position
        position_stats = defaultdict(list)
        
        for player_data in season_results.values():
            position = player_data['primary_position']
            final_rating = player_data['final_rating']
            position_stats[position].append(final_rating)
            
        # Beregn statistikker
        position_means = {}
        for position, ratings in position_stats.items():
            if ratings:
                mean_rating = np.mean(ratings)
                std_rating = np.std(ratings)
                min_rating = min(ratings)
                max_rating = max(ratings)
                count = len(ratings)
                
                position_means[position] = mean_rating
                
                print(f"{position}: {mean_rating:5.0f} avg | {count:3d} spillere | "
                      f"{min_rating:4.0f}-{max_rating:4.0f} | std:{std_rating:4.0f}")
                
        # Beregn balance coefficient
        if len(position_means) > 1:
            mean_values = list(position_means.values())
            overall_mean = np.mean(mean_values)
            coefficient_of_variation = np.std(mean_values) / overall_mean * 100
            
            print(f"\n📊 Balance coefficient: {coefficient_of_variation:.1f}% "
                  f"({'✅ GOOD' if coefficient_of_variation < 20 else '⚠️ NEEDS WORK'})")
        
    def save_season_results(self, season_results: dict, season: str):
        """
        Gemmer sæson resultater til CSV fil
        """
        if not season_results:
            return
            
        # Konverter til DataFrame
        results_list = []
        for player_data in season_results.values():
            results_list.append(player_data)
            
        df = pd.DataFrame(results_list)
        
        # Sorter efter final rating
        df = df.sort_values('final_rating', ascending=False)
        
        # Gem til CSV
        filename = f'seasonal_elo_{season.replace("-", "_")}.csv'
        df.to_csv(filename, index=False)
        
        print(f"💾 Gemt: {filename} ({len(df)} spillere)")
        
        # Print top 10
        print(f"\n🏆 TOP 10 SPILLERE {season}:")
        for i, row in df.head(10).iterrows():
            gk_marker = "🥅" if row['is_goalkeeper'] else ""
            elite_marker = f"[{row['elite_status']}]" if row['elite_status'] != 'NORMAL' else ""
            
            print(f"  {i+1:2d}. {row['player']} {gk_marker}: {row['final_rating']:.0f} "
                  f"({row['rating_change']:+.0f}) {elite_marker}")
                  
    def run_complete_seasonal_analysis(self):
        """
        Kører komplet sæson-baseret analyse med regression to mean
        """
        print("\n🚀 STARTER KOMPLET SÆSON-BASERET ANALYSE")
        print("=" * 60)
        
        all_season_results = {}
        previous_season_data = None
        
        # Debug available seasons  
        print(f"📅 Configurerede sæsoner: {self.seasons}")
        
        for season in self.seasons:
            print(f"\n📅 BEHANDLER SÆSON {season}")
            print("=" * 40)
            
            # === BEREGN START RATINGS FRA FORRIGE SÆSON ===
            start_ratings = {}
            
            if previous_season_data:
                print(f"📈 Beregner start ratings baseret på {len(previous_season_data)} spillere")
                
                # Beregn ligagennemsnit fra forrige sæson
                previous_ratings = [data['final_rating'] for data in previous_season_data.values()]
                league_avg = np.mean(previous_ratings) if previous_ratings else BASE_RATING
                
                print(f"📊 Forrige sæson gennemsnit: {league_avg:.1f}")
                
                regression_count = 0
                bonus_count = 0
                penalty_count = 0
                
                for player_name, player_data in previous_season_data.items():
                    start_rating = self.calculate_season_start_rating(
                        player_name, player_data, league_avg
                    )
                    start_ratings[player_name] = start_rating
                    
                    # Statistik
                    if start_rating > BASE_RATING:
                        bonus_count += 1
                    elif start_rating < BASE_RATING:
                        penalty_count += 1
                    
                    if abs(start_rating - player_data['final_rating']) > 50:
                        regression_count += 1
                        
                print(f"📊 Regression oversigt:")
                print(f"   🎯 {bonus_count} spillere med bonus start rating")
                print(f"   📉 {penalty_count} spillere med penalty start rating")
                print(f"   🔄 {regression_count} spillere med betydelig regression")
            else:
                print("📊 Første sæson - alle starter på base rating")
                
            # === KØR MASTER SYSTEM FOR DENNE SÆSON ===
            season_results = self.run_master_system_for_season(season, start_ratings)
            
            if not season_results:
                print(f"⚠️ Springer over {season} - ingen data")
                continue
                
            # === ANALYSER OG GEM ===
            self.analyze_seasonal_position_balance(season_results, season)
            self.save_season_results(season_results, season)
            
            # Gem til samlet analyse
            all_season_results[season] = season_results
            previous_season_data = season_results
            
        # === FINAL MULTI-SEASON ANALYSE ===
        self.generate_multi_season_analysis(all_season_results)
        
    def generate_multi_season_analysis(self, all_results: dict):
        """
        Genererer analyse på tværs af alle sæsoner
        """
        print(f"\n📊 MULTI-SÆSON ANALYSE")
        print("=" * 60)
        
        if not all_results:
            print("❌ Ingen sæsondata til analyse")
            return
            
        # Find spillere med flest sæsoner
        player_season_count = defaultdict(int)
        player_career_data = defaultdict(list)
        
        for season, season_data in all_results.items():
            for player_name, player_data in season_data.items():
                player_season_count[player_name] += 1
                player_career_data[player_name].append({
                    'season': season,
                    'final_rating': player_data['final_rating'],
                    'games': player_data['games']
                })
                
        # Top karriere spillere
        career_players = [(player, count) for player, count in player_season_count.items() 
                         if count >= 3]  # Mindst 3 sæsoner
        career_players.sort(key=lambda x: x[1], reverse=True)
        
        print(f"🏆 KARRIERE SPILLERE (≥3 sæsoner): {len(career_players)}")
        
        # Analyser karriere udvikling
        career_analysis = []
        
        for player_name, season_count in career_players[:20]:  # Top 20
            player_seasons = player_career_data[player_name]
            
            # Beregn karriere statistikker
            ratings = [s['final_rating'] for s in player_seasons]
            games = [s['games'] for s in player_seasons]
            
            avg_rating = np.mean(ratings)
            peak_rating = max(ratings)
            total_games = sum(games)
            
            # Karriere trend (første vs sidste sæson)
            if len(ratings) >= 2:
                career_change = ratings[-1] - ratings[0]
            else:
                career_change = 0
                
            career_analysis.append({
                'player': player_name,
                'seasons': season_count,
                'avg_rating': round(avg_rating, 1),
                'peak_rating': round(peak_rating, 1),
                'career_change': round(career_change, 1),
                'total_games': total_games
            })
            
        # Sorter efter gennemsnitsrating
        career_analysis.sort(key=lambda x: x['avg_rating'], reverse=True)
        
        print(f"\n🏆 TOP 10 KARRIERE SPILLERE:")
        for i, player in enumerate(career_analysis[:10]):
            trend_marker = "📈" if player['career_change'] > 50 else "📉" if player['career_change'] < -50 else "➡️"
            
            print(f"  {i+1:2d}. {player['player']}: {player['avg_rating']:.0f} avg "
                  f"(peak: {player['peak_rating']:.0f}, {player['seasons']} sæsoner) "
                  f"{trend_marker} {player['career_change']:+.0f}")
                  
        # Gem karriere analyse
        career_df = pd.DataFrame(career_analysis)
        career_df.to_csv('career_analysis.csv', index=False)
        print(f"\n💾 Karriere analyse gemt: career_analysis.csv")
        
        print(f"\n✅ SÆSON-BASERET ANALYSE KOMPLET!")
        print(f"📁 Genererede filer:")
        for season in all_results.keys():
            filename = f'seasonal_elo_{season.replace("-", "_")}.csv'
            print(f"  • {filename}")
        print(f"  • career_analysis.csv")


# === MAIN EXECUTION ===
if __name__ == "__main__":
    print("🏐 STARTER SÆSON-BASERET HÅNDBOL ELO ANALYSE")
    print("=" * 60)
    
    # Initialiser systemet
    seasonal_system = SeasonalHandballEloSystem()
    
    # Kør komplet analyse
    seasonal_system.run_complete_seasonal_analysis()
    
    print("\n🎉 SÆSON-BASERET ANALYSE KOMPLET!")
    print("=" * 60)
    print("📊 Features implementeret:")
    print("  ✅ Sæson-for-sæson ELO processering")
    print("  ✅ Intelligent regression to mean mellem sæsoner")
    print("  ✅ Progressiv regression baseret på rating distance")
    print("  ✅ Games-baseret carry-over faktorer")
    print("  ✅ Per-sæson CSV output filer")
    print("  ✅ Position balance analyse per sæson")
    print("  ✅ Karriere analyse på tværs af sæsoner")
    print("  ✅ Elite status tracking")
    print("  ✅ Målvogter identification")
    print("\n🏆 REGRESSION TO MEAN SIKRER FAIR COMPETITION!") 