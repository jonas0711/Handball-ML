#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 DEBUG SCRIPT - PLAYER TEAM MAPPING ANALYSE
==============================================

Analyserer spillernes holdtilknytning for at identificere:
1. Conflicting team codes (samme kode i begge ligaer)
2. Player distribution til teams
3. Detaljeret mapping debugging

Jonas' Debug Tool - December 2024
"""

import pandas as pd
import os
from collections import defaultdict, Counter

def analyze_player_based_teams():
    """Analyserer alle spillerbaserede team filer"""
    print("🔍 ANALYSERER SPILLERBASEREDE TEAM MAPPINGS")
    print("=" * 70)
    
    base_dir = "ELO_Results/Team_CSV/Player_Based"
    
    # Collect all team data by (team_code, season)
    all_teams = defaultdict(list)
    conflicting_teams = defaultdict(set)  # team_code -> set of leagues
    
    # Process all CSV files
    for filename in os.listdir(base_dir):
        if filename.endswith('.csv') and 'career' not in filename:
            filepath = os.path.join(base_dir, filename)
            try:
                df = pd.read_csv(filepath)
                
                for _, row in df.iterrows():
                    team_code = row['team_code']
                    league = row['league']
                    
                    # Track leagues for each team_code
                    conflicting_teams[team_code].add(league)
                    
                    team_data = {
                        'file': filename,
                        'season': row['season'],
                        'team_name': row['team_name'],
                        'league': league,
                        'players': row['total_players'],
                        'avg_rating': row['team_avg_rating']
                    }
                    all_teams[team_code].append(team_data)
                    
            except Exception as e:
                print(f"⚠️ Fejl i {filename}: {e}")
                
    # Find actual conflicts (team codes in multiple leagues)
    actual_conflicts = {code: leagues for code, leagues in conflicting_teams.items() 
                       if len(leagues) > 1}
    
    # Analyze conflicts
    print(f"\n🔍 TEAM CODE KONFLIKT ANALYSE")
    print("-" * 50)
    
    if actual_conflicts:
        print(f"⚠️ FUNDET {len(actual_conflicts)} KONFLIKTENDE TEAM KODER:")
        
        for team_code, leagues in actual_conflicts.items():
            print(f"\n🚨 KONFLIKT: {team_code} findes i {leagues}")
            
            # Show detailed data for conflicts
            seasons = all_teams[team_code]
            for season_data in seasons:
                print(f"   📁 {season_data['file']}: {season_data['team_name']} "
                      f"({season_data['league']}, {season_data['players']} spillere, "
                      f"rating: {season_data['avg_rating']:.1f})")
    else:
        print("✅ INGEN KONFLIKTER FUNDET - Alle team koder er unikke per liga")
        
    # Special analysis for problematic teams
    print(f"\n🎯 ANALYSE AF PROBLEMATISKE TEAMS:")
    print("-" * 50)
    
    problematic_teams = ['SJE', 'TMS', 'AJA']  # Known problematic codes
    
    for team_code in problematic_teams:
        if team_code in all_teams:
            seasons = all_teams[team_code]
            leagues = set(s['league'] for s in seasons)
            
            print(f"\n📊 {team_code} (Ligaer: {leagues}):")
            
            # Group by league
            herreliga_seasons = [s for s in seasons if s['league'] == 'Herreliga']
            kvindeliga_seasons = [s for s in seasons if s['league'] == 'Kvindeliga']
            
            if herreliga_seasons:
                print(f"   🏃‍♂️ Herreliga ({len(herreliga_seasons)} sæsoner):")
                for s in herreliga_seasons:
                    print(f"      {s['season']}: {s['team_name']} ({s['players']} spillere)")
                    
            if kvindeliga_seasons:
                print(f"   🏃‍♀️ Kvindeliga ({len(kvindeliga_seasons)} sæsoner):")
                for s in kvindeliga_seasons:
                    print(f"      {s['season']}: {s['team_name']} ({s['players']} spillere)")
                    
            # Check for gender confusion
            team_names = [s['team_name'] for s in seasons]
            unique_names = set(team_names)
            
            if len(unique_names) > 1:
                print(f"   ⚠️ Forskellige holdnavne brugt: {unique_names}")
            
            # Check if it's clearly a women's team in men's league
            first_season = seasons[0]
            if ('kvinde' in first_season['team_name'].lower() or 
                'women' in first_season['team_name'].lower()):
                if first_season['league'] == 'Herreliga':
                    print(f"   🚨 KRITISK FEJL: Kvindehåndbold i Herreliga!")
                    
    # Detailed analysis for SJE specifically  
    print(f"\n🎯 DETALJERET SJE ANALYSE:")
    print("-" * 50)
    
    sje_data = all_teams.get('SJE', [])
    if sje_data:
        print(f"SJE har {len(sje_data)} sæsoner i systemet:")
        
        for season_data in sje_data:
            print(f"📅 {season_data['season']}: {season_data['team_name']}")
            print(f"   Liga: {season_data['league']}")
            print(f"   Spillere: {season_data['players']}")
            print(f"   Rating: {season_data['avg_rating']:.1f}")
            
            # Analyze why this is wrong
            if season_data['league'] == 'Herreliga' and 'kvinde' in season_data['team_name'].lower():
                print(f"   🚨 FEJL: Dette er klart et kvindehåndbold hold!")
            print()
    else:
        print("❌ Ingen SJE data fundet")
        
    # Create comprehensive CSV report 
    print(f"\n💾 GENERERER OMFATTENDE RAPPORT")
    print("-" * 50)
    
    all_report_data = []
    
    for team_code, seasons in all_teams.items():
        leagues = set(s['league'] for s in seasons)
        is_conflict = len(leagues) > 1
        
        for season_data in seasons:
            # Determine if this specific entry is problematic
            is_problem = False
            problem_type = ""
            
            if is_conflict:
                is_problem = True
                problem_type = "Multi-league conflict"
            elif (team_code == 'SJE' and 
                  season_data['league'] == 'Herreliga' and 
                  'kvinde' in season_data['team_name'].lower()):
                is_problem = True
                problem_type = "Women's team in men's league"
                
            all_report_data.append({
                'team_code': team_code,
                'season': season_data['season'],
                'team_name': season_data['team_name'],
                'league': season_data['league'],
                'total_players': season_data['players'],
                'avg_rating': season_data['avg_rating'],
                'file': season_data['file'],
                'is_conflict': is_conflict,
                'is_problem': is_problem,
                'problem_type': problem_type,
                'leagues_for_code': "|".join(sorted(leagues))
            })
            
    if all_report_data:
        df_full_report = pd.DataFrame(all_report_data)
        output_path = "debug_team_mappings_analysis.csv"
        df_full_report.to_csv(output_path, index=False)
        print(f"💾 Omfattende rapport gemt: {output_path}")
        
        # Summary statistics
        conflicts = df_full_report[df_full_report['is_conflict'] == True]
        problems = df_full_report[df_full_report['is_problem'] == True]
        
        print(f"📊 RAPPORT STATISTIK:")
        print(f"   Total entries: {len(df_full_report)}")
        print(f"   Konflikter: {len(conflicts)}")
        print(f"   Problemer: {len(problems)}")
        
        if len(problems) > 0:
            print(f"\n🚨 PROBLEMATISKE ENTRIES:")
            for _, problem in problems.iterrows():
                print(f"   - {problem['team_code']} ({problem['season']}): "
                      f"{problem['team_name']} i {problem['league']}")
                print(f"     Problem: {problem['problem_type']}")
        
    return actual_conflicts, all_teams

def recommend_fixes():
    """Anbefaler konkrete fixes til problemerne"""
    print(f"\n🛠️ ANBEFALEDE FIXES:")
    print("=" * 70)
    
    print("1. 🔧 TEAM CODE SEPARATION:")
    print("   - SJH: SønderjyskE Herrehåndbold (Herreliga)")  
    print("   - SJK: SønderjyskE Kvindehåndbold (Kvindeliga)")
    print("   - TMH: TMS Ringsted Herrer (Herreliga)")
    print("   - TMK: TMS Ringsted Kvinder (Kvindeliga)")
    print("   - AJH: Ajax København Herrer (Herreliga)")
    print("   - AJK: Ajax København Kvinder (Kvindeliga)")
    
    print("\n2. 🔧 KODE ÆNDRINGER I player_based_team_elo_system.py:")
    print("   - Fjern SJE fra HERRELIGA_TEAMS")
    print("   - Tilføj SJH til HERRELIGA_TEAMS")
    print("   - Skift SJE til SJK i KVINDELIGA_TEAMS")
    print("   - Opdater TEAM_NAME_MAPPINGS med kønsspecifikke patterns")
    
    print("\n3. 🔧 SPECIAL HANDLING I get_team_code_from_name():")
    print("   - Detect 'kvinde'/'women' keywords for SønderjyskE")
    print("   - Return SJK for kvindehåndbold, SJH for herrehåndbold")
    print("   - Tilføj backward compatibility for legacy SJE kode")
    
    print("\n4. ✅ VALIDERING EFTER FIX:")
    print("   - Regenerer player-based team ELO system")
    print("   - Verificer at SJK kun findes i Kvindeliga")
    print("   - Tjek at antal spillere er fornuftigt")

if __name__ == "__main__":
    conflicts, all_teams = analyze_player_based_teams()
    
    if conflicts:
        print(f"\n⚠️ FUNDET {len(conflicts)} KONFLIKTENDE TEAM KODER")
        recommend_fixes()
    else:
        print(f"\n✅ INGEN KONFLIKTER FUNDET - ALLE TEAM KODER ER UNIKKE")
        # Still check for logical problems like women's teams in men's leagues
        sje_data = all_teams.get('SJE', [])
        if sje_data and any(s['league'] == 'Herreliga' for s in sje_data):
            print(f"\n⚠️ LOGISK PROBLEM: SJE kvindehåndbold findes i Herreliga")
            recommend_fixes() 