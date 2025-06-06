#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 KVINDELIGA TEAM SÆSON-BASERET ELO SYSTEM
==========================================

FOKUSERER KUN PÅ KVINDELIGA HOLD MED:
✅ Kun Kvindeliga team data
✅ Hold-baseret ELO rating system
✅ Sæson-for-sæson processering med intelligent regression
✅ Hjemmebane fordel
✅ Målforskels påvirkning
✅ Team momentum tracking
✅ Karriere analyse på tværs af sæsoner

KVINDELIGA HOLD KODER:
- AHB: Aarhus Håndbold Kvinder
- BFH: Bjerringbro FH
- EHA: EH Aalborg
- HHE: Horsens Håndbold Elite
- IKA: Ikast Håndbold
- KBH: København Håndbold
- NFH: Nykøbing F. Håndbold
- ODE: Odense Håndbold
- RIN: Ringkøbing Håndbold
- SVK: Silkeborg-Voel KFUM
- SKB: Skanderborg Håndbold
- SJE: SønderjyskE Kvindehåndbold
- TES: Team Esbjerg
- VHK: Viborg HK
- TMS: TMS Ringsted

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

# === FORBEDRET KVINDELIGA TEAM SYSTEM PARAMETRE ===
BASE_TEAM_RATING = 1400           # Base rating for teams (højere end spillere)
HOME_ADVANTAGE = 75               # Hjemmebane fordel i ELO points
MIN_GAMES_FOR_FULL_CARRY = 8      # REDUCERET fra 10 - flere hold får carry-over
MAX_CARRY_BONUS = 400             # ØGET DRAMATISK fra 200 til 400
MIN_CARRY_PENALTY = -300          # ØGET DRAMATISK fra -150 til -300
REGRESSION_STRENGTH = 0.25        # DRAMATISK REDUCERET fra 0.60 til 0.25 - meget mindre regression!

# DRAMATISK ØGEDE K-faktorer for større ændringer per kamp
K_FACTORS = {
    'new_team': 80,      # ØGET fra 40 - nye hold kan ændre sig hurtigt
    'normal': 50,        # ØGET fra 25 - normale hold får større ændringer
    'elite': 35          # ØGET fra 15 - selv elite hold kan ændre sig betydeligt
}

# Kvindeliga team koder og navne
KVINDELIGA_TEAMS = {
    'AHB': 'Aarhus Håndbold Kvinder',
    'BFH': 'Bjerringbro FH',
    'EHA': 'EH Aalborg',
    'HHE': 'Horsens Håndbold Elite',
    'IKA': 'Ikast Håndbold',
    'KBH': 'København Håndbold',
    'NFH': 'Nykøbing F. Håndbold',
    'ODE': 'Odense Håndbold',
    'RIN': 'Ringkøbing Håndbold',
    'SVK': 'Silkeborg-Voel KFUM',
    'SKB': 'Skanderborg Håndbold',
    'SJE': 'SønderjyskE Kvindehåndbold',
    'TES': 'Team Esbjerg',
    'VHK': 'Viborg HK',
    'TMS': 'TMS Ringsted',
    # EKSTRA TEAMS FUNDET I DATA
    'VEN': 'Vendsyssel Håndbold',
    'RAN': 'Randers HK',
    'HOL': 'Holstebro Håndbold',
    'AJA': 'Ajax København'  # Separat hold - ikke tilknyttet København Håndbold
}

