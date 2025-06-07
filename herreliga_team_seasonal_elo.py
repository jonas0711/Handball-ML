#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 HERRELIGA TEAM SÆSON-BASERET ELO SYSTEM (AVANCERET)
=====================================================

FOKUSERER KUN PÅ HERRELIGA HOLD MED:
✅ Kun Herreliga team data
✅ Hold-baseret ELO rating system
✅ Sæson-for-sæson processering med intelligent regression
✅ Hjemmebane fordel
✅ AVANCERET PERFORMANCE FAKTOR: Bruger detaljerede kampdata (effektivitet, turnovers)
✅ Karriere analyse på tværs af sæsoner

HERRELIGA HOLD KODER:
- AAH: Aalborg Håndbold
- BSH: Bjerringbro-Silkeborg
- FHK: Fredericia Håndbold Klub
- GIF: Grindsted GIF Håndbold
- GOG: GOG
- KIF: KIF Kolding
- MTH: Mors-Thy Håndbold
- NSH: Nordsjælland Håndbold
- REH: Ribe-Esbjerg HH
- SAH: SAH - Skanderborg AGF
- SKH: Skjern Håndbold
- SJE: SønderjyskE Herrehåndbold
- TTH: TTH Holstebro

Jonas' Custom System - December 2024 (Opgraderet Version)
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

# Import specific Herreliga mappings
from team_config import HERRELIGA_TEAMS, HERRELIGA_NAME_MAPPINGS

# === FORBEDRET HERRELIGA TEAM SYSTEM PARAMETRE ===
BASE_TEAM_RATING = 1400           # Base rating for teams (højere end spillere)
HOME_ADVANTAGE = 65               # REDUCERET fra 75 for at give performance factor mere vægt
MIN_GAMES_FOR_FULL_CARRY = 8
MAX_CARRY_BONUS = 400
MIN_CARRY_PENALTY = -300
REGRESSION_STRENGTH = 0.25

# ØGEDE K-faktorer for større ændringer per kamp
K_FACTORS = {
    'new_team': 70,      # ØGET fra 40
    'normal': 45,        # ØGET fra 25
    'elite': 30          # ØGET fra 15
}

