import os
import glob
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from tqdm import tqdm # For progress bars
import logging

# --- KONFIGURATION ---
# Opdater disse stier til din lokale opsætning
KVINDELIGA_DB_BASE_PATH = r"C:\Users\jonas\Desktop\Handball-ML\Kvindeliga-database"
HERRELIGA_DB_BASE_PATH = r"C:\Users\jonas\Desktop\Handball-ML\Herreliga-database"
SEASON_TO_PROCESS = "2024-2025"
OUTPUT_CSV_PATH = r"C:\Users\jonas\Desktop\Handball-ML\handball_ml_dataset_extended.csv"
LOG_FILE_PATH = r"C:\Users\jonas\Desktop\Handball-ML\create_ml_dataset_extended.log"

FORM_WINDOWS = [3, 5, 10]
MIN_GAMES_FOR_FEATURES_OVERALL = 5
MIN_GAMES_FOR_FORM_WINDOW = 2 # Minimum kampe for at beregne en form-window feature

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE_PATH, mode='w'), # Overskriv logfil ved hver kørsel
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Holdkoder og navne (udvidet og konsistent)
TEAM_CODE_MAP = {
    "AHB": "Aarhus Håndbold Kvinder", "BFH": "Bjerringbro FH", "EHA": "EH Aalborg",
    "HHE": "Horsens Håndbold Elite", "IKA": "Ikast Håndbold", "KBH": "København Håndbold",
    "NFH": "Nykøbing F. Håndbold", "ODE": "Odense Håndbold", "RIN": "Ringkøbing Håndbold",
    "SVK": "Silkeborg-Voel KFUM", "SKB": "Skanderborg Håndbold", "SJEK": "SønderjyskE Kvindehåndbold",
    "TES": "Team Esbjerg", "VHK": "Viborg HK", "TMS": "TMS Ringsted",
    "AAH": "Aalborg Håndbold", "BSH": "Bjerringbro-Silkeborg", "FHK": "Fredericia Håndbold Klub",
    "GIF": "Grindsted GIF Håndbold", "GOG": "GOG", "KIF": "KIF Kolding",
    "MTH": "Mors-Thy Håndbold", "NSH": "Nordsjælland Håndbold", "REH": "Ribe-Esbjerg HH",
    "SAH": "SAH - Skanderborg AGF", "SKH": "Skjern Håndbold", "SJEH": "SønderjyskE Herrehåndbold",
    "TTH": "TTH Holstebro"
}
TEAM_NAME_TO_CODE_MAP = {v: k for k, v in TEAM_CODE_MAP.items()}
TEAM_NAME_VARIANTS = { # Sørg for at kanoniske navne her matcher værdierne i TEAM_CODE_MAP
    "Aarhus Håndbold Kvinder": ["Aarhus Håndbold Kvinder", "Aarhus Håndbold"],
    "EH Aalborg": ["EH Aalborg", "EHA", "Aalborg EH"],
    "Team Esbjerg": ["Team Esbjerg", "Esbjerg", "TES"],
    "Skanderborg Håndbold": ["Skanderborg Håndbold", "SKB"],
    "SAH - Skanderborg AGF": ["SAH - Skanderborg AGF", "Skanderborg AGF", "SAH", "SAH – Skanderborg AGF"],
    "Grindsted GIF Håndbold": ["Grindsted GIF Håndbold", "Grindsted GIF,_Håndbold", "Grindsted GIF", "GIF", "Grindsted GIF, Håndbold"],
    "Silkeborg-Voel KFUM": ["Silkeborg-Voel KFUM", "Voel KFUM", "Silkeborg Voel", "SVK", "Silkeborg-Voel"],
    "SønderjyskE Kvindehåndbold": ["SønderjyskE Kvindehåndbold", "SønderjyskE", "SJEK", "SønderjyskE Damer"],
    "SønderjyskE Herrehåndbold": ["SønderjyskE Herrehåndbold", "Sønderjyske Herrehåndbold", "Sønderjyske", "SJEH", "SønderjyskE Herrer"]
}

# Hændelsestyper
GOAL_EVENTS = ["Mål", "Mål på straffe"]
SHOT_EVENTS_FOR_ACCURACY = ["Mål", "Mål på straffe", "Skud reddet", "Skud forbi", "Skud på stolpe", "Straffekast reddet", "Straffekast forbi", "Straffekast på stolpe"]
TURNOVER_EVENTS = ["Fejlaflevering", "Regelfejl", "Tabt bold", "Passivt spil"]
POSITIVE_DISCIPLINARY_EVENTS = ["Tilkendt straffe"] # Hvor holdet får en fordel
NEGATIVE_DISCIPLINARY_EVENTS = ["Advarsel", "Udvisning", "Udvisning (2x)", "Rødt kort", "Rødt kort, direkte", "Blåt kort"]
KONTRA_POSITIONS = ["1:e", "2:e"] # Første og anden bølge kontra


