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

# Import player aliases
from team_config import PLAYER_NAME_ALIASES

# Princip 2: Separat Position Analyse System
class PositionAnalyzer:
    """
    Analyserer en hel sæson for at bestemme spilleres primære positioner.
    Fokuserer kun på "rene" positioner og ignorerer situationsbestemte.
    """
    def __init__(self, base_dir: str = ".", league_dir: str = "Kvindeliga-database"):
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
        print(f"📊 Starter positionsanalyse for Kvindeliga sæson {season}...")
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

    def finalize_goalkeeper_identification(self):
        """
        Anvender strengere regler for endeligt at bekræfte målmænd.
        En spiller skal have en høj procentdel af sine aktioner som målmand.
        """
        print("\n🔒 Finaliserer målmandsidentifikation med strengere regler...")
        
        truly_confirmed_goalkeepers = set()
        reclassified_players = 0

        for player_name in self.confirmed_goalkeepers:
            player_actions = self.player_positions.get(player_name)
            
            # Hvis spilleren slet ikke har nogen registrerede "rene" markspiller-aktioner, antages de at være målmand.
            if not player_actions:
                truly_confirmed_goalkeepers.add(player_name)
                continue

            total_field_actions = sum(player_actions.values())
            
            # Antag et gennemsnitligt antal målmandsaktioner. Her sætter vi et estimat.
            # For en mere præcis måling skulle vi tælle 'Skud reddet' etc.
            # Men for nu bruger vi en heuristik: Hvis markspiller-aktioner er meget få, er de sandsynligvis målmand.
            # En målmand har typisk meget få rene positionshandlinger.
            # Hvis en "målmand" har over 50 registrerede markspiller-aktioner, er det mistænkeligt.
            if total_field_actions < 50: # Justerbar tærskel
                truly_confirmed_goalkeepers.add(player_name)
            else:
                # Spilleren har for mange markspiller-aktioner til at være en dedikeret målmand.
                print(f"  - REKLASSIFICERET: {player_name} fjernet som målmand (for mange markspiller-aktioner: {total_field_actions})")
                reclassified_players += 1
        
        original_count = len(self.confirmed_goalkeepers)
        self.confirmed_goalkeepers = truly_confirmed_goalkeepers
        
        print(f"✅ Målmandsidentifikation fuldført.")
        print(f"  - {original_count} → {len(self.confirmed_goalkeepers)} målmænd efter validering.")
        print(f"  - {reclassified_players} spillere blev omklassificeret til markspillere.")

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
        # NEW: Global player database for long-term ELO memory
        self.player_career_database = {}
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
        🧠 ULTRA-INDIVIDUALISERET START RATING BEREGNING
        
        Nye faktorer inkluderet:
        1. Performance sidste sæson (final rating)
        2. Momentum sidste kampe (seneste 5 kampe vægtning)  
        3. Position-specifik progression rate
        4. Konsistens gennem sæsonen
        5. Hold-styrke og liga-sværhedsgrad
        6. Antal kampe spillet (stabilitet)
        7. Elite status (progression sværhedsgrad)
        """
        if previous_season_data is None:
            return BASE_RATING

        # Standardiser spillernavnet for at finde det i datasættet
        player_name_upper = " ".join(player_name.strip().upper().split())
        
        # Find det kanoniske navn, der matcher
        canonical_name = None
        for name, data in previous_season_data.items():
            if " ".join(name.strip().upper().split()) == player_name_upper:
                canonical_name = name
                break
        
        # Hvis spilleren ikke blev fundet i sidste sæsons data, returneres base rating
        if not canonical_name:
            return BASE_RATING
        
        player_data = previous_season_data[canonical_name]
        
        # === 1. GRUNDLAG: Sidste sæsons endelige rating ===
        final_rating = player_data.get('final_rating', BASE_RATING)
        
        # === 2. REGRESSION MOD MIDDELVÆRDIEN ===
        # Stærkere regression for spillere langt fra middelværdien
        distance_from_mean = final_rating - BASE_RATING
        regression_effect = distance_from_mean * REGRESSION_STRENGTH
        regressed_rating = final_rating - regression_effect
        
        # === 3. SPIL-VÆGTET JUSTERING (Carry-over) ===
        games_played = player_data.get('games', 0)
        carry_factor = min(games_played / MIN_GAMES_FOR_FULL_CARRY, 1.0)
        
        # Juster hvor meget af den oprindelige rating, der "bæres over"
        start_rating = (regressed_rating * carry_factor) + (BASE_RATING * (1 - carry_factor))
        
        # === 4. MOMENTUM FRA SLUTNINGEN AF SIDSTE SÆSON ===
        momentum = player_data.get('momentum_factor', 1.0)
        # Anvend momentum (kan være > 1 eller < 1)
        momentum_adjustment = (momentum - 1.0) * 50  # Justerbar effekt
        
        # === 5. KONSISTENS-FAKTOR ===
        consistency = player_data.get('rating_consistency', 50) # Højere er dårligere
        consistency_penalty = max(0, (consistency - 15)) * 1.5 # Straf for inkonsistens
        
        # === 6. POSITIONS-SPECIFIK PROGRESSION ===
        position = player_data.get('primary_position', 'Ukendt')
        progression_rate = POSITION_PROGRESSION_RATES.get(position, 1.0)
        position_bonus = (progression_rate - 1.0) * 100 # Justerbar effekt
        
        # Sammensæt den endelige start-rating
        final_start_rating = start_rating + momentum_adjustment - consistency_penalty + position_bonus

        # Sørg for at ratingen er inden for et rimeligt spænd
        final_start_rating = np.clip(
            final_start_rating,
            BASE_RATING + MIN_CARRY_PENALTY,
            BASE_RATING + MAX_CARRY_BONUS
        )
        
        return float(final_start_rating)

    def run_kvindeliga_season(self, season: str, start_ratings: Dict = None, position_analyzer: Optional[PositionAnalyzer] = None) -> Dict:
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
                if start_ratings.values():
                    print(f"📊 Rating range: {min(start_ratings.values()):.0f} - {max(start_ratings.values()):.0f}")
                    rating_spread = max(start_ratings.values()) - min(start_ratings.values())
                    print(f"📏 Rating spread: {rating_spread:.0f} points")
                
                for player_name, start_rating in start_ratings.items():
                    master_system.player_elos[player_name] = start_rating
                    # Set goalkeeper default if applicable
                    if player_name in master_system.confirmed_goalkeepers:
                        if start_rating == BASE_RATING:
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
            
            # ANVEND STRENGERE REGLER FOR AT FJERNE FEJLKLASSIFICEREDE MÅLMÆND
            if position_analyzer:
                position_analyzer.finalize_goalkeeper_identification()

            # Data containers for denne sæson
            player_elos = defaultdict(lambda: BASE_RATING)
            player_games = defaultdict(int)
            
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
        filename = f"kvindeliga_seasonal_elo_{season.replace('-', '_')}.csv"
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False, encoding='utf-8')
        
        # Print statistics
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
        Henter alle unikke spillernavne fra database-filerne for en given sæson.
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
                for unmatched_name in unmatched_current:
                    # Find det bedste match over en vis tærskel
                    best_match = None
                    highest_ratio = 0.88 # Høj tærskel for at undgå falske positiver
                    
                    # Standardiser det uoverensstemmende navn én gang
                    normalized_unmatched = self._normalize_and_get_canonical_name(unmatched_name)
                    
                    for career_name in canonical_career_names:
                        # Sammenlign de allerede normaliserede navne
                        similarity = levenshtein_ratio(normalized_unmatched, career_name)
                        if similarity > highest_ratio:
                            highest_ratio = similarity
                            best_match = career_name
                            
                    if best_match:
                        # Undgå at matche samme karriere-navn til flere nuværende navne
                        if best_match not in mapping.values():
                            mapping[unmatched_name] = best_match
                            levenshtein_matches_found += 1
                        else:
                            print(f"      ⚠️ Levenshtein-match for '{unmatched_name}' til '{best_match}' blev afvist (allerede mappet).")
        
        if levenshtein_matches_found > 0:
            print(f"    ✅ Trin 2: Fandt {levenshtein_matches_found} yderligere matches via Levenshtein.")

        # Returner den endelige mapping
        return mapping

    def run_complete_kvindeliga_analysis(self):
        """
        Kører hele ELO-analysen for alle Kvindeliga sæsoner i rækkefølge.
        """
        print("\n\n=== STARTER FULD KVINDELIGA ELO ANALYSE ===")
        print("===========================================")
        
        previous_season_player_data = {}
        
        # Første sæsonanalyse for at finde alle spillere
        position_analyzer = PositionAnalyzer(self.base_dir, league_dir="Kvindeliga-database")
        for season in self.seasons:
            position_analyzer.analyze_season(season)
            
        for season in self.seasons:
            print(f"\n--- SÆSON {season} ---")
            
            # 1. Hent alle unikke navne for den nuværende sæson
            current_season_player_names = self._get_all_player_names_for_season(season)
            print(f"  - Fundet {len(current_season_player_names)} unikke spillernavne i databasen.")
            
            # 2. Find mapping mellem nuværende navne og kanoniske navne fra forrige sæson
            player_name_mapping = self._find_player_name_mapping(current_season_player_names, previous_season_player_data)
            print(f"  - {len(player_name_mapping)} spillere matchet til forrige sæson.")
            
            # 3. Beregn start ratings for alle spillere i den nuværende sæson
            start_ratings = {}
            for current_name in current_season_player_names:
                canonical_name = player_name_mapping.get(current_name, current_name)
                
                previous_data = previous_season_player_data.get(canonical_name)
                
                start_ratings[current_name] = self.calculate_ultra_individual_start_rating(
                    player_name=current_name,
                    previous_season_data=previous_season_player_data,
                )
            
            # 4. Kør ELO-beregningen for sæsonen
            season_results = self.run_kvindeliga_season(season, start_ratings, position_analyzer)
            
            # 5. Opdater karriere-databasen med resultaterne fra denne sæson
            if season_results:
                print(f"  - Opdaterer karriere-databasen med {len(season_results)} spilleres resultater...")
                for player_name, data in season_results.items():
                    # Brug det kanoniske navn for at sikre konsistens
                    canonical_name = player_name_mapping.get(player_name, player_name)
                    previous_season_player_data[canonical_name] = data
            
        print("\n=== FULD KVINDELIGA ANALYSE FULDFØRT ===")

if __name__ == '__main__':
    # Initialiser og kør det sæson-baserede ELO system for Kvindeliga
    kvindeliga_elo_system = KvindeligaSeasonalEloSystem()
    kvindeliga_elo_system.run_complete_kvindeliga_analysis() 