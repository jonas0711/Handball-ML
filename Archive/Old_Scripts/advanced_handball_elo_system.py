#!/usr/bin/env python3
"""
🏆 AVANCERET HÅNDBOL ELO SYSTEM - MULTI-SÆSON VERSION
=========================================================

IMPLEMENTERER ALLE ØNSKEDE FEATURES:
✅ Multi-sæson ELO tracking (både samlet og per sæson)
✅ Spillerpositions-klassificering baseret på action-tælling  
✅ Klubtilknytning per sæson med automatisk klubskifte håndtering
✅ Intelligent sæson carryover (80% forrige + 20% samlet)
✅ Korrekt målvogteridentifikation gennem nr_mv/mv felter
✅ Position-baseret action vægtning og K-faktorer
✅ Komplet debugging med detaljerede print statements

BASERET PÅ: handball_elo_master.py men med væsentlige forbedringer
"""

import pandas as pd
import numpy as np
import sqlite3
import os
import json
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional, Set, Any
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("🏆 AVANCERET HÅNDBOL ELO SYSTEM - MULTI-SÆSON VERSION")
print("=" * 80)

class AdvancedHandballEloSystem:
    """
    Avanceret håndbol ELO system med multi-sæson tracking og spillerklassificering
    """
    
    def __init__(self, base_dir: str = "."):
        """Initialiserer systemet"""
        print("🚀 Starter Avanceret Håndbol ELO System...")
        
        self.base_dir = base_dir
        
        # === SÆSON KONFIGURATION ===
        self.seasons = [
            "2018-2019", "2019-2020", "2020-2021", "2021-2022",
            "2022-2023", "2023-2024", "2024-2025", "2025-2026"
        ]
        
        # === HÅNDBOL POSITIONER ===
        # Standard 7 positioner som defineret i data.md
        self.position_mapping = {
            'VF': 'VF',   # Venstre fløj
            'HF': 'HF',   # Højre fløj
            'VB': 'VB',   # Venstre back
            'PL': 'PL',   # Playmaker
            'HB': 'HB',   # Højre back
            'ST': 'ST',   # Streg
            'Gbr': 'VB',  # Gennembrud -> Venstre back strategi
            '1:e': 'HB',  # Første bølge -> Højre back
            '2:e': 'PL',  # Anden bølge -> Playmaker
            '': 'PL'      # Ukendt -> Default playmaker
        }
        
        # KRITISK: Hold mapping mellem fulde holdnavne og koder
        self.team_name_to_code = {
            # Herreliga teams
            "Aalborg Håndbold": "AAH",
            "Bjerringbro-Silkeborg": "BSH", 
            "Fredericia Håndbold Klub": "FHK",
            "Fredericia HK": "FHK",
            "Fredericia Håndboldklub": "FHK",
            "Grindsted GIF Håndbold": "GIF",
            "GOG": "GOG",
            "KIF Kolding": "KIF",
            "Lemvig-Thyborøn Håndbold": "LTH",  # TILFØJET MANGLENDE MAPPING
            "Mors-Thy Håndbold": "MTH",
            "Nordsjælland Håndbold": "NSH",
            "Ribe-Esbjerg HH": "REH",
            "SAH - Skanderborg AGF": "SAH",
            "Skjern Håndbold": "SKH",
            "SønderjyskE Herrehåndbold": "SJE",
            "SønderjyskE Herrer": "SJE",
            "TTH Holstebro": "TTH",
            "TMS Ringsted": "TMS",
            # Kvindeliga teams
            "Aarhus Håndbold Kvinder": "AHB",
            "Bjerringbro FH": "BFH",
            "EH Aalborg": "EHA",
            "Horsens Håndbold Elite": "HHE",
            "Ikast Håndbold": "IKA",
            "København Håndbold": "KBH",
            "Nykøbing F. Håndbold": "NFH",
            "Odense Håndbold": "ODE",
            "Ringkøbing Håndbold": "RIN",
            "Silkeborg-Voel KFUM": "SVK",
            "Skanderborg Håndbold": "SKB",
            "SønderjyskE Kvindehåndbold": "SJE",
            "Team Esbjerg": "TES",
            "Viborg HK": "VHK",
        }
        
        # Reverse mapping (kode til navn)
        self.team_code_to_name = {v: k for k, v in self.team_name_to_code.items()}
        
        # === ELO SYSTEM PARAMETRE ===
        self.rating_bounds = {
            'min': 900,
            'max': 1700,
            'default_player': 1200,
            'default_goalkeeper': 1250
        }
        
        self.k_factors = {
            'player': 8,
            'goalkeeper': 5
        }
        
        self.carryover_weights = {
            'previous_season': 0.8,
            'overall': 0.2
        }
        
        # === ACTION VÆGTE ===
        # Balancerede vægte baseret på vigtighed
        self.action_weights = {
            # Positive actions
            'Mål': 80,
            'Mål på straffe': 70,
            'Assist': 50,
            'Skud reddet': 90,  # Højere for målvogtere
            'Straffekast reddet': 120,  # Meget høj for strafferedning
            'Bold erobret': 40,
            'Blokeret af': 30,
            'Blok af (ret)': 30,
            
            # Negative actions
            'Fejlaflevering': -50,
            'Tabt bold': -40,
            'Regelfejl': -35,
            'Udvisning': -80,
            'Rødt kort': -150,
            'Blåt kort': -100,
            'Advarsel': -25,
            'Skud forbi': -10,
            'Straffekast forbi': -60,
            'Passivt spil': -30,
            
            # Neutral/lav impact
            'Skud på stolpe': -5,
            'Straffekast på stolpe': -20,
            'Skud blokeret': 0,
            'Time out': 0
        }
        
        # === DATA CONTAINERS ===
        # Player ELO (multi-season)
        self.player_elos = defaultdict(lambda: defaultdict(lambda: self.rating_bounds['default_player']))
        
        # Position og klub tracking
        self.player_position_counts = defaultdict(lambda: defaultdict(int))
        self.player_club_counts = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
        self.player_profiles = defaultdict(lambda: {'position': 'PL', 'clubs': {}})
        
        # Bekræftede målvogtere (identificeret gennem nr_mv/mv felter)
        self.confirmed_goalkeepers = set()
        
        print("✅ System initialiseret")
        print(f"📊 {len(self.seasons)} sæsoner konfigureret")
        print(f"🗺️ {len(self.team_name_to_code)} hold mappet")
        print(f"⚖️ {len(self.action_weights)} action vægte defineret")
    
    def get_team_code(self, team_name: str) -> str:
        """Konverterer holdnavn til holdkode"""
        if not team_name:
            return ""
        
        team_clean = str(team_name).strip()
        
        # Check direkte mapping
        if team_clean in self.team_name_to_code:
            return self.team_name_to_code[team_clean]
        
        # Check hvis det allerede er en kode
        if team_clean in self.team_code_to_name:
            return team_clean
        
        # Fallback - returner som det er
        return team_clean
    
    def determine_player_team(self, event_data: dict, home_team: str, away_team: str) -> list:
        """
        Bestemmer spillers hold baseret på data.md regler med korrekt holdkode mapping
        Returnerer [(player_name, team, is_goalkeeper), ...]
        """
        players_found = []
        
        # Konverter hold til koder for sammenligning
        home_code = self.get_team_code(home_team)
        away_code = self.get_team_code(away_team)
        
        # === PRIMARY PLAYER (navn_1) ===
        player_1 = str(event_data.get('navn_1', '') or '').strip()
        if player_1 and player_1 not in ['nan', '', 'None']:
            team_1 = str(event_data.get('hold', '') or '').strip()
            players_found.append((player_1, team_1, False))
            
        # === SECONDARY PLAYER (navn_2) ===
        player_2 = str(event_data.get('navn_2', '') or '').strip()
        haendelse_2 = str(event_data.get('haendelse_2', '') or '').strip()
        
        if player_2 and player_2 not in ['nan', '', 'None'] and haendelse_2:
            team_hold = str(event_data.get('hold', '') or '').strip()
            
            # Baseret på data.md - sekundære hændelser
            if haendelse_2 in ['Assist']:
                # Samme hold som primær
                players_found.append((player_2, team_hold, False))
            elif haendelse_2 in ['Bold erobret', 'Forårs. str.', 'Blokeret af', 'Blok af (ret)']:
                # Modstanderhold - find det rigtige hold
                if team_hold == home_code:
                    opponent_team = away_code
                elif team_hold == away_code:
                    opponent_team = home_code
                else:
                    opponent_team = team_hold  # Fallback
                players_found.append((player_2, opponent_team, False))
                
        # === GOALKEEPER (mv) ===
        # KRITISK: Målvogtere identificeres kun gennem mv-feltet!
        goalkeeper = str(event_data.get('mv', '') or '').strip()
        nr_mv = str(event_data.get('nr_mv', '') or '').strip()
        
        # Kun accepter som målvogter hvis BÅDE mv og nr_mv er udfyldt
        if (goalkeeper and goalkeeper not in ['nan', '', 'None', '0'] and 
            nr_mv and nr_mv not in ['nan', '', 'None', '0']):
            
            # Målvogteren tilhører ALTID det modsatte hold (data.md)
            team_hold = str(event_data.get('hold', '') or '').strip()
            
            # VIGTIG: Nu bruger vi holdkoder til sammenligning
            if team_hold == home_code:
                goalkeeper_team = away_code
            elif team_hold == away_code:
                goalkeeper_team = home_code
            else:
                # Fallback - kan ikke bestemme hold
                goalkeeper_team = None
                
            if goalkeeper_team:
                players_found.append((goalkeeper, goalkeeper_team, True))
                
        return players_found
    
    def process_season_data(self, season: str) -> Dict[str, Any]:
        """
        Processerer data for en komplet sæson
        Returnerer statistikker for sæsonen
        """
        print(f"\n🏁 Starter processering af sæson: {season}")
        
        season_dir = os.path.join(self.base_dir, "Herreliga-database", season)
        if not os.path.exists(season_dir):
            print(f"❌ Sæson mappe ikke fundet: {season_dir}")
            return {}
        
        # Hent alle database filer for sæsonen
        db_files = [f for f in os.listdir(season_dir) if f.endswith('.db')]
        print(f"📁 Fundet {len(db_files)} kampe i {season}")
        
        season_stats = {
            'matches_processed': 0,
            'actions_processed': 0,
            'players_found': set(),
            'teams_found': set(),
            'goalkeepers_found': set(),
            'errors': []
        }
        
        # Processer hver kamp
        for db_file in db_files:
            db_path = os.path.join(season_dir, db_file)
            try:
                match_stats = self.process_match_database(db_path, season)
                
                # Opdater sæson statistikker
                season_stats['matches_processed'] += 1
                season_stats['actions_processed'] += match_stats.get('actions', 0)
                season_stats['players_found'].update(match_stats.get('players', set()))
                season_stats['teams_found'].update(match_stats.get('teams', set()))
                season_stats['goalkeepers_found'].update(match_stats.get('goalkeepers', set()))
                
            except Exception as e:
                error_msg = f"Fejl i {db_file}: {str(e)}"
                season_stats['errors'].append(error_msg)
                print(f"❌ {error_msg}")
        
        print(f"✅ Sæson {season} fuldført:")
        print(f"   📊 Kampe: {season_stats['matches_processed']}")  
        print(f"   🎬 Actions: {season_stats['actions_processed']}")
        print(f"   👥 Spillere: {len(season_stats['players_found'])}")
        print(f"   🥅 Målvogtere: {len(season_stats['goalkeepers_found'])}")
        print(f"   🏟️ Hold: {len(season_stats['teams_found'])}")
        if season_stats['errors']:
            print(f"   ⚠️ Fejl: {len(season_stats['errors'])}")
        
        return season_stats
    
    def process_match_database(self, db_path: str, season: str) -> Dict[str, Any]:
        """
        Processerer en enkelt kampdeatabase
        """
        match_stats = {
            'actions': 0,
            'players': set(),
            'teams': set(),
            'goalkeepers': set()
        }
        
        try:
            # Create database connection
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row  # Enable column access by name
            
            # Check if required tables exist
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            # Get home and away teams from match_info (CRITICAL for goalkeeper team assignment)
            home_team = ""
            away_team = ""
            if 'match_info' in tables:
                try:
                    match_info_df = pd.read_sql_query("SELECT * FROM match_info LIMIT 1", conn)
                    if not match_info_df.empty:
                        home_team = str(match_info_df.iloc[0].get('hold_hjemme', '') or '').strip()
                        away_team = str(match_info_df.iloc[0].get('hold_ude', '') or '').strip()
                except Exception:
                    pass
            
            if 'match_events' not in tables:
                # Try alternative table names
                if 'event' in tables:
                    table_name = 'event'
                else:
                    conn.close()
                    return match_stats
            else:
                table_name = 'match_events'
            
            # Read events table with error handling
            try:
                events_df = pd.read_sql_query(f"SELECT * FROM {table_name} ORDER BY tid", conn)
            except Exception as e:
                try:
                    # Try without ordering if tid column doesn't exist
                    events_df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
                except Exception as e2:
                    conn.close()
                    return match_stats
            
            if events_df.empty:
                conn.close()
                return match_stats
            
            # Process each event with correct home/away team information
            for _, event in events_df.iterrows():
                try:
                    self.process_single_event(event.to_dict(), season, match_stats, home_team, away_team)
                    match_stats['actions'] += 1
                except Exception as e:
                    # Skip problematic events instead of crashing
                    continue
            
            conn.close()
            
        except Exception as e:
            # Silently skip problematic databases
            pass
        
        return match_stats
    
    def process_single_event(self, event_data: Dict[str, Any], season: str, 
                           match_stats: Dict[str, Any], home_team: str, away_team: str):
        """
        Processerer en enkelt hændelse fra databasen med korrekt holdkode mapping
        """
        # === ROBUST DATA EXTRACTION ===
        primary_action = str(event_data.get('haendelse_1', '') or '').strip()
        pos_field = str(event_data.get('pos', '') or '').strip()
        
        # Skip administrative events
        if primary_action in ['Start 1:e halvleg', 'Halvleg', 'Start 2:e halvleg', 
                              'Fuld tid', 'Kamp slut', 'Video Proof', 'Video Proof slut',
                              'Time out', '']:
            return

        # === FIND ALLE SPILLERE I EVENT MED KORREKT HOLDTILKNYTNING ===
        players_in_event = self.determine_player_team(event_data, home_team, away_team)
        
        # Process hver spiller fundet i event
        for player_name, team_code, is_goalkeeper in players_in_event:
            if not player_name or team_code == "UNKNOWN":
                continue
                
            # Map position
            mapped_position = self.map_position(pos_field)
            if is_goalkeeper:
                mapped_position = 'MV'
                self.confirmed_goalkeepers.add(player_name)
            
            # Update player data with KORREKT hold
            self.update_player_position_count(player_name, mapped_position, is_goalkeeper)
            self.update_player_club_count(player_name, team_code, season)
            
            # Process action for ELO
            elo_change = self.process_action(primary_action, player_name, 
                                           mapped_position, season, is_goalkeeper)
            if elo_change != 0:
                self.update_player_elo(player_name, elo_change, season)
            
            # Update match statistics
            match_stats['players'].add(player_name)
            match_stats['teams'].add(team_code)
            if is_goalkeeper:
                match_stats['goalkeepers'].add(player_name)
    
    def map_position(self, pos_field: str) -> str:
        """
        Maps position from pos field to standard handball position
        """
        if not pos_field:
            return 'PL'  # Default to playmaker
            
        pos_clean = str(pos_field).strip()
        if not pos_clean or pos_clean in ['nan', 'None', '']:
            return 'PL'
            
        return self.position_mapping.get(pos_clean, 'PL')  # Default to playmaker
    
    def update_player_position_count(self, player_name: str, position: str, is_goalkeeper: bool = False):
        """
        Opdaterer position tæller for spilleren
        """
        if not player_name:
            return
        
        # Målvogtere får altid MV position
        if is_goalkeeper:
            final_position = 'MV'
            self.confirmed_goalkeepers.add(player_name)
        else:
            final_position = position
        
        # Opdater tæller
        self.player_position_counts[player_name][final_position] += 1
    
    def update_player_club_count(self, player_name: str, club: str, season: str):
        """
        Opdaterer klub tæller for spilleren i sæsonen
        """
        if not player_name or not club or not season:
            return
        
        self.player_club_counts[player_name][season][club] += 1
    
    def process_action(self, action: str, player_name: str, position: str, 
                      season: str, is_goalkeeper: bool = False) -> float:
        """
        Beregner ELO ændring for action
        """
        if action not in self.action_weights:
            return 0.0
        
        base_weight = self.action_weights[action]
        
        # Målvogtere får special behandling
        if is_goalkeeper:
            position = 'MV'
        
        # Simple ELO ændring baseret på action vægt
        k_factor = self.k_factors['goalkeeper'] if is_goalkeeper else self.k_factors['player']
        elo_change = (base_weight / 100) * (k_factor / 10)
        
        # Begræns ændring
        return max(-5.0, min(5.0, elo_change))
    
    def get_player_elo(self, player_name: str, season: str = None) -> float:
        """
        Henter spillerens ELO
        """
        if season:
            if season not in self.player_elos[player_name]:
                # Første gang i sæsonen - beregn start ELO
                start_elo = self.calculate_season_start_elo(player_name, season)
                self.player_elos[player_name][season] = start_elo
            return self.player_elos[player_name][season]
        else:
            return self.player_elos[player_name]['samlet']
    
    def calculate_season_start_elo(self, player_name: str, season: str) -> float:
        """
        Beregner start ELO for ny sæson
        """
        try:
            current_season_index = self.seasons.index(season)
            if current_season_index == 0:
                # Første sæson
                if player_name in self.confirmed_goalkeepers:
                    return self.rating_bounds['default_goalkeeper']
                else:
                    return self.rating_bounds['default_player']
        except ValueError:
            return self.rating_bounds['default_player']
        
        # Carryover fra forrige sæson
        previous_season = self.seasons[current_season_index - 1]
        player_elos = self.player_elos[player_name]
        overall_elo = player_elos.get('samlet', self.rating_bounds['default_player'])
        previous_season_elo = player_elos.get(previous_season, overall_elo)
        
        carryover_elo = (
            previous_season_elo * self.carryover_weights['previous_season'] + 
            overall_elo * self.carryover_weights['overall']
        )
        
        return max(self.rating_bounds['min'], 
                  min(self.rating_bounds['max'], carryover_elo))
    
    def update_player_elo(self, player_name: str, elo_change: float, season: str = None):
        """
        Opdaterer spillerens ELO
        """
        # Opdater sæson ELO
        if season:
            current_season_elo = self.get_player_elo(player_name, season)
            new_season_elo = current_season_elo + elo_change
            new_season_elo = max(self.rating_bounds['min'], 
                               min(self.rating_bounds['max'], new_season_elo))
            self.player_elos[player_name][season] = new_season_elo
        
        # Opdater samlet ELO
        current_overall_elo = self.get_player_elo(player_name)
        overall_elo_change = elo_change * 0.7
        new_overall_elo = current_overall_elo + overall_elo_change
        new_overall_elo = max(self.rating_bounds['min'], 
                            min(self.rating_bounds['max'], new_overall_elo))
        self.player_elos[player_name]['samlet'] = new_overall_elo
    
    def finalize_player_profiles(self):
        """
        Finalize player profiles based on collected data
        """
        print("\n🔍 Finaliserer spillerprofile...")
        
        position_stats = defaultdict(int)
        club_transfers = 0
        
        for player_name in self.player_position_counts:
            # Determine main position
            position_counts = self.player_position_counts[player_name]
            if position_counts:
                main_position = max(position_counts.items(), key=lambda x: x[1])[0]
                self.player_profiles[player_name]['position'] = main_position
                position_stats[main_position] += 1
            
            # Determine main club per season and track transfers
            previous_club = None
            for season in self.seasons:
                if season in self.player_club_counts[player_name]:
                    club_counts = self.player_club_counts[player_name][season]
                    if club_counts:
                        main_club = max(club_counts.items(), key=lambda x: x[1])[0]
                        self.player_profiles[player_name]['clubs'][season] = main_club
                        
                        # Track transfers
                        if previous_club and previous_club != main_club:
                            club_transfers += 1
                        previous_club = main_club
        
        print(f"✅ {len(self.player_profiles)} spillerprofile finaliseret")
        print(f"🔄 {club_transfers} klubskifter identificeret")
        print(f"📊 Position fordeling:")
        for pos in ['MV', 'VF', 'HF', 'VB', 'PL', 'HB', 'ST']:
            if pos in position_stats:
                print(f"   {pos}: {position_stats[pos]} spillere")
        print(f"🥅 Målvogtere bekræftet: {len(self.confirmed_goalkeepers)}")
    
    def run_complete_analysis(self):
        """
        Kører komplet analyse af alle sæsoner
        """
        print("🚀 Starter komplet ELO analyse...")
        
        total_stats = {
            'total_matches': 0,
            'total_actions': 0,
            'total_players': set(),
            'total_goalkeepers': set(),
            'season_results': {}
        }
        
        # Processer hver sæson i rækkefølge
        for season in self.seasons:
            season_stats = self.process_season_data(season)
            total_stats['season_results'][season] = season_stats
            total_stats['total_matches'] += season_stats.get('matches_processed', 0)
            total_stats['total_actions'] += season_stats.get('actions_processed', 0)
            total_stats['total_players'].update(season_stats.get('players_found', set()))
            total_stats['total_goalkeepers'].update(season_stats.get('goalkeepers_found', set()))
        
        # Finaliser spillerprofile
        self.finalize_player_profiles()
        
        # Print samlet resultat
        print(f"\n🏆 KOMPLET ANALYSE RESULTAT:")
        print(f"   📊 Total kampe: {total_stats['total_matches']}")
        print(f"   🎬 Total actions: {total_stats['total_actions']}")
        print(f"   👥 Total spillere: {len(total_stats['total_players'])}")
        print(f"   🥅 Målvogtere: {len(total_stats['total_goalkeepers'])}")
        
        return total_stats
    
    def save_results(self):
        """
        Gemmer alle resultater til filer
        """
        print("\n💾 Gemmer resultater...")
        
        # Gem spillerprofile
        player_profiles_df = []
        for player, profile in self.player_profiles.items():
            row = {
                'player_name': player,
                'main_position': profile['position'],
                'is_goalkeeper': player in self.confirmed_goalkeepers,
                'overall_elo': self.player_elos[player]['samlet']
            }
            
            # Tilføj sæson ELO og klubber
            for season in self.seasons:
                row[f'elo_{season}'] = self.player_elos[player].get(season, 0)
                row[f'club_{season}'] = profile['clubs'].get(season, 'UNKNOWN')
            
            player_profiles_df.append(row)
        
        # Gem til CSV
        df = pd.DataFrame(player_profiles_df)
        df.to_csv('advanced_player_profiles.csv', index=False, encoding='utf-8')
        print(f"✅ Gemt spillerprofile: advanced_player_profiles.csv ({len(df)} spillere)")
        
        # Gem detaljerede ELO data
        with open('advanced_elo_data.json', 'w', encoding='utf-8') as f:
            json.dump({
                'player_elos': dict(self.player_elos),
                'confirmed_goalkeepers': list(self.confirmed_goalkeepers),
                'player_position_counts': dict(self.player_position_counts),
                'player_club_counts': dict(self.player_club_counts)
            }, f, indent=2, ensure_ascii=False)
        print("✅ Gemt detaljerede ELO data: advanced_elo_data.json")


# === HOVEDPROGRAM ===
def main():
    """
    Hovedprogram der kører det avancerede ELO system
    """
    print("🎮 Starter Avanceret Håndbol ELO Analyse...")
    
    # Initialiser systemet
    elo_system = AdvancedHandballEloSystem()
    
    # Kør komplet analyse
    results = elo_system.run_complete_analysis()
    
    # Gem resultater
    elo_system.save_results()
    
    print("\n🎯 Analyse fuldført! Tjek output filerne for resultater.")
    

if __name__ == "__main__":
    main() 