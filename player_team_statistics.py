#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Håndboldhændelser - Spiller-Hold Tilknytning og Spillerstatistik

Dette script gennemgår alle kampdatabaser (.db filer) i både Herreliga-database
og Kvindeliga-database mapperne og:
1. Opretter en 'players_team' tabel i hver database, der tilknytter hver unik spiller 
   til deres hold baseret på kamphændelser.
2. Opretter en 'player_statistics' tabel med detaljeret statistik for hver spiller 
   baseret på alle mulige datapunkter i kamphændelserne.

Scriptet følger logikken beskrevet i data.md for at korrekt tildele spillere til hold
og beregne deres statistikker.
"""

import os
import glob
import sqlite3
import logging
from collections import defaultdict, Counter

# Konfiguration
HERRELIGA_DB_DIR = "Herreliga-database"
KVINDELIGA_DB_DIR = "Kvindeliga-database"
LOG_FILE = "player_team_assignment.log"

# Hændelser hvor nr_2/navn_2 tilhører det MODSATTE hold af 'hold'
OPPOSITE_TEAM_EVENTS = ["Bold erobret", "Forårs. str.", "Blokeret af", "Blok af (ret)"]

# Hændelser hvor nr_2/navn_2 tilhører SAMME hold som 'hold'
SAME_TEAM_EVENTS = ["Assist"]

# Værdier der ikke er spillernavne
NOT_PLAYER_NAMES = ["Retur", "Bold erobret", "Assist", "Blokeret af", "Blok af (ret)", "Forårs. str."]

# Administrative hændelser (ikke spillerrelaterede)
ADMIN_EVENTS = ["Video Proof", "Video Proof slut", "Halvleg", "Start 1:e halvleg", "Start 2:e halvleg", 
                "Fuld tid", "Kamp slut", "Time out", "Start"]

# Målvogter-relaterede hændelser
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
    
    # Sekundære hændelser
    ("assists", "INTEGER", "Antal assister"),
    ("ball_stolen", "INTEGER", "Antal gange bolden er erobret"),
    ("caused_penalty", "INTEGER", "Antal gange forårsaget straffekast"),
    ("blocks", "INTEGER", "Antal blokerede skud"),
    
    # Disciplinære hændelser
    ("warnings", "INTEGER", "Antal advarsler (gult kort)"),
    ("suspensions", "INTEGER", "Antal udvisninger (2 min)"),
    ("red_cards", "INTEGER", "Antal røde kort"),
    ("blue_cards", "INTEGER", "Antal blå kort"),
    
    # Målvogterstatistik
    ("gk_saves", "INTEGER", "Antal redninger som målvogter"),
    ("gk_goals_against", "INTEGER", "Antal mål indkasseret som målvogter"),
    ("gk_penalty_saves", "INTEGER", "Antal straffekast reddet som målvogter"),
    ("gk_penalty_goals_against", "INTEGER", "Antal mål på straffekast indkasseret som målvogter"),
    
    # Total spilletid (estimeret ud fra første til sidste hændelse)
    ("total_events", "INTEGER", "Samlet antal hændelser spilleren er involveret i"),
    ("first_event_time", "TEXT", "Tid for spillerens første hændelse i kampen"),
    ("last_event_time", "TEXT", "Tid for spillerens sidste hændelse i kampen")
]

# Konfigurer logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def find_all_databases():
    """
    Finder alle .db filer i Herreliga-database og Kvindeliga-database mapperne
    
    Returns:
        list: Liste med stier til alle .db filer
    """
    # Find alle .db filer i Herreliga-database
    herreliga_pattern = os.path.join(HERRELIGA_DB_DIR, "**", "*.db")
    herreliga_dbs = glob.glob(herreliga_pattern, recursive=True)
    
    # Find alle .db filer i Kvindeliga-database
    kvindeliga_pattern = os.path.join(KVINDELIGA_DB_DIR, "**", "*.db")
    kvindeliga_dbs = glob.glob(kvindeliga_pattern, recursive=True)
    
    # Kombiner resultaterne
    all_dbs = herreliga_dbs + kvindeliga_dbs
    
    logger.info(f"Fandt {len(all_dbs)} databaser i alt ({len(herreliga_dbs)} i herreligaen, {len(kvindeliga_dbs)} i kvindeligaen)")
    return all_dbs

def create_players_team_table(db_path):
    """
    Opretter en ny tabel i databasen, der tilknytter spillere til hold
    
    Args:
        db_path: Sti til databasefilen
    
    Returns:
        bool: True hvis operationen var succesfuld, ellers False
    """
    logger.info(f"Behandler database: {db_path}")
    
    try:
        # Opret forbindelse til databasen
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tjek om tabellen allerede eksisterer
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players_team'")
        if cursor.fetchone():
            logger.info(f"Tabel 'players_team' eksisterer allerede i {db_path}, sletter den for at genopbygge")
            cursor.execute("DROP TABLE players_team")
        
        # Opret ny tabel til spiller-hold tilknytning
        cursor.execute("""
        CREATE TABLE players_team (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_number INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            team_code TEXT NOT NULL,
            occurrences INTEGER NOT NULL,
            UNIQUE(player_number, player_name, team_code)
        )
        """)
        
        # Hent hold-koder fra kampen
        cursor.execute("SELECT DISTINCT hold FROM match_events WHERE hold IS NOT NULL")
        team_codes = [row[0] for row in cursor.fetchall()]
        
        if not team_codes:
            logger.warning(f"Kunne ikke finde holdkoder i {db_path}, springer over")
            conn.close()
            return False
        
        logger.info(f"Holdkoder i kamp: {', '.join(team_codes)}")
        
        # Tæller for spillerforekomster pr. hold
        player_team_counts = defaultdict(Counter)
        
        # 1. Analyser primære hændelser (nr_1, navn_1)
        cursor.execute("""
        SELECT hold, nr_1, navn_1, COUNT(*) as count FROM match_events 
        WHERE nr_1 IS NOT NULL AND nr_1 > 0 
        AND navn_1 IS NOT NULL AND navn_1 != ''
        AND haendelse_1 NOT IN ('Video Proof', 'Video Proof slut', 'Halvleg', 'Start 1:e halvleg', 'Start 2:e halvleg', 'Fuld tid', 'Kamp slut', 'Time out')
        GROUP BY hold, nr_1, navn_1
        """)
        
        for team_code, player_number, player_name, count in cursor.fetchall():
            # Skipper spillere uden navn eller med specielle navne
            if not player_name or player_name in NOT_PLAYER_NAMES:
                continue
            
            # Tilføj til tælleren for dette hold
            player_key = (player_number, player_name)
            player_team_counts[player_key][team_code] += count
        
        # 2. Analyser sekundære hændelser (nr_2, navn_2) - SAME_TEAM_EVENTS
        for event_type in SAME_TEAM_EVENTS:
            cursor.execute("""
            SELECT hold, nr_2, navn_2, COUNT(*) as count FROM match_events 
            WHERE nr_2 IS NOT NULL AND nr_2 > 0 
            AND navn_2 IS NOT NULL AND navn_2 != '' 
            AND haendelse_2 = ?
            GROUP BY hold, nr_2, navn_2
            """, (event_type,))
            
            for team_code, player_number, player_name, count in cursor.fetchall():
                # Skipper spillere uden navn eller med specielle navne
                if not player_name or player_name in NOT_PLAYER_NAMES:
                    continue
                
                # Tilføj til tælleren for dette hold
                player_key = (player_number, player_name)
                player_team_counts[player_key][team_code] += count
        
        # 3. Analyser sekundære hændelser (nr_2, navn_2) - OPPOSITE_TEAM_EVENTS
        for event_type in OPPOSITE_TEAM_EVENTS:
            cursor.execute("""
            SELECT hold, nr_2, navn_2, COUNT(*) as count FROM match_events 
            WHERE nr_2 IS NOT NULL AND nr_2 > 0 
            AND navn_2 IS NOT NULL AND navn_2 != '' 
            AND haendelse_2 = ?
            GROUP BY hold, nr_2, navn_2
            """, (event_type,))
            
            for team_code, player_number, player_name, count in cursor.fetchall():
                # Skipper spillere uden navn eller med specielle navne
                if not player_name or player_name in NOT_PLAYER_NAMES:
                    continue
                
                # For OPPOSITE_TEAM_EVENTS skal spilleren tilknyttes det modsatte hold
                opposite_team = None
                for other_team in team_codes:
                    if other_team != team_code:
                        opposite_team = other_team
                        break
                
                if opposite_team:
                    # Tilføj til tælleren for det modsatte hold
                    player_key = (player_number, player_name)
                    player_team_counts[player_key][opposite_team] += count
        
        # 4. Analyser målvogtere (nr_mv, mv) - De tilhører altid det modsatte hold
        cursor.execute("""
        SELECT hold, nr_mv, mv, COUNT(*) as count FROM match_events 
        WHERE nr_mv IS NOT NULL AND nr_mv > 0
        AND mv IS NOT NULL AND mv != ''
        AND haendelse_1 IN ('Mål', 'Skud reddet', 'Skud forbi', 'Skud på stolpe', 'Mål på straffe', 'Straffekast reddet')
        GROUP BY hold, nr_mv, mv
        """)
        
        for team_code, player_number, player_name, count in cursor.fetchall():
            # Skipper spillere uden navn eller med specielle navne
            if not player_name or player_name in NOT_PLAYER_NAMES:
                continue
            
            # For målvogtere skal spilleren tilknyttes det modsatte hold
            opposite_team = None
            for other_team in team_codes:
                if other_team != team_code:
                    opposite_team = other_team
                    break
            
            if opposite_team:
                # Tilføj til tælleren for det modsatte hold
                player_key = (player_number, player_name)
                player_team_counts[player_key][opposite_team] += count
        
        # 5. For hver spiller, tildel dem til det hold de hyppigst er knyttet til
        player_assignments = []
        
        for player_key, team_counts in player_team_counts.items():
            player_number, player_name = player_key
            
            # Find det hold som spilleren hyppigst er knyttet til
            if team_counts:
                most_common_team, occurrences = team_counts.most_common(1)[0]
                
                player_assignments.append({
                    "player_number": player_number,
                    "player_name": player_name,
                    "team_code": most_common_team,  # Dette er den korrekte nøgle!
                    "occurrences": occurrences
                })
        
        # 6. Indsæt spillertilknytninger i databasen
        for player in player_assignments:
            try:
                cursor.execute("""
                INSERT INTO players_team (player_number, player_name, team_code, occurrences)
                VALUES (?, ?, ?, ?)
                """, (
                    player["player_number"],
                    player["player_name"],
                    player["team_code"],  # FIX: Bruger nu team_code i stedet for player_code
                    player["occurrences"]
                ))
            except sqlite3.IntegrityError:
                # Hvis der er en integrity error, så overskriver vi med den nye værdi
                logger.warning(f"Duplikat spiller i {db_path}: {player['player_name']} (#{player['player_number']}), opdaterer")
                cursor.execute("""
                UPDATE players_team
                SET occurrences = ?
                WHERE player_number = ? AND player_name = ? AND team_code = ?
                """, (
                    player["occurrences"],
                    player["player_number"],
                    player["player_name"],
                    player["team_code"]  # FIX: Bruger nu team_code i stedet for player_code
                ))
        
        # Gem ændringer
        conn.commit()
        
        logger.info(f"Oprettet players_team tabel i {db_path} med {len(player_assignments)} spillere")
        
        # Luk forbindelsen
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Fejl ved behandling af {db_path}: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return False

def create_player_statistics_table(db_path):
    """
    Opretter en ny tabel i databasen med detaljeret statistik for hver spiller
    
    Args:
        db_path: Sti til databasefilen
    
    Returns:
        bool: True hvis operationen var succesfuld, ellers False
    """
    logger.info(f"Opretter detaljeret spillerstatistik i: {db_path}")
    
    try:
        # Opret forbindelse til databasen
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Tjek om tabellen allerede eksisterer
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='player_statistics'")
        if cursor.fetchone():
            logger.info(f"Tabel 'player_statistics' eksisterer allerede i {db_path}, sletter den for at genopbygge")
            cursor.execute("DROP TABLE player_statistics")
        
        # Opret ny tabel til spillerstatistik med alle definerede kolonner
        create_table_sql = """
        CREATE TABLE player_statistics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_number INTEGER NOT NULL,
            player_name TEXT NOT NULL,
            team_code TEXT NOT NULL,
        """
        
        # Tilføj alle standard statistikfelter
        for col_name, col_type, _ in STANDARD_STAT_COLUMNS:
            create_table_sql += f"{col_name} {col_type} DEFAULT 0,"
        
        # Afslut SQL-erklæringen med UNIQUE constraint
        create_table_sql += """
            UNIQUE(player_number, player_name, team_code)
        )
        """
        
        cursor.execute(create_table_sql)
        
        # Først skal vi sikre os at players_team tabellen eksisterer
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='players_team'")
        if not cursor.fetchone():
            logger.warning(f"players_team tabel mangler i {db_path}, opretter den først")
            # Luk forbindelsen og kald create_players_team_table
            conn.close()
            if not create_players_team_table(db_path):
                logger.error(f"Kunne ikke oprette players_team tabel i {db_path}")
                return False
            # Genåbn forbindelsen
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
        
        # Hent alle spillere og deres holdtilknytning fra players_team
        cursor.execute("SELECT player_number, player_name, team_code FROM players_team")
        players = cursor.fetchall()
        
        if not players:
            logger.warning(f"Ingen spillere fundet i players_team i {db_path}, springer over")
            conn.close()
            return False
        
        logger.info(f"Fandt {len(players)} spillere at beregne statistik for i {db_path}")
        
        # For hver spiller, beregn alle statistikker
        for player_number, player_name, team_code in players:
            # Initialiser statistik-dictionary
            stats = {col_name: 0 for col_name, _, _ in STANDARD_STAT_COLUMNS}
            stats["first_event_time"] = "99.99"  # Høj værdi til sammenligning
            stats["last_event_time"] = "0.00"    # Lav værdi til sammenligning
            
            # 1. Tæl primære hændelser (nr_1, navn_1)
            cursor.execute("""
            SELECT haendelse_1, tid FROM match_events 
            WHERE nr_1 = ? AND navn_1 = ? 
            AND haendelse_1 NOT IN ('Video Proof', 'Video Proof slut', 'Halvleg', 'Start 1:e halvleg', 
                                    'Start 2:e halvleg', 'Fuld tid', 'Kamp slut', 'Time out', 'Start')
            """, (player_number, player_name))
            
            for event_type, event_time in cursor.fetchall():
                # Opdater total_events
                stats["total_events"] += 1
                
                # Opdater first_event_time og last_event_time
                try:
                    if float(event_time) < float(stats["first_event_time"]):
                        stats["first_event_time"] = event_time
                    if float(event_time) > float(stats["last_event_time"]):
                        stats["last_event_time"] = event_time
                except ValueError:
                    # Hvis event_time ikke kan konverteres til float, spring over denne opdatering
                    logger.warning(f"Kunne ikke konvertere tid '{event_time}' til tal for spiller {player_name}")
                
                # Tæl forskellige typer af hændelser
                if event_type == "Mål":
                    stats["goals"] += 1
                elif event_type == "Mål på straffe":
                    stats["penalty_goals"] += 1
                elif event_type == "Skud forbi":
                    stats["shots_missed"] += 1
                elif event_type == "Skud på stolpe":
                    stats["shots_post"] += 1
                elif event_type == "Skud blokeret":
                    stats["shots_blocked"] += 1
                elif event_type == "Skud reddet":
                    stats["shots_saved"] += 1
                elif event_type == "Straffekast forbi":
                    stats["penalty_missed"] += 1
                elif event_type == "Straffekast på stolpe":
                    stats["penalty_post"] += 1
                elif event_type == "Straffekast reddet":
                    stats["penalty_saved"] += 1
                elif event_type in ["Regelfejl", "Fejlaflevering"]:
                    stats["technical_errors"] += 1
                elif event_type == "Tabt bold":
                    stats["ball_lost"] += 1
                elif event_type == "Advarsel":
                    stats["warnings"] += 1
                elif event_type == "Udvisning" or event_type == "Udvisning (2x)":
                    stats["suspensions"] += 1
                elif event_type == "Rødt kort" or event_type == "Rødt kort, direkte":
                    stats["red_cards"] += 1
                elif event_type == "Blåt kort":
                    stats["blue_cards"] += 1
            
            # 2. Tæl sekundære hændelser (nr_2, navn_2)
            cursor.execute("""
            SELECT haendelse_2, tid FROM match_events 
            WHERE nr_2 = ? AND navn_2 = ?
            """, (player_number, player_name))
            
            for event_type, event_time in cursor.fetchall():
                # Opdater total_events
                stats["total_events"] += 1
                
                # Opdater first_event_time og last_event_time
                try:
                    if float(event_time) < float(stats["first_event_time"]):
                        stats["first_event_time"] = event_time
                    if float(event_time) > float(stats["last_event_time"]):
                        stats["last_event_time"] = event_time
                except ValueError:
                    # Hvis event_time ikke kan konverteres til float, spring over denne opdatering
                    logger.warning(f"Kunne ikke konvertere tid '{event_time}' til tal for spiller {player_name}")
                
                # Tæl forskellige typer af sekundære hændelser
                if event_type == "Assist":
                    stats["assists"] += 1
                elif event_type == "Bold erobret":
                    stats["ball_stolen"] += 1
                elif event_type == "Forårs. str.":
                    stats["caused_penalty"] += 1
                elif event_type in ["Blokeret af", "Blok af (ret)"]:
                    stats["blocks"] += 1
            
            # 3. Tæl målvogterstatistik (nr_mv, mv)
            cursor.execute("""
            SELECT haendelse_1, tid FROM match_events 
            WHERE nr_mv = ? AND mv = ?
            """, (player_number, player_name))
            
            for event_type, event_time in cursor.fetchall():
                # Opdater total_events
                stats["total_events"] += 1
                
                # Opdater first_event_time og last_event_time
                try:
                    if float(event_time) < float(stats["first_event_time"]):
                        stats["first_event_time"] = event_time
                    if float(event_time) > float(stats["last_event_time"]):
                        stats["last_event_time"] = event_time
                except ValueError:
                    # Hvis event_time ikke kan konverteres til float, spring over denne opdatering
                    logger.warning(f"Kunne ikke konvertere tid '{event_time}' til tal for spiller {player_name}")
                
                # Tæl forskellige typer af målvogterstatistik
                if event_type == "Skud reddet":
                    stats["gk_saves"] += 1
                elif event_type == "Mål":
                    stats["gk_goals_against"] += 1
                elif event_type == "Straffekast reddet":
                    stats["gk_penalty_saves"] += 1
                elif event_type == "Mål på straffe":
                    stats["gk_penalty_goals_against"] += 1
            
            # Ret first_event_time og last_event_time hvis der ikke var nogen hændelser
            if stats["first_event_time"] == "99.99":
                stats["first_event_time"] = None
            if stats["last_event_time"] == "0.00":
                stats["last_event_time"] = None
            
            # Indsæt spiller-statistik i databasen
            insert_sql = """
            INSERT INTO player_statistics 
            (player_number, player_name, team_code, 
            """
            
            # Tilføj alle statistikkolonner
            insert_sql += ", ".join([col_name for col_name, _, _ in STANDARD_STAT_COLUMNS])
            
            insert_sql += """) 
            VALUES (?, ?, ?, 
            """
            
            # Tilføj placeholder for hver statistikkolonne
            insert_sql += ", ".join(["?" for _ in STANDARD_STAT_COLUMNS])
            
            insert_sql += ")"
            
            # Forbered parametre til forespørgslen
            params = [player_number, player_name, team_code]
            for col_name, _, _ in STANDARD_STAT_COLUMNS:
                params.append(stats[col_name])
            
            # Kør SQL-forespørgslen
            try:
                cursor.execute(insert_sql, params)
            except sqlite3.IntegrityError:
                logger.warning(f"Duplikat spiller i {db_path}: {player_name} (#{player_number}), springer over")
        
        # Gem ændringer
        conn.commit()
        
        logger.info(f"Oprettet player_statistics tabel i {db_path} med statistik for {len(players)} spillere")
        
        # Luk forbindelsen
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Fejl ved oprettelse af player_statistics i {db_path}: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return False

def main():
    """Hovedfunktion der behandler alle databaser"""
    logger.info("==== Starter oprettelse af spiller-hold tilknytning og statistik ====")
    
    # Find alle databaser
    all_dbs = find_all_databases()
    
    # Behandl hver database
    players_team_success = 0
    players_team_failed = 0
    statistics_success = 0
    statistics_failed = 0
    
    for db_path in all_dbs:
        try:
            # 1. Opret players_team tabel
            if create_players_team_table(db_path):
                players_team_success += 1
            else:
                players_team_failed += 1
            
            # 2. Opret player_statistics tabel
            if create_player_statistics_table(db_path):
                statistics_success += 1
            else:
                statistics_failed += 1
        except Exception as e:
            logger.error(f"Uventet fejl ved behandling af {db_path}: {str(e)}")
            players_team_failed += 1
            statistics_failed += 1
    
    # Log resultatet
    logger.info("==== Oprettelse af spiller-hold tilknytning og statistik afsluttet ====")
    logger.info(f"Behandlet {len(all_dbs)} databaser:")
    logger.info(f"  - players_team: {players_team_success} succesfulde, {players_team_failed} fejlede")
    logger.info(f"  - player_statistics: {statistics_success} succesfulde, {statistics_failed} fejlede")
    
    # Vis resultat i terminalen
    print("\nOprettelse af spiller-hold tilknytning og statistik afsluttet!")
    print(f"Behandlet {len(all_dbs)} databaser:")
    print(f"  - players_team tabel: {players_team_success} succesfulde, {players_team_failed} fejlede")
    print(f"  - player_statistics tabel: {statistics_success} succesfulde, {statistics_failed} fejlede")
    print(f"Se {LOG_FILE} for detaljer.")

if __name__ == "__main__":
    main()