# FORBEDRET TEAM MAPPING SYSTEM - håndterer navnevariationer på tværs af sæsoner
TEAM_NAME_MAPPINGS = {
    # Aarhus variationer (KRITISK)
    'aarhus united': 'AHB',
    'aarhus håndbold kvinder': 'AHB',
    'aarhus håndbold': 'AHB',
    'aarhus': 'AHB',
    
    # Bjerringbro FH
    'bjerringbro fh': 'BFH',
    'bjerringbro': 'BFH',
    
    # EH Aalborg
    'eh aalborg': 'EHA',
    'eh aalborg kvinder': 'EHA',
    
    # Horsens Håndbold Elite
    'horsens håndbold elite': 'HHE',
    'horsens': 'HHE',
    
    # Ikast Håndbold
    'ikast håndbold': 'IKA',
    'ikast': 'IKA',
    
    # København variationer (KRITISK)
    'ajax københavn': 'AJA',  # Ajax København (EGET SELVSTÆNDIGT HOLD siden 1934)
    'københavn håndbold': 'KBH',
    'fc københavn': 'KBH',
    'københavn': 'KBH',
    
    # Nykøbing F. variationer (KRITISK)
    'nykøbing f. håndbold': 'NFH',
    'nykøbing f. håndboldklub': 'NFH',
    'nykøbing f.': 'NFH',
    'nykøbing': 'NFH',
    
    # Odense Håndbold
    'odense håndbold': 'ODE',
    'odense': 'ODE',
    
    # Ringkøbing Håndbold
    'ringkøbing håndbold': 'RIN',
    'ringkøbing': 'RIN',
    
    # Silkeborg-Voel KFUM variationer (KRITISK)
    'silkeborg-voel kfum': 'SVK',
    'voel kfum': 'SVK',
    'silkeborg voel': 'SVK',
    'voel': 'SVK',
    
    # Skanderborg Håndbold
    'skanderborg håndbold': 'SKB',
    'skanderborg': 'SKB',
    
    # SønderjyskE variationer (KRITISK)
    'sønderjyske': 'SJE',
    'sønderjyske kvindehåndbold': 'SJE',
    'sønderjyske kvinder': 'SJE',
    'sønderjyske håndbold': 'SJE',
    
    # Team Esbjerg
    'team esbjerg': 'TES',
    'esbjerg': 'TES',
    
    # Viborg HK
    'viborg hk': 'VHK',
    'viborg': 'VHK',
    
    # TMS Ringsted
    'tms ringsted': 'TMS',
    'tms': 'TMS',
    'ringsted': 'TMS',
    
    # EKSTRA MAPPINGS BASERET PÅ UNMAPPED TEAMS  
    # Vendsyssel Håndbold
    'vendsyssel håndbold': 'VEN',
    'vendsyssel': 'VEN',
    
    # Randers HK
    'randers hk': 'RAN',
    'randers': 'RAN',
    
    # Holstebro Håndbold
    'holstebro håndbold': 'HOL',
    'holstebro': 'HOL',
    
    # FC Midtjylland (2017-2018) - BLEV TIL IKAST HÅNDBOLD
    'fc midtjylland': 'IKA',  # FC Midtjylland var forgænger til nuværende Ikast Håndbold
    'midtjylland': 'IKA'
}

