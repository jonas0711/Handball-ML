#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Håndboldhændelser - Spiller-Hold Tilknytning

Dette script gennemgår alle kampdatabaser (.db filer) i både Herreliga-database
og Kvindeliga-database mapperne og opretter en ny tabel i hver database, der
tilknytter hver unik spiller til deres hold baseret på kamphændelser.

Scriptet følger logikken beskrevet i data.md for at korrekt tildele spillere til hold.
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
                    "team_code": most_common_team,
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
                    player["team_code"],
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
                    player["team_code"]
                ))
        
        # Gem ændringer
        conn.commit()
        
        logger.info(f"Oprettet players_team tabel i {db_path} med {len(player_assignments)} spillere")
        
        # Luk forbindelsen
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Fejl ved behandling af {db_path}: {str(e)}")
        return False

def main():
    """Hovedfunktion der behandler alle databaser"""
    logger.info("==== Starter oprettelse af spiller-hold tilknytning ====")
    
    # Find alle databaser
    all_dbs = find_all_databases()
    
    # Behandl hver database
    successful = 0
    failed = 0
    
    for db_path in all_dbs:
        try:
            if create_players_team_table(db_path):
                successful += 1
            else:
                failed += 1
        except Exception as e:
            logger.error(f"Uventet fejl ved behandling af {db_path}: {str(e)}")
            failed += 1
    
    # Log resultatet
    logger.info("==== Oprettelse af spiller-hold tilknytning afsluttet ====")
    logger.info(f"Behandlet {len(all_dbs)} databaser: {successful} succesfulde, {failed} fejlede")
    
    # Vis resultat i terminalen
    print("\nOprettelse af spiller-hold tilknytning afsluttet!")
    print(f"Behandlet {len(all_dbs)} databaser:")
    print(f"  - Succesfulde: {successful}")
    print(f"  - Fejlede: {failed}")
    print(f"Se {LOG_FILE} for detaljer.")

if __name__ == "__main__":
    main()