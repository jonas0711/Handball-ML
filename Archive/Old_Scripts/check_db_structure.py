#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TJEK DATABASE STRUKTUR SCRIPT
"""

import sqlite3
import os

def check_database_structure(db_path):
    """Tjekker strukturen af en database"""
    if not os.path.exists(db_path):
        print(f"❌ Database findes ikke: {db_path}")
        return
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Find alle tabeller
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n📊 Database: {os.path.basename(db_path)}")
        print(f"   Tabeller: {tables}")
        
        # Tjek struktur af første tabel
        if tables:
            first_table = tables[0]
            cursor.execute(f"PRAGMA table_info({first_table})")
            columns = cursor.fetchall()
            print(f"   Kolonner i {first_table}: {[col[1] for col in columns]}")
            
            # Vis første par rækker
            cursor.execute(f"SELECT * FROM {first_table} LIMIT 3")
            rows = cursor.fetchall()
            print(f"   Første 3 rækker: {len(rows)} rækker fundet")
            
        conn.close()
        
    except Exception as e:
        print(f"⚠️ Fejl ved læsning af {db_path}: {e}")

if __name__ == "__main__":
    # Tjek nogle databaser
    databases = [
        "Herreliga-database/2024-2025/herreliga_2024_2025_stats.db",
        "Kvindeliga-database/2024-2025/kvindeliga_2024_2025_stats.db",
        "1-Division-Herrer-database/2024-2025/1_division_herrer_2024_2025_stats.db"
    ]
    
    for db_path in databases:
        check_database_structure(db_path) 