#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Håndboldhændelser - Spiller-Hold Tilknytning og Spillerstatistik

Dette script gennemgår alle *individuelle* kampdatabaser (.db filer) i både
Herreliga-database og Kvindeliga-database mapperne for en given sæson og:
1. Opretter/genopbygger en 'players_team' tabel i hver database, der tilknytter
   hver unik spiller til deres hold baseret på kamphændelser i den specifikke kamp.
2. Opretter/genopbygger en 'player_statistics' tabel i hver database med
   detaljeret statistik for hver spiller baseret på hændelser i den specifikke kamp.
3. Opretter/genopbygger for hver liga/sæson en samlet statistik-database (`_stats.db`) med:
   - En tabel for hvert hold med samlet holdstatistik (baseret på match_info).
   - En tabel for hvert holds spillere med aggregeret statistik på tværs af kampe.
   - En ligatabel med standings og point.

Scriptet følger logikken beskrevet i data.md for at korrekt tildele spillere til hold
og beregne deres statistikker. Det undgår at behandle `_stats.db` og `_central.db` filer.
"""

import os
import glob
import sqlite3
import logging
import re
import time # Tilføjet for tidstagning
from collections import defaultdict, Counter
import traceback

# ======================================================
# KONFIGURATION
# ======================================================
HERRELIGA_DB_DIR = "Herreliga-database"
KVINDELIGA_DB_DIR = "Kvindeliga-database"
DIVISION_HERRER_DB_DIR = "1-Division-Herrer-database"
DIVISION_KVINDER_DB_DIR = "1-Division-Kvinder-database"
LOG_DIR = "Logs"
LOG_FILE = os.path.join(LOG_DIR, "player_team_assignment.log")

# Hændelser hvor nr_2/navn_2 tilhører det MODSATTE hold af 'hold'
OPPOSITE_TEAM_EVENTS = ["Bold erobret", "Forårs. str.", "Blokeret af", "Blok af (ret)"]

# Hændelser hvor nr_2/navn_2 tilhører SAMME hold som 'hold'
SAME_TEAM_EVENTS = ["Assist"]

# Værdier der ikke er spillernavne ( Bruges i create_players_team_table )
NOT_PLAYER_NAMES = ["Retur", "Bold erobret", "Assist", "Blokeret af", "Blok af (ret)", "Forårs. str."]

# Administrative hændelser (ikke spillerrelaterede) - Bruges i statistikberegning
ADMIN_EVENTS = ["Video Proof", "Video Proof slut", "Halvleg", "Start 1:e halvleg", "Start 2:e halvleg",
                "Fuld tid", "Kamp slut", "Time out", "Start"]

# Målvogter-relaterede hændelser (primær handling fra modstander)
GOALKEEPER_EVENTS = ["Mål", "Skud reddet", "Skud forbi", "Skud på stolpe", "Mål på straffe",
                     "Straffekast reddet", "Straffekast på stolpe", "Straffekast forbi"]

# Standard statistik-kolonner der altid skal være i player_statistics tabellen
# Format: (kolonne_navn, datatype, beskrivelse)
STANDARD_STAT_COLUMNS = [
    # Primære angrebshændelser
    ("goals", "INTEGER", "Antal mål scoret"),
    ("penalty_goals", "INTEGER", "Antal mål på straffekast"),
    ("shots_missed", "INTEGER", "Antal skud forbi mål"),
    ("shots_post", "INTEGER", "Antal skud på stolpen"),
    ("shots_blocked", "INTEGER", "Antal skud blokeret"),
    ("shots_saved", "INTEGER", "Antal skud reddet af målvogter"),
    ("penalty_missed", "INTEGER", "Antal straffekast forbi"),
    ("penalty_post", "INTEGER", "Antal straffekast på stolpen"),
    ("penalty_saved", "INTEGER", "Antal straffekast reddet"),
    ("technical_errors", "INTEGER", "Antal tekniske fejl (regelfejl, fejlaflevering)"),
    ("ball_lost", "INTEGER", "Antal gange bolden er tabt"),
    ("penalties_drawn", "INTEGER", "Antal gange tilkendt straffekast (positiv)"), # NY

    # Sekundære hændelser
    ("assists", "INTEGER", "Antal assister"),
    ("ball_stolen", "INTEGER", "Antal gange bolden er erobret"),
    ("caused_penalty", "INTEGER", "Antal gange forårsaget straffekast (negativ)"),
    ("blocks", "INTEGER", "Antal blokerede skud (fra modstander)"),

    # Disciplinære hændelser
    ("warnings", "INTEGER", "Antal advarsler (gult kort)"),
    ("suspensions", "INTEGER", "Antal udvisninger (2 min)"),
    ("red_cards", "INTEGER", "Antal røde kort"),
    ("blue_cards", "INTEGER", "Antal blå kort"),

    # Målvogterstatistik
    ("gk_saves", "INTEGER", "Antal redninger som målvogter (skud i spil)"),
    ("gk_goals_against", "INTEGER", "Antal mål indkasseret som målvogter (skud i spil)"),
    ("gk_penalty_saves", "INTEGER", "Antal straffekast reddet som målvogter"),
    ("gk_penalty_goals_against", "INTEGER", "Antal mål på straffekast indkasseret som målvogter"),

    # Total spilletid (estimeret ud fra første til sidste hændelse)
    ("total_events", "INTEGER", "Samlet antal hændelser spilleren er involveret i"),
    ("first_event_time", "TEXT", "Tid for spillerens første hændelse i kampen"),
    ("last_event_time", "TEXT", "Tid for spillerens sidste hændelse i kampen")
]

# Holdkoder til holdnavne kort
TEAM_CODE_MAP = {
    # Kvindeligaen
    "AHB": "Aarhus Håndbold Kvinder", "BFH": "Bjerringbro FH", "EHA": "EH Aalborg",
    "HHE": "Horsens Håndbold Elite", "IKA": "Ikast Håndbold", "KBH": "København Håndbold",
    "NFH": "Nykøbing F. Håndbold", "ODE": "Odense Håndbold", "RIN": "Ringkøbing Håndbold",
    "SVK": "Silkeborg-Voel KFUM", "SKB": "Skanderborg Håndbold", "SJE": "SønderjyskE Kvindehåndbold",
    "TES": "Team Esbjerg", "VHK": "Viborg HK", "TMS": "TMS Ringsted",
    # Herreligaen
    "AAH": "Aalborg Håndbold", "BSH": "Bjerringbro-Silkeborg", "FHK": "Fredericia Håndbold Klub",
    "GIF": "Grindsted GIF Håndbold", "GOG": "GOG", "KIF": "KIF Kolding",
    "MTH": "Mors-Thy Håndbold", "NSH": "Nordsjælland Håndbold", "REH": "Ribe-Esbjerg HH",
    "SAH": "SAH - Skanderborg AGF", "SKH": "Skjern Håndbold", "SJE": "SønderjyskE Herrehåndbold",
    "TTH": "TTH Holstebro"
}

# Varianter af holdnavne - map alle varianter til det kanoniske holdnavn
TEAM_NAME_VARIANTS = {
    "Silkeborg-Voel KFUM": ["Silkeborg-Voel KFUM", "Voel KFUM", "Silkeborg Voel", "SVK", "Silkeborg-Voel"],
    "EH Aalborg": ["EH Aalborg", "EHA", "Aalborg EH"],
    "Team Esbjerg": ["Team Esbjerg", "Esbjerg", "TES"],
    "Skanderborg Håndbold": ["Skanderborg Håndbold", "SKB"],
    "SAH - Skanderborg AGF": ["SAH - Skanderborg AGF", "Skanderborg AGF", "SAH", "SAH – Skanderborg AGF"],
    "Grindsted GIF Håndbold": ["Grindsted GIF Håndbold", "Grindsted GIF,_Håndbold", "Grindsted GIF", "GIF", "Grindsted GIF, Håndbold"],
    "SønderjyskE Kvindehåndbold": ["SønderjyskE Kvindehåndbold", "SønderjyskE"],
    "SønderjyskE Herrehåndbold": ["SønderjyskE Herrehåndbold", "Sønderjyske Herrehåndbold", "Sønderjyske"]
    # Tilføj flere varianter her hvis nødvendigt
}
# ======================================================

# Opret log mappe hvis den ikke findes
os.makedirs(LOG_DIR, exist_ok=True)

# Konfigurer logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, mode='w'), # Brug 'w' for at overskrive loggen ved hver kørsel
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Hjælpefunktioner ---

def normalize_team_name(team_name):
    """Normaliserer et holdnavn til den kanoniske form."""
    if not team_name: return team_name
    team_name_strip = team_name.strip()
    for canonical, variants in TEAM_NAME_VARIANTS.items():
        if team_name_strip in variants: return canonical
    if team_name_strip in TEAM_CODE_MAP: return TEAM_CODE_MAP[team_name_strip]
    return team_name_strip

def sanitize_table_name(name):
    """Konverterer en streng til et gyldigt SQLite tabelnavn."""
    if not name: return "Unknown"
    name = normalize_team_name(name)
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if re.match(r'^\d', sanitized): sanitized = 'T_' + sanitized
    return sanitized

def find_all_databases():
    """Finder alle *individuelle* kamp .db filer (undgår _stats.db, .bak, _central.db)."""
    all_dbs_raw = []
    if os.path.exists(HERRELIGA_DB_DIR):
        all_dbs_raw.extend(glob.glob(os.path.join(HERRELIGA_DB_DIR, "**", "*.db"), recursive=True))
    if os.path.exists(KVINDELIGA_DB_DIR):
        all_dbs_raw.extend(glob.glob(os.path.join(KVINDELIGA_DB_DIR, "**", "*.db"), recursive=True))
    if os.path.exists(DIVISION_HERRER_DB_DIR):
        all_dbs_raw.extend(glob.glob(os.path.join(DIVISION_HERRER_DB_DIR, "**", "*.db"), recursive=True))
    if os.path.exists(DIVISION_KVINDER_DB_DIR):
        all_dbs_raw.extend(glob.glob(os.path.join(DIVISION_KVINDER_DB_DIR, "**", "*.db"), recursive=True))

    all_dbs_filtered = [
        db for db in all_dbs_raw
        if not os.path.basename(db).endswith("_stats.db")
        and not os.path.basename(db).endswith(".bak") # Korrigeret til .bak
        and not os.path.basename(db).endswith("_central.db") # Eksplicit filtrering
    ]
    logger.info(f"Fandt {len(all_dbs_filtered)} individuelle kampdatabaser at behandle.")
    return all_dbs_filtered

def find_all_league_season_dirs():
    """Finder alle liga/sæson-mapper der indeholder individuelle kampdatabaser."""
    result = []
    # Både hovedligaer og 1. Division
    league_dirs = [
        (HERRELIGA_DB_DIR, "Herreliga"), 
        (KVINDELIGA_DB_DIR, "Kvindeliga"),
        (DIVISION_HERRER_DB_DIR, "1-Division-Herrer"),
        (DIVISION_KVINDER_DB_DIR, "1-Division-Kvinder")
    ]
    
    for base_dir, league_name in league_dirs:
        if os.path.exists(base_dir):
            for item in os.listdir(base_dir):
                path = os.path.join(base_dir, item)
                # Tjek om det er en mappe OG har format YYYY-YYYY OG indeholder relevante .db filer
                if os.path.isdir(path) and re.match(r'^\d{4}-\d{4}$', item):
                    has_game_dbs = any(
                        f.endswith(".db") and
                        not f.endswith("_stats.db") and
                        not f.endswith("_central.db") and
                        not f.endswith(".bak") # Tilføjet .bak filter
                        for f in os.listdir(path)
                    )
                    if has_game_dbs:
                        result.append((league_name, item))
    return result

# --- Kernefunktioner ---

def create_players_team_table(db_path):
    """
    Opretter/genopbygger 'players_team' tabellen i en database baseret på hændelser.

    Args:
        db_path (str): Sti til databasefilen.

    Returns:
        bool: True hvis succesfuld, ellers False.
    """
    logger.info(f"Opdaterer 'players_team' i: {os.path.basename(db_path)}")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Tjek om nødvendig tabel 'match_events' eksisterer
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_events'")
        if not cursor.fetchone():
            logger.warning(f"'match_events' tabel mangler i {db_path}. Springer over.")
            return False # Kan ikke fortsætte uden match_events

        cursor.execute("DROP TABLE IF EXISTS players_team")
        cursor.execute("""
        CREATE TABLE players_team (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_number INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            team_code TEXT NOT NULL,
            occurrences INTEGER NOT NULL,
            UNIQUE(player_number, player_name, team_code)
        )""")

        cursor.execute("SELECT DISTINCT hold FROM match_events WHERE hold IS NOT NULL AND hold != ''")
        team_codes = [row[0] for row in cursor.fetchall()]

        if len(team_codes) < 2:
            logger.warning(f"Utilstrækkelige holdkoder ({len(team_codes)}) fundet i {db_path}. Springer over.")
            return False # Kræver mindst to hold for at bestemme modstander
        logger.debug(f"Holdkoder i {os.path.basename(db_path)}: {', '.join(team_codes)}")

        player_team_counts = defaultdict(Counter) # {(nr, navn): {holdkode: count}}

        # 1. Primære hændelser (nr_1, navn_1) - Spiller tilhører 'hold'
        admin_placeholders = ','.join(['?'] * len(ADMIN_EVENTS))
        sql_primary = f"""
        SELECT hold, nr_1, navn_1, COUNT(*) FROM match_events
        WHERE hold IS NOT NULL AND hold != '' AND nr_1 IS NOT NULL AND nr_1 > 0 AND navn_1 IS NOT NULL AND navn_1 != ''
        AND haendelse_1 NOT IN ({admin_placeholders})
        GROUP BY hold, nr_1, navn_1
        """
        cursor.execute(sql_primary, ADMIN_EVENTS)
        for team_code, nr, name, count in cursor.fetchall():
            if name not in NOT_PLAYER_NAMES:
                player_team_counts[(nr, name)][team_code] += count

        # 2. Sekundære hændelser (nr_2, navn_2) - SAME_TEAM_EVENTS
        for event_type in SAME_TEAM_EVENTS:
            cursor.execute("""
            SELECT hold, nr_2, navn_2, COUNT(*) FROM match_events
            WHERE hold IS NOT NULL AND hold != '' AND nr_2 IS NOT NULL AND nr_2 > 0 AND navn_2 IS NOT NULL AND navn_2 != '' AND haendelse_2 = ?
            GROUP BY hold, nr_2, navn_2
            """, (event_type,))
            for team_code, nr, name, count in cursor.fetchall():
                if name not in NOT_PLAYER_NAMES:
                    player_team_counts[(nr, name)][team_code] += count

        # 3. Sekundære hændelser (nr_2, navn_2) - OPPOSITE_TEAM_EVENTS
        for event_type in OPPOSITE_TEAM_EVENTS:
            cursor.execute("""
            SELECT hold, nr_2, navn_2, COUNT(*) FROM match_events
            WHERE hold IS NOT NULL AND hold != '' AND nr_2 IS NOT NULL AND nr_2 > 0 AND navn_2 IS NOT NULL AND navn_2 != '' AND haendelse_2 = ?
            GROUP BY hold, nr_2, navn_2
            """, (event_type,))
            for team_code, nr, name, count in cursor.fetchall():
                # Find modstanderholdet
                opposite_team = next((tc for tc in team_codes if tc != team_code), None)
                if opposite_team and name not in NOT_PLAYER_NAMES:
                    player_team_counts[(nr, name)][opposite_team] += count

        # 4. Målvogtere (nr_mv, mv) - Tilhører det MODSATTE hold af 'hold'
        gk_placeholders = ','.join(['?'] * len(GOALKEEPER_EVENTS))
        sql_gk = f"""
        SELECT hold, nr_mv, mv, COUNT(*) FROM match_events
        WHERE hold IS NOT NULL AND hold != '' AND nr_mv IS NOT NULL AND nr_mv > 0 AND mv IS NOT NULL AND mv != ''
        AND haendelse_1 IN ({gk_placeholders})
        GROUP BY hold, nr_mv, mv
        """
        cursor.execute(sql_gk, GOALKEEPER_EVENTS)
        for team_code, nr, name, count in cursor.fetchall():
             # Find modstanderholdet
            opposite_team = next((tc for tc in team_codes if tc != team_code), None)
            if opposite_team and name not in NOT_PLAYER_NAMES:
                player_team_counts[(nr, name)][opposite_team] += count

        # 5. Indsæt spillertilknytninger
        player_assignments = 0
        for (nr, name), counts in player_team_counts.items():
            if counts:
                # Find det hold, spilleren oftest er associeret med
                most_common_team, occurrences = counts.most_common(1)[0]
                try:
                    cursor.execute("""
                    INSERT INTO players_team (player_number, player_name, team_code, occurrences)
                    VALUES (?, ?, ?, ?)
                    """, (nr, name, most_common_team, occurrences))
                    player_assignments += 1
                except sqlite3.IntegrityError:
                    logger.warning(f"Duplikat i {db_path}: Spiller {name}(#{nr}) på hold {most_common_team}. Ignoreret.")
                except Exception as insert_e:
                     logger.error(f"Fejl ved indsættelse i players_team for {name}(#{nr}): {insert_e}")

        conn.commit()
        logger.info(f"Opdateret 'players_team' i {os.path.basename(db_path)} med {player_assignments} unikke spiller/hold-relationer.")
        return True

    except sqlite3.OperationalError as op_e:
        logger.error(f"Database operationel fejl i {db_path} (create_players_team_table): {op_e}")
        return False
    except Exception as e:
        logger.error(f"Generel fejl i create_players_team_table for {db_path}: {e}\n{traceback.format_exc()}")
        return False
    finally:
        if conn: conn.close()

def create_player_statistics_table(db_path):
    """
    Opretter/genopbygger 'player_statistics' tabellen med detaljeret statistik for hver spiller.

    Args:
        db_path (str): Sti til databasefilen.

    Returns:
        bool: True hvis succesfuld, ellers False.
    """
    logger.info(f"Opdaterer 'player_statistics' i: {os.path.basename(db_path)}")
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Tjek om nødvendige tabeller eksisterer
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_events'")
        if not cursor.fetchone():
            logger.warning(f"'match_events' tabel mangler i {db_path}. Springer statistik over.")
            conn.close()
            return False # Kan ikke fortsætte uden match_events
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players_team'")
        if not cursor.fetchone():
            logger.warning(f"'players_team' tabel mangler i {db_path}. Springer statistik over.")
            conn.close()
            return False # Kan ikke fortsætte uden players_team

        cursor.execute("DROP TABLE IF EXISTS player_statistics")
        # Opret tabel dynamisk baseret på STANDARD_STAT_COLUMNS
        columns_sql = ",\n".join([f"    `{col_name}` {col_type} DEFAULT 0" for col_name, col_type, _ in STANDARD_STAT_COLUMNS]) # Brug backticks for sikkerhed
        create_sql = f"""
        CREATE TABLE player_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            `player_number` INTEGER NOT NULL,
            `player_name` TEXT NOT NULL,
            `team_code` TEXT NOT NULL,
        {columns_sql},
            UNIQUE(player_number, player_name, team_code)
        )"""
        cursor.execute(create_sql)

        cursor.execute("SELECT player_number, player_name, team_code FROM players_team")
        players = cursor.fetchall()
        if not players:
            logger.warning(f"Ingen spillere fundet i 'players_team' for {db_path}. Springer statistik over.")
            conn.close()
            return True # Ikke en fejl, bare ingen spillere

        logger.debug(f"Beregner statistik for {len(players)} spillere i {os.path.basename(db_path)}")

        admin_placeholders = ','.join(['?'] * len(ADMIN_EVENTS))
        for player_number, player_name, team_code in players:
            # Initialiser statistik for denne spiller
            # --- START RETTELSE ---
            stats = {col_name: 0 for col_name, col_type, _ in STANDARD_STAT_COLUMNS if col_type != "TEXT"}
            # --- SLUT RETTELSE ---
            # Tilføj tekstfelter manuelt, da de ikke skal have 0 som default
            stats["first_event_time"] = "99.99"
            stats["last_event_time"] = "0.00"

            # --- Hent og tæl hændelser ---
            # 1. Primære (nr_1)
            sql_primary = f"""SELECT haendelse_1, tid FROM match_events
                           WHERE nr_1 = ? AND navn_1 = ? AND haendelse_1 NOT IN ({admin_placeholders})"""
            cursor.execute(sql_primary, (player_number, player_name) + tuple(ADMIN_EVENTS))
            for event_type, event_time in cursor.fetchall():
                stats["total_events"] += 1
                try:
                    if event_time: # Sikrer at tid ikke er None
                        time_val = float(event_time)
                        # Brug try-except for konvertering af stats-tid også
                        try:
                            if time_val < float(stats["first_event_time"]): stats["first_event_time"] = event_time
                        except (ValueError, TypeError): pass # Ignorer hvis first_event_time er None/ugyldig
                        try:
                            if time_val > float(stats["last_event_time"]): stats["last_event_time"] = event_time
                        except (ValueError, TypeError): pass # Ignorer hvis last_event_time er None/ugyldig
                except (ValueError, TypeError): pass # Ignorer ugyldige tider

                # Opdater statistik-tællere
                if event_type == "Mål": stats["goals"] += 1
                elif event_type == "Mål på straffe": stats["penalty_goals"] += 1
                elif event_type == "Skud forbi": stats["shots_missed"] += 1
                elif event_type == "Skud på stolpe": stats["shots_post"] += 1
                elif event_type == "Skud blokeret": stats["shots_blocked"] += 1
                elif event_type == "Skud reddet": stats["shots_saved"] += 1
                elif event_type == "Straffekast forbi": stats["penalty_missed"] += 1
                elif event_type == "Straffekast på stolpe": stats["penalty_post"] += 1
                elif event_type == "Straffekast reddet": stats["penalty_saved"] += 1
                elif event_type in ["Regelfejl", "Fejlaflevering"]: stats["technical_errors"] += 1
                elif event_type == "Tabt bold": stats["ball_lost"] += 1
                elif event_type == "Tilkendt straffe": stats["penalties_drawn"] += 1 # NY
                elif event_type == "Advarsel": stats["warnings"] += 1
                elif event_type == "Udvisning" or event_type == "Udvisning (2x)": stats["suspensions"] += 1
                elif event_type == "Rødt kort" or event_type == "Rødt kort, direkte": stats["red_cards"] += 1
                elif event_type == "Blåt kort": stats["blue_cards"] += 1

            # 2. Sekundære (nr_2)
            cursor.execute("SELECT haendelse_2, tid FROM match_events WHERE nr_2 = ? AND navn_2 = ?", (player_number, player_name))
            for event_type, event_time in cursor.fetchall():
                stats["total_events"] += 1
                try:
                    if event_time:
                        time_val = float(event_time)
                        # Brug try-except for konvertering af stats-tid også
                        try:
                            if time_val < float(stats["first_event_time"]): stats["first_event_time"] = event_time
                        except (ValueError, TypeError): pass # Ignorer hvis first_event_time er None/ugyldig
                        try:
                             if time_val > float(stats["last_event_time"]): stats["last_event_time"] = event_time
                        except (ValueError, TypeError): pass # Ignorer hvis last_event_time er None/ugyldig
                except (ValueError, TypeError): pass

                if event_type == "Assist": stats["assists"] += 1
                elif event_type == "Bold erobret": stats["ball_stolen"] += 1
                elif event_type == "Forårs. str.": stats["caused_penalty"] += 1
                elif event_type in ["Blokeret af", "Blok af (ret)"]: stats["blocks"] += 1

            # 3. Målvogter (nr_mv)
            cursor.execute("SELECT haendelse_1, tid FROM match_events WHERE nr_mv = ? AND mv = ?", (player_number, player_name))
            for event_type, event_time in cursor.fetchall():
                 stats["total_events"] += 1
                 try:
                     if event_time:
                         time_val = float(event_time)
                         # Brug try-except for konvertering af stats-tid også
                         try:
                             if time_val < float(stats["first_event_time"]): stats["first_event_time"] = event_time
                         except (ValueError, TypeError): pass # Ignorer hvis first_event_time er None/ugyldig
                         try:
                             if time_val > float(stats["last_event_time"]): stats["last_event_time"] = event_time
                         except (ValueError, TypeError): pass # Ignorer hvis last_event_time er None/ugyldig
                 except (ValueError, TypeError): pass

                 # Tæl målvogter hændelser baseret på MODSTANDERENS primære hændelse
                 if event_type == "Skud reddet": stats["gk_saves"] += 1
                 elif event_type == "Mål": stats["gk_goals_against"] += 1
                 elif event_type == "Straffekast reddet": stats["gk_penalty_saves"] += 1
                 elif event_type == "Mål på straffe": stats["gk_penalty_goals_against"] += 1

            # --- Indsæt statistik ---
            # Håndter start/slut tid hvis ingen hændelser
            if stats["first_event_time"] == "99.99": stats["first_event_time"] = None
            if stats["last_event_time"] == "0.00": stats["last_event_time"] = None

            # Byg INSERT statement dynamisk
            stat_cols = [f"`{col[0]}`" for col in STANDARD_STAT_COLUMNS] # Brug backticks
            stat_placeholders = ', '.join(['?'] * len(stat_cols))
            insert_sql = f"""INSERT INTO player_statistics
                          (`player_number`, `player_name`, `team_code`, {', '.join(stat_cols)})
                          VALUES (?, ?, ?, {stat_placeholders})"""
            # Hent værdier fra stats dict, brug None for tekstfelter der ikke blev initialiseret
            params = [player_number, player_name, team_code] + [stats.get(col[0], None) for col in STANDARD_STAT_COLUMNS]
            try:
                cursor.execute(insert_sql, params)
            except sqlite3.IntegrityError:
                 logger.warning(f"Duplikat statistik i {db_path}: Spiller {player_name}(#{player_number}). Ignoreret.")
            except Exception as insert_e:
                 logger.error(f"Fejl ved indsættelse i player_statistics for {player_name}(#{player_number}): {insert_e}")

        conn.commit()
        logger.info(f"Opdateret 'player_statistics' i {os.path.basename(db_path)} for {len(players)} spillere.")
        return True

    except sqlite3.OperationalError as op_e:
        logger.error(f"Database operationel fejl i {db_path} (create_player_statistics_table): {op_e}")
        return False
    except Exception as e:
        logger.error(f"Generel fejl i create_player_statistics_table for {db_path}: {e}\n{traceback.format_exc()}")
        return False
    finally:
        if conn: conn.close()

def create_aggregated_db(league_type, season):
    """
    Opretter/genopbygger en samlet statistik-database for en liga/sæson.

    Args:
        league_type (str): "Herreliga" eller "Kvindeliga".
        season (str): Sæson i format "YYYY-YYYY".

    Returns:
        bool: True hvis succesfuld, ellers False.
    """
    logger.info(f"Starter aggregering for {league_type} {season}")
    # Find den korrekte base mappe baseret på league_type
    if league_type == "Herreliga":
        base_db_dir = HERRELIGA_DB_DIR
    elif league_type == "Kvindeliga":
        base_db_dir = KVINDELIGA_DB_DIR
    elif league_type == "1-Division-Herrer":
        base_db_dir = DIVISION_HERRER_DB_DIR
    elif league_type == "1-Division-Kvinder":
        base_db_dir = DIVISION_KVINDER_DB_DIR
    else:
        logger.error(f"Ukendt league_type: {league_type}")
        return False
    db_dir = os.path.join(base_db_dir, season)
    output_db_path = os.path.join(db_dir, f"{league_type.lower()}_{season.replace('-', '_')}_stats.db")

    # Backup og slet eksisterende
    if os.path.exists(output_db_path):
        backup_path = output_db_path + ".bak"
        try:
            # Slet gammel backup hvis den findes
            if os.path.exists(backup_path):
                os.remove(backup_path)
            os.replace(output_db_path, backup_path)
            logger.info(f"Backup oprettet: {backup_path}")
        except Exception as e:
            logger.warning(f"Kunne ikke lave backup af {output_db_path}: {e}")
            try: os.remove(output_db_path)
            except Exception as rem_e: logger.error(f"Kunne heller ikke slette {output_db_path}: {rem_e}")

    # Find individuelle kamp-DBs i den specifikke sæsonmappe
    game_dbs = [os.path.join(db_dir, f) for f in os.listdir(db_dir)
                if f.endswith(".db") and not f.endswith("_stats.db") and not f.endswith(".bak") and not f.endswith("_central.db")]

    if not game_dbs:
        logger.warning(f"Ingen kampdatabaser fundet i {db_dir} til aggregering.")
        return False
    logger.info(f"Aggregerer data fra {len(game_dbs)} kampdatabaser.")

    # Data strukturer
    teams_data = {}         # {team_name: {stats}}
    players_data = {}       # {team_code: {(nr, navn): {stats}}}
    # Start med kendte koder og tilføj dynamisk
    # Brug defaultdict for at undgå KeyError ved første indsættelse
    teams_code_map = defaultdict(lambda: None, TEAM_CODE_MAP)

    # Bearbejd hver kampdatabase
    for game_db in game_dbs:
        conn_game = None
        try:
            logger.debug(f"Bearbejder kamp: {os.path.basename(game_db)}")
            conn_game = sqlite3.connect(game_db)
            cursor_game = conn_game.cursor()

            # Hent kamp info
            cursor_game.execute("SELECT hold_hjemme, hold_ude, resultat FROM match_info")
            match_info = cursor_game.fetchone()
            if not match_info:
                logger.warning(f"Ingen match_info fundet i {os.path.basename(game_db)}")
                continue
            hjemme, ude, res = match_info
            hjemme_norm = normalize_team_name(hjemme)
            ude_norm = normalize_team_name(ude)

            # Opdater holdstatistik (sejr/tab/uafgjort, mål)
            process_match_result(teams_data, hjemme_norm, ude_norm, res)

            # Hent holdkoder og opdater map
            cursor_game.execute("SELECT DISTINCT hold FROM match_events WHERE hold IS NOT NULL AND hold != ''")
            for code, in cursor_game.fetchall():
                if code not in teams_code_map and code in TEAM_CODE_MAP:
                     teams_code_map[code] = normalize_team_name(TEAM_CODE_MAP[code])
                elif code not in teams_code_map:
                     # Hvis koden ikke er kendt, prøv at gætte baseret på kampinfo
                     if code in hjemme_norm: teams_code_map[code] = hjemme_norm
                     elif code in ude_norm: teams_code_map[code] = ude_norm
                     else: logger.warning(f"Ukendt holdkode '{code}' fundet i {os.path.basename(game_db)}")

            # Hent spillerstatistik
            cursor_game.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_statistics'")
            if cursor_game.fetchone():
                cursor_game.execute("SELECT * FROM player_statistics")
                columns = [desc[0] for desc in cursor_game.description]
                for row in cursor_game.fetchall():
                    p_stats = dict(zip(columns, row))
                    nr, name, code = p_stats.get('player_number'), p_stats.get('player_name'), p_stats.get('team_code')

                    if not nr or not name or not code:
                        logger.warning(f"Manglende spillerinfo i række i {os.path.basename(game_db)}: {p_stats}")
                        continue

                    p_key = (nr, name)
                    # Initialiser hold-dict for spillerdata hvis det ikke findes
                    if code not in players_data: players_data[code] = {}
                    # Initialiser spiller-dict hvis det ikke findes
                    if p_key not in players_data[code]:
                        players_data[code][p_key] = {'player_number': nr, 'player_name': name, 'team_code': code, 'games_played': 0}
                        # Initialiser alle numeriske statistikfelter til 0
                        for col, c_type, _ in STANDARD_STAT_COLUMNS:
                            if c_type != "TEXT": players_data[code][p_key][col] = 0

                    # Opdater spilantal og statistik
                    players_data[code][p_key]['games_played'] += 1
                    for col, c_type, _ in STANDARD_STAT_COLUMNS:
                        if c_type != "TEXT" and col in p_stats and p_stats[col] is not None:
                            try:
                                # Konverter til int før addition for at undgå typefejl
                                players_data[code][p_key][col] += int(p_stats[col])
                            except (ValueError, TypeError):
                                logger.warning(f"Kunne ikke konvertere statistik '{col}' ({p_stats[col]}) til tal for {name} i {os.path.basename(game_db)}")

            else:
                 logger.warning(f"Ingen 'player_statistics' tabel fundet i {os.path.basename(game_db)}")


        except sqlite3.Error as db_err:
            logger.error(f"Databasefejl ved behandling af {os.path.basename(game_db)}: {db_err}")
        except Exception as e:
            logger.error(f"Generel fejl ved behandling af {os.path.basename(game_db)}: {e}\n{traceback.format_exc()}")
        finally:
            if conn_game: conn_game.close()

    # Opret og skriv til aggregeret database
    conn_agg = None
    try:
        conn_agg = sqlite3.connect(output_db_path)
        cursor_agg = conn_agg.cursor()

        # 1. Opret ligatabel
        create_league_table(cursor_agg, teams_data, teams_code_map, league_type)

        # 2. Opret hold-specifikke tabeller (stats + spillere)
        process_team_and_player_data(cursor_agg, teams_data, players_data, teams_code_map)

        conn_agg.commit()
        logger.info(f"Samlet statistikdatabase oprettet: {output_db_path}")
        return True

    except Exception as e:
        logger.error(f"Fejl ved oprettelse af aggregeret database {output_db_path}: {e}\n{traceback.format_exc()}")
        return False
    finally:
        if conn_agg: conn_agg.close()


def process_match_result(teams_data, hold_hjemme, hold_ude, resultat):
    """Bearbejder kampresultat for at opdatere holdstatistikker (sejre/tab/mål)."""
    # Initialiser hold-data hvis det ikke findes
    if hold_hjemme not in teams_data: teams_data[hold_hjemme] = {'played': 0, 'win': 0, 'draw': 0, 'loss': 0, 'goals_for': 0, 'goals_against': 0, 'points': 0, 'code': ""}
    if hold_ude not in teams_data: teams_data[hold_ude] = {'played': 0, 'win': 0, 'draw': 0, 'loss': 0, 'goals_for': 0, 'goals_against': 0, 'points': 0, 'code': ""}

    try:
        res_clean = resultat.strip().replace(" ", "") # Fjern mellemrum
        if not re.match(r'^\d+-\d+$', res_clean):
            logger.error(f"Ugyldigt resultatformat '{resultat}' for {hold_hjemme} vs {hold_ude}")
            return

        h_goals, u_goals = map(int, res_clean.split('-'))

        # Opdater statistik
        teams_data[hold_hjemme]['played'] += 1
        teams_data[hold_ude]['played'] += 1
        teams_data[hold_hjemme]['goals_for'] += h_goals
        teams_data[hold_hjemme]['goals_against'] += u_goals
        teams_data[hold_ude]['goals_for'] += u_goals
        teams_data[hold_ude]['goals_against'] += h_goals

        # Pointtildeling
        if h_goals > u_goals:
            teams_data[hold_hjemme]['win'] += 1; teams_data[hold_hjemme]['points'] += 2
            teams_data[hold_ude]['loss'] += 1
        elif h_goals < u_goals:
            teams_data[hold_ude]['win'] += 1; teams_data[hold_ude]['points'] += 2
            teams_data[hold_hjemme]['loss'] += 1
        else:
            teams_data[hold_hjemme]['draw'] += 1; teams_data[hold_hjemme]['points'] += 1
            teams_data[hold_ude]['draw'] += 1; teams_data[hold_ude]['points'] += 1
    except Exception as e:
        logger.error(f"Kunne ikke parse resultat '{resultat}' for {hold_hjemme} vs {hold_ude}: {e}")

def create_league_table(cursor, teams_data, teams_code_map, league_type):
    """Opretter ligatabel (standings) i den aggregerede database."""
    table_name = "Herreligaen" if league_type == "Herreliga" else "Kvindeligaen"
    safe_table_name = sanitize_table_name(table_name)

    cursor.execute(f'DROP TABLE IF EXISTS `{safe_table_name}`') # Brug backticks
    cursor.execute(f'''CREATE TABLE `{safe_table_name}` (
        id INTEGER PRIMARY KEY AUTOINCREMENT, `team_name` TEXT NOT NULL, `team_code` TEXT,
        `played` INTEGER NOT NULL DEFAULT 0, `win` INTEGER NOT NULL DEFAULT 0, `draw` INTEGER NOT NULL DEFAULT 0, `loss` INTEGER NOT NULL DEFAULT 0,
        `goals_for` INTEGER NOT NULL DEFAULT 0, `goals_against` INTEGER NOT NULL DEFAULT 0, `goal_difference` INTEGER NOT NULL DEFAULT 0, `points` INTEGER NOT NULL DEFAULT 0
    )''')

    # Sorter hold baseret på point, målforskel, scorede mål
    teams_sorted = sorted(teams_data.items(),
                          key=lambda x: (int(x[1].get('points', 0)), # Point
                                         int(x[1].get('goals_for', 0)) - int(x[1].get('goals_against', 0)), # Målforskel
                                         int(x[1].get('goals_for', 0))), # Flest scorede mål
                          reverse=True)

    # Indsæt data for hvert hold
    for team_name, stats in teams_sorted:
        # Find holdkoden, enten fra stats eller ved opslag
        team_code = stats.get('code') or next((c for c, n in teams_code_map.items() if normalize_team_name(n) == team_name), "")
        goal_diff = stats.get('goals_for', 0) - stats.get('goals_against', 0)
        cursor.execute(f'''INSERT INTO `{safe_table_name}`
            (`team_name`, `team_code`, `played`, `win`, `draw`, `loss`, `goals_for`, `goals_against`, `goal_difference`, `points`)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (team_name, team_code, stats.get('played', 0), stats.get('win', 0), stats.get('draw', 0), stats.get('loss', 0),
             stats.get('goals_for', 0), stats.get('goals_against', 0), goal_diff, stats.get('points', 0)))

def process_team_and_player_data(cursor, teams_data, players_data, teams_code_map):
    """Opretter hold-specifikke statistik- og spillertabeller i den aggregerede database."""
    for team_code, players in players_data.items():
        try:
            # Find og normaliser holdnavn
            team_name = teams_code_map.get(team_code, team_code)
            team_name_norm = normalize_team_name(team_name)
            safe_team_name = sanitize_table_name(team_name_norm)
            player_table_name = f"{safe_team_name}_players"

            # 1. Opret/indsæt holdstatistik (kun 1 række per hold)
            cursor.execute(f'DROP TABLE IF EXISTS `{safe_team_name}`')
            cursor.execute(f'''CREATE TABLE `{safe_team_name}` (
                id INTEGER PRIMARY KEY, `team_name` TEXT NOT NULL, `team_code` TEXT NOT NULL, `played` INTEGER DEFAULT 0, `win` INTEGER DEFAULT 0,
                `draw` INTEGER DEFAULT 0, `loss` INTEGER DEFAULT 0, `goals_for` INTEGER DEFAULT 0, `goals_against` INTEGER DEFAULT 0,
                `goal_difference` INTEGER DEFAULT 0, `points` INTEGER DEFAULT 0
            )''')
            team_stats = teams_data.get(team_name_norm, {}) # Hent holdets samlede stats
            goal_diff = team_stats.get('goals_for', 0) - team_stats.get('goals_against', 0)
            cursor.execute(f'''INSERT INTO `{safe_team_name}` (id, `team_name`, `team_code`, `played`, `win`, `draw`, `loss`,
                           `goals_for`, `goals_against`, `goal_difference`, `points`) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                           (team_name_norm, team_code, team_stats.get('played', 0), team_stats.get('win', 0), team_stats.get('draw', 0),
                            team_stats.get('loss', 0), team_stats.get('goals_for', 0), team_stats.get('goals_against', 0),
                            goal_diff, team_stats.get('points', 0)))

            # 2. Opret spillertabel
            cursor.execute(f'DROP TABLE IF EXISTS `{player_table_name}`')
            # Byg CREATE TABLE dynamisk for spillere
            stat_cols_agg = ",\n".join([f"    `{col[0]}` INTEGER NOT NULL DEFAULT 0" for col in STANDARD_STAT_COLUMNS if col[1] != 'TEXT']) # Kun numeriske
            cursor.execute(f"""CREATE TABLE `{player_table_name}` (
                id INTEGER PRIMARY KEY AUTOINCREMENT, `player_number` INTEGER NOT NULL, `player_name` TEXT NOT NULL,
                `team_code` TEXT NOT NULL, `games_played` INTEGER NOT NULL DEFAULT 0,
                {stat_cols_agg},
                UNIQUE(player_number, player_name)
            )""")

            # Sortér spillere efter nummer for konsistens
            sorted_players = sorted(players.items(), key=lambda item: int(item[0][0]) if str(item[0][0]).isdigit() else 999)

            # Indsæt spillerdata
            for (nr, name), stats in sorted_players:
                columns = ["player_number", "player_name", "team_code", "games_played"]
                values = [nr, name, team_code, stats.get("games_played", 0)]
                # Tilføj alle numeriske statistik-kolonner
                for col, c_type, _ in STANDARD_STAT_COLUMNS:
                    if c_type != "TEXT":
                        columns.append(col)
                        values.append(stats.get(col, 0)) # Brug 0 hvis stat mangler

                # Byg og kør INSERT
                cols_str = ", ".join(f'`{c}`' for c in columns) # Brug backticks
                placeholders = ", ".join(["?"] * len(columns))
                cursor.execute(f'INSERT INTO `{player_table_name}` ({cols_str}) VALUES ({placeholders})', values)

        except Exception as e:
            logger.error(f"Fejl ved oprettelse af tabel for hold {team_code} ({team_name_norm}): {e}\n{traceback.format_exc()}")

def create_all_aggregated_dbs():
    """Finder alle liga/sæson-mapper og opretter/opdaterer aggregerede databaser."""
    league_seasons = find_all_league_season_dirs()
    if not league_seasons:
        logger.warning("Ingen liga/sæson-mapper fundet til aggregering.")
        return 0
    logger.info(f"Fandt {len(league_seasons)} liga/sæson-mapper at aggregere: {league_seasons}")

    success_count = 0
    for league_type, season in league_seasons:
        if create_aggregated_db(league_type, season):
            success_count += 1
    return success_count

# --- Main Execution ---

def main():
    """Hovedfunktion der behandler alle individuelle databaser og opretter aggregerede."""
    overall_start_time = time.time() # Start tidtagning
    logger.info("==== Starter Spiller/Hold Tilknytning & Statistik Opdatering ====")

    # Find alle individuelle kampdatabaser
    all_dbs = find_all_databases()
    if not all_dbs:
        logger.warning("Ingen individuelle kampdatabaser fundet. Afslutter.")
        print("Ingen individuelle kampdatabaser fundet.")
        return

    players_team_success, players_team_failed = 0, 0
    statistics_success, statistics_failed = 0, 0

    # Behandl hver individuel database
    for db_path in all_dbs:
        # 1. Opdater players_team tabel
        if create_players_team_table(db_path):
            players_team_success += 1
            # 2. Opdater player_statistics tabel (kun hvis players_team lykkedes)
            if create_player_statistics_table(db_path):
                statistics_success += 1
            else:
                statistics_failed += 1
        else:
            players_team_failed += 1
            # Hvis players_team fejler, kan statistik heller ikke laves
            statistics_failed += 1

    logger.info("---- Individuel Database Behandling Afsluttet ----")
    logger.info(f"Behandlet {len(all_dbs)} databaser:")
    logger.info(f"  - 'players_team': {players_team_success} succes, {players_team_failed} fejl")
    logger.info(f"  - 'player_statistics': {statistics_success} succes, {statistics_failed} fejl")

    # Opret/Opdater aggregerede statistikdatabaser
    logger.info("==== Starter Aggregeret Statistik Database Opdatering ====")
    agg_success_count = create_all_aggregated_dbs()
    logger.info(f"==== Aggregering Afsluttet ({agg_success_count} databaser opdateret) ====")

    overall_end_time = time.time() # Slut tidtagning
    total_duration = overall_end_time - overall_start_time

    # Vis resultat i terminalen
    print("\n==== Spiller/Hold Tilknytning & Statistik Opdatering Afsluttet ====")
    print(f"Total køretid: {total_duration:.2f} sekunder") # Vis total køretid
    print(f"\nIndividuelle kampdatabaser ({len(all_dbs)} behandlet):")
    print(f"  - 'players_team' tabel: {players_team_success} succes, {players_team_failed} fejl")
    print(f"  - 'player_statistics' tabel: {statistics_success} succes, {statistics_failed} fejl")
    print(f"\nAggregerede statistikdatabaser:")
    print(f"  - {agg_success_count} databaser oprettet/opdateret")
    print(f"\nSe {LOG_FILE} for detaljer.")

if __name__ == "__main__":
    main()