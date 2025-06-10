#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 DETEKTOR FOR FEJLKLASSIFICEREDE MÅLVOGTERE
===============================================

ANALYSERER SPILLERE FOR AT IDENTIFICERE:
- Markspillere fejlagtigt klassificeret som målvogtere (som Peter Balling)
- Spillere med blandet data (både markspiller OG målvogter aktioner)
- Hybrid-spillere der skal have speciel behandling
- Målvogtere der fejlagtigt klassificeres som markspillere

LØSER DET KRITISKE PROBLEM MED KUNSTIGT HØJE RATINGS.

Jonas' Critical Fix - December 2024
"""

import pandas as pd
import numpy as np
import sqlite3
import os
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional, Set
import warnings
warnings.filterwarnings('ignore')

print("🔍 DETEKTOR FOR FEJLKLASSIFICEREDE MÅLVOGTERE")
print("=" * 80)

class GoalkeeperMisclassificationDetector:
    """
    Analyserer alle spillere for at identificere fejlklassificerede målvogtere
    """
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = base_dir
        
        # Database directories  
        self.herreliga_dir = os.path.join(base_dir, "Herreliga-database")
        self.kvindeliga_dir = os.path.join(base_dir, "Kvindeliga-database")
        
        # Rene markspiller positioner
        self.field_positions = {'VF', 'HF', 'VB', 'PL', 'HB', 'ST'}
        
        # Data containers
        self.player_stats = defaultdict(lambda: {
            'field_actions': defaultdict(int),  # Aktioner per markspiller position
            'goalkeeper_actions': 0,            # Antal gange i mv-feltet
            'goalkeeper_saves': 0,              # Faktiske redninger
            'goalkeeper_goals_against': 0,      # Mål mod spilleren som målvogter
            'seasons_active': set(),            # Hvilke sæsoner spilleren var aktiv
            'teams': set(),                     # Hvilke hold spilleren har spillet for
            'total_actions': 0,                 # Total antal aktioner
            'likely_position': 'Unknown'        # Sandsynlig primær position
        })
        
        # Output containers
        self.misclassified_players = []
        self.hybrid_players = []
        self.protected_field_players = []  # Spillere der ALDRIG skal have målvogter-bonus
        
        print("✅ Detektor initialiseret")
        print(f"📁 Herreliga directory: {self.herreliga_dir}")
        print(f"📁 Kvindeliga directory: {self.kvindeliga_dir}")
        
    def analyze_player_database(self, db_path: str, season: str, league: str):
        """Analyserer en enkelt database fil for spillerdata"""
        try:
            conn = sqlite3.connect(db_path)
            
            # Tjek tabeller eksisterer
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if 'match_events' not in tables:
                conn.close()
                return
                
            # Læs events
            events_df = pd.read_sql_query("SELECT * FROM match_events", conn)
            conn.close()
            
            if events_df.empty:
                return
                
            # Analyser hver event
            for _, event in events_df.iterrows():
                self.process_event(event, season, league)
                
        except Exception as e:
            print(f"  ⚠️ Fejl i {db_path}: {e}")
            
    def process_event(self, event: pd.Series, season: str, league: str):
        """Processerer en enkelt event for spillerdata"""
        
        # === ANALYSER PRIMÆR SPILLER (navn_1) ===
        player_1 = str(event.get('navn_1', '')).strip()
        pos = str(event.get('pos', '')).strip()
        action = str(event.get('haendelse_1', '')).strip()
        
        if player_1 and player_1 not in ['nan', '', 'None']:
            # Opdater spillerdata
            stats = self.player_stats[player_1]
            stats['seasons_active'].add(f"{league}-{season}")
            stats['total_actions'] += 1
            
            # Tæl markspiller positioner
            if pos in self.field_positions:
                stats['field_actions'][pos] += 1
                
            # Tæl målvogter-relaterede aktioner for primær spiller
            if action in ['Skud reddet', 'Straffekast reddet']:
                stats['goalkeeper_saves'] += 1
                
        # === ANALYSER SEKUNDÆR SPILLER (navn_2) ===  
        player_2 = str(event.get('navn_2', '')).strip()
        if player_2 and player_2 not in ['nan', '', 'None']:
            stats = self.player_stats[player_2]
            stats['seasons_active'].add(f"{league}-{season}")
            stats['total_actions'] += 1
            
        # === ANALYSER MÅLVOGTER (mv) ===
        goalkeeper = str(event.get('mv', '')).strip()
        if goalkeeper and goalkeeper not in ['nan', '', 'None', '0']:
            stats = self.player_stats[goalkeeper]
            stats['seasons_active'].add(f"{league}-{season}")
            stats['goalkeeper_actions'] += 1
            stats['total_actions'] += 1
            
            # Tæl mål mod målvogteren
            if action == 'Mål':
                stats['goalkeeper_goals_against'] += 1
                
    def analyze_all_seasons(self):
        """Analyserer alle sæsoner i begge ligaer"""
        print("\n📊 ANALYSERER ALLE SÆSONER FOR FEJLKLASSIFICEREDE MÅLVOGTERE")
        print("-" * 70)
        
        # Definer sæsoner
        seasons = [
            "2017-2018", "2018-2019", "2019-2020", "2020-2021",
            "2021-2022", "2022-2023", "2023-2024", "2024-2025"
        ]
        
        total_files_processed = 0
        total_players_found = 0
        
        # Analyser Herreliga
        print("\n🔵 HERRELIGA ANALYSE")
        for season in seasons:
            season_path = os.path.join(self.herreliga_dir, season)
            if os.path.exists(season_path):
                db_files = [f for f in os.listdir(season_path) if f.endswith('.db')]
                print(f"  📅 {season}: {len(db_files)} kampe")
                
                for db_file in db_files:
                    db_path = os.path.join(season_path, db_file)
                    self.analyze_player_database(db_path, season, "Herreliga")
                    total_files_processed += 1
                    
        # Analyser Kvindeliga  
        print("\n🔴 KVINDELIGA ANALYSE")
        for season in seasons:
            season_path = os.path.join(self.kvindeliga_dir, season)
            if os.path.exists(season_path):
                db_files = [f for f in os.listdir(season_path) if f.endswith('.db')]
                print(f"  📅 {season}: {len(db_files)} kampe")
                
                for db_file in db_files:
                    db_path = os.path.join(season_path, db_file)
                    self.analyze_player_database(db_path, season, "Kvindeliga")
                    total_files_processed += 1
                    
        total_players_found = len(self.player_stats)
        print(f"\n✅ ANALYSE KOMPLET")
        print(f"📄 {total_files_processed} database filer processeret")
        print(f"👥 {total_players_found} unikke spillere analyseret")
        
    def classify_players(self):
        """Klassificerer spillere baseret på deres aktivitetsmønster"""
        print("\n🧠 KLASSIFICERER SPILLERE BASERET PÅ AKTIVITETSMØNSTER")
        print("-" * 70)
        
        pure_goalkeepers = []
        pure_field_players = []
        misclassified_goalkeepers = []
        hybrid_players = []
        protected_field_players = []
        
        for player_name, stats in self.player_stats.items():
            # Beregn procenter
            total_actions = stats['total_actions']
            if total_actions == 0:
                continue
                
            field_actions_total = sum(stats['field_actions'].values())
            goalkeeper_actions = stats['goalkeeper_actions']
            
            field_percentage = (field_actions_total / total_actions) * 100
            goalkeeper_percentage = (goalkeeper_actions / total_actions) * 100
            
            # Find dominerende markspiller position
            if stats['field_actions']:
                dominant_position = max(stats['field_actions'], key=stats['field_actions'].get)
                dominant_position_count = stats['field_actions'][dominant_position]
                dominant_position_percentage = (dominant_position_count / total_actions) * 100
            else:
                dominant_position = None
                dominant_position_percentage = 0
                
            # === KLASSIFICERING BASERET PÅ STRENGERE REGLER ===
            
            # 1. RENE MÅLVOGTERE (meget strengere regler)
            if (goalkeeper_percentage >= 85 and 
                stats['goalkeeper_saves'] >= 15 and
                field_percentage <= 15 and
                goalkeeper_actions >= 25):
                
                classification = "PURE_GOALKEEPER"
                pure_goalkeepers.append((player_name, stats, classification))
                
            # 2. RENE MARKSPILLERE (typisk case)  
            elif (field_percentage >= 75 and
                  goalkeeper_percentage <= 10 and
                  dominant_position is not None):
                
                classification = "PURE_FIELD_PLAYER"
                pure_field_players.append((player_name, stats, classification))
                
                # Tilføj til beskyttede markspillere (ALDRIG målvogter-bonus)
                if field_percentage >= 85:
                    protected_field_players.append(player_name)
                
            # 3. FEJLKLASSIFICEREDE MÅLVOGTERE (KRITISK PROBLEM!)
            elif (field_percentage >= 60 and
                  goalkeeper_percentage <= 40 and
                  dominant_position is not None and
                  total_actions >= 20):
                
                classification = "MISCLASSIFIED_GOALKEEPER"
                misclassified_goalkeepers.append((player_name, stats, classification, dominant_position))
                print(f"  🚨 FEJLKLASSIFICERET: {player_name}")
                print(f"     🏃 Markspiller: {field_percentage:.1f}% (position: {dominant_position})")
                print(f"     🥅 Målvogter: {goalkeeper_percentage:.1f}%")
                print(f"     📊 Total aktioner: {total_actions}")
                
            # 4. HYBRID SPILLERE (komplekse cases)  
            elif (field_percentage >= 20 and
                  goalkeeper_percentage >= 20 and
                  total_actions >= 10):
                
                classification = "HYBRID_PLAYER"
                hybrid_players.append((player_name, stats, classification))
                
            # 5. UKENDT (for få data)
            else:
                classification = "INSUFFICIENT_DATA"
                
        # Gem resultater
        self.misclassified_players = misclassified_goalkeepers
        self.hybrid_players = hybrid_players
        self.protected_field_players = protected_field_players
        
        # Udskriv statistikker
        print(f"\n📊 KLASSIFICERINGS RESULTATER:")
        print(f"🥅 Rene målvogtere: {len(pure_goalkeepers)}")
        print(f"🏃 Rene markspillere: {len(pure_field_players)}")
        print(f"🚨 FEJLKLASSIFICEREDE målvogtere: {len(misclassified_goalkeepers)}")
        print(f"🔄 Hybrid spillere: {len(hybrid_players)}")
        print(f"🛡️ Beskyttede markspillere: {len(protected_field_players)}")
        
        return {
            'pure_goalkeepers': pure_goalkeepers,
            'pure_field_players': pure_field_players,
            'misclassified_goalkeepers': misclassified_goalkeepers,
            'hybrid_players': hybrid_players,
            'protected_field_players': protected_field_players
        }
        
    def find_peter_balling_case(self):
        """Finder specifikt Peter Balling og lignende cases"""
        print("\n🎯 SØGER EFTER PETER BALLING OG LIGNENDE CASES")
        print("-" * 70)
        
        peter_balling_found = False
        similar_cases = []
        
        for player_name, stats in self.player_stats.items():
            # Søg efter Peter Balling specifikt
            if "Peter" in player_name and "Balling" in player_name:
                peter_balling_found = True
                print(f"\n🎯 FUNDET: {player_name}")
                self.print_detailed_player_stats(player_name, stats)
                
            # Find lignende cases (markspillere med højre back som primær position)
            field_actions_total = sum(stats['field_actions'].values())
            if (field_actions_total > 0 and 
                stats['field_actions'].get('HB', 0) > 0 and
                stats['goalkeeper_actions'] > 0):
                
                total_actions = stats['total_actions']
                field_percentage = (field_actions_total / total_actions) * 100
                hb_percentage = (stats['field_actions']['HB'] / total_actions) * 100
                gk_percentage = (stats['goalkeeper_actions'] / total_actions) * 100
                
                # Lignende mønster som Peter Balling
                if (hb_percentage >= 30 and    # Betydelig HB aktivitet
                    gk_percentage > 10 and     # Nogen målvogter aktivitet
                    field_percentage >= 50):   # Overvejende markspiller
                    
                    similar_cases.append((player_name, hb_percentage, gk_percentage, total_actions))
                    
        if not peter_balling_found:
            print("❌ Peter Balling ikke fundet i dataene")
        else:
            print("✅ Peter Balling analyseret")
            
        if similar_cases:
            print(f"\n🔍 LIGNENDE CASES FUNDET ({len(similar_cases)}):")
            for name, hb_pct, gk_pct, total in similar_cases:
                print(f"  • {name}: HB={hb_pct:.1f}%, MV={gk_pct:.1f}% (total: {total})")
        else:
            print("ℹ️ Ingen lignende cases fundet")
            
    def print_detailed_player_stats(self, player_name: str, stats: dict):
        """Udskriver detaljeret statistik for en spiller"""
        total_actions = stats['total_actions']
        field_actions_total = sum(stats['field_actions'].values())
        
        print(f"  📊 DETALJERET ANALYSE AF {player_name}:")
        print(f"     🎯 Total aktioner: {total_actions}")
        print(f"     🏃 Markspiller aktioner: {field_actions_total} ({field_actions_total/total_actions*100:.1f}%)")
        print(f"     🥅 Målvogter aktioner: {stats['goalkeeper_actions']} ({stats['goalkeeper_actions']/total_actions*100:.1f}%)")
        print(f"     🎯 Redninger: {stats['goalkeeper_saves']}")
        print(f"     ⚽ Mål mod (som MV): {stats['goalkeeper_goals_against']}")
        print(f"     📅 Aktive sæsoner: {len(stats['seasons_active'])}")
        
        print(f"     📍 Markspiller positioner:")
        for pos, count in stats['field_actions'].items():
            percentage = (count / total_actions) * 100
            print(f"        {pos}: {count} aktioner ({percentage:.1f}%)")
            
    def run_complete_analysis(self):
        """Kører komplet analyse"""
        print("\n🚀 STARTER KOMPLET MÅLVOGTER FEJLKLASSIFICERING ANALYSE")
        print("=" * 80)
        
        # Trin 1: Analyser alle sæsoner
        self.analyze_all_seasons()
        
        # Trin 2: Klassificer spillere
        classification_results = self.classify_players()
        
        # Trin 3: Find Peter Balling case
        self.find_peter_balling_case()
        
        return classification_results

# === MAIN EXECUTION ===
if __name__ == "__main__":
    print("🔍 STARTER DETEKTOR FOR FEJLKLASSIFICEREDE MÅLVOGTERE")
    print("=" * 80)
    
    # Opret detektor
    detector = GoalkeeperMisclassificationDetector()
    
    # Kør komplet analyse
    results = detector.run_complete_analysis()
    
    print("\n🎯 ANALYSE KOMPLET!")
    print("=" * 80) 