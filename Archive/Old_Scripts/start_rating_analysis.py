#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏁 START_RATING PROGRESSION ANALYSE
==================================
Fokuseret analyse af hvordan start_rating progression fungerer mellem sæsoner
"""

import pandas as pd
import glob

def analyze_start_rating_progression():
    """Analyserer start_rating progression mellem sæsoner"""
    print("🏁 START_RATING PROGRESSION ANALYSE")
    print("=" * 70)
    
    # Find alle herreliga filer
    herreliga_files = sorted([f for f in glob.glob("*.csv") if f.startswith('herreliga_seasonal_elo_')])
    
    # Find et par spillere til detaljeret sporing
    sample_players = ['Nicolaj JØRGENSEN', 'Noah GAUDIN', 'Emil MADSEN', 'Mads Svane KNUDSEN']
    
    # 1. GRUNDLÆGGENDE START_RATING ANALYSE
    print("\n📊 GRUNDLÆGGENDE START_RATING STATISTIK:")
    print("-" * 50)
    
    for file in herreliga_files:
        season = file.replace('herreliga_seasonal_elo_', '').replace('.csv', '').replace('_', '-')
        df = pd.read_csv(file)
        
        start_ratings = df['start_rating']
        unique_starts = start_ratings.unique()
        
        print(f"📅 {season}:")
        print(f"  📈 Start rating interval: {start_ratings.min():.0f} - {start_ratings.max():.0f}")
        print(f"  📊 Gennemsnit start rating: {start_ratings.mean():.1f}")
        print(f"  🔢 Antal unikke start ratings: {len(unique_starts)}")
        
        # Tjek for specielle værdier
        players_at_1000 = len(df[df['start_rating'] == 1000])
        players_around_1400 = len(df[(df['start_rating'] >= 1390) & (df['start_rating'] <= 1410)])
        
        if players_at_1000 > 0:
            print(f"  🆕 Spillere der starter på 1000: {players_at_1000}")
        if players_around_1400 > 10:
            print(f"  🎯 Spillere omkring ~1400: {players_around_1400}")
    
    # 2. DETALJERET SPILLER PROGRESSION
    print(f"\n👥 DETALJERET SPILLER PROGRESSION:")
    print("-" * 50)
    
    for player in sample_players:
        print(f"\n🏃 {player}:")
        player_seasons = []
        
        for file in herreliga_files:
            season = file.replace('herreliga_seasonal_elo_', '').replace('.csv', '').replace('_', '-')
            df = pd.read_csv(file)
            
            player_data = df[df['player'] == player]
            if not player_data.empty:
                row = player_data.iloc[0]
                player_seasons.append({
                    'season': season,
                    'start': row['start_rating'],
                    'final': row['final_rating'],
                    'change': row['rating_change'],
                    'games': row['games']
                })
        
        if len(player_seasons) > 1:
            for i, season_data in enumerate(player_seasons):
                if i == 0:
                    print(f"  📅 {season_data['season']}: {season_data['start']:.0f} → {season_data['final']:.0f} (+{season_data['change']:.0f}) [{season_data['games']} kampe] (første sæson)")
                else:
                    prev_final = player_seasons[i-1]['final']
                    current_start = season_data['start']
                    diff = current_start - prev_final
                    
                    status = "✅" if abs(diff) <= 10 else "⚠️"
                    print(f"  📅 {season_data['season']}: {season_data['start']:.0f} → {season_data['final']:.0f} (+{season_data['change']:.0f}) [{season_data['games']} kampe] {status} (diff: {diff:+.0f})")
        elif len(player_seasons) == 1:
            season_data = player_seasons[0]
            print(f"  📅 {season_data['season']}: {season_data['start']:.0f} → {season_data['final']:.0f} (+{season_data['change']:.0f}) [{season_data['games']} kampe] (kun denne sæson)")
        else:
            print(f"  ❌ Ikke fundet i nogen sæson")
    
    # 3. SYSTEM ANALYSE
    print(f"\n🔍 SYSTEM ANALYSE:")
    print("-" * 50)
    
    # Læs de to seneste sæsoner for analyse
    df_2023 = pd.read_csv('herreliga_seasonal_elo_2023_2024.csv')
    df_2024 = pd.read_csv('herreliga_seasonal_elo_2024_2025.csv')
    
    # Find spillere der findes i begge sæsoner
    common_players = set(df_2023['player']).intersection(set(df_2024['player']))
    
    perfect_progression = 0
    reset_to_standard = 0
    slight_adjustments = 0
    major_differences = 0
    
    for player in common_players:
        final_2023 = df_2023[df_2023['player'] == player]['final_rating'].iloc[0]
        start_2024 = df_2024[df_2024['player'] == player]['start_rating'].iloc[0]
        
        diff = abs(start_2024 - final_2023)
        
        if diff <= 1:
            perfect_progression += 1
        elif start_2024 >= 1390 and start_2024 <= 1410:  # Systemets standard rating
            reset_to_standard += 1
        elif diff <= 10:
            slight_adjustments += 1
        else:
            major_differences += 1
    
    total_common = len(common_players)
    
    print(f"📊 Analyse af {total_common} spillere der findes i både 2023-24 og 2024-25:")
    print(f"  ✅ Perfekt progression (diff ≤1): {perfect_progression} ({perfect_progression/total_common*100:.1f}%)")
    print(f"  🔄 Reset til standard (~1400): {reset_to_standard} ({reset_to_standard/total_common*100:.1f}%)")
    print(f"  🔧 Små justeringer (diff ≤10): {slight_adjustments} ({slight_adjustments/total_common*100:.1f}%)")
    print(f"  ⚠️  Store forskelle (diff >10): {major_differences} ({major_differences/total_common*100:.1f}%)")
    
    # 4. KONKLUSION
    print(f"\n🎯 KONKLUSION:")
    print("-" * 50)
    
    if reset_to_standard > total_common * 0.7:  # Mere end 70%
        print("🔄 SYSTEMET BRUGER STANDARD START RATING:")
        print("   Systemet nulstiller spilleres rating til ~1400 hver sæson")
        print("   Dette er en KORREKT implementering hvis det er designet sådan")
        print("   ✅ Sikrer balance og forhindrer rating inflation")
        print("   ✅ Gør hver sæson til en 'ren start'")
        print("   ✅ Fokuserer på sæson performance fremfor historisk rating")
    elif perfect_progression > total_common * 0.7:
        print("🏁 SYSTEMET BRUGER PERFEKT PROGRESSION:")
        print("   Spilleres start rating matcher forrige sæsons final rating")
        print("   Dette bevarer rating kontinuitet på tværs af sæsoner")
    else:
        print("🔀 SYSTEMET BRUGER BLANDET TILGANG:")
        print("   Kombination af progression og reset baseret på kriterier")
        print("   Dette kan være kompleks logik baseret på spillerens status")
    
    # 5. VALIDERING AF NYE SPILLERE
    print(f"\n🆕 NYE SPILLERE ANALYSE:")
    print("-" * 50)
    
    # Find spillere med start_rating = 1000 (nye spillere)
    new_players_2024 = df_2024[df_2024['start_rating'] == 1000]
    
    if len(new_players_2024) > 0:
        print(f"📊 {len(new_players_2024)} nye spillere i 2024-25 (starter på 1000):")
        print(f"  📈 Gennemsnitlig rating stigning: {new_players_2024['rating_change'].mean():.1f}")
        print(f"  🎯 Højeste final rating: {new_players_2024['final_rating'].max():.0f}")
        print(f"  📊 Gennemsnit kampe: {new_players_2024['games'].mean():.1f}")
        
        # Vis de bedste nye spillere
        top_new = new_players_2024.nlargest(3, 'final_rating')
        print(f"  🏆 Top 3 nye spillere:")
        for _, player in top_new.iterrows():
            print(f"     • {player['player']}: 1000 → {player['final_rating']:.0f} (+{player['rating_change']:.0f})")
    else:
        print("📊 Ingen nye spillere fundet i 2024-25")

if __name__ == "__main__":
    analyze_start_rating_progression() 