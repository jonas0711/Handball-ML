#!/usr/bin/env python3
"""
SPILLER ELO ANALYSE SYSTEM
=========================

Dette script analyserer en specifik spillers ELO udvikling gennem en sæson.
Det viser hver enkelt handling, rating ændring og forklaring for hvorfor 
spilleren har fået den rating de har.

FORMÅL: Undersøge hvorfor spillere har fået deres specifikke ratings
EKSEMPEL: MORTEN HEMPEL JENSEN med rating 1697.9 (LEGENDARY)

FEATURES:
- Trin-for-trin rating udvikling
- Detaljeret action analyse  
- Kontekst forklaring for hver ændring
- Performance sammenligning
- Momentum tracking
- Position analyse
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

class PlayerEloAnalyzer:
    """
    Analyserer en spillers ELO udvikling gennem en sæson
    """
    
    def __init__(self, base_dir: str = ".", target_player: str = "MORTEN HEMPEL JENSEN", 
                 target_season: str = "2023-2024", league: str = "Herreliga"):
        """Initialiserer analyser for specifik spiller"""
        
        self.base_dir = base_dir
        self.target_player = target_player.strip()
        self.target_season = target_season
        self.league = league
        
        # Database sti
        if league == "Herreliga":
            self.database_dir = os.path.join(base_dir, "Herreliga-database", target_season)
        else:
            self.database_dir = os.path.join(base_dir, "Kvindeliga-database", target_season)
        
        # ELO system parametre (samme som master system)
        self.rating_bounds = {
            'min': 800,
            'max': 3000,
            'default_player': 1200,
            'default_goalkeeper': 1250,
            'elite_threshold': 1700,
            'legendary_threshold': 2100
        }
        
        self.k_factors = {
            'player': 8,
            'goalkeeper': 12
        }
        
        # Action vægte (fra master system)
        self.action_weights = {
            'Mål': 65, 'Assist': 55, 'Mål på straffe': 60, 'Bold erobret': 40,
            'Blok af (ret)': 35, 'Blokeret af': 30, 'Tilkendt straffe': 25,
            'Retur': 20, 'Forårs. str.': -35, 'Skud reddet': 70,
            'Straffekast reddet': 120, 'Skud på stolpe': -5,
            'Straffekast på stolpe': -10, 'Skud blokeret': -8,
            'Skud forbi': -15, 'Straffekast forbi': -25, 'Passivt spil': -20,
            'Regelfejl': -22, 'Tabt bold': -25, 'Fejlaflevering': -30,
            'Advarsel': -15, 'Udvisning': -45, 'Udvisning (2x)': -75,
            'Blåt kort': -60, 'Rødt kort': -90, 'Rødt kort, direkte': -90,
            'Protest': -20, 'Time out': 0
        }
        
        self.goalkeeper_penalty_weights = {
            'Mål': -8, 'Mål på straffe': -12, 
            'Skud på stolpe': 25, 'Straffekast på stolpe': 30
        }
        
        # Position multipliers (fra master system - kun for målvogtere)
        self.position_multipliers = {
            'MV': {
                'Skud reddet': 4.5, 'Straffekast reddet': 6.0,
                'Skud på stolpe': 3.5, 'Straffekast på stolpe': 4.0,
                'Mål': 2.0, 'Assist': 1.5, 'Bold erobret': 1.3,
                'Fejlaflevering': 0.8, 'Tabt bold': 0.8, 'Regelfejl': 0.9,
                'default_action': 1.8
            }
        }
        
        # Kontekst multipliers
        self.time_multipliers = {
            'early_game': 0.8, 'mid_game': 1.0, 'late_game': 1.4, 'final_phase': 1.8
        }
        self.score_multipliers = {
            'blowout': 0.65, 'comfortable': 0.9, 'competitive': 1.2, 'tight': 1.5, 'tied': 1.7
        }
        
        # Elite scaling
        self.elite_scaling = {
            'normal': 1.0, 'elite': 0.6, 'legendary': 0.3
        }
        
        # Scale faktorer
        self.scale_factors = {
            'player': 0.008, 'goalkeeper': 0.015, 'max_change': 16
        }
        
        # Tracking
        self.player_actions = []  # Alle spillerens handlinger
        self.rating_history = []  # Rating udvikling
        self.match_summaries = []  # Resumé per kamp
        self.current_rating = self.rating_bounds['default_player']
        self.is_goalkeeper = False
        self.position_counts = Counter()
        self.momentum_history = []
        
        print(f"🔍 ANALYSER INITIALISERET FOR {target_player}")
        print(f"📅 Sæson: {target_season} ({league})")
        print(f"📁 Database: {self.database_dir}")
        print(f"🎯 Start rating: {self.current_rating}")
        
    def determine_player_team(self, event_data: dict) -> list:
        """Bestemmer spillers hold - samme logik som master system"""
        players_found = []
        
        # PRIMARY PLAYER
        player_1 = str(event_data.get('navn_1', '')).strip()
        if player_1 and player_1 not in ['nan', '', 'None']:
            team_1 = str(event_data.get('hold', '')).strip()
            players_found.append((player_1, team_1, False))
            
        # SECONDARY PLAYER
        player_2 = str(event_data.get('navn_2', '')).strip()
        haendelse_2 = str(event_data.get('haendelse_2', '')).strip()
        
        if player_2 and player_2 not in ['nan', '', 'None'] and haendelse_2:
            team_hold = str(event_data.get('hold', '')).strip()
            
            if haendelse_2 in ['Assist']:
                players_found.append((player_2, team_hold, False))
            elif haendelse_2 in ['Bold erobret', 'Forårs. str.', 'Blokeret af', 'Blok af (ret)']:
                players_found.append((player_2, "OPPONENT", False))
                
        # GOALKEEPER
        goalkeeper = str(event_data.get('mv', '')).strip()
        if goalkeeper and goalkeeper not in ['nan', '', 'None', '0']:
            players_found.append((goalkeeper, "OPPONENT", True))
            
        return players_found
        
    def get_time_multiplier(self, time_str: str) -> float:
        """Håndbold-specifik tid multiplier"""
        try:
            time_val = float(time_str)
            
            if time_val >= 58:
                return self.time_multipliers['final_phase']
            elif time_val >= 55:
                return 2.4
            elif time_val >= 50:
                return self.time_multipliers['late_game']
            elif 28 <= time_val <= 30:
                return 1.6
            elif 25 <= time_val <= 28:
                return 1.4
            elif 45 <= time_val <= 50:
                return 1.5
            elif 40 <= time_val <= 45:
                return 1.2
            else:
                return self.time_multipliers['mid_game']
        except:
            return 1.0
            
    def get_score_multiplier(self, home_score: int, away_score: int) -> float:
        """Score-baseret multiplier"""
        diff = abs(home_score - away_score)
        
        if diff == 0:
            return self.score_multipliers['tied']
        elif diff <= 2:
            return self.score_multipliers['tight']
        elif diff <= 5:
            return self.score_multipliers['competitive']
        elif diff <= 10:
            return self.score_multipliers['comfortable']
        else:
            return self.score_multipliers['blowout']
            
    def analyze_momentum_context(self, action: str, time_val: float, 
                                home_score: int, away_score: int,
                                team: str, home_team: str, away_team: str) -> Dict:
        """Momentum analyse - samme som master system"""
        is_home_team = (team == home_team)
        score_diff = abs(home_score - away_score)
        action_type = self.classify_action_type(action)
        
        comeback_multiplier = 1.0
        lead_loss_multiplier = 1.0
        leadership_change_multiplier = 1.0
        critical_error_multiplier = 1.0
        
        # COMEBACK DETECTION
        if action_type == 'POSITIVE' and action in ['Mål', 'Mål på straffe']:
            if is_home_team and home_score < away_score:
                if score_diff >= 5:
                    comeback_multiplier = 2.2
                elif score_diff >= 3:
                    comeback_multiplier = 1.8
                elif score_diff >= 1:
                    comeback_multiplier = 1.4
            elif not is_home_team and away_score < home_score:
                if score_diff >= 5:
                    comeback_multiplier = 2.2
                elif score_diff >= 3:
                    comeback_multiplier = 1.8
                elif score_diff >= 1:
                    comeback_multiplier = 1.4
        
        # LEDERSKIFTE DETECTION
        if action in ['Mål', 'Mål på straffe']:
            new_home_score = home_score + (1 if is_home_team else 0)
            new_away_score = away_score + (0 if is_home_team else 1)
            
            if home_score > away_score and new_away_score >= new_home_score:
                leadership_change_multiplier = 2.5
            elif away_score > home_score and new_home_score >= new_away_score:
                leadership_change_multiplier = 2.5
            elif home_score == away_score:
                leadership_change_multiplier = 1.8
        
        return {
            'comeback': comeback_multiplier,
            'lead_loss': lead_loss_multiplier,
            'leadership_change': leadership_change_multiplier,
            'critical_error': critical_error_multiplier,
            'max_multiplier': max(comeback_multiplier, lead_loss_multiplier, 
                                leadership_change_multiplier, critical_error_multiplier)
        }
        
    def classify_action_type(self, action: str) -> str:
        """Klassificer handling som positiv/negativ/neutral"""
        positive_actions = {
            'Mål', 'Assist', 'Mål på straffe', 'Bold erobret', 'Skud reddet', 
            'Straffekast reddet', 'Blok af (ret)', 'Blokeret af', 'Retur',
            'Tilkendt straffe'
        }
        
        negative_actions = {
            'Fejlaflevering', 'Tabt bold', 'Skud forbi', 'Straffekast forbi',
            'Regelfejl', 'Passivt spil', 'Udvisning', 'Udvisning (2x)',
            'Advarsel', 'Rødt kort', 'Rødt kort, direkte', 'Blåt kort',
            'Forårs. str.'
        }
        
        if action in positive_actions:
            return 'POSITIVE'
        elif action in negative_actions:
            return 'NEGATIVE'
        else:
            return 'NEUTRAL'
            
    def calculate_context_importance(self, action: str, time_str: str, 
                                   home_score: int, away_score: int,
                                   team: str, home_team: str, away_team: str) -> float:
        """Beregn kontekstuel vigtighed - samme som master system"""
        try:
            time_val = float(time_str)
        except:
            time_val = 30.0
            
        score_diff = abs(home_score - away_score)
        
        # Timing multiplier
        if time_val >= 58:
            timing_multiplier = 3.0
        elif time_val >= 55:
            timing_multiplier = 2.4
        elif time_val >= 50:
            timing_multiplier = 1.8
        elif 28 <= time_val <= 30:
            timing_multiplier = 1.6
        elif 25 <= time_val <= 28:
            timing_multiplier = 1.4
        elif 45 <= time_val <= 50:
            timing_multiplier = 1.5
        elif 40 <= time_val <= 45:
            timing_multiplier = 1.2
        else:
            timing_multiplier = 1.0
            
        # Score proximity
        if score_diff == 0:
            score_proximity = 2.2
        elif score_diff == 1:
            score_proximity = 1.9
        elif score_diff == 2:
            score_proximity = 1.6
        elif score_diff <= 4:
            score_proximity = 1.3
        elif score_diff <= 6:
            score_proximity = 1.1
        else:
            score_proximity = 0.8
            
        # Momentum analyse
        momentum_analysis = self.analyze_momentum_context(
            action, time_val, home_score, away_score, team, home_team, away_team
        )
        momentum_multiplier = momentum_analysis['max_multiplier']
        
        # Action scaling
        action_type = self.classify_action_type(action)
        if action_type == 'POSITIVE':
            action_scaling = 1.0
        elif action_type == 'NEGATIVE':
            action_scaling = 1.2
        else:
            action_scaling = 0.9
        
        # Målvogter kritisk bonus
        goalkeeper_critical_bonus = 1.0
        if action in ['Skud reddet', 'Straffekast reddet'] and self.is_goalkeeper:
            if timing_multiplier >= 2.0 and score_diff <= 1:
                goalkeeper_critical_bonus = 4.0
            elif timing_multiplier >= 1.8 and score_diff <= 2:
                goalkeeper_critical_bonus = 3.0
            elif timing_multiplier >= 1.5 and score_diff <= 1:
                goalkeeper_critical_bonus = 1.8
        
        # Kombiner faktorer
        context_multiplier = (
            timing_multiplier * 0.25 +
            score_proximity * 0.25 +
            momentum_multiplier * 0.25 +
            action_scaling * 0.10 +
            goalkeeper_critical_bonus * 0.10 +
            1.0 * 0.05  # Base
        )
        
        return max(0.4, min(5.0, context_multiplier))
        
    def process_player_action(self, action: str, position: str, time_str: str,
                             home_score: int, away_score: int, team: str,
                             home_team: str, away_team: str, match_info: dict):
        """Processerer en spillers handling og beregner rating ændring"""
        
        # Check om spilleren er målvogter
        using_goalkeeper_penalty = self.is_goalkeeper and action in self.goalkeeper_penalty_weights
        
        if using_goalkeeper_penalty:
            base_weight = self.goalkeeper_penalty_weights[action]
        else:
            base_weight = self.action_weights.get(action, 0)
            
        if base_weight == 0:
            return
            
        # Multipliers
        time_mult = self.get_time_multiplier(time_str)
        score_mult = self.get_score_multiplier(home_score, away_score)
        
        # Position multiplier (kun for målvogtere)
        if self.is_goalkeeper and position == 'MV':
            pos_mult = self.position_multipliers['MV'].get(action, 
                       self.position_multipliers['MV']['default_action'])
        else:
            pos_mult = 1.0
            
        # Kontekst multiplier
        if using_goalkeeper_penalty:
            context_mult = 1.0
        else:
            context_mult = self.calculate_context_importance(
                action, time_str, home_score, away_score, team, home_team, away_team
            )
        
        # Total vægt
        total_weight = base_weight * time_mult * score_mult * pos_mult * context_mult
        
        # Elite scaling
        if self.current_rating >= self.rating_bounds['legendary_threshold']:
            elite_multiplier = self.elite_scaling['legendary']
            elite_status = "LEGENDARY"
        elif self.current_rating >= self.rating_bounds['elite_threshold']:
            elite_multiplier = self.elite_scaling['elite']
            elite_status = "ELITE"
        else:
            elite_multiplier = self.elite_scaling['normal']
            elite_status = "NORMAL"
            
        # K-faktor
        k_factor = self.k_factors['goalkeeper'] if self.is_goalkeeper else self.k_factors['player']
        
        # Rating ændring
        max_change = self.scale_factors['max_change']
        scale = self.scale_factors['goalkeeper'] if self.is_goalkeeper else self.scale_factors['player']
        
        rating_change = total_weight * scale * elite_multiplier
        rating_change = max(-max_change, min(max_change, rating_change))
        
        # Opdater rating
        old_rating = self.current_rating
        self.current_rating = max(self.rating_bounds['min'],
                                min(self.rating_bounds['max'], 
                                    self.current_rating + rating_change))
        
        # Log handlingen
        action_info = {
            'match': match_info['match_name'],
            'time': time_str,
            'action': action,
            'position': position,
            'team': team,
            'home_score': home_score,
            'away_score': away_score,
            'base_weight': base_weight,
            'time_mult': time_mult,
            'score_mult': score_mult,
            'pos_mult': pos_mult,
            'context_mult': context_mult,
            'total_weight': total_weight,
            'elite_status': elite_status,
            'elite_multiplier': elite_multiplier,
            'rating_change': rating_change,
            'old_rating': old_rating,
            'new_rating': self.current_rating,
            'goalkeeper_penalty': using_goalkeeper_penalty
        }
        
        self.player_actions.append(action_info)
        self.rating_history.append({
            'match': match_info['match_name'],
            'time': time_str,
            'rating': self.current_rating
        })
        
        # Opdater position count
        if position:
            self.position_counts[position] += 1
            if position == 'MV':
                self.is_goalkeeper = True
                
    def analyze_match(self, db_path: str) -> bool:
        """Analyserer en enkelt kamp"""
        try:
            conn = sqlite3.connect(db_path)
            
            # Tjek tabeller
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            if 'match_info' not in tables or 'match_events' not in tables:
                conn.close()
                return False
            
            match_info = pd.read_sql_query("SELECT * FROM match_info", conn)
            if match_info.empty:
                conn.close()
                return False
                
            events = pd.read_sql_query("SELECT * FROM match_events ORDER BY id", conn)
            if events.empty:
                conn.close()
                return False
                
            conn.close()
            
            home_team = match_info.iloc[0]['hold_hjemme']
            away_team = match_info.iloc[0]['hold_ude']
            match_name = f"{home_team} vs {away_team}"
            
            # Match info
            match_data = {
                'match_name': match_name,
                'home_team': home_team,
                'away_team': away_team
            }
            
            current_home = 0
            current_away = 0
            player_found_in_match = False
            actions_in_match = 0
            
            # Team mapping for OPPONENT resolution
            team_mapping = {home_team: away_team, away_team: home_team}
            
            print(f"\n🏐 ANALYSERER: {match_name}")
            
            for _, event in events.iterrows():
                action = str(event.get('haendelse_1', '')).strip()
                if action in ['Halvleg', 'Start 1:e halvleg', 'Start 2:e halvleg',
                             'Fuld tid', 'Kamp slut', '', 'nan']:
                    continue
                    
                time_str = str(event.get('tid', '0'))
                pos_field = str(event.get('pos', '')).strip()
                goal_score = str(event.get('maal', '')).strip()
                
                # Opdater current score
                if goal_score and '-' in goal_score:
                    try:
                        parts = goal_score.split('-')
                        current_home = int(parts[0])
                        current_away = int(parts[1])
                    except:
                        pass
                        
                # Find alle spillere i event
                players_in_event = self.determine_player_team(event)
                
                for player_name, team_code, is_goalkeeper in players_in_event:
                    # FLEKSIBEL NAVNEMATCH - tillader delvis match og ignorerer mellemrum/store bogstaver
                    player_clean = player_name.strip().upper()
                    target_clean = self.target_player.strip().upper()
                    
                    if not (target_clean == player_clean or 
                           target_clean in player_clean or 
                           player_clean in target_clean or
                           target_clean.replace(' ', '') == player_clean.replace(' ', '')):
                        continue
                        
                    player_found_in_match = True
                    
                    # Resolve OPPONENT team
                    if team_code == "OPPONENT":
                        primary_team = str(event.get('hold', '')).strip()
                        if primary_team in team_mapping:
                            team_code = team_mapping[primary_team]
                        else:
                            continue
                    
                    # Bestem position
                    if is_goalkeeper:
                        position = 'MV'
                        self.is_goalkeeper = True
                    elif pos_field in ['VF', 'HF', 'VB', 'PL', 'HB', 'ST']:
                        position = pos_field
                    else:
                        position = 'PL'  # Default
                    
                    # Processér handlingen
                    self.process_player_action(
                        action, position, time_str, current_home, current_away,
                        team_code, home_team, away_team, match_data
                    )
                    
                    actions_in_match += 1
                    
            if player_found_in_match:
                print(f"   ✅ {self.target_player} fundet - {actions_in_match} handlinger")
                self.match_summaries.append({
                    'match': match_name,
                    'actions': actions_in_match,
                    'rating_start': self.rating_history[-actions_in_match]['rating'] if actions_in_match > 0 and len(self.rating_history) >= actions_in_match else self.current_rating,
                    'rating_end': self.current_rating,
                    'rating_change': self.current_rating - (self.rating_history[-actions_in_match]['rating'] if actions_in_match > 0 and len(self.rating_history) >= actions_in_match else self.current_rating)
                })
                return True
            else:
                print(f"   ⚪ {self.target_player} ikke fundet")
                return False
                
        except Exception as e:
            print(f"   ❌ Fejl: {e}")
            return False
            
    def analyze_season(self):
        """Analyserer hele sæsonen"""
        print(f"\n🔍 STARTER ANALYSE AF {self.target_player}")
        print("=" * 60)
        
        if not os.path.exists(self.database_dir):
            print(f"❌ Database directory ikke fundet: {self.database_dir}")
            return
            
        db_files = [f for f in os.listdir(self.database_dir) if f.endswith('.db')]
        db_files.sort()
        
        print(f"📁 Fundet {len(db_files)} kampe i {self.target_season}")
        
        matches_found = 0
        total_actions = 0
        
        for db_file in db_files:
            db_path = os.path.join(self.database_dir, db_file)
            if self.analyze_match(db_path):
                matches_found += 1
                
        total_actions = len(self.player_actions)
        
        print(f"\n📊 ANALYSE KOMPLET")
        print(f"   🏟️ Kampe med spilleren: {matches_found}/{len(db_files)}")
        print(f"   🎯 Total handlinger: {total_actions}")
        print(f"   📈 Start rating: {self.rating_bounds['default_player']}")
        print(f"   📈 Slut rating: {self.current_rating:.1f}")
        print(f"   📈 Total ændring: {self.current_rating - self.rating_bounds['default_player']:+.1f}")
        
        # Generer detaljeret rapport
        self.generate_detailed_report()
        
    def generate_detailed_report(self):
        """Genererer detaljeret rapport"""
        print(f"\n📋 DETALJERET RAPPORT FOR {self.target_player}")
        print("=" * 80)
        
        if not self.player_actions:
            print("❌ Ingen handlinger fundet for spilleren")
            return
            
        # Position analyse
        primary_position = self.position_counts.most_common(1)[0][0] if self.position_counts else 'PL'
        print(f"🎯 PRIMÆR POSITION: {primary_position}")
        print(f"   Position fordeling: {dict(self.position_counts)}")
        print(f"   Målvogter: {'Ja' if self.is_goalkeeper else 'Nej'}")
        
        # Rating udvikling
        print(f"\n📈 RATING UDVIKLING:")
        print(f"   Start: {self.rating_bounds['default_player']}")
        print(f"   Slut: {self.current_rating:.1f}")
        print(f"   Ændring: {self.current_rating - self.rating_bounds['default_player']:+.1f}")
        
        if self.current_rating >= self.rating_bounds['legendary_threshold']:
            status = "LEGENDARY"
        elif self.current_rating >= self.rating_bounds['elite_threshold']:
            status = "ELITE"
        else:
            status = "NORMAL"
        print(f"   Status: {status}")
        
        # Action analyse
        action_summary = Counter()
        positive_actions = 0
        negative_actions = 0
        total_rating_change = 0
        
        for action_info in self.player_actions:
            action_summary[action_info['action']] += 1
            total_rating_change += action_info['rating_change']
            
            action_type = self.classify_action_type(action_info['action'])
            if action_type == 'POSITIVE':
                positive_actions += 1
            elif action_type == 'NEGATIVE':
                negative_actions += 1
                
        print(f"\n🎯 ACTION SAMMENFATNING:")
        print(f"   Total handlinger: {len(self.player_actions)}")
        print(f"   Positive handlinger: {positive_actions}")
        print(f"   Negative handlinger: {negative_actions}")
        print(f"   Neutral handlinger: {len(self.player_actions) - positive_actions - negative_actions}")
        
        print(f"\n🏆 TOP HANDLINGER:")
        for action, count in action_summary.most_common(10):
            avg_impact = sum(a['rating_change'] for a in self.player_actions if a['action'] == action) / count
            print(f"   {action}: {count}x (Ø impact: {avg_impact:+.2f})")
        
        # Støreste rating ændringer
        print(f"\n📊 STØRSTE RATING ÆNDRINGER:")
        
        # Positive ændringer
        positive_changes = sorted([a for a in self.player_actions if a['rating_change'] > 0],
                                key=lambda x: x['rating_change'], reverse=True)[:10]
        if positive_changes:
            print(f"   💚 STØRSTE GEVINSTER:")
            for i, action in enumerate(positive_changes[:5], 1):
                print(f"      {i}. {action['action']} i {action['match']} @ {action['time']}min")
                print(f"         Rating: {action['old_rating']:.1f} → {action['new_rating']:.1f} ({action['rating_change']:+.2f})")
                print(f"         Kontekst: {action['context_mult']:.1f}x, Elite: {action['elite_status']}")
        
        # Negative ændringer  
        negative_changes = sorted([a for a in self.player_actions if a['rating_change'] < 0],
                                key=lambda x: x['rating_change'])[:10]
        if negative_changes:
            print(f"   💔 STØRSTE TAB:")
            for i, action in enumerate(negative_changes[:5], 1):
                print(f"      {i}. {action['action']} i {action['match']} @ {action['time']}min")
                print(f"         Rating: {action['old_rating']:.1f} → {action['new_rating']:.1f} ({action['rating_change']:+.2f})")
                print(f"         Kontekst: {action['context_mult']:.1f}x, Elite: {action['elite_status']}")
        
        # Match performance
        print(f"\n🏟️ KAMP PERFORMANCE:")
        if self.match_summaries:
            self.match_summaries.sort(key=lambda x: x['rating_change'], reverse=True)
            print(f"   🥇 BEDSTE KAMPE:")
            for i, match in enumerate(self.match_summaries[:3], 1):
                print(f"      {i}. {match['match']}: {match['rating_change']:+.1f} ({match['actions']} handlinger)")
            
            print(f"   🥉 VÆRSTE KAMPE:")
            worst_matches = sorted(self.match_summaries, key=lambda x: x['rating_change'])[:3]
            for i, match in enumerate(worst_matches, 1):
                print(f"      {i}. {match['match']}: {match['rating_change']:+.1f} ({match['actions']} handlinger)")
        
        # Gem detaljeret CSV
        self.save_detailed_csv()
        
    def save_detailed_csv(self):
        """Gemmer detaljeret CSV med alle handlinger"""
        if not self.player_actions:
            return
            
        # Konverter til DataFrame
        df = pd.DataFrame(self.player_actions)
        
        # Tilføj ekstra info
        df['player_name'] = self.target_player
        df['season'] = self.target_season
        df['league'] = self.league
        df['action_type'] = df['action'].apply(self.classify_action_type)
        
        # Sorter efter tid
        df = df.sort_values(['match', 'time'])
        
        # Gem
        filename = f"player_analysis_{self.target_player.replace(' ', '_')}_{self.target_season}_{self.league}.csv"
        df.to_csv(filename, index=False)
        
        print(f"\n💾 DETALJERET ANALYSE GEMT: {filename}")
        
        # Gem også match sammenfatning
        if self.match_summaries:
            match_df = pd.DataFrame(self.match_summaries)
            match_df['player_name'] = self.target_player
            match_df['season'] = self.target_season
            match_df['league'] = self.league
            
            match_filename = f"match_summary_{self.target_player.replace(' ', '_')}_{self.target_season}_{self.league}.csv"
            match_df.to_csv(match_filename, index=False)
            
            print(f"💾 KAMP SAMMENFATNING GEMT: {match_filename}")

# === MAIN EXECUTION ===
if __name__ == "__main__":
    print("🔍 SPILLER ELO ANALYSER")
    print("=" * 60)
    
    # ANALYSÉR MORTEN HEMPEL JENSEN
    target_player = "MORTEN HEMPEL JENSEN"
    target_season = "2023-2024"
    league = "Herreliga"
    
    print(f"🎯 ANALYSERER: {target_player}")
    print(f"📅 Sæson: {target_season}")
    print(f"🏆 Liga: {league}")
    
    # Initialiser analyser
    analyzer = PlayerEloAnalyzer(
        target_player=target_player,
        target_season=target_season,
        league=league
    )
    
    # Kør analyse
    analyzer.analyze_season()
    
    print(f"\n🎯 ANALYSE KOMPLET FOR {target_player}!")
    print("=" * 60)
    print("📁 Genererede filer:")
    print(f"  • player_analysis_{target_player.replace(' ', '_')}_{target_season}_{league}.csv")
    print(f"  • match_summary_{target_player.replace(' ', '_')}_{target_season}_{league}.csv")
    print()
    print("🔍 RESULTATER:")
    print("  ✅ Detaljeret action-by-action analyse")
    print("  ✅ Rating udvikling trin-for-trin")
    print("  ✅ Kontekstuel forklaring for hver ændring")
    print("  ✅ Match performance sammenligning")
    print("  ✅ Action type analyse")
    print("  ✅ Elite progression tracking")
    print()
    print("💡 BRUG RESULTATERNE TIL:")
    print("  🔬 Identificere hvorfor spilleren har høj/lav rating")
    print("  📊 Forstå hvilke handlinger der påvirker mest")
    print("  🎯 Verificere om rating er rimelig")
    print("  🏆 Sammenligne performance på tværs af kampe")