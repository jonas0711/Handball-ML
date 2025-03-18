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
    "GIF": "Grindsted GIF Håndbold"
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
    players = get_team_players(team_name)
    return render_template('team_players.html', team_name=team_name, players=players)

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
    
    success = update_player_name(old_name, new_name, team_name)
    
    return jsonify({"success": success})

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', message="Side ikke fundet"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', message="Intern serverfejl"), 500

if __name__ == '__main__':
    app.run(debug=True) 