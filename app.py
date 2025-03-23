from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import sqlite3
import glob
import pandas as pd
import platform
import logging
from pathlib import Path
from collections import defaultdict

app = Flask(__name__)

# Konfiguration af logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='handball_admin.log'
)
logger = logging.getLogger('handball_admin')

# Konstanter fra players.py
# Værdier der ikke er spillernavne
NOT_PLAYER_NAMES = ["Retur", "Bold erobret", "Assist", "Blokeret af", "Blok af (ret)", "Forårs. str."]

# Hændelser hvor nr_2/navn_2 tilhører det MODSATTE hold af 'hold'
OPPOSITE_TEAM_EVENTS = ["Bold erobret", "Forårs. str.", "Blokeret af", "Blok af (ret)"]

# Hændelser hvor nr_2/navn_2 tilhører SAMME hold som 'hold'
SAME_TEAM_EVENTS = ["Assist"]

# Fast kortlægning af holdkoder til holdnavne baseret på den korrekte liste
TEAM_CODE_MAP = {
    "AHB": "Aarhus Håndbold Kvinder",
    "BFH": "Bjerringbro FH",
    "EHA": "EH Aalborg",
    "HHE": "Horsens Håndbold Elite",
    "IKA": "Ikast Håndbold",
    "KBH": "København Håndbold",
    "NFH": "Nykøbing F. Håndbold",
    "ODE": "Odense Håndbold",
    "RIN": "Ringkøbing Håndbold",
    "SVK": "Silkeborg-Voel KFUM",
    "SKB": "Skanderborg Håndbold",
    "SJE": "SønderjyskE Kvindehåndbold",
    "TES": "Team Esbjerg",
    "VHK": "Viborg HK",
    "TMS": "TMS Ringsted",
    # Herreliga-koder kan tilføjes efter behov
    "AAH": "Aalborg Håndbold",
    "KIF": "KIF Kolding",
    "GOG": "GOG",
    "BSH": "Bjerringbro-Silkeborg",
    "FHK": "Fredericia Håndbold Klub",
    "TTH": "TTH Holstebro",
    "MTH": "Mors-Thy Håndbold",
    "REH": "Ribe-Esbjerg HH",
    "NSH": "Nordsjælland Håndbold",
    "SAH": "SAH - Skanderborg AGF",
    "SKH": "Skjern Håndbold",
    "GIF": "Grindsted GIF Håndbold",
    "SJE": "Sønderjyske Herrehåndbold"
}

# Kombiner mulige varianter af holdnavne (til normalisering)
TEAM_NAME_VARIANTS = {
    "Silkeborg-Voel KFUM": ["Silkeborg-Voel KFUM", "Voel KFUM", "Silkeborg Voel", "Silkeborg-Voel"]
}

# Platform-specifik stihåndtering
if platform.system() == 'Windows':
    HERRELIGA_DB_DIR = os.path.join("Herreliga-database", "2024-2025")
    KVINDELIGA_DB_DIR = os.path.join("Kvindeliga-database", "2024-2025")
else:
    HERRELIGA_DB_DIR = os.path.join("Herreliga-database", "2024-2025")
    KVINDELIGA_DB_DIR = os.path.join("Kvindeliga-database", "2024-2025")

# Sti til liga-databaser
HERRELIGA_CENTRAL_DB = os.path.join("Herreliga-database", "herreliga_central.db")
KVINDELIGA_CENTRAL_DB = os.path.join("Kvindeliga-database", "kvindeliga_central.db")

def normalize_team_name(team_name):
    """
    Normaliserer et holdnavn til den kanoniske form
    """
    if not team_name:
        return team_name
        
    for canonical, variants in TEAM_NAME_VARIANTS.items():
        if team_name in variants:
            return canonical
    return team_name

# Hjælpefunktioner
def get_all_databases():
    """Finder alle databasefiler fra begge mapper"""
    # Sikrer at mapperne eksisterer
    if not os.path.exists(HERRELIGA_DB_DIR):
        logger.warning(f"Mappe ikke fundet: {HERRELIGA_DB_DIR}")
        herreliga_dbs = []
    else:
        herreliga_dbs = glob.glob(os.path.join(HERRELIGA_DB_DIR, "*.db"))
    
    if not os.path.exists(KVINDELIGA_DB_DIR):
        logger.warning(f"Mappe ikke fundet: {KVINDELIGA_DB_DIR}")
        kvindeliga_dbs = []
    else:
        kvindeliga_dbs = glob.glob(os.path.join(KVINDELIGA_DB_DIR, "*.db"))
    
    # Formaterer til visning
    herreliga_dbs = [{"path": db, "name": os.path.basename(db), "league": "Herreliga"} 
                     for db in herreliga_dbs]
    kvindeliga_dbs = [{"path": db, "name": os.path.basename(db), "league": "Kvindeliga"} 
                      for db in kvindeliga_dbs]
    
    logger.info(f"Fandt {len(herreliga_dbs)} Herreliga-databaser og {len(kvindeliga_dbs)} Kvindeliga-databaser")
    return herreliga_dbs + kvindeliga_dbs