class KvindeligaTeamSeasonalEloSystem:
    """
    🏆 KVINDELIGA TEAM SÆSON-BASERET ELO SYSTEM
    """
    
    def __init__(self, base_dir: str = "."):
        print("🏆 KVINDELIGA TEAM SÆSON-BASERET ELO SYSTEM")
        print("=" * 70)
        
        self.base_dir = base_dir
        self.kvindeliga_dir = os.path.join(base_dir, "Kvindeliga-database")
        
        # Team data storage
        self.all_season_results = {}
        self.team_career_data = defaultdict(list)
        
        # Available seasons (UDVIDET til at inkludere alle sæsoner)
        self.seasons = [
            "2017-2018", "2018-2019", "2019-2020", "2020-2021",
            "2021-2022", "2022-2023", "2023-2024", "2024-2025", "2025-2026"
        ]
        
        # Validate seasons
        self.validate_kvindeliga_seasons()
        
        print("✅ Kvindeliga Team ELO system initialiseret")
        print(f"📅 Tilgængelige sæsoner: {len(self.seasons)}")
        print(f"🎯 Base team rating: {BASE_TEAM_RATING}")
        print(f"🏠 Hjemmebane fordel: {HOME_ADVANTAGE}")
        
    def validate_kvindeliga_seasons(self):
        """Validerer Kvindeliga sæsoner"""
        print(f"\n🔍 VALIDERER KVINDELIGA SÆSONER")
        print("-" * 50)
        
        valid_seasons = []
        
        for season in self.seasons:
            season_path = os.path.join(self.kvindeliga_dir, season)
            
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
        print(f"\n📊 {len(self.seasons)} gyldige Kvindeliga sæsoner")
        
    def get_team_code_from_name(self, team_name: str) -> str:
        """
        FORBEDRET TEAM CODE FINDER - håndterer navnevariationer på tværs af sæsoner
        """
        if not team_name:
            return "UNK"
            
        team_name_lower = team_name.lower().strip()
        
        # First try exact mapping
        if team_name_lower in TEAM_NAME_MAPPINGS:
            return TEAM_NAME_MAPPINGS[team_name_lower]
            
        # Then try partial matching
        for mapping_name, code in TEAM_NAME_MAPPINGS.items():
            if mapping_name in team_name_lower or team_name_lower in mapping_name:
                return code
                
        # Legacy fallback - try original method
        for code, name in KVINDELIGA_TEAMS.items():
            if name.lower() in team_name_lower or team_name_lower in name.lower():
                return code
                
        # Final fallback
        print(f"⚠️ UNMAPPED KVINDELIGA TEAM: '{team_name}'")
        return team_name[:3].upper()
        
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
            
    def calculate_goal_difference_factor(self, goal_diff: int) -> float:
        """🚀 DRAMATISK FORBEDRET multiplikator for at skabe større rating ændringer"""
        abs_diff = abs(goal_diff)
        
        # DRAMATISK ØGEDE FAKTORER for at give større ændringer
        if abs_diff == 1:
            return 2.0    # ØGET fra 1.0 - selv tætte kampe skal give betydelig ændring
        elif abs_diff <= 2:
            return 2.5    # ØGET fra 1.1
        elif abs_diff <= 5:
            return 3.5    # ØGET fra 1.3
        elif abs_diff <= 10:
            return 5.0    # ØGET fra 1.6
        elif abs_diff <= 15:
            return 7.0    # ØGET fra 1.8
        else:
            return 10.0   # ØGET fra 2.0 - store sejre skal give massive ændringer!
            
    def process_kvindeliga_season(self, season: str, team_ratings: Dict = None) -> Dict:
        """Processerer en Kvindeliga sæson og returnerer team resultater"""
        print(f"\n🏐 PROCESSERER KVINDELIGA SÆSON {season}")
        print("-" * 50)
        
        if team_ratings is None:
            team_ratings = {}
            
        # Initialize team data
        team_games = defaultdict(int)
        team_momentum = defaultdict(list)  # Last 5 matches
        
        season_path = os.path.join(self.kvindeliga_dir, season)
        
        if not os.path.exists(season_path):
            print(f"❌ Ingen data for {season}")
            return {}
            
        db_files = [f for f in os.listdir(season_path) if f.endswith('.db')]
        
        if not db_files:
            print(f"❌ Ingen database filer for {season}")
            return {}
            
        matches_processed = 0
        
        for db_file in db_files:
            db_path = os.path.join(season_path, db_file)
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Get match info
                cursor.execute("SELECT * FROM match_info LIMIT 1")
                match_info = cursor.fetchone()
                
                if not match_info:
                    conn.close()
                    continue
                    
                # Parse match info
                kamp_id, hold_hjemme, hold_ude, resultat, halvleg_resultat, dato, sted, turnering = match_info
                
                # FJERNET TURNERING FILTRERING - accepter alle kampe i Kvindeliga-database mappen
                # Gamle navne varierer: "HTH GO Ligaen", "Kvindeligaen", osv.
                # Da vi allerede er i Kvindeliga-database mappen, er alle kampe relevante
                    
                # Parse result
                if resultat and '-' in resultat:
                    try:
                        hjemme_maal, ude_maal = map(int, resultat.split('-'))
                        
                        # Get team codes
                        hjemme_code = self.get_team_code_from_name(hold_hjemme)
                        ude_code = self.get_team_code_from_name(hold_ude)
                        
                        # Initialize ratings if not present
                        if hjemme_code not in team_ratings:
                            team_ratings[hjemme_code] = BASE_TEAM_RATING
                        if ude_code not in team_ratings:
                            team_ratings[ude_code] = BASE_TEAM_RATING
                            
                        # Calculate match result
                        if hjemme_maal > ude_maal:
                            hjemme_score, ude_score = 1.0, 0.0
                        elif hjemme_maal < ude_maal:
                            hjemme_score, ude_score = 0.0, 1.0
                        else:
                            hjemme_score, ude_score = 0.5, 0.5
                            
                        # Calculate expected scores
                        hjemme_expected = self.calculate_expected_score(
                            team_ratings[hjemme_code], team_ratings[ude_code], is_home=True
                        )
                        ude_expected = 1 - hjemme_expected
                        
                        # Calculate goal difference factor
                        goal_diff = abs(hjemme_maal - ude_maal)
                        goal_factor = self.calculate_goal_difference_factor(goal_diff)
                        
                        # Get K-factors
                        hjemme_k = self.get_k_factor(team_ratings[hjemme_code], team_games[hjemme_code])
                        ude_k = self.get_k_factor(team_ratings[ude_code], team_games[ude_code])
                        
                        # Update ratings with ADDITIONAL AMPLIFICATION FACTOR
                        AMPLIFICATION_FACTOR = 3.0  # 🚀 TREDOBLER alle rating ændringer!
                        
                        hjemme_change = hjemme_k * goal_factor * (hjemme_score - hjemme_expected) * AMPLIFICATION_FACTOR
                        ude_change = ude_k * goal_factor * (ude_score - ude_expected) * AMPLIFICATION_FACTOR
                        
                        team_ratings[hjemme_code] += hjemme_change
                        team_ratings[ude_code] += ude_change
                        
                        # Update game counts
                        team_games[hjemme_code] += 1
                        team_games[ude_code] += 1
                        
                        # Update momentum (last 5 matches)
                        team_momentum[hjemme_code].append(hjemme_change)
                        team_momentum[ude_code].append(ude_change)
                        
                        if len(team_momentum[hjemme_code]) > 5:
                            team_momentum[hjemme_code].pop(0)
                        if len(team_momentum[ude_code]) > 5:
                            team_momentum[ude_code].pop(0)
                            
                        matches_processed += 1
                        
                    except (ValueError, TypeError) as e:
                        print(f"  ⚠️ Kunne ikke parse resultat '{resultat}' for {db_file}: {e}")
                        
                conn.close()
                
            except Exception as e:
                print(f"  ❌ Fejl i {db_file}: {e}")
                
        print(f"✅ {matches_processed} Kvindeliga kampe processeret")
        
        # Generate season results
        season_results = {}
        
        for team_code in team_ratings:
            if team_games[team_code] > 0:  # Only teams that played
                team_name = KVINDELIGA_TEAMS.get(team_code, team_code)
                
                # Calculate momentum
                momentum_scores = team_momentum.get(team_code, [])
                avg_momentum = np.mean(momentum_scores) if momentum_scores else 0
                
                # Elite status
                rating = team_ratings[team_code]
                if rating >= 1700:
                    elite_status = "ELITE"
                elif rating >= 1600:
                    elite_status = "STRONG"
                else:
                    elite_status = "NORMAL"
                    
                season_results[team_code] = {
                    'season': season,
                    'team_code': team_code,
                    'team_name': team_name,
                    'final_rating': round(rating, 1),
                    'games': team_games[team_code],
                    'elite_status': elite_status,
                    'momentum': round(avg_momentum, 2)
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
            
        # Elite status factor - elite hold beholder mere
        if prev_elite_status == 'ELITE':
            elite_factor = 0.85  # ØGET fra 0.65 - elite beholder meget mere
        elif prev_elite_status == 'STRONG':
            elite_factor = 0.90  # ØGET fra 0.80
        else:
            elite_factor = 0.95  # ØGET fra 0.90 - normale hold mister næsten intet
            
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
        
    def save_kvindeliga_season_csv(self, season_results: Dict, season: str):
        """Gemmer Kvindeliga sæson resultater til ELO_Results/Team_CSV"""
        if not season_results:
            return
            
        df = pd.DataFrame(list(season_results.values()))
        df = df.sort_values('final_rating', ascending=False)
        
        # Ensure ELO_Results/Team_CSV/Kvindeliga directory exists
        output_dir = os.path.join("ELO_Results", "Team_CSV", "Kvindeliga")
        os.makedirs(output_dir, exist_ok=True)
        
        filename = f'kvindeliga_team_seasonal_elo_{season.replace("-", "_")}.csv'
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False)
        
        print(f"💾 Gemt: {filepath} ({len(df)} hold)")
        
        # Show top teams
        print(f"\n🏆 TOP KVINDELIGA HOLD {season}:")
        for i, (_, row) in enumerate(df.head(10).iterrows(), 1):
            elite_badge = f"[{row['elite_status']}]" if row['elite_status'] != 'NORMAL' else ""
            print(f"  {i:2d}. {row['team_name']}: {row['final_rating']:.0f} "
                  f"({row['games']} kampe) {elite_badge}")
                  
    def run_complete_kvindeliga_team_analysis(self):
        """Hovedfunktion - kører komplet analyse"""
        print("\n🚀 STARTER KOMPLET KVINDELIGA TEAM ANALYSE")
        print("=" * 70)
        
        previous_season_data = None
        
        for season in self.seasons:
            print(f"\n📅 === KVINDELIGA SÆSON {season} ===")
            
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
            season_results = self.process_kvindeliga_season(season, start_ratings)
            
            if not season_results:
                print(f"⚠️ Springer over {season} - ingen resultater")
                continue
                
            # Update career data
            for team_code, team_data in season_results.items():
                if 'start_rating' not in team_data:
                    team_data['start_rating'] = start_ratings.get(team_code, BASE_TEAM_RATING)
                team_data['rating_change'] = team_data['final_rating'] - team_data['start_rating']
                
                self.team_career_data[team_code].append({
                    'season': season,
                    'final_rating': team_data['final_rating'],
                    'games': team_data['games'],
                    'rating_change': team_data['rating_change']
                })
                
            # Store and save
            self.all_season_results[season] = season_results
            self.save_kvindeliga_season_csv(season_results, season)
            
            previous_season_data = season_results
            
        # Generate final analyses
        self.generate_kvindeliga_career_analysis()
        self.generate_kvindeliga_summary_report()
        
    def generate_kvindeliga_career_analysis(self):
        """Genererer karriere analyse for Kvindeliga hold"""
        print(f"\n🏆 KVINDELIGA HOLD KARRIERE ANALYSE")
        print("=" * 70)
        
        career_teams = []
        
        for team_code, seasons_data in self.team_career_data.items():
            if len(seasons_data) >= 3:
                team_name = KVINDELIGA_TEAMS.get(team_code, team_code)
                ratings = [s['final_rating'] for s in seasons_data]
                games = [s['games'] for s in seasons_data]
                
                career_stats = {
                    'team_code': team_code,
                    'team_name': team_name,
                    'seasons_played': len(seasons_data),
                    'avg_rating': round(np.mean(ratings), 1),
                    'peak_rating': round(max(ratings), 1),
                    'total_games': sum(games),
                    'career_change': round(ratings[-1] - ratings[0], 1),
                    'consistency': round(np.std(ratings), 1)
                }
                
                career_teams.append(career_stats)
                
        career_teams.sort(key=lambda x: x['avg_rating'], reverse=True)
        
        print(f"📊 {len(career_teams)} Kvindeliga hold med karriere data (≥3 sæsoner)")
        
        print(f"\n🏆 TOP KVINDELIGA HOLD (KARRIERE):")
        for i, team in enumerate(career_teams, 1):
            trend = "📈" if team['career_change'] > 50 else "📉" if team['career_change'] < -50 else "➡️"
            
            print(f"  {i:2d}. {team['team_name']}: {team['avg_rating']:.0f} avg, "
                  f"peak {team['peak_rating']:.0f} ({team['seasons_played']} sæsoner) "
                  f"{trend}{team['career_change']:+.0f}")
                  
        # Save career analysis to ELO_Results/Team_CSV/Kvindeliga
        career_df = pd.DataFrame(career_teams)
        output_dir = os.path.join("ELO_Results", "Team_CSV", "Kvindeliga")
        os.makedirs(output_dir, exist_ok=True)
        career_filepath = os.path.join(output_dir, 'kvindeliga_team_career_analysis.csv')
        career_df.to_csv(career_filepath, index=False)
        print(f"\n💾 Kvindeliga karriere analyse gemt: {career_filepath}")
        
    def generate_kvindeliga_summary_report(self):
        """Genererer samlet rapport"""
        print(f"\n📊 KVINDELIGA SAMLET RAPPORT")
        print("=" * 70)
        
        total_teams = set()
        total_matches = 0
        season_summary = []
        
        for season, results in self.all_season_results.items():
            total_teams.update(results.keys())
            season_matches = sum(team['games'] for team in results.values()) // 2  # Each match counted twice
            
            ratings = [team['final_rating'] for team in results.values()]
            elite_count = sum(1 for r in ratings if r >= 1600)
            
            season_summary.append({
                'season': season,
                'teams': len(results),
                'total_matches': season_matches,
                'avg_rating': round(np.mean(ratings), 1),
                'elite_teams': elite_count,
                'max_rating': round(max(ratings), 1)
            })
            
            total_matches += season_matches
            
        print(f"🏐 KVINDELIGA SAMLET STATISTIK:")
        print(f"  📊 Total hold: {len(total_teams)}")
        print(f"  🏟️ Total kampe: {total_matches:,}")
        print(f"  📅 Sæsoner: {len(self.all_season_results)}")
        
        print(f"\n📅 SÆSON OVERSIGT:")
        for s in season_summary:
            print(f"  {s['season']}: {s['teams']} hold, {s['total_matches']} kampe, "
                  f"avg {s['avg_rating']:.0f} (Elite: {s['elite_teams']})")
                  
        # Save summary to ELO_Results/Team_CSV/Kvindeliga
        summary_df = pd.DataFrame(season_summary)
        output_dir = os.path.join("ELO_Results", "Team_CSV", "Kvindeliga")
        os.makedirs(output_dir, exist_ok=True)
        summary_filepath = os.path.join(output_dir, 'kvindeliga_team_seasonal_summary_report.csv')
        summary_df.to_csv(summary_filepath, index=False)
        print(f"\n💾 Kvindeliga rapport gemt: {summary_filepath}")


# === MAIN EXECUTION ===
if __name__ == "__main__":
    print("🏆 STARTER KVINDELIGA TEAM SÆSON-BASERET ELO SYSTEM")
    print("=" * 80)
    
    # Create system instance
    kvindeliga_team_system = KvindeligaTeamSeasonalEloSystem()
    
    # Run complete analysis
    kvindeliga_team_system.run_complete_kvindeliga_team_analysis()
    
    print("\n🎉 KVINDELIGA TEAM SYSTEM KOMPLET!")
    print("=" * 80)
    print("🎯 Kvindeliga Team Features:")
    print("  ✅ Kun Kvindeliga hold data")
    print("  ✅ Intelligent regression to mean")
    print("  ✅ Hjemmebane fordel (75 points)")
    print("  ✅ Målforskels påvirkning")
    print("  ✅ Team momentum tracking")
    print("  ✅ Karriere analyse på tværs af sæsoner")
    print("  ✅ Elite team kategorisering")
    print("  ✅ Per-sæson detaljerede CSV filer")
    print("\n🏆 KVINDELIGA TEAM ELO KOMPLET!") 