#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import sys
import time
import os
import re
import sqlite3
import glob
from datetime import datetime

def log_message(message):
    """Logger en besked med tidsstempel"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def extract_match_id_from_txt_filename(filename):
    """
    Udtrækker match_id fra TXT-filnavn
    
    Args:
        filename (str): TXT-filnavn (f.eks. 'match_748358_a.txt')
        
    Returns:
        str or None: Match ID hvis det findes, ellers None
    """
    # Match på mønstre som "match_748358_a.txt"
    match = re.search(r'match_(\d+)', filename)
    if match:
        return match.group(1)
    return None

def extract_match_id_from_txt_content(txt_file_path):
    """
    Udtrækker match_id fra TXT-filens indhold
    
    Args:
        txt_file_path (str): Sti til TXT-filen
        
    Returns:
        str or None: Match ID hvis det findes, ellers None
    """
    try:
        with open(txt_file_path, 'r', encoding='utf-8') as f:
            content = f.read(2000)  # Læs kun de første 2000 tegn for at spare tid
            
            # Søg efter kamp-ID i indholdet (format: 748358 / 5-4-2025)
            match = re.search(r'(\d{6})\s*/\s*\d{1,2}-\d{1,2}-\d{4}', content)
            if match:
                return match.group(1)
    except Exception as e:
        log_message(f"❌ Fejl ved læsning af TXT-fil for match_id: {str(e)}")
    
    return None

def is_match_id_in_database(match_id, db_dir):
    """
    Tjekker om et match_id allerede eksisterer i en database-fil i den givne mappe
    
    Args:
        match_id (str): Match ID der skal søges efter
        db_dir (str): Mappe med database-filer
        
    Returns:
        tuple: (bool: findes_i_db, str: db_filnavn eller None)
    """
    if not os.path.exists(db_dir):
        return False, None
    
    # Find alle DB-filer i mappen
    db_files = glob.glob(os.path.join(db_dir, "*.db"))
    
    for db_file in db_files:
        try:
            # Spring over stats-filer og centrale filer
            if "stats" in os.path.basename(db_file).lower() or "central" in os.path.basename(db_file).lower():
                continue
            
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Tjek om tabellen match_info eksisterer
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='match_info'")
            if not cursor.fetchone():
                conn.close()
                continue
            
            # Søg efter match_id i match_info tabellen
            cursor.execute("SELECT kamp_id FROM match_info WHERE kamp_id = ?", (match_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                return True, os.path.basename(db_file)
        
        except Exception as e:
            # Ignorer fejl i enkelte DB-filer og fortsæt
            continue
    
    return False, None

def is_txt_already_processed(txt_file_path, db_dir):
    """
    Tjekker om en TXT-fil allerede er processeret til database
    
    Args:
        txt_file_path (str): Sti til TXT-filen
        db_dir (str): Mappe med database-filer
        
    Returns:
        tuple: (bool: er_processeret, str: reason/db_filnavn)
    """
    filename = os.path.basename(txt_file_path)
    
    # 1. Prøv at udtrække match_id fra filnavnet
    match_id = extract_match_id_from_txt_filename(filename)
    
    if not match_id:
        # 2. Hvis ikke fundet i filnavnet, prøv at læse det fra indholdet
        match_id = extract_match_id_from_txt_content(txt_file_path)
        
        if not match_id:
            return False, f"Kunne ikke udtrække match_id fra {filename}"
    
    # 3. Tjek om match_id eksisterer i database
    is_processed, db_filename = is_match_id_in_database(match_id, db_dir)
    
    if is_processed:
        return True, f"Match ID {match_id} fundet i {db_filename}"
    else:
        return False, f"Match ID {match_id} ikke fundet i database"

def check_txt_processing_status(liga, season):
    """
    Tjekker status for TXT-fil processering for en specifik liga og sæson
    
    Args:
        liga (str): Liga navn
        season (str): Sæson (f.eks. '2024-2025')
        
    Returns:
        dict: Statistik over processeret/uprocesseret
    """
    # Byg stier til TXT- og DB-mapper
    if liga == 'kvindeligaen':
        txt_dir = os.path.join('Kvindeliga-txt-tabel', season)
        db_dir = os.path.join('Kvindeliga-database', season)
    elif liga == 'herreligaen':
        txt_dir = os.path.join('Herreliga-txt-tabel', season)
        db_dir = os.path.join('Herreliga-database', season)
    else:
        return {"error": f"Ukendt liga: {liga}"}
    
    # Find alle TXT-filer
    txt_files = glob.glob(os.path.join(txt_dir, "*.txt"))
    
    stats = {
        "total_txt_files": len(txt_files),
        "already_processed": 0,
        "not_processed": 0,
        "error_files": 0,
        "processed_details": [],
        "not_processed_details": []
    }
    
    for txt_file in txt_files:
        is_processed, reason = is_txt_already_processed(txt_file, db_dir)
        
        if "Kunne ikke udtrække match_id" in reason:
            stats["error_files"] += 1
        elif is_processed:
            stats["already_processed"] += 1
            stats["processed_details"].append({
                "file": os.path.basename(txt_file),
                "reason": reason
            })
        else:
            stats["not_processed"] += 1
            stats["not_processed_details"].append({
                "file": os.path.basename(txt_file),
                "reason": reason
            })
    
    return stats

def run_processor(liga, season):
    """Kører handball_data_processor.py for en specifik liga og sæson"""
    log_message(f"🏃 Starter processering af {liga} {season}")
    
    # Tjek først hvor mange filer der skal processeres
    status = check_txt_processing_status(liga, season)
    
    if "error" in status:
        log_message(f"❌ Fejl ved tjek af {liga} {season}: {status['error']}")
        return False
    
    log_message(f"📊 Status for {liga} {season}:")
    log_message(f"    Total TXT-filer: {status['total_txt_files']}")
    log_message(f"    Allerede processeret: {status['already_processed']}")
    log_message(f"    Mangler processering: {status['not_processed']}")
    log_message(f"    Fejl-filer: {status['error_files']}")
    
    # Hvis alle filer allerede er processeret, spring over
    if status['not_processed'] == 0:
        log_message(f"✅ Alle TXT-filer for {liga} {season} er allerede processeret til database. Springer over.")
        return True
    
    # Vis detaljer om filer der mangler processering
    if status['not_processed'] > 0 and len(status['not_processed_details']) <= 10:
        log_message(f"📝 Filer der mangler processering:")
        for detail in status['not_processed_details']:
            log_message(f"    - {detail['file']}: {detail['reason']}")
    elif status['not_processed'] > 10:
        log_message(f"📝 {status['not_processed']} filer mangler processering (for mange til at vise alle)")
    
    # Kør handball_data_processor.py
    cmd = [sys.executable, "handball_data_processor.py", "--liga", liga, "--sæson", season]
    
    try:
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
        end_time = time.time()
        duration = end_time - start_time
        
        if result.returncode == 0:
            log_message(f"✅ {liga} {season} færdig på {duration:.1f} sekunder")
            
            # Tjek status igen efter processering
            new_status = check_txt_processing_status(liga, season)
            processed_now = new_status['already_processed'] - status['already_processed']
            log_message(f"📈 Resultat: {processed_now} nye filer processeret til database")
            
        else:
            log_message(f"❌ {liga} {season} fejlede med return code {result.returncode}")
            if result.stderr:
                log_message(f"Error: {result.stderr[:200]}...")
        
        return result.returncode == 0
        
    except Exception as e:
        log_message(f"❌ Fejl ved kørsel af {liga} {season}: {e}")
        return False

def main():
    """Hovedfunktion der kører alle sæsoner"""
    
    # Generer alle sæsoner fra 2017-2018 til 2024-2025 (nyeste først)
    # Dette starter med den nuværende sæson og arbejder bagud
    start_year = 2024  # Nyeste sæson starter år
    end_year = 2017    # Ældste sæson starter år
    
    seasons = []
    for year in range(start_year, end_year - 1, -1):  # Tæl bagud fra 2024 til 2017
        season = f"{year}-{year + 1}"
        seasons.append(season)
    
    ligaer = ["herreligaen", "kvindeligaen"]
    
    log_message("🎯 STARTER AUTOMATISK PROCESSERING AF ALLE SÆSONER")
    log_message(f"📋 Sæsoner: {', '.join(seasons)} (total: {len(seasons)} sæsoner)")
    log_message(f"🏆 Ligaer: {', '.join(ligaer)}")
    log_message(f"📊 Total jobs: {len(seasons)} × {len(ligaer)} = {len(seasons) * len(ligaer)} jobs")
    
    total_start_time = time.time()
    successful = 0
    failed = 0
    
    # Kør alle kombinationer - for hver sæson, skift mellem ligaerne
    for season in seasons:
        for liga in ligaer:
            log_message(f"\n🔄 Behandler {liga} {season}...")
            
            if run_processor(liga, season):
                successful += 1
            else:
                failed += 1
                
            # Kort pause mellem hver processering
            time.sleep(2)
    
    # Samlet statistik
    total_time = time.time() - total_start_time
    total_jobs = len(seasons) * len(ligaer)
    
    log_message(f"\n" + "="*60)
    log_message("🏁 ALLE PROCESSERING FÆRDIG!")
    log_message(f"⏱️  Total tid: {total_time:.1f} sekunder ({total_time/60:.1f} minutter)")
    log_message(f"✅ Succesfulde: {successful}/{total_jobs}")
    log_message(f"❌ Fejlede: {failed}/{total_jobs}")
    log_message("="*60)
    
    # Afsluttende status
    if failed == 0:
        log_message("🎉 ALLE SÆSONER ER BEHANDLET SUCCESFULDT!")
    else:
        log_message(f"⚠️  {failed} sæsoner fejlede - tjek logs for detaljer")

if __name__ == "__main__":
    main() 