def get_table_names(db_path):
    """Henter alle tabelnavne i en database"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        conn.close()
        return [table[0] for table in tables]
    except sqlite3.Error as e:
        logger.error(f"Fejl ved hentning af tabelnavne fra {db_path}: {e}")
        return []

def get_table_data(db_path, table_name):
    """Henter alle data fra en tabel som en pandas DataFrame"""
    try:
        conn = sqlite3.connect(db_path)
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
        conn.close()
        return df
    except sqlite3.Error as e:
        logger.error(f"Fejl ved hentning af data fra {db_path}/{table_name}: {e}")
        return pd.DataFrame()

def get_all_unique_teams():
    """Henter alle unikke holdnavne og holdkoder på tværs af alle databaser"""
    all_teams = set()
    databases = get_all_databases()
    
    for db in databases:
        try:
            conn = sqlite3.connect(db['path'])
            cursor = conn.cursor()
            
            # Tilføj alle holdkoder fra match_events
            try:
                cursor.execute("SELECT DISTINCT hold FROM match_events WHERE hold IS NOT NULL")
                team_codes = cursor.fetchall()
                for team in team_codes:
                    if team[0] and team[0].strip():  # Undgå None eller tomme værdier
                        all_teams.add(team[0].strip())
            except sqlite3.OperationalError:
                pass
            
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Fejl ved hentning af hold fra {db['path']}: {e}")
    
    # Tilføj også alle kendte holdkoder fra kortlægningen
    for code in TEAM_CODE_MAP.keys():
        all_teams.add(code)
    
    logger.info(f"Fandt {len(all_teams)} unikke hold")
    return sorted(list(all_teams))

def get_team_players(team_code):
    """
    Henter alle spillere for et specifikt hold på tværs af alle databaser.
    Implementeret baseret på samme logik som players.py
    
    Args:
        team_code: Holdkoden (f.eks. "EHA", "ODE", etc.)
        
    Returns:
        list: Liste over spillere for holdet
    """
    # Det komplette sæt af alle spillere for dette hold
    all_players = defaultdict(set)
    
    # Antal forekomster af hver spiller
    player_counts = defaultdict(int)
    
    # Find team_name hvis team_code er i kortlægningen
    target_team_name = TEAM_CODE_MAP.get(team_code)
    
    databases = get_all_databases()
    logger.info(f"Søger efter spillere for hold {team_code} ({target_team_name if target_team_name else 'ukendt navn'}) i {len(databases)} databaser")
    
    processed_dbs = 0
    # Processer hver database
    for db in databases:
        try:
            conn = sqlite3.connect(db['path'])
            cursor = conn.cursor()
            
            # 1. Hent kampinformation for at finde hold
            try:
                cursor.execute("SELECT kamp_id, hold_hjemme, hold_ude, dato FROM match_info")
                match_info = cursor.fetchone()
                
                if not match_info:
                    conn.close()
                    continue
                
                kamp_id, hold_hjemme, hold_ude, kamp_dato = match_info
                
                # Normaliser holdnavne
                hold_hjemme = normalize_team_name(hold_hjemme)
                hold_ude = normalize_team_name(hold_ude)
                
                # 2. Find alle holdkoder i kampen
                cursor.execute("SELECT DISTINCT hold FROM match_events WHERE hold IS NOT NULL")
                team_codes = [row[0] for row in cursor.fetchall()]
                
                # 3. Forbind holdkoder med holdnavne fra TEAM_CODE_MAP
                match_team_codes = {}
                
                for code in team_codes:
                    if code in TEAM_CODE_MAP:
                        team_name = TEAM_CODE_MAP[code]
                        
                        # Tjek om dette hold er et af holdene i kampen
                        if team_name == hold_hjemme or team_name == hold_ude:
                            match_team_codes[code] = team_name
                
                # Hvis vi ikke kunne finde alle holdkoder, prøv at gætte baseret på antal mål
                if len(match_team_codes) < len(team_codes):
                    unassigned_codes = [code for code in team_codes if code not in match_team_codes]
                    
                    if len(unassigned_codes) > 0 and len(match_team_codes) > 0:
                        # Find hold, der endnu ikke har en kode
                        assigned_teams = set(match_team_codes.values())
                        unassigned_teams = []
                        if hold_hjemme not in assigned_teams:
                            unassigned_teams.append(hold_hjemme)
                        if hold_ude not in assigned_teams:
                            unassigned_teams.append(hold_ude)
                        
                        # Tæl mål for hver uassigneret holdkode
                        code_goals = {}
                        for code in unassigned_codes:
                            cursor.execute("""
                            SELECT COUNT(*) FROM match_events 
                            WHERE hold = ? AND (haendelse_1 = 'Mål' OR haendelse_1 = 'Mål på straffe')
                            """, (code,))
                            goals = cursor.fetchone()[0]
                            code_goals[code] = goals
                        
                        # Sortér koder efter antal mål
                        sorted_codes = sorted(code_goals.items(), key=lambda x: x[1], reverse=True)
                        
                        # Tildel koder til hold
                        if len(sorted_codes) > 0 and len(unassigned_teams) > 0:
                            if len(sorted_codes) >= len(unassigned_teams):
                                for i, team in enumerate(unassigned_teams):
                                    match_team_codes[sorted_codes[i][0]] = team
                
                # Tjek om vores målhold er med i denne kamp
                target_team_in_match = False
                target_code = None
                
                # Check 1: Er vores holdkode direkte i match_team_codes?
                if team_code in match_team_codes:
                    target_team_in_match = True
                    target_code = team_code
                
                # Check 2: Er vores holdnavn et af holdene i kampen?
                elif target_team_name:
                    if target_team_name == hold_hjemme or target_team_name == hold_ude:
                        target_team_in_match = True
                        # Find holdkoden for vores holdnavn
                        for code, name in match_team_codes.items():
                            if name == target_team_name:
                                target_code = code
                                break
                
                # Hvis vores hold ikke er med i denne kamp, gå videre til næste database
                if not target_team_in_match:
                    conn.close()
                    continue
                
                # Hold styr på hvilket hold der er modstanderholdet
                opposite_team = hold_hjemme if hold_ude == target_team_name else hold_ude
                
                # Hjælpefunktion til at få det modsatte hold
                def get_opposite_team(team_code):
                    team = match_team_codes.get(team_code)
                    if team == hold_hjemme:
                        return hold_ude
                    elif team == hold_ude:
                        return hold_hjemme
                    return None
                
                processed_dbs += 1
                logger.info(f"Fandt hold {target_team_name} i kamp {kamp_id} i database {db['path']}")
                
                # Nu da vi har fundet holdkoder og vores målhold, kan vi hente spillerne
                # 1. Udtrække spillere fra primære hændelser (nr_1, navn_1)
                if target_code:
                    cursor.execute("""
                    SELECT nr_1, navn_1 FROM match_events 
                    WHERE hold = ? 
                      AND nr_1 IS NOT NULL AND nr_1 > 0 
                      AND navn_1 IS NOT NULL AND navn_1 != ''
                      AND haendelse_1 NOT IN ('Video Proof', 'Video Proof slut', 'Halvleg', 'Start 1:e halvleg', 'Start 2:e halvleg')
                    """, (target_code,))
                    
                    for nr, navn in cursor.fetchall():
                        if navn not in NOT_PLAYER_NAMES:
                            all_players[nr].add(navn)
                            player_counts[(nr, navn)] += 1
                    
                    # 2. Udtrække spillere fra sekundære hændelser (nr_2, navn_2)
                    cursor.execute("""
                    SELECT hold, nr_2, navn_2, haendelse_2 FROM match_events 
                    WHERE (hold = ? OR hold != ?)
                      AND nr_2 IS NOT NULL AND nr_2 > 0 
                      AND navn_2 IS NOT NULL AND navn_2 != '' 
                      AND haendelse_2 IS NOT NULL
                    """, (target_code, target_code))
                    
                    for hndl_code, nr, navn, event in cursor.fetchall():
                        if navn not in NOT_PLAYER_NAMES:
                            is_player_from_team = False
                            
                            if hndl_code == target_code and event in SAME_TEAM_EVENTS:
                                # Samme hold (f.eks. Assist)
                                is_player_from_team = True
                            elif hndl_code != target_code and event in OPPOSITE_TEAM_EVENTS:
                                # Modstanderhold (f.eks. Bold erobret)
                                is_player_from_team = True
                            
                            if is_player_from_team:
                                all_players[nr].add(navn)
                                player_counts[(nr, navn)] += 1
                
                # 3. Udtrække målvogtere (nr_mv, mv) - de tilhører det MODSATTE hold
                cursor.execute("""
                SELECT hold, nr_mv, mv FROM match_events 
                WHERE hold IS NOT NULL 
                  AND nr_mv IS NOT NULL AND nr_mv > 0
                  AND mv IS NOT NULL AND mv != ''
                  AND haendelse_1 IN ('Mål', 'Skud reddet', 'Skud forbi', 'Skud på stolpe', 'Mål på straffe', 'Straffekast reddet')
                """)
                
                for hndl_code, nr, navn in cursor.fetchall():
                    if navn not in NOT_PLAYER_NAMES:
                        # Tjek om dette er en målvogter fra vores hold (når modstanderholdet skyder)
                        if hndl_code != target_code:
                            # Når modstanderholdet skyder, er målvogteren fra vores hold
                            all_players[nr].add(navn)
                            player_counts[(nr, navn)] += 1
            
            except sqlite3.OperationalError as e:
                logger.warning(f"Fejl ved læsning af data fra {db['path']}: {e}")
            
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Fejl ved adgang til database {db['path']}: {e}")
    
    logger.info(f"Gennemgik {processed_dbs} databaser med hold {team_code}")
    
    # Konverter til liste af ordbøger for lettere brug i skabeloner
    player_list = []
    
    for nr, names in all_players.items():
        for name in names:
            count = player_counts[(nr, name)]
            
            # Vi tager alle spillere der optræder - men kunne filtrere efter antal hvis nødvendigt
            player_list.append({
                "number": nr, 
                "name": name, 
                "databases": count
            })
    
    # Sortér efter nummer (konverterer til int hvis muligt)
    def get_player_number(player):
        try:
            return int(player["number"])
        except (ValueError, TypeError):
            return 999
    
    player_list.sort(key=get_player_number)
    
    logger.info(f"Fandt {len(player_list)} spillere for hold {team_code}")
    return player_list

def update_player_name(old_name, new_name, team_code):
    """
    Opdaterer en spillers navn på tværs af alle databaser
    
    Args:
        old_name (str): Det nuværende navn
        new_name (str): Det nye navn
        team_code (str): Holdkoden
        
    Returns:
        bool: True hvis opdateringen var succesfuld
    """
    databases = get_all_databases()
    success = True
    updated_count = 0
    
    for db in databases:
        try:
            conn = sqlite3.connect(db['path'])
            cursor = conn.cursor()
            
            try:
                # 1. Opdater primære hændelser
                cursor.execute("""
                    UPDATE match_events 
                    SET navn_1 = ? 
                    WHERE hold = ? AND navn_1 = ?
                """, (new_name, team_code, old_name))
                updated_count += cursor.rowcount
                
                # 2. Opdater sekundære hændelser - for SAME_TEAM_EVENTS
                for event_type in SAME_TEAM_EVENTS:
                    cursor.execute("""
                        UPDATE match_events 
                        SET navn_2 = ? 
                        WHERE hold = ? AND navn_2 = ? AND haendelse_2 = ?
                    """, (new_name, team_code, old_name, event_type))
                    updated_count += cursor.rowcount
                
                # 3. Opdater sekundære hændelser - for OPPOSITE_TEAM_EVENTS
                for event_type in OPPOSITE_TEAM_EVENTS:
                    cursor.execute("""
                        UPDATE match_events 
                        SET navn_2 = ? 
                        WHERE hold != ? AND navn_2 = ? AND haendelse_2 = ?
                    """, (new_name, team_code, old_name, event_type))
                    updated_count += cursor.rowcount
                
                # 4. Opdater målvogtere (fra det modsatte hold)
                cursor.execute("""
                    UPDATE match_events 
                    SET mv = ? 
                    WHERE hold != ? AND mv = ?
                    AND haendelse_1 IN ('Mål', 'Skud reddet', 'Skud forbi', 'Skud på stolpe', 
                                  'Mål på straffe', 'Straffekast reddet')
                """, (new_name, team_code, old_name))
                updated_count += cursor.rowcount
                
                conn.commit()
            except sqlite3.OperationalError as e:
                logger.error(f"Fejl ved opdatering af spiller i {db['path']}: {e}")
                success = False
                conn.rollback()
            
            conn.close()
        except sqlite3.Error as e:
            logger.error(f"Fejl ved adgang til database {db['path']}: {e}")
            success = False
    
    logger.info(f"Opdaterede spillernavn {old_name} til {new_name} for hold {team_code}. Succes: {success}, Poster opdateret: {updated_count}")
    return success

# Tilføj nye funktioner til at håndtere central spillerdatabase

def create_or_update_central_db(league_type="herreliga"):
    """
    Opretter eller opdaterer den centrale spillerdatabase for den angivne liga
    
    Args:
        league_type: Enten "herreliga" eller "kvindeliga"
    """
    if league_type.lower() == "herreliga":
        central_db_path = HERRELIGA_CENTRAL_DB
        db_dir = HERRELIGA_DB_DIR
    else:
        central_db_path = KVINDELIGA_CENTRAL_DB
        db_dir = KVINDELIGA_DB_DIR
    
    logger.info(f"Opretter/opdaterer central database for {league_type} i {central_db_path}")
    
    # Opret forbindelse til den centrale database
    try:
        # Fjern den eksisterende database hvis den findes
        if os.path.exists(central_db_path):
            os.remove(central_db_path)
            logger.info(f"Slettet eksisterende database: {central_db_path}")
        
        conn = sqlite3.connect(central_db_path)
        cursor = conn.cursor()
        
        # Opretter tabeller hvis de ikke findes
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS teams (
            team_code TEXT PRIMARY KEY,
            team_name TEXT NOT NULL,
            league TEXT NOT NULL
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_number INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            team_code TEXT NOT NULL,
            occurrence_count INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (team_code) REFERENCES teams (team_code),
            UNIQUE (player_number, player_name, team_code)
        )
        """)
        
        # Indsæt alle kendte hold i teams tabellen
        for code, name in TEAM_CODE_MAP.items():
            cursor.execute("""
            INSERT OR REPLACE INTO teams (team_code, team_name, league)
            VALUES (?, ?, ?)
            """, (code, name, league_type))
        
        conn.commit()
        
        # Dictionary til at holde styr på hvor mange gange en spiller optræder på hvert hold
        # format: {(player_number, player_name): {team_code: count}}
        player_team_counts = {}
        
        # Find alle databasefiler i den angivne mappe
        if not os.path.exists(db_dir):
            logger.error(f"Database mappe findes ikke: {db_dir}")
            return False
        
        db_files = glob.glob(os.path.join(db_dir, "*.db"))
        logger.info(f"Fandt {len(db_files)} databasefiler i {db_dir}")
        
        # Gennemgå hver database og tæl spillerforekomster
        for db_file in db_files:
            logger.info(f"Behandler kamp fra {os.path.basename(db_file)}")
            
            try:
                # Brug en modificeret version af get_team_players til at finde spillere
                for team_code in get_all_team_codes_from_db(db_file):
                    if team_code not in TEAM_CODE_MAP:
                        continue  # Spring over hold, vi ikke kender
                    
                    player_counts = get_player_counts_for_team(db_file, team_code)
                    
                    # Opdater den globale spillertælling
                    for player_key, count in player_counts.items():
                        if player_key not in player_team_counts:
                            player_team_counts[player_key] = {}
                        
                        if team_code not in player_team_counts[player_key]:
                            player_team_counts[player_key][team_code] = 0
                        
                        player_team_counts[player_key][team_code] += count
            
            except Exception as e:
                logger.error(f"Fejl ved behandling af {db_file}: {e}")
        
        # Logning af FRANDSEN spillere før groupering
        for (num, name), team_counts in player_team_counts.items():
            if "FRANDSEN" in name:
                logger.info(f"FØR GROUPERING: Spiller {name} (#{num}) fundet på hold: " + 
                           ", ".join([f"{code}={count}" for code, count in team_counts.items()]))
        
        # For hver spiller, find det hold hvor de optræder hyppigst
        # Dictionary til at tjekke om en spiller allerede er tilknyttet et hold
        # Format: {(player_name): (team_code, count)}
        player_primary_team = {}
        
        # Sorter alle spillere efter deres samlede antal forekomster (faldende)
        # Dette sikrer at spillere der forekommer oftere (og derfor er mere "sikre") behandles først
        all_players = []
        for (player_number, player_name), team_counts in player_team_counts.items():
            total_count = sum(team_counts.values())
            all_players.append(((player_number, player_name), team_counts, total_count))
        
        all_players.sort(key=lambda x: x[2], reverse=True)
        
        # Tildel hver spiller til det hold, hvor de hyppigst optræder
        for (player_number, player_name), team_counts, total_count in all_players:
            # Ændring: Inkluder alle spillere, selv dem med kun 1 forekomst
            if not team_counts:
                continue  # Spring kun over, hvis der ikke er nogen forekomster overhovedet
            
            # Find det hold med højeste antal forekomster
            primary_team = max(team_counts.items(), key=lambda x: x[1])
            team_code, occurrence_count = primary_team
            
            # Tjek om spilleren allerede eksisterer med et andet nummer på et andet hold
            if player_name in player_primary_team:
                existing_team, existing_count = player_primary_team[player_name]
                
                # Hvis spilleren forekommer hyppigere på det nuværende hold, opdater tilknytningen
                if occurrence_count > existing_count:
                    logger.info(f"Spiller {player_name} findes hyppigere på {team_code} ({occurrence_count}) end på {existing_team} ({existing_count})")
                    player_primary_team[player_name] = (team_code, occurrence_count)
            else:
                player_primary_team[player_name] = (team_code, occurrence_count)
        
        # Logning af FRANDSEN spillere efter tildeling til primære hold
        for name, (team, count) in player_primary_team.items():
            if "FRANDSEN" in name:
                logger.info(f"EFTER TILDELING: Spiller {name} er tildelt til hold {team} med {count} forekomster")
        
        # Nu indsætter vi spillerne i databasen, kun på deres primære hold
        for (player_number, player_name), team_counts, _ in all_players:
            name_primary_team = player_primary_team.get(player_name)
            if not name_primary_team:
                continue
                
            primary_team_code, occurrence_count = name_primary_team
            
            # Ændring: Indsæt alle spillere på deres primære hold, uanset antallet af forekomster
            if team_counts.get(primary_team_code, 0) > 0:  # Sikrer at spilleren har mindst 1 forekomst på holdet
                try:
                    cursor.execute("""
                    INSERT INTO players 
                    (player_number, player_name, team_code, occurrence_count) 
                    VALUES (?, ?, ?, ?)
                    """, (player_number, player_name, primary_team_code, occurrence_count))
                    
                    # Log indsættelse af TMS-spillere og FRANDSEN-spillere
                    if "FRANDSEN" in player_name or primary_team_code == "TMS":
                        logger.info(f"INDSÆTTELSE: Spiller {player_name} (#{player_number}) indsat i database på hold {primary_team_code} med {occurrence_count} forekomster")
                        
                except sqlite3.Error as e:
                    logger.error(f"Fejl ved indsættelse af spiller {player_name}: {e}")
        
        conn.commit()
        logger.info(f"Central database for {league_type} opdateret med succes")
        return True
    
    except sqlite3.Error as e:
        logger.error(f"Databasefejl ved oprettelse af central database: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def get_all_team_codes_from_db(db_path):
    """Henter alle holdkoder fra en database"""
    team_codes = set()
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find holdkoder fra match_events
        cursor.execute("SELECT DISTINCT hold FROM match_events WHERE hold IS NOT NULL")
        for row in cursor.fetchall():
            if row[0] and row[0].strip():
                team_codes.add(row[0].strip())
        
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Fejl ved hentning af holdkoder fra {db_path}: {e}")
    
    return team_codes

def get_player_counts_for_team(db_path, team_code):
    """
    Henter antal forekomster for hver spiller for et givet hold i en database
    
    Returns:
        dict: {(player_number, player_name): count}
    """
    player_counts = {}
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. Hent kampinformation
        try:
            cursor.execute("SELECT kamp_id, hold_hjemme, hold_ude FROM match_info")
            match_info = cursor.fetchone()
            
            if not match_info:
                conn.close()
                return player_counts
            
            kamp_id, hold_hjemme, hold_ude = match_info
            
            # Tjek om holdet er med i kampen (via TEAM_CODE_MAP)
            team_in_match = False
            team_name = TEAM_CODE_MAP.get(team_code)
            
            if team_name and (team_name == hold_hjemme or team_name == hold_ude):
                team_in_match = True
            
            if not team_in_match:
                conn.close()
                return player_counts
            
            # Primære spillere
            cursor.execute("""
                SELECT nr_1, navn_1, COUNT(*) as count
                FROM match_events 
                WHERE hold = ? 
                AND nr_1 IS NOT NULL AND nr_1 > 0 
                AND navn_1 IS NOT NULL AND navn_1 != ''
                AND haendelse_1 NOT IN ('Video Proof', 'Video Proof slut', 'Halvleg', 'Start 1:e halvleg', 'Start 2:e halvleg')
                GROUP BY nr_1, navn_1
            """, (team_code,))
            
            for nr, navn, count in cursor.fetchall():
                if navn not in NOT_PLAYER_NAMES:
                    player_key = (nr, navn)
                    if player_key not in player_counts:
                        player_counts[player_key] = 0
                    player_counts[player_key] += count
            
            # Sekundære spillere - SAME_TEAM_EVENTS
            for event_type in SAME_TEAM_EVENTS:
                cursor.execute("""
                    SELECT nr_2, navn_2, COUNT(*) as count
                    FROM match_events 
                    WHERE hold = ? 
                    AND nr_2 IS NOT NULL AND nr_2 > 0 
                    AND navn_2 IS NOT NULL AND navn_2 != ''
                    AND haendelse_2 = ?
                    GROUP BY nr_2, navn_2
                """, (team_code, event_type))
                
                for nr, navn, count in cursor.fetchall():
                    if navn not in NOT_PLAYER_NAMES:
                        player_key = (nr, navn)
                        if player_key not in player_counts:
                            player_counts[player_key] = 0
                        player_counts[player_key] += count
            
            # Målvogtere fra modstanderhændelser
            cursor.execute("""
                SELECT nr_mv, mv, COUNT(*) as count
                FROM match_events 
                WHERE hold != ? 
                AND nr_mv IS NOT NULL AND nr_mv > 0
                AND mv IS NOT NULL AND mv != ''
                AND haendelse_1 IN ('Mål', 'Skud reddet', 'Skud forbi', 'Skud på stolpe', 
                             'Mål på straffe', 'Straffekast reddet')
                GROUP BY nr_mv, mv
            """, (team_code,))
            
            for nr, navn, count in cursor.fetchall():
                if navn not in NOT_PLAYER_NAMES:
                    player_key = (nr, navn)
                    if player_key not in player_counts:
                        player_counts[player_key] = 0
                    player_counts[player_key] += count
        
        except sqlite3.Error as e:
            logger.error(f"SQL-fejl i get_player_counts_for_team: {e}")
        
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Fejl ved forbindelse til database {db_path}: {e}")
    
    return player_counts

def get_players_from_central_db(team_code, league_type="herreliga"):
    """
    Henter spillere for et specifikt hold fra den centrale database
    
    Args:
        team_code: Holdkoden
        league_type: Enten "herreliga" eller "kvindeliga"
        
    Returns:
        list: Liste over spillere for holdet
    """
    player_list = []
    
    if league_type.lower() == "herreliga":
        central_db_path = HERRELIGA_CENTRAL_DB
    else:
        central_db_path = KVINDELIGA_CENTRAL_DB
    
    if not os.path.exists(central_db_path):
        logger.error(f"Central database for {league_type} findes ikke: {central_db_path}")
        return player_list
    
    try:
        conn = sqlite3.connect(central_db_path)
        cursor = conn.cursor()
        
        # Log alle spillere i databasen for at se, om Sebastian FRANDSEN er til stede
        cursor.execute("SELECT player_name, team_code FROM players WHERE player_name LIKE '%FRANDSEN%'")
        frandsen_players = cursor.fetchall()
        for player, team in frandsen_players:
            logger.info(f"Fandt FRANDSEN-spiller i central database: {player} på hold {team}")
        
        # Log antal spillere pr. hold
        cursor.execute("SELECT team_code, COUNT(*) FROM players GROUP BY team_code")
        team_counts = cursor.fetchall()
        for tc, count in team_counts:
            logger.info(f"Hold {tc} har {count} spillere i central database")
        
        # Hent spillere for det specifikke hold
        cursor.execute("""
            SELECT player_number, player_name, occurrence_count
            FROM players
            WHERE team_code = ?
            ORDER BY player_number
        """, (team_code,))
        
        for row in cursor.fetchall():
            player_number, player_name, count = row
            player_list.append({
                "number": player_number,
                "name": player_name,
                "databases": count  # Vi beholder samme navn for at undgå at ændre skabelonen
            })
            
            # Log hver spiller vi finder
            logger.info(f"Fandt spiller {player_name} ({player_number}) på hold {team_code} med {count} forekomster")
        
        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Fejl ved hentning af spillere fra central database: {e}")
    
    return player_list

def update_player_in_central_db(old_name, new_name, team_code, league_type="herreliga"):
    """
    Opdaterer en spillers navn i den centrale database
    
    Args:
        old_name: Det nuværende navn
        new_name: Det nye navn
        team_code: Holdkoden
        league_type: Enten "herreliga" eller "kvindeliga"
        
    Returns:
        bool: True hvis opdateringen var succesfuld
    """
    if league_type.lower() == "herreliga":
        central_db_path = HERRELIGA_CENTRAL_DB
    else:
        central_db_path = KVINDELIGA_CENTRAL_DB
    
    if not os.path.exists(central_db_path):
        logger.error(f"Central database for {league_type} findes ikke: {central_db_path}")
        return False
    
    try:
        conn = sqlite3.connect(central_db_path)
        cursor = conn.cursor()
        
        # Find spilleren for at få nummeret og occurrence_count
        cursor.execute("""
            SELECT player_number, occurrence_count FROM players
            WHERE player_name = ? AND team_code = ?
        """, (old_name, team_code))
        
        result = cursor.fetchone()
        if not result:
            logger.error(f"Spiller {old_name} ikke fundet for hold {team_code}")
            conn.close()
            return False
        
        player_number, occurrence_count = result
        
        # Kontroller om der allerede findes en spiller med det nye navn og samme nummer
        cursor.execute("""
            SELECT id FROM players
            WHERE player_name = ? AND team_code = ? AND player_number = ?
        """, (new_name, team_code, player_number))
        
        existing_player = cursor.fetchone()
        
        if existing_player:
            # Hvis der allerede findes en spiller med det nye navn, fjern den gamle spiller
            cursor.execute("""
                DELETE FROM players
                WHERE player_name = ? AND team_code = ? AND player_number = ?
            """, (old_name, team_code, player_number))
        else:
            # Ellers opdater den eksisterende spiller
            cursor.execute("""
                UPDATE players SET player_name = ?
                WHERE player_name = ? AND team_code = ? AND player_number = ?
            """, (new_name, old_name, team_code, player_number))
        
        # Opdater også i alle kampdata-databaser (eksisterende funktion)
        conn.commit()
        conn.close()
        
        # Kald den eksisterende funktion for at opdatere i alle kampdatabaser
        return update_player_name(old_name, new_name, team_code)
    
    except sqlite3.Error as e:
        logger.error(f"Fejl ved opdatering af spiller i central database: {e}")
        return False

# Ruter
@app.route('/')
def index():
    """Forside - liste over alle databaser"""
    databases = get_all_databases()
    return render_template('index.html', databases=databases)

@app.route('/database/<path:db_path>')
def view_database(db_path):
    """Se en specifik databases tabeller"""
    if not os.path.exists(db_path):
        return render_template('error.html', message=f"Databasefil ikke fundet: {db_path}")
    
    tables = get_table_names(db_path)
    if not tables:
        return render_template('error.html', message=f"Ingen tabeller fundet i database: {db_path}")
    
    return render_template('database.html', db_path=db_path, tables=tables, 
                          db_name=os.path.basename(db_path))

@app.route('/database/<path:db_path>/table/<table_name>')
def view_table(db_path, table_name):
    """Se en specifik tabel i en database"""
    if not os.path.exists(db_path):
        return render_template('error.html', message=f"Databasefil ikke fundet: {db_path}")
    
    df = get_table_data(db_path, table_name)
    if df.empty:
        return render_template('error.html', message=f"Tabel {table_name} ikke fundet eller er tom")
    
    return render_template('table.html', db_path=db_path, table_name=table_name, 
                          columns=df.columns.tolist(), data=df.to_dict('records'),
                          db_name=os.path.basename(db_path))

@app.route('/database/<path:db_path>/table/<table_name>/edit', methods=['POST'])
def edit_table(db_path, table_name):
    """Håndterer tabelredigeringer"""
    if not os.path.exists(db_path):
        return jsonify({"success": False, "error": f"Databasefil ikke fundet: {db_path}"})
    
    data = request.get_json()
    if not data or 'updates' not in data:
        return jsonify({"success": False, "error": "Ugyldigt dataformat"})
    
    try:
        # Opdater databasen
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        for update in data['updates']:
            row_id = update.get('id')
            column = update.get('column')
            value = update.get('value')
            
            if not all([row_id, column]):
                continue
            
            # Udfør opdateringen - med parametriserede forespørgsler af sikkerhedshensyn
            cursor.execute(f"UPDATE {table_name} SET {column} = ? WHERE id = ?", 
                          (value, row_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Opdateret tabel {table_name} i {db_path} med {len(data['updates'])} ændringer")
        return jsonify({"success": True})
    except sqlite3.Error as e:
        logger.error(f"Fejl ved opdatering af tabel {table_name} i {db_path}: {e}")
        return jsonify({"success": False, "error": str(e)})

# Hold- og spillerruter
@app.route('/teams')
def view_teams():
    """Se alle unikke hold på tværs af alle databaser"""
    all_teams = get_all_unique_teams()
    
    # Opret en ordbog med hold-kode til navn for at vise i skabelonen
    team_names = {code: name for code, name in TEAM_CODE_MAP.items()}
    
    return render_template('teams.html', teams=all_teams, team_names=team_names)

@app.route('/teams/<team_name>')
def view_team_players(team_name):
    """Se alle spillere for et specifikt hold"""
    # Bestem ligatype baseret på holdkoden
    league_type = "herreliga"  # Standard
    
    # Tjek om teamkoden er i kvindeliga-mappede hold
    women_teams = ["AHB", "BFH", "EHA", "HHE", "IKA", "KBH", "NFH", "ODE", 
                  "RIN", "SVK", "SKB", "SJE", "TES", "VHK"]  # Fjernet TMS fra listen
    
    if team_name in women_teams:
        league_type = "kvindeliga"
    
    # Tjek om den centrale database findes
    central_db_exists = False
    if league_type == "herreliga":
        central_db_exists = os.path.exists(HERRELIGA_CENTRAL_DB)
        if not central_db_exists:
            logger.warning(f"Central herreliga database ikke fundet, opbygger den nu")
            create_or_update_central_db("herreliga")
    else:
        central_db_exists = os.path.exists(KVINDELIGA_CENTRAL_DB)
        if not central_db_exists:
            logger.warning(f"Central kvindeliga database ikke fundet, opbygger den nu")
            create_or_update_central_db("kvindeliga")
    
    # Tving opbygning af central database for at sikre, at den er opdateret
    logger.info(f"Genopbygger central database for {league_type}")
    create_or_update_central_db(league_type)
        
    # Forsøg at hente fra central database først
    logger.info(f"Henter spillere fra central database for hold {team_name}")
    players = get_players_from_central_db(team_name, league_type)
    
    logger.info(f"Fundet {len(players)} spillere i central database for {team_name}")
    
    # FJERNET: Vi bruger ikke længere fallback til get_team_players
    # Vis en advarsel i stedet for at bruge den gamle metode
    if not players:
        logger.error(f"ADVARSEL: Ingen spillere fundet i central database for {team_name}")
        # Returner en tom liste i stedet for at falde tilbage til den gamle metode
        players = []
    
    # Log de første fem spillere (hvis der er nogen) for debugging
    if players:
        first_five = players[:5]
        logger.info(f"Første fem spillere fundet for {team_name}: " + 
                   ", ".join([f"{p['name']} (#{p['number']})" for p in first_five]))
    
    return render_template('team_players.html', 
                          team_name=team_name, 
                          team_full_name=TEAM_CODE_MAP.get(team_name, team_name),
                          players=players)

@app.route('/player/edit', methods=['POST'])
def edit_player():
    """Rediger en spillers navn på tværs af alle databaser"""
    data = request.get_json()
    if not data:
        return jsonify({"success": False, "error": "Ugyldigt dataformat"})
    
    old_name = data.get('old_name')
    new_name = data.get('new_name')
    team_name = data.get('team_name')
    
    if not all([old_name, new_name, team_name]):
        return jsonify({"success": False, "error": "Manglende påkrævede felter"})
    
    # Bestem ligatype baseret på holdkoden
    league_type = "herreliga"  # Standard
    women_teams = ["AHB", "BFH", "EHA", "HHE", "IKA", "KBH", "NFH", "ODE", 
                  "RIN", "SVK", "SKB", "SJE", "TES", "VHK"]
    
    if team_name in women_teams:
        league_type = "kvindeliga"
    
    # Opdater i både central database og kampdatabaser
    success = update_player_in_central_db(old_name, new_name, team_name, league_type)
    
    return jsonify({"success": success})

@app.route('/build_central_db/<league_type>')
def build_central_db(league_type):
    """Opbygger den centrale database for en liga"""
    if league_type not in ['herreliga', 'kvindeliga']:
        return render_template('error.html', message="Ugyldig ligatype. Brug 'herreliga' eller 'kvindeliga'.")
    
    success = create_or_update_central_db(league_type)
    
    if success:
        return render_template('success.html', 
                              message=f"Central database for {league_type} opbygget med succes",
                              back_url=url_for('index'))
    else:
        return render_template('error.html', 
                              message=f"Fejl ved opbygning af central database for {league_type}")

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="Side ikke fundet"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', message="Intern serverfejl"), 500

if __name__ == '__main__':
    app.run(debug=True) 