def normalize_team_name(team_name):
    if pd.isna(team_name) or not isinstance(team_name, str): return None
    team_name_strip = team_name.strip()
    for canonical, variants in TEAM_NAME_VARIANTS.items():
        if team_name_strip in variants: return canonical
    if team_name_strip in TEAM_CODE_MAP: return TEAM_CODE_MAP[team_name_strip]
    if team_name_strip in TEAM_NAME_TO_CODE_MAP: return team_name_strip
    logger.debug(f"Holdnavn '{team_name_strip}' ikke fundet i maps, returnerer uændret.")
    return team_name_strip

def get_team_code_from_name(team_name_normalized):
    if pd.isna(team_name_normalized): return None
    return TEAM_NAME_TO_CODE_MAP.get(team_name_normalized, team_name_normalized)


class DetailedMatchStatsCalculator:
    def __init__(self, events_df, team_code, opponent_team_code):
        self.events_df = events_df
        self.team_code = team_code
        self.opponent_team_code = opponent_team_code
        self.team_events = self.events_df[self.events_df['hold'] == self.team_code].copy()
        self.opponent_events = self.events_df[self.events_df['hold'] == self.opponent_team_code].copy()

    def calculate(self):
        stats = defaultdict(float)
        if self.team_events.empty: return stats

        # Mål og skud
        team_goals = self.team_events[self.team_events['haendelse_1'].isin(GOAL_EVENTS)]
        stats['goals_scored'] = len(team_goals)
        stats['penalty_goals_scored'] = len(team_goals[team_goals['haendelse_1'] == "Mål på straffe"])
        
        total_shots_for_accuracy = self.team_events[self.team_events['haendelse_1'].isin(SHOT_EVENTS_FOR_ACCURACY)]
        stats['total_shots_taken'] = len(total_shots_for_accuracy)
        if stats['total_shots_taken'] > 0:
            stats['shooting_pct'] = stats['goals_scored'] / stats['total_shots_taken']
        
        # Kontra
        stats['kontra_goals'] = len(team_goals[team_goals['pos'].isin(KONTRA_POSITIONS)])
        if stats['goals_scored'] > 0:
            stats['kontra_goals_pct_of_total'] = stats['kontra_goals'] / stats['goals_scored']

        # Mål pr. position
        for pos in self.team_events['pos'].dropna().unique():
            pos_goals = len(team_goals[team_goals['pos'] == pos])
            stats[f'goals_pos_{str(pos).replace(":", "")}'] = pos_goals # Undgå : i kolonnenavn
            if stats['goals_scored'] > 0:
                 stats[f'goals_pct_pos_{str(pos).replace(":", "")}'] = pos_goals / stats['goals_scored']

        # Turnovers
        stats['turnovers_committed'] = len(self.team_events[self.team_events['haendelse_1'].isin(TURNOVER_EVENTS)])

        # Straffekast
        stats['penalties_awarded_to_team'] = len(self.team_events[self.team_events['haendelse_1'] == "Tilkendt straffe"])
        if stats['penalties_awarded_to_team'] > 0:
            stats['penalty_conversion_pct'] = stats['penalty_goals_scored'] / stats['penalties_awarded_to_team']
        
        # Straffekast forårsaget (af dette hold, dvs. givet til modstander)
        # Dette er når *modstanderholdet* har 'Tilkendt straffe' eller vores spillere har 'Forårs. str.' i haendelse_2
        # Her kigger vi på, hvornår MODSTANDEREN fik tildelt straffe
        stats['penalties_caused_by_team'] = len(self.opponent_events[self.opponent_events['haendelse_1'] == "Tilkendt straffe"])
        # Alternativt, hvis 'Forårs. str.' altid er på vores hold:
        # stats['penalties_caused_by_team'] += len(self.team_events[self.team_events['haendelse_2'] == "Forårs. str."])

        # Disciplin
        for neg_event in NEGATIVE_DISCIPLINARY_EVENTS:
            clean_neg_event = neg_event.lower().replace(" ", "_").replace("(", "").replace(")", "").replace(",", "")
            stats[f'discipline_{clean_neg_event}'] = len(self.team_events[self.team_events['haendelse_1'] == neg_event])
        
        # Assists (fra primær hændelse, da haendelse_2="Assist" er på samme hold)
        stats['assists_made'] = len(self.team_events[self.team_events['haendelse_2'] == "Assist"])
        if stats['goals_scored'] > 0 :
            stats['assist_to_goal_ratio'] = stats['assists_made'] / stats['goals_scored']
            
        # Bolderobringer (fra sekundær hændelse, når modstander har primær hændelse)
        stats['steals_made'] = len(self.opponent_events[self.opponent_events['haendelse_2'] == "Bold erobret"])
        
        # Blokeringer (fra sekundær hændelse)
        stats['blocks_made'] = len(self.opponent_events[self.opponent_events['haendelse_2'].isin(["Blokeret af", "Blok af (ret)"])])

        # Målmandsstats for holdet (baseret på når MODSTANDEREN skyder)
        gk_events_faced = self.opponent_events[self.opponent_events['nr_mv'].notna()] # Hændelser hvor vores målmand var involveret
        stats['gk_saves_team'] = len(gk_events_faced[gk_events_faced['haendelse_1'].isin(["Skud reddet", "Straffekast reddet"])])
        gk_goals_against_field = len(gk_events_faced[gk_events_faced['haendelse_1'] == "Mål"])
        gk_goals_against_penalty = len(gk_events_faced[gk_events_faced['haendelse_1'] == "Mål på straffe"])
        stats['gk_goals_against_team'] = gk_goals_against_field + gk_goals_against_penalty
        
        total_shots_faced_for_gk = stats['gk_saves_team'] + stats['gk_goals_against_team']
        if total_shots_faced_for_gk > 0:
            stats['gk_save_pct_team'] = stats['gk_saves_team'] / total_shots_faced_for_gk
            
        return stats