class HerreligaTeamSeasonalEloSystem:
    """
    🏆 HERRELIGA TEAM SÆSON-BASERET ELO SYSTEM (AVANCERET)
    """
    
    def __init__(self, base_dir: str = "."):
        print("🏆 HERRELIGA TEAM SÆSON-BASERET ELO SYSTEM (AVANCERET)")
        print("=" * 70)
        
        self.base_dir = base_dir
        self.herreliga_dir = os.path.join(base_dir, "Herreliga-database")
        
        # Team data storage
        self.all_season_results = {}
        self.team_career_data = defaultdict(list)
        
        # Available seasons
        self.seasons = [
            "2017-2018", "2018-2019", "2019-2020", "2020-2021",
            "2021-2022", "2022-2023", "2023-2024", "2024-2025", "2025-2026"
        ]
        
        # Validate seasons
        self.validate_herreliga_seasons()
        
        print("✅ Herreliga Team ELO system initialiseret")
        print(f"📅 Tilgængelige sæsoner: {len(self.seasons)}")
        print(f"🎯 Base team rating: {BASE_TEAM_RATING}")
        print(f"🏠 Hjemmebane fordel: {HOME_ADVANTAGE}")
        print("⚡️ Bruger avanceret performance factor baseret på kamp-events")
        
    def validate_herreliga_seasons(self):
        """Validerer Herreliga sæsoner"""
        print(f"\n🔍 VALIDERER HERRELIGA SÆSONER")
        print("-" * 50)
        
        valid_seasons = []
        
        for season in self.seasons:
            season_path = os.path.join(self.herreliga_dir, season)
            
            if os.path.exists(season_path):
                db_files = [f for f in os.listdir(season_path) if f.endswith('.db')]
                if db_files:
                    valid_seasons.append(season)
                    print(f"  ✅ {season}: {len(db_files)} kampe")
                else:
                    print(f"  ❌ {season}: ingen database filer")
            else:
                print(f"  ❌ {season}: directory findes ikke")
                
        self.seasons = valid_seasons
        print(f"\n📊 {len(self.seasons)} gyldige Herreliga sæsoner")
        
    def get_team_code_from_name(self, team_name: str) -> str:
        """
        REFACTORED: Uses the dedicated HERRELIGA_NAME_MAPPINGS for accuracy.
        """
        if not team_name:
            return "UNK"

        clean_name = team_name.strip().lower()
        
        # Direct lookup in the Herreliga-specific mapping
        if clean_name in HERRELIGA_NAME_MAPPINGS:
            return HERRELIGA_NAME_MAPPINGS[clean_name]

        # Fallback search through keys (less reliable, but a good backup)
        for key, code in HERRELIGA_NAME_MAPPINGS.items():
            if key in clean_name:
                return code
    
        # print(f"⚠️ UNMAPPED HERRELIGA TEAM: '{team_name}'") # Reduced verbosity
        return "UNK"
        
    def calculate_expected_score(self, team_a_rating: float, team_b_rating: float, 
                               is_home: bool = False) -> float:
        """Beregner forventet score for team A mod team B"""
        rating_diff = team_a_rating - team_b_rating
        
        # Tilføj hjemmebane fordel
        if is_home:
            rating_diff += HOME_ADVANTAGE
            
        expected = 1 / (1 + 10**(-rating_diff / 400))
        return expected
        
    def get_k_factor(self, team_rating: float, games_played: int) -> int:
        """Beregner K-faktor baseret på team rating og erfaring"""
        if games_played < 10:
            return K_FACTORS['new_team']
        elif team_rating >= 1600:
            return K_FACTORS['elite']
        else:
            return K_FACTORS['normal']
            
    def calculate_performance_factor(self, goal_diff: int, efficiency_diff: int) -> float:
        """
        🚀 AVANCERET PERFORMANCE FAKTOR
        Kombinerer målforskel med et holds 'efficiency' (turnovers vs. forced turnovers etc.)
        """
        abs_goal_diff = abs(goal_diff)
        
        # Trin 1: Grundfaktor baseret på målforskel (lidt reduceret for at give plads til efficiency)
        if abs_goal_diff == 1:   base_factor = 1.8
        elif abs_goal_diff <= 3: base_factor = 2.2
        elif abs_goal_diff <= 6: base_factor = 3.0
        elif abs_goal_diff <= 10: base_factor = 4.0
        else: base_factor = 5.0
            
        # Trin 2: Justering baseret på effektivitetsforskel
        # En positiv efficiency_diff betyder, at det vindende hold var mere effektivt.
        # Vi normaliserer det, så det giver en fornuftig justering.
        efficiency_adjustment = efficiency_diff * 0.08  # Hver 'netto-effektiv' hændelse justerer med 0.08
        
        # Trin 3: Kombiner og cap justeringen
        # Begræns justeringen for at undgå ekstreme resultater fra en enkelt kamp
        capped_adjustment = max(-1.5, min(1.5, efficiency_adjustment))
        
        final_factor = base_factor + capped_adjustment
        
        return max(0.5, final_factor) # Sørg for at faktoren altid er positiv

    def process_herreliga_season(self, season: str, team_ratings: Dict = None) -> Dict:
        """Processerer en Herreliga sæson og returnerer team resultater"""
        print(f"\n🏐 PROCESSERER HERRELIGA SÆSON {season}")
        print("-" * 50)
        
        if team_ratings is None:
            team_ratings = {}
            
        # Initialize team data for the season
        team_stats = defaultdict(lambda: {
            'games': 0, 'momentum': [], 'goals_for': 0, 'goals_against': 0, 'efficiency_scores': []
        })

        season_path = os.path.join(self.herreliga_dir, season)
        
        if not os.path.exists(season_path):
            print(f"❌ Ingen data for {season}")
            return {}
            
        db_files = sorted([f for f in os.listdir(season_path) if f.endswith('.db')])
        
        matches_processed = 0
        
        for db_file in db_files:
            db_path = os.path.join(season_path, db_file)
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM match_info LIMIT 1")
                match_info = cursor.fetchone()
                
                if not match_info:
                    conn.close()
                    continue
                    
                _, hold_hjemme_navn, hold_ude_navn, resultat, _, _, _, _ = match_info
                
                if not (resultat and '-' in resultat):
                    conn.close()
                    continue

                hjemme_maal, ude_maal = map(int, resultat.split('-'))
                hjemme_code = self.get_team_code_from_name(hold_hjemme_navn)
                ude_code = self.get_team_code_from_name(hold_ude_navn)
                
                if hjemme_code == "UNK" or ude_code == "UNK":
                    conn.close()
                    continue

                # Initialize ratings if not present
                for code in [hjemme_code, ude_code]:
                    if code not in team_ratings:
                        team_ratings[code] = BASE_TEAM_RATING
                
                # --- AVANCERET STATISTIK INDSAMLING ---
                hjemme_events = {'goals': hjemme_maal, 'turnovers': 0, 'forced_turnovers': 0, 'saves': 0, 'assists': 0}
                ude_events = {'goals': ude_maal, 'turnovers': 0, 'forced_turnovers': 0, 'saves': 0, 'assists': 0}

                cursor.execute("SELECT hold, haendelse_1, haendelse_2, mv FROM match_events")
                events = cursor.fetchall()
                
                for event_hold, h1, h2, mv_navn in events:
                    event_team_code = self.get_team_code_from_name(event_hold)
                    
                    # Positive defensive actions
                    if h1 == 'Skud reddet' and mv_navn:
                        if event_team_code == hjemme_code: ude_events['saves'] += 1
                        else: hjemme_events['saves'] += 1
                    if h2 == 'Bold erobret':
                        if event_team_code == hjemme_code: ude_events['forced_turnovers'] += 1
                        else: hjemme_events['forced_turnovers'] += 1

                    # Negative offensive actions
                    if h1 in ['Fejlaflevering', 'Regelfejl', 'Tabt bold', 'Passivt spil']:
                        if event_team_code == hjemme_code: hjemme_events['turnovers'] += 1
                        elif event_team_code == ude_code: ude_events['turnovers'] += 1
                    
                    # Positive offensive actions
                    if h2 == 'Assist':
                        if event_team_code == hjemme_code: hjemme_events['assists'] += 1
                        elif event_team_code == ude_code: ude_events['assists'] += 1

                # Calculate efficiency scores
                hjemme_efficiency = (hjemme_events['forced_turnovers'] + hjemme_events['saves'] + hjemme_events['assists']) - hjemme_events['turnovers']
                ude_efficiency = (ude_events['forced_turnovers'] + ude_events['saves'] + ude_events['assists']) - ude_events['turnovers']
                
                # --- ELO BEREGNING ---
                goal_diff = hjemme_maal - ude_maal
                if goal_diff > 0:
                    hjemme_score, ude_score = 1.0, 0.0
                    efficiency_diff = hjemme_efficiency - ude_efficiency
                elif goal_diff < 0:
                    hjemme_score, ude_score = 0.0, 1.0
                    efficiency_diff = ude_efficiency - hjemme_efficiency
                else:
                    hjemme_score, ude_score = 0.5, 0.5
                    efficiency_diff = 0

                hjemme_expected = self.calculate_expected_score(team_ratings[hjemme_code], team_ratings[ude_code], is_home=True)
                ude_expected = 1 - hjemme_expected
                
                performance_factor = self.calculate_performance_factor(goal_diff, efficiency_diff)
                
                hjemme_k = self.get_k_factor(team_ratings[hjemme_code], team_stats[hjemme_code]['games'])
                ude_k = self.get_k_factor(team_ratings[ude_code], team_stats[ude_code]['games'])
                
                AMPLIFICATION_FACTOR = 1.5
                hjemme_change = hjemme_k * performance_factor * (hjemme_score - hjemme_expected) * AMPLIFICATION_FACTOR
                ude_change = ude_k * performance_factor * (ude_score - ude_expected) * AMPLIFICATION_FACTOR
                
                team_ratings[hjemme_code] += hjemme_change
                team_ratings[ude_code] += ude_change
                
                # Update seasonal team stats
                for code, change, goals_f, goals_a, eff in [
                    (hjemme_code, hjemme_change, hjemme_maal, ude_maal, hjemme_efficiency),
                    (ude_code, ude_change, ude_maal, hjemme_maal, ude_efficiency)
                ]:
                    team_stats[code]['games'] += 1
                    team_stats[code]['momentum'].append(change)
                    if len(team_stats[code]['momentum']) > 5:
                        team_stats[code]['momentum'].pop(0)
                    team_stats[code]['goals_for'] += goals_f
                    team_stats[code]['goals_against'] += goals_a
                    team_stats[code]['efficiency_scores'].append(eff)

                matches_processed += 1
                conn.close()
                
            except Exception as e:
                print(f"  ❌ Fejl i {db_file}: {e}")
                
        print(f"✅ {matches_processed} Herreliga kampe processeret")
        
        # Generate final season results dictionary
        season_results = {}
        for team_code in team_ratings:
            stats = team_stats.get(team_code)
            if stats and stats['games'] > 0:
                team_name = HERRELIGA_TEAMS.get(team_code, team_code)
                rating = team_ratings[team_code]
                
                # FORBEDRET ELITE STATUS: Mere præcist hierarki
                if rating >= 1750: elite_status = "ELITE"
                elif rating >= 1600: elite_status = "STRONG"
                else: elite_status = "NORMAL"

                season_results[team_code] = {
                    'season': season,
                    'team_code': team_code,
                    'team_name': team_name,
                    'final_rating': round(rating, 1),
                    'games': stats['games'],
                    'elite_status': elite_status,
                    'momentum': round(np.mean(stats['momentum']), 2) if stats['momentum'] else 0,
                    'avg_goals_for': round(stats['goals_for'] / stats['games'], 1),
                    'avg_goals_against': round(stats['goals_against'] / stats['games'], 1),
                    'avg_efficiency_score': round(np.mean(stats['efficiency_scores']), 1)
                }
                
        return season_results
        
    def calculate_intelligent_team_start_rating(self, team_code: str,
                                              previous_season_data: Dict = None,
                                              league_avg: float = None) -> float:
        """🚀 DRAMATISK FORBEDRET start rating med MEGET mindre regression"""
        
        if not previous_season_data:
            return BASE_TEAM_RATING
            
        prev_rating = previous_season_data.get('final_rating', BASE_TEAM_RATING)
        prev_games = previous_season_data.get('games', 0)
        prev_elite_status = previous_season_data.get('elite_status', 'NORMAL')
        prev_momentum = previous_season_data.get('momentum', 0)
        
        if prev_rating == BASE_TEAM_RATING:
            return BASE_TEAM_RATING
            
        # Calculate regression target
        mean_rating = league_avg if league_avg else BASE_TEAM_RATING
        distance_from_mean = prev_rating - mean_rating
        
        # DRAMATISK FORBEDREDE FAKTORER - meget mindre regression
        
        # Games factor - øget carry-over
        if prev_games >= MIN_GAMES_FOR_FULL_CARRY:
            games_factor = 1.0  # Fuld carry-over
        elif prev_games >= 5:
            games_factor = 0.85 + 0.15 * (prev_games - 5) / 3  # ØGET fra 0.6 base
        else:
            games_factor = 0.70  # ØGET fra 0.4 - meget mindre straf for få kampe
            
        # Elite status factor - elite hold beholder mere (Tilpasset nye niveauer)
        if prev_elite_status == 'ELITE':
            elite_factor = 0.90  # ØGET fra 0.85 - elite beholder endnu mere
        elif prev_elite_status == 'STRONG':
            elite_factor = 0.95  # ØGET fra 0.90
        else:
            elite_factor = 1.0   # ØGET fra 0.95 - normale hold mister næsten intet ift. status
            
        # Momentum factor (NY!) - hold med godt momentum beholder mere
        if prev_momentum > 5:
            momentum_factor = 1.10  # Bonus for godt momentum
        elif prev_momentum > 0:
            momentum_factor = 1.05  # Lille bonus for positivt momentum
        elif prev_momentum > -5:
            momentum_factor = 1.0   # Neutralt
        else:
            momentum_factor = 0.95  # Lille straf for dårligt momentum
            
        # Distance factor - DRAMATISK reduceret regression
        abs_distance = abs(distance_from_mean)
        if abs_distance > 400:
            distance_factor = 0.75  # ØGET fra 0.45 - meget mindre regression!
        elif abs_distance > 300:
            distance_factor = 0.85  # ØGET fra 0.60
        elif abs_distance > 200:
            distance_factor = 0.90  # ØGET fra 0.75
        elif abs_distance > 100:
            distance_factor = 0.95  # ØGET fra 0.90
        else:
            distance_factor = 0.98  # ØGET fra 0.90 - næsten ingen regression for små afstande
            
        # PERFORMANCE BONUS (NY!) - belønner stærk performance
        if distance_from_mean > 200 and prev_games >= MIN_GAMES_FOR_FULL_CARRY:
            performance_bonus = min(100, distance_from_mean * 0.15)  # Op til 100 bonus points
        else:
            performance_bonus = 0
            
        # Combine factors
        combined_factor = games_factor * elite_factor * distance_factor * momentum_factor
        
        # Calculate new rating
        regressed_distance = distance_from_mean * combined_factor
        new_start_rating = mean_rating + regressed_distance + performance_bonus
        
        # Apply caps med større spredning
        rating_change = new_start_rating - BASE_TEAM_RATING
        if rating_change > MAX_CARRY_BONUS:
            new_start_rating = BASE_TEAM_RATING + MAX_CARRY_BONUS
        elif rating_change < MIN_CARRY_PENALTY:
            new_start_rating = BASE_TEAM_RATING + MIN_CARRY_PENALTY
            
        # Debug output for store ændringer
        total_change = new_start_rating - prev_rating
        if abs(total_change) > 30:  # Vis kun betydelige ændringer
            print(f"    🔄 {team_code}: {prev_rating:.0f} → {new_start_rating:.0f} "
                  f"({total_change:+.0f}) [Games:{prev_games}, Status:{prev_elite_status}]")
            
        return round(new_start_rating, 1)
        
    def save_herreliga_season_csv(self, season_results: Dict, season: str):
        """Gemmer Herreliga sæson resultater til ELO_Results/Team_CSV"""
        if not season_results:
            return
            
        df = pd.DataFrame(list(season_results.values()))
        df = df.sort_values('final_rating', ascending=False)
        
        # Ensure ELO_Results/Team_CSV/Herreliga directory exists
        output_dir = os.path.join("ELO_Results", "Team_CSV", "Herreliga")
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f'herreliga_team_seasonal_elo_{season.replace("-", "_")}.csv'
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False)
        
        print(f"💾 Gemt: {filepath} ({len(df)} hold)")
        
        # Show top teams
        print(f"\n🏆 TOP HERRELIGA HOLD {season}:")
        for i, (_, row) in enumerate(df.head(10).iterrows(), 1):
            elite_badge = f"[{row['elite_status']}]" if row['elite_status'] != 'NORMAL' else ""
            print(f"  {i:2d}. {row['team_name']:<25} Rating: {row['final_rating']:.0f} "
                  f"(Eff: {row['avg_efficiency_score']:+.1f}) {elite_badge}")
                  
    def run_complete_herreliga_team_analysis(self):
        """Hovedfunktion - kører komplet analyse"""
        print("\n🚀 STARTER KOMPLET HERRELIGA TEAM ANALYSE (AVANCERET)")
        print("=" * 70)
        
        previous_season_data = None
        
        for season in self.seasons:
            print(f"\n📅 === HERRELIGA SÆSON {season} ===")
            
            # Calculate start ratings
            start_ratings = {}
            
            if previous_season_data:
                print(f"📈 Beregner start ratings fra {len(previous_season_data)} hold")
                
                prev_ratings = [data['final_rating'] for data in previous_season_data.values()]
                league_avg = np.mean(prev_ratings) if prev_ratings else BASE_TEAM_RATING
                
                print(f"📊 Forrige sæson gennemsnit: {league_avg:.1f}")
                
                for team_code, team_data in previous_season_data.items():
                    start_rating = self.calculate_intelligent_team_start_rating(
                        team_code, team_data, league_avg
                    )
                    start_ratings[team_code] = start_rating
                    
            # Process season
            season_results = self.process_herreliga_season(season, start_ratings)
            
            if not season_results:
                print(f"⚠️ Springer over {season} - ingen resultater")
                continue
                
            # Update career data
            for team_code, team_data in season_results.items():
                if 'start_rating' not in team_data:
                    team_data['start_rating'] = start_ratings.get(team_code, BASE_TEAM_RATING)
                team_data['rating_change'] = team_data['final_rating'] - team_data['start_rating']
                
                self.team_career_data[team_code].append(team_data) # Gem hele dict
                
            # Store and save
            self.all_season_results[season] = season_results
            self.save_herreliga_season_csv(season_results, season)
            
            previous_season_data = season_results
            
        # Generate final analyses
        self.generate_herreliga_career_analysis()
        self.generate_herreliga_summary_report()
        
    def generate_herreliga_career_analysis(self):
        """Genererer karriere analyse for Herreliga hold"""
        print(f"\n🏆 HERRELIGA HOLD KARRIERE ANALYSE")
        print("=" * 70)
        
        career_teams = []
        
        for team_code, seasons_data in self.team_career_data.items():
            if len(seasons_data) >= 3:
                team_name = HERRELIGA_TEAMS.get(team_code, team_code)
                ratings = [s['final_rating'] for s in seasons_data]
                
                career_stats = {
                    'team_code': team_code,
                    'team_name': team_name,
                    'seasons_played': len(seasons_data),
                    'avg_rating': round(np.mean(ratings), 1),
                    'peak_rating': round(max(ratings), 1),
                    'peak_season': seasons_data[np.argmax(ratings)]['season'],
                    'total_games': sum(s['games'] for s in seasons_data),
                    'career_change': round(ratings[-1] - ratings[0], 1),
                    'consistency_std': round(np.std(ratings), 1)
                }
                
                career_teams.append(career_stats)
                
        if not career_teams:
            print("📊 Ingen hold med nok data til karriere analyse (min. 3 sæsoner).")
            return

        career_teams.sort(key=lambda x: x['avg_rating'], reverse=True)
        
        print(f"📊 {len(career_teams)} Herreliga hold med karriere data (≥3 sæsoner)")
        
        print(f"\n🏆 TOP HERRELIGA HOLD (KARRIERE):")
        for i, team in enumerate(career_teams, 1):
            trend = "📈" if team['career_change'] > 50 else "📉" if team['career_change'] < -50 else "➡️"
            
            print(f"  {i:2d}. {team['team_name']:<25} Avg Rating: {team['avg_rating']:.0f}, "
                  f"Peak: {team['peak_rating']:.0f} ({team['peak_season']}) "
                  f"{trend}{team['career_change']:+.0f}")
                  
        # Save career analysis to ELO_Results/Team_CSV/Herreliga
        career_df = pd.DataFrame(career_teams)
        output_dir = os.path.join("ELO_Results", "Team_CSV", "Herreliga")
        os.makedirs(output_dir, exist_ok=True)
        career_filepath = os.path.join(output_dir, 'herreliga_team_career_analysis.csv')
        career_df.to_csv(career_filepath, index=False)
        print(f"\n💾 Herreliga karriere analyse gemt: {career_filepath}")
        
    def generate_herreliga_summary_report(self):
        """Genererer samlet rapport"""
        print(f"\n📊 HERRELIGA SAMLET RAPPORT")
        print("=" * 70)
        
        total_teams = set()
        total_matches = 0
        season_summary = []
        
        if not self.all_season_results:
            print("Ingen sæsonresultater at rapportere.")
            return

        for season, results in self.all_season_results.items():
            total_teams.update(results.keys())
            season_matches = sum(team['games'] for team in results.values()) // 2
            
            if not results: continue

            ratings = [team['final_rating'] for team in results.values()]
            elite_count = sum(1 for r in ratings if r >= 1750) # Opdateret til ny ELITE grænse
            strong_count = sum(1 for r in ratings if 1600 <= r < 1750) # Tæl STRONG hold
            
            season_summary.append({
                'season': season,
                'teams': len(results),
                'total_matches': season_matches,
                'avg_rating': round(np.mean(ratings), 1),
                'elite_teams': elite_count,
                'strong_teams': strong_count, # Tilføj strong count
                'max_rating': round(max(ratings), 1),
                'top_team': results[max(results, key=lambda t: results[t]['final_rating'])]['team_name']
            })
            
            total_matches += season_matches
            
        print(f"🏐 HERRELIGA SAMLET STATISTIK:")
        print(f"  📊 Total unikke hold: {len(total_teams)}")
        print(f"  🏟️ Total kampe: {total_matches:,}")
        print(f"  📅 Sæsoner: {len(self.all_season_results)}")
        
        print(f"\n📅 SÆSON OVERSIGT:")
        for s in season_summary:
            print(f"  {s['season']}: {s['teams']} hold, {s['total_matches']} kampe, "
                  f"avg {s['avg_rating']:.0f} (Elite: {s['elite_teams']}, Strong: {s['strong_teams']}), Top: {s['top_team']} ({s['max_rating']:.0f})")
                  
        # Save summary to ELO_Results/Team_CSV/Herreliga
        summary_df = pd.DataFrame(season_summary)
        output_dir = os.path.join("ELO_Results", "Team_CSV", "Herreliga")
        os.makedirs(output_dir, exist_ok=True)
        summary_filepath = os.path.join(output_dir, 'herreliga_team_seasonal_summary_report.csv')
        summary_df.to_csv(summary_filepath, index=False)
        print(f"\n💾 Herreliga rapport gemt: {summary_filepath}")


# === MAIN EXECUTION ===
if __name__ == "__main__":
    print("🏆 STARTER HERRELIGA TEAM SÆSON-BASERET ELO SYSTEM (AVANCERET)")
    print("=" * 80)
    
    # Create system instance
    herreliga_team_system = HerreligaTeamSeasonalEloSystem()
    
    # Run complete analysis
    herreliga_team_system.run_complete_herreliga_team_analysis()
    
    print("\n🎉 HERRELIGA TEAM SYSTEM KOMPLET!")
    print("=" * 80)
    print("🎯 Herreliga Team Features:")
    print("  ✅ Kun Herreliga hold data")
    print("  ✅ Intelligent regression to mean")
    print("  ✅ Hjemmebane fordel")
    print("  ✅ AVANCERET Performance Factor (målforskel + effektivitet)")
    print("  ✅ Karriere analyse på tværs af sæsoner")
    print("  ✅ Detaljerede CSV filer med udvidede statistikker")
    print("\n🏆 HERRELIGA TEAM ELO KOMPLET!") 