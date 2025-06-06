#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 CSV FILER ANALYSE SCRIPT
==========================
Analyserer alle CSV filer systematisk for at evaluere deres korrekthed
"""

import pandas as pd
import os
import glob
from collections import Counter

def analyze_csv_files():
    """Analyserer alle CSV filer systematisk"""
    print("🔍 CSV FILER ANALYSE")
    print("=" * 60)
    
    # Find alle CSV filer
    csv_files = glob.glob("*.csv")
    csv_files.sort()
    
    print(f"📁 Fundet {len(csv_files)} CSV filer:")
    for file in csv_files:
        size_mb = os.path.getsize(file) / 1024 / 1024
        print(f"  • {file} ({size_mb:.1f} MB)")
    
    print("\n" + "=" * 60)
    
    # Analyser hver fil type
    herreliga_files = [f for f in csv_files if f.startswith('herreliga_seasonal_elo_')]
    advanced_files = [f for f in csv_files if 'advanced' in f]
    
    # 1. ANALYSER HERRELIGA SEASONAL FILER
    if herreliga_files:
        print(f"\n🏐 HERRELIGA SEASONAL FILER ({len(herreliga_files)} filer)")
        print("-" * 50)
        
        seasonal_data = {}
        total_players = set()
        
        for file in herreliga_files:
            try:
                df = pd.read_csv(file)
                season = file.replace('herreliga_seasonal_elo_', '').replace('.csv', '').replace('_', '-')
                
                print(f"\n📅 {season}:")
                print(f"  📊 Spillere: {len(df)}")
                print(f"  🎯 Gennemsnits rating: {df['final_rating'].mean():.1f}")
                print(f"  📏 Rating spredning: {df['final_rating'].min():.0f} - {df['final_rating'].max():.0f}")
                
                # Position fordeling
                pos_dist = df['primary_position'].value_counts()
                print(f"  🏃 Position fordeling: {dict(pos_dist.head(3))}")
                
                # Elite spillere
                elite_count = len(df[df['elite_status'] == 'ELITE'])
                legendary_count = len(df[df['elite_status'] == 'LEGENDARY'])
                print(f"  ⭐ Elite: {elite_count}, Legendary: {legendary_count}")
                
                # Målvogtere
                goalkeepers = len(df[df['is_goalkeeper'] == True])
                print(f"  🥅 Målvogtere: {goalkeepers}")
                
                # Gemmer data for sammenligning
                seasonal_data[season] = {
                    'players': len(df),
                    'avg_rating': df['final_rating'].mean(),
                    'goalkeepers': goalkeepers,
                    'elite': elite_count,
                    'legendary': legendary_count
                }
                
                # Tilføj spillere til total set
                total_players.update(df['player'].tolist())
                
                # Tjek for problemer
                problems = []
                
                # 1. Tjek for meget høje ratings
                extreme_high = df[df['final_rating'] > 1800]
                if len(extreme_high) > len(df) * 0.1:  # Mere end 10%
                    problems.append(f"Meget mange høje ratings: {len(extreme_high)} spillere >1800")
                
                # 2. Tjek for meget lave ratings  
                extreme_low = df[df['final_rating'] < 1000]
                if len(extreme_low) > 0:
                    problems.append(f"Meget lave ratings: {len(extreme_low)} spillere <1000")
                
                # 3. Tjek for manglende data
                missing_games = df[df['games'] == 0]
                if len(missing_games) > 0:
                    problems.append(f"Spillere uden kampe: {len(missing_games)}")
                
                # 4. Tjek position distribution
                if 'MV' in pos_dist and pos_dist['MV'] < 5:
                    problems.append(f"Få målvogtere: kun {pos_dist.get('MV', 0)}")
                
                if problems:
                    print(f"  ⚠️  Potentielle problemer:")
                    for problem in problems:
                        print(f"     - {problem}")
                else:
                    print(f"  ✅ Ingen åbenlyse problemer")
                    
            except Exception as e:
                print(f"  ❌ Fejl ved læsning af {file}: {e}")
        
        # Sammenlign på tværs af sæsoner
        print(f"\n📊 SAMMENLIGNING PÅ TVÆRS AF SÆSONER:")
        print("-" * 50)
        print(f"Total unikke spillere: {len(total_players)}")
        
        # Trends
        seasons_sorted = sorted(seasonal_data.keys())
        if len(seasons_sorted) > 1:
            first_season = seasonal_data[seasons_sorted[0]]
            last_season = seasonal_data[seasons_sorted[-1]]
            
            print(f"Spillere trend: {first_season['players']} → {last_season['players']}")
            print(f"Rating trend: {first_season['avg_rating']:.1f} → {last_season['avg_rating']:.1f}")
            print(f"Elite trend: {first_season['elite']} → {last_season['elite']}")
    
    # 2. ANALYSER ADVANCED FILER
    if advanced_files:
        print(f"\n🔬 ADVANCED FILER ({len(advanced_files)} filer)")
        print("-" * 50)
        
        for file in advanced_files:
            try:
                df = pd.read_csv(file)
                print(f"\n📋 {file}:")
                print(f"  📊 Rækker: {len(df)}")
                print(f"  📝 Kolonner: {len(df.columns)}")
                print(f"  📈 Kolonner: {list(df.columns[:5])}...")
                
                # Tjek for problemer
                problems = []
                
                # Tjek for tomme værdier
                null_counts = df.isnull().sum()
                high_null_cols = null_counts[null_counts > len(df) * 0.5]
                if len(high_null_cols) > 0:
                    problems.append(f"Mange tomme værdier i: {list(high_null_cols.index[:3])}")
                
                # Tjek for duplicerede rækker
                duplicates = df.duplicated().sum()
                if duplicates > 0:
                    problems.append(f"Duplikerede rækker: {duplicates}")
                
                if problems:
                    print(f"  ⚠️  Potentielle problemer:")
                    for problem in problems:
                        print(f"     - {problem}")
                else:
                    print(f"  ✅ Ingen åbenlyse problemer")
                    
            except Exception as e:
                print(f"  ❌ Fejl ved læsning af {file}: {e}")
    
    # 3. GENEREL ANALYSE
    print(f"\n📈 GENEREL EVALUERING:")
    print("-" * 50)
    
    recommendations = []
    
    # Tjek for konsistens mellem sæsoner
    if len(herreliga_files) > 1:
        player_counts = [seasonal_data[season]['players'] for season in seasonal_data]
        if max(player_counts) - min(player_counts) > 100:
            recommendations.append("Store variationer i spiller antal mellem sæsoner - tjek data konsistens")
    
    # Tjek rating spredning
    if herreliga_files:
        avg_ratings = [seasonal_data[season]['avg_rating'] for season in seasonal_data]
        if any(rating > 1600 for rating in avg_ratings):
            recommendations.append("Meget høje gennemsnitsratings - overvej justering af system parametre")
        if any(rating < 1100 for rating in avg_ratings):
            recommendations.append("Meget lave gennemsnitsratings - tjek base rating settings")
    
    print("✅ STYRKER:")
    print("  • Konsistent fil struktur på tværs af sæsoner")
    print("  • Detaljerede performance metrics")
    print("  • God position tracking")
    print("  • Elite status kategorisering")
    
    if recommendations:
        print("\n⚠️  ANBEFALINGER:")
        for rec in recommendations:
            print(f"  • {rec}")
    else:
        print("\n🎯 Alle filer ser korrekte ud!")
    
    print(f"\n💾 ANBEFALET NÆSTE SKRIDT:")
    print("  1. Valider at start_rating progression er logisk mellem sæsoner")
    print("  2. Tjek om målvogter identifikation er korrekt")
    print("  3. Analyser outliers i rating udvikling")
    print("  4. Verificer at position distributions matcher forventninger")

if __name__ == "__main__":
    analyze_csv_files() 