# ... (normalize_team_name, get_team_code_from_name, define_target_variable er uændrede) ...

def load_all_data(db_base_paths, season):
    """Indlæser match_info, player_statistics og match_events for alle kampe."""
    all_matches_list = []
    all_player_stats_dict = {} # key: db_path, value: player_stats_df
    all_match_events_dict = {} # key: db_path, value: match_events_df

    for base_path in db_base_paths:
        season_path = os.path.join(base_path, season)
        if not os.path.exists(season_path):
            logger.warning(f"Sti ikke fundet {season_path}")
            continue

        db_files = glob.glob(os.path.join(season_path, "*.db"))
        db_files = [f for f in db_files if not os.path.basename(f).endswith(("_stats.db", "_central.db", ".bak"))]

        for db_file in tqdm(db_files, desc=f"Indlæser data fra {os.path.basename(base_path)}/{season}"):
            try:
                conn = sqlite3.connect(db_file)
                # Match Info
                match_df = pd.read_sql_query("SELECT * FROM match_info", conn)
                if not match_df.empty:
                    match_df['db_path'] = db_file # Vigtigt for senere opslag
                    match_df['liga'] = "Kvindeliga" if "Kvindeliga" in base_path else "Herreliga"
                    all_matches_list.append(match_df)

                    # Player Statistics
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_statistics';")
                    if cursor.fetchone():
                        all_player_stats_dict[db_file] = pd.read_sql_query("SELECT * FROM player_statistics", conn)
                    else:
                        all_player_stats_dict[db_file] = pd.DataFrame()
                        logger.warning(f"Tabel 'player_statistics' mangler i {db_file}")
                    
                    # Match Events
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_events';")
                    if cursor.fetchone():
                        all_match_events_dict[db_file] = pd.read_sql_query("SELECT * FROM match_events", conn)
                    else:
                        all_match_events_dict[db_file] = pd.DataFrame()
                        logger.warning(f"Tabel 'match_events' mangler i {db_file}")
                conn.close()
            except Exception as e:
                logger.error(f"Fejl ved læsning af {db_file}: {e}")

    if not all_matches_list: return pd.DataFrame(), {}, {}

    combined_matches_df = pd.concat(all_matches_list, ignore_index=True)
    combined_matches_df['dato'] = pd.to_datetime(combined_matches_df['dato'], format='%d-%m-%Y', errors='coerce')
    combined_matches_df.dropna(subset=['dato', 'resultat', 'hold_hjemme', 'hold_ude'], inplace=True)
    
    logger.info("Normaliserer holdnavne i combined_matches_df...")
    combined_matches_df['hold_hjemme'] = combined_matches_df['hold_hjemme'].apply(normalize_team_name)
    combined_matches_df['hold_ude'] = combined_matches_df['hold_ude'].apply(normalize_team_name)
    # Drop rækker hvor normalisering fejlede (resulterede i None)
    combined_matches_df.dropna(subset=['hold_hjemme', 'hold_ude'], inplace=True)

    combined_matches_df.sort_values(by=['dato', 'kamp_id'], inplace=True)
    combined_matches_df.reset_index(drop=True, inplace=True)

    logger.info(f"Total antal kampe indlæst og sorteret: {len(combined_matches_df)}")
    return combined_matches_df, all_player_stats_dict, all_match_events_dict


def calculate_historical_team_stats(team_name_normalized, current_match_date, all_matches_df,
                                    all_player_stats_dict, all_match_events_dict, form_windows_config):
    team_code = get_team_code_from_name(team_name_normalized)
    if not team_code:
        logger.warning(f"Kunne ikke finde team_code for {team_name_normalized}. Returnerer tomme stats.")
        return {}

    team_history_df = all_matches_df[
        ((all_matches_df['hold_hjemme'] == team_name_normalized) | (all_matches_df['hold_ude'] == team_name_normalized)) &
        (all_matches_df['dato'] < current_match_date)
    ].copy()

    features = {}
    player_stat_cols_to_avg = [ # Fra player_statistics
        'goals', 'penalty_goals', 'shots_missed', 'shots_post', 'shots_blocked',
        'shots_saved', 'penalty_missed', 'penalty_post', 'penalty_saved',
        'technical_errors', 'ball_lost', 'penalties_drawn', 'assists', 'ball_stolen',
        'caused_penalty', 'blocks', 'warnings', 'suspensions', 'red_cards', 'blue_cards',
        'gk_saves', 'gk_goals_against', 'gk_penalty_saves', 'gk_penalty_goals_against', 'total_events'
    ]
    # Nye features fra DetailedMatchStatsCalculator
    detailed_stat_cols_to_avg = [
        'goals_scored', 'penalty_goals_scored', 'total_shots_taken', 'shooting_pct',
        'kontra_goals', 'kontra_goals_pct_of_total', 'turnovers_committed',
        'penalties_awarded_to_team', 'penalty_conversion_pct', 'penalties_caused_by_team',
        'assists_made', 'assist_to_goal_ratio', 'steals_made', 'blocks_made',
        'gk_saves_team', 'gk_goals_against_team', 'gk_save_pct_team'
    ] # Plus dynamiske 'goals_pos_X' og 'discipline_X'

    periods = {'overall': team_history_df}
    for fw in form_windows_config: periods[f'form_{fw}'] = team_history_df.tail(fw)

    for period_label, period_df in periods.items():
        prefix = f"{period_label}_"
        min_games_for_period = MIN_GAMES_FOR_FEATURES_OVERALL if period_label == 'overall' else MIN_GAMES_FOR_FORM_WINDOW

        if period_df.empty or len(period_df) < min_games_for_period:
            # Sæt defaults for alle features for denne periode
            features[f'{prefix}games_played'] = 0
            for stat_type in ['win_pct', 'draw_pct', 'loss_pct', 'avg_goals_for', 'avg_goals_against', 'avg_goal_diff', 'points_pct']:
                features[f'{prefix}{stat_type}'] = 0.0
            for pscol in player_stat_cols_to_avg: features[f'{prefix}avg_player_{pscol}'] = 0.0
            for dscol in detailed_stat_cols_to_avg: features[f'{prefix}avg_detailed_{dscol}'] = 0.0
            # Specifikke defaults for potentielt dynamiske kolonner
            for pos_example in ['ST', 'VF', 'HF', 'HB', 'VB', 'PL', 'Gbr', '1:e', '2:e']: # Eksempler
                 features[f'{prefix}avg_detailed_goals_pos_{pos_example}'] = 0.0
                 features[f'{prefix}avg_detailed_goals_pct_pos_{pos_example}'] = 0.0
            for disc_example in NEGATIVE_DISCIPLINARY_EVENTS:
                 clean_disc_example = disc_example.lower().replace(" ", "_").replace("(", "").replace(")", "").replace(",", "")
                 features[f'{prefix}avg_detailed_discipline_{clean_disc_example}'] = 0.0
            continue # Næste periode

        games_played_in_period = len(period_df)
        wins, draws, losses, goals_for_sum, goals_against_sum, points_sum = 0, 0, 0, 0, 0, 0
        
        period_agg_player_stats = defaultdict(float)
        period_agg_detailed_stats = defaultdict(float)
        games_with_player_stats = 0
        games_with_detailed_stats = 0

        for _, hist_match in period_df.iterrows():
            try:
                h_g, u_g = map(int, str(hist_match['resultat']).replace(" ", "").split('-'))
                is_home = hist_match['hold_hjemme'] == team_name_normalized
                
                if is_home:
                    goals_for_sum += h_g; goals_against_sum += u_g
                    if h_g > u_g: wins += 1; points_sum += 2
                    elif h_g == u_g: draws += 1; points_sum += 1
                    else: losses += 1
                else:
                    goals_for_sum += u_g; goals_against_sum += h_g
                    if u_g > h_g: wins += 1; points_sum += 2
                    elif u_g == h_g: draws += 1; points_sum += 1
                    else: losses += 1

                # Aggreger player_statistics
                player_stats_df = all_player_stats_dict.get(hist_match['db_path'])
                if player_stats_df is not None and not player_stats_df.empty:
                    current_team_player_stats = player_stats_df[player_stats_df['team_code'] == team_code]
                    if not current_team_player_stats.empty:
                        games_with_player_stats +=1
                        for pscol in player_stat_cols_to_avg:
                            period_agg_player_stats[pscol] += current_team_player_stats[pscol].sum()
                
                # Aggreger detailed_match_stats
                match_events_df = all_match_events_dict.get(hist_match['db_path'])
                if match_events_df is not None and not match_events_df.empty:
                    opponent_team_name_hist = hist_match['hold_ude'] if is_home else hist_match['hold_hjemme']
                    opponent_team_code_hist = get_team_code_from_name(opponent_team_name_hist)
                    if opponent_team_code_hist:
                        calculator = DetailedMatchStatsCalculator(match_events_df, team_code, opponent_team_code_hist)
                        detailed_stats_for_match = calculator.calculate()
                        if detailed_stats_for_match:
                            games_with_detailed_stats += 1
                            for ds_key, ds_val in detailed_stats_for_match.items():
                                period_agg_detailed_stats[ds_key] += ds_val
            except ValueError:
                games_played_in_period -= 1 # Juster hvis resultat er korrupt
                logger.warning(f"Korrupt resultat for kamp_id {hist_match['kamp_id']} for hold {team_name_normalized}")
                continue
        
        features[f'{prefix}games_played'] = games_played_in_period
        if games_played_in_period > 0:
            features[f'{prefix}win_pct'] = wins / games_played_in_period
            features[f'{prefix}draw_pct'] = draws / games_played_in_period
            features[f'{prefix}loss_pct'] = losses / games_played_in_period
            features[f'{prefix}avg_goals_for'] = goals_for_sum / games_played_in_period
            features[f'{prefix}avg_goals_against'] = goals_against_sum / games_played_in_period
            features[f'{prefix}avg_goal_diff'] = (goals_for_sum - goals_against_sum) / games_played_in_period
            features[f'{prefix}points_pct'] = points_sum / (games_played_in_period * 2)

            if games_with_player_stats > 0:
                for pscol in player_stat_cols_to_avg:
                    features[f'{prefix}avg_player_{pscol}'] = period_agg_player_stats[pscol] / games_with_player_stats
            else:
                for pscol in player_stat_cols_to_avg: features[f'{prefix}avg_player_{pscol}'] = 0.0

            if games_with_detailed_stats > 0:
                for ds_key in period_agg_detailed_stats: # Iterer over nøgler der faktisk blev talt
                    features[f'{prefix}avg_detailed_{ds_key}'] = period_agg_detailed_stats[ds_key] / games_with_detailed_stats
            else: # Sæt defaults hvis ingen detailed stats
                for dscol_template in detailed_stat_cols_to_avg: features[f'{prefix}avg_detailed_{dscol_template}'] = 0.0
                for pos_example in ['ST', 'VF', 'HF', 'HB', 'VB', 'PL', 'Gbr', '1e', '2e']: # Eksempler, fjern ":"
                     features[f'{prefix}avg_detailed_goals_pos_{pos_example}'] = 0.0
                     features[f'{prefix}avg_detailed_goals_pct_pos_{pos_example}'] = 0.0
                for disc_example in NEGATIVE_DISCIPLINARY_EVENTS:
                     clean_disc_example = disc_example.lower().replace(" ", "_").replace("(", "").replace(")", "").replace(",", "")
                     features[f'{prefix}avg_detailed_discipline_{clean_disc_example}'] = 0.0
        # ... (defaults for hvis games_played_in_period er 0, som i forrige script) ...

    # Streak features (kun 'overall' giver mening for streak)
    wins_in_a_row = 0
    losses_in_a_row = 0
    undefeated_in_a_row = 0
    if not team_history_df.empty:
        for _, row in team_history_df.iloc[::-1].iterrows(): # Gennemgå i omvendt kronologisk rækkefølge
            try:
                h_g_s, u_g_s = map(int, str(row['resultat']).replace(" ", "").split('-'))
                won = (row['hold_hjemme'] == team_name_normalized and h_g_s > u_g_s) or \
                      (row['hold_ude'] == team_name_normalized and u_g_s > h_g_s)
                lost = (row['hold_hjemme'] == team_name_normalized and h_g_s < u_g_s) or \
                       (row['hold_ude'] == team_name_normalized and u_g_s < h_g_s)

                if won:
                    wins_in_a_row += 1; losses_in_a_row = 0; undefeated_in_a_row +=1
                elif lost:
                    losses_in_a_row += 1; wins_in_a_row = 0; undefeated_in_a_row = 0
                else: # Uafgjort
                    wins_in_a_row = 0; losses_in_a_row = 0; undefeated_in_a_row +=1
            except ValueError:
                break # Stop hvis resultat er korrupt
        features['streak_wins'] = wins_in_a_row
        features['streak_losses'] = losses_in_a_row
        features['streak_undefeated'] = undefeated_in_a_row
    else:
        features['streak_wins'] = 0; features['streak_losses'] = 0; features['streak_undefeated'] = 0
            
    return features

# ... (calculate_h2h_statistics er stort set uændret, men kan udvides med flere H2H detaljer) ...
# ... (build_ml_dataset skal nu kalde den udvidede calculate_historical_team_stats) ...
# ... (main-funktionen skal nu kalde den nye load_all_data) ...

def build_ml_dataset(matches_with_target_df, all_player_stats_dict, all_match_events_dict, form_windows_config):
    ml_feature_list = []
    team_last_match_date = defaultdict(lambda: None)
    team_games_played_count_in_dataset = defaultdict(int)

    # Pre-cache team codes for performance
    cached_team_codes = {name: get_team_code_from_name(name) for name in pd.concat([matches_with_target_df['hold_hjemme'], matches_with_target_df['hold_ude']]).unique() if pd.notna(name)}

    for _, current_match in tqdm(matches_with_target_df.iterrows(), total=len(matches_with_target_df), desc="Engineering features for ML dataset"):
        home_team_name = current_match['hold_hjemme']
        away_team_name = current_match['hold_ude']
        match_date = current_match['dato']

        # Tjek om holdnavne er gyldige efter normalisering
        if pd.isna(home_team_name) or pd.isna(away_team_name):
            logger.warning(f"Skipping kamp_id {current_match['kamp_id']} due to NaN team name after normalization.")
            continue

        # Filtrer tidligt for at undgå unødvendige beregninger
        if team_games_played_count_in_dataset[home_team_name] < MIN_GAMES_FOR_FEATURES_OVERALL or \
           team_games_played_count_in_dataset[away_team_name] < MIN_GAMES_FOR_FEATURES_OVERALL:
            team_games_played_count_in_dataset[home_team_name] +=1
            team_games_played_count_in_dataset[away_team_name] +=1
            continue

        features = {
            'kamp_id': current_match['kamp_id'], 'dato': match_date, 'liga': current_match['liga'],
            'hold_hjemme_navn': home_team_name, 'hold_ude_navn': away_team_name,
            'hold_hjemme_kode': cached_team_codes.get(home_team_name),
            'hold_ude_kode': cached_team_codes.get(away_team_name)
        }
        if not features['hold_hjemme_kode'] or not features['hold_ude_kode']:
            logger.warning(f"Skipping kamp_id {current_match['kamp_id']} due to missing team code for {home_team_name} or {away_team_name}.")
            continue


        home_hist_stats = calculate_historical_team_stats(home_team_name, match_date, matches_with_target_df, all_player_stats_dict, all_match_events_dict, form_windows_config)
        for k, v in home_hist_stats.items(): features[f'h_{k}'] = v

        away_hist_stats = calculate_historical_team_stats(away_team_name, match_date, matches_with_target_df, all_player_stats_dict, all_match_events_dict, form_windows_config)
        for k, v in away_hist_stats.items(): features[f'a_{k}'] = v
        
        h2h_stats = calculate_h2h_statistics(home_team_name, away_team_name, match_date, matches_with_target_df) # calculate_h2h_statistics uændret fra forrige
        for k, v in h2h_stats.items(): features[k] = v

        if team_last_match_date[home_team_name]:
            features['h_days_since_last_match'] = (match_date - team_last_match_date[home_team_name]).days
        else: features['h_days_since_last_match'] = np.nan
        
        if team_last_match_date[away_team_name]:
            features['a_days_since_last_match'] = (match_date - team_last_match_date[away_team_name]).days
        else: features['a_days_since_last_match'] = np.nan
        
        features['month'] = match_date.month
        features['day_of_week'] = match_date.dayofweek

        # Differens-features (meget udvidet)
        # Sammenlign alle numeriske features der starter med 'h_overall_' og 'a_overall_' (eller 'h_form_X_' etc.)
        home_feature_keys = [k for k in features if k.startswith('h_')]
        for h_key in home_feature_keys:
            base_key = h_key[2:] # Fjern 'h_' prefix
            a_key = f'a_{base_key}'
            if a_key in features and isinstance(features[h_key], (int, float)) and isinstance(features[a_key], (int, float)):
                features[f'diff_{base_key}'] = features[h_key] - features[a_key]

        features['target'] = current_match['target']
        ml_feature_list.append(features)

        team_last_match_date[home_team_name] = match_date
        team_last_match_date[away_team_name] = match_date
        team_games_played_count_in_dataset[home_team_name] +=1
        team_games_played_count_in_dataset[away_team_name] +=1
        
    return pd.DataFrame(ml_feature_list)

def main():
    logger.info(f"Starter oprettelse af UDVIDET ML datasæt for sæson: {SEASON_TO_PROCESS}")
    
    db_paths_to_scan = []
    kvinde_path = os.path.join(KVINDELIGA_DB_BASE_PATH, SEASON_TO_PROCESS)
    herre_path = os.path.join(HERRELIGA_DB_BASE_PATH, SEASON_TO_PROCESS)

    if os.path.exists(kvinde_path): db_paths_to_scan.append(KVINDELIGA_DB_BASE_PATH)
    if os.path.exists(herre_path): db_paths_to_scan.append(HERRELIGA_DB_BASE_PATH)

    if not db_paths_to_scan:
        logger.error(f"Ingen database stier fundet for sæson {SEASON_TO_PROCESS}. Afslutter.")
        return

    all_matches_df, all_player_stats_dict, all_match_events_dict = load_all_data(db_paths_to_scan, SEASON_TO_PROCESS)
    if all_matches_df.empty:
        logger.error("Ingen kampdata indlæst. Afslutter.")
        return

    matches_with_target = define_target_variable(all_matches_df) # define_target_variable uændret
    if matches_with_target.empty:
        logger.error("Ingen kampe med gyldig målvariabel. Afslutter.")
        return
    logger.info(f"Antal kampe med gyldig målvariabel: {len(matches_with_target)}")

    ml_dataset_df = build_ml_dataset(matches_with_target, all_player_stats_dict, all_match_events_dict, FORM_WINDOWS)
    if ml_dataset_df.empty:
        logger.error("ML datasæt er tomt efter feature engineering. Afslutter.")
        return

    # Grundlæggende NaN håndtering (mere avanceret kan være nødvendigt)
    numeric_cols = ml_dataset_df.select_dtypes(include=np.number).columns.tolist()
    for col in numeric_cols:
        if col not in ['kamp_id', 'target', 'month', 'day_of_week']: # Undgå at ændre ID'er og target
            ml_dataset_df[col].fillna(ml_dataset_df[col].median(), inplace=True) # Imputer med median

    ml_dataset_df.dropna(subset=['target'], inplace=True) # Sørg for target ikke er NaN

    try:
        output_folder = os.path.dirname(OUTPUT_CSV_PATH)
        if output_folder and not os.path.exists(output_folder): os.makedirs(output_folder)
        ml_dataset_df.to_csv(OUTPUT_CSV_PATH, index=False, encoding='utf-8-sig', sep=';') # Brug semikolon som separator
        logger.info(f"UDVIDET ML datasæt gemt til: {OUTPUT_CSV_PATH}")
        logger.info(f"Datasæt dimensioner: {ml_dataset_df.shape}")
        
        # Print nogle diagnostiske oplysninger
        if not ml_dataset_df.empty:
            logger.info("\nEksempel på række (første):")
            logger.info(ml_dataset_df.head(1).to_string())
            logger.info(f"\nKolonner ({len(ml_dataset_df.columns)} i alt): {ml_dataset_df.columns.tolist()}")
            nan_counts = ml_dataset_df.isnull().sum()
            logger.info("\nNaN værdier pr. kolonne (hvis nogen):")
            logger.info(nan_counts[nan_counts > 0].sort_values(ascending=False).to_string())
        else:
            logger.warning("Datasættet er tomt efter al behandling.")

    except Exception as e:
        logger.error(f"Fejl ved gemning af datasæt: {e}", exc_info=True)

if __name__ == "__main__":
    # Kør `player_team_statistics.py` først for at sikre, at de nødvendige tabeller
    # `players_team` og `player_statistics` findes i hver kampdatabase.
    # Ellers vil `all_player_stats_dict` være tom, og mange features vil mangle.
    
    # Tilføj her en bekræftelse eller automatisk kørsel af forudsætningsscripts hvis muligt.
    print("ADVARSEL: Sørg for at `player_team_statistics.py` er kørt forud for dette script,")
    print("ellers vil mange features mangle, da `player_statistics` tabellerne ikke vil være til stede.")
    # input("Tryk Enter for at fortsætte, hvis du har kørt forudsætningsscripts...")
    
    # Kopier calculate_h2h_statistics fra forrige script, da den er uændret
    def calculate_h2h_statistics(home_team, away_team, current_match_date, all_matches_df):
        h2h_df = all_matches_df[
            (
                ((all_matches_df['hold_hjemme'] == home_team) & (all_matches_df['hold_ude'] == away_team)) |
                ((all_matches_df['hold_hjemme'] == away_team) & (all_matches_df['hold_ude'] == home_team))
            ) &
            (all_matches_df['dato'] < current_match_date)
        ].copy()

        features = {}
        h2h_games_played = len(h2h_df)
        features['h2h_games_played'] = h2h_games_played

        if h2h_games_played == 0:
            features['h2h_home_team_direct_win_pct'] = 0.0
            features['h2h_avg_goals_home_vs_away'] = 0.0
            features['h2h_avg_goals_away_vs_home'] = 0.0
            features['h2h_avg_goal_diff_home_vs_away'] = 0.0
            for i in range(1, 4): # Sidste 1, 2, 3 H2H resultater
                features[f'h2h_last_{i}_home_team_won'] = np.nan # Eller 0.5 for "ukendt"
            return features

        home_direct_wins = 0
        home_goals_vs_away_sum = 0
        away_goals_vs_home_sum = 0
        valid_h2h_games_for_calc = 0
        
        last_n_results_home_won = []

        for _, hist_match in h2h_df.iterrows():
            try:
                res_str = str(hist_match['resultat']).replace(" ", "")
                h_g, u_g = map(int, res_str.split('-'))
                valid_h2h_games_for_calc +=1
                
                current_iter_home_won = 0
                if hist_match['hold_hjemme'] == home_team: # `home_team` var hjemme i denne H2H kamp
                    home_goals_vs_away_sum += h_g
                    away_goals_vs_home_sum += u_g
                    if h_g > u_g: home_direct_wins += 1; current_iter_home_won = 1
                    elif h_g < u_g: current_iter_home_won = 0
                    else: current_iter_home_won = 0.5 # Uafgjort
                else: # `home_team` var ude i denne H2H kamp (dvs. `away_team` var hjemme)
                    home_goals_vs_away_sum += u_g # Mål scoret af home_team (som var ude)
                    away_goals_vs_home_sum += h_g # Mål scoret af away_team (som var hjemme)
                    if u_g > h_g: home_direct_wins += 1; current_iter_home_won = 1
                    elif u_g < h_g: current_iter_home_won = 0
                    else: current_iter_home_won = 0.5 # Uafgjort
                last_n_results_home_won.append(current_iter_home_won)
            except ValueError:
                logger.warning(f"Kunne ikke parse H2H resultat: {hist_match['resultat']} for {home_team} vs {away_team}")
                continue
        
        if valid_h2h_games_for_calc > 0:
            features['h2h_home_team_direct_win_pct'] = home_direct_wins / valid_h2h_games_for_calc
            features['h2h_avg_goals_home_vs_away'] = home_goals_vs_away_sum / valid_h2h_games_for_calc
            features['h2h_avg_goals_away_vs_home'] = away_goals_vs_home_sum / valid_h2h_games_for_calc
            features['h2h_avg_goal_diff_home_vs_away'] = (home_goals_vs_away_sum - away_goals_vs_home_sum) / valid_h2h_games_for_calc
        else: # Hvis alle H2H resultater var korrupte
            features['h2h_home_team_direct_win_pct'] = 0.0
            features['h2h_avg_goals_home_vs_away'] = 0.0
            features['h2h_avg_goals_away_vs_home'] = 0.0
            features['h2h_avg_goal_diff_home_vs_away'] = 0.0
            
        # Sidste N H2H resultater (omvendt rækkefølge for "sidste")
        last_n_results_home_won.reverse()
        for i in range(1, 4):
            if i <= len(last_n_results_home_won):
                features[f'h2h_last_{i}_home_team_won'] = last_n_results_home_won[i-1]
            else:
                features[f'h2h_last_{i}_home_team_won'] = np.nan # Eller 0.5
        return features

    main()