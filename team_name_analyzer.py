#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🔍 HÅNDBOL TEAM NAVN ANALYSE SCRIPT
===================================

ANALYSERER ALLE UNIKKE HOLDNAVNE I DATABASER FOR:
✅ Kvindeliga: alle sæsoner fra 2017-2018 til 2024-2025
✅ Herreliga: alle sæsoner fra 2017-2018 til 2024-2025
✅ Identificerer navne-variationer og potentielle mapping fejl
✅ Genererer detaljerede rapporter for team mapping forbedringer
✅ Søger efter patterns og skiftende holdnavne

Jonas' Team Mapping System - December 2024
"""

import pandas as pd
import sqlite3
import os
from collections import defaultdict, Counter
from typing import Dict, List, Set, Tuple
import warnings
warnings.filterwarnings('ignore')

class TeamNameAnalyzer:
    """
    🔍 ANALYSERER ALLE TEAM NAVNE I HÅNDBOL DATABASER
    """
    
    def __init__(self, base_dir: str = "."):
        print("🔍 HÅNDBOL TEAM NAVN ANALYSE SCRIPT")
        print("=" * 70)
        
        self.base_dir = base_dir
        
        # Database directories
        self.kvindeliga_dir = os.path.join(base_dir, "Kvindeliga-database")
        self.herreliga_dir = os.path.join(base_dir, "Herreliga-database")
        
        # Data storage
        self.kvindeliga_team_names = defaultdict(set)  # season -> set of team names
        self.herreliga_team_names = defaultdict(set)  # season -> set of team names
        
        self.kvindeliga_all_names = set()  # All unique team names across all seasons
        self.herreliga_all_names = set()  # All unique team names across all seasons
        
        # Seasons to analyze
        self.seasons = [
            "2017-2018", "2018-2019", "2019-2020", "2020-2021",
            "2021-2022", "2022-2023", "2023-2024", "2024-2025"
        ]
        
        # Eksisterende team mappings fra systemerne
        self.current_kvindeliga_teams = {
            'AHB': 'Aarhus Håndbold Kvinder',
            'BFH': 'Bjerringbro FH',
            'EHA': 'EH Aalborg',
            'HHE': 'Horsens Håndbold Elite',
            'IKA': 'Ikast Håndbold',
            'KBH': 'København Håndbold',
            'NFH': 'Nykøbing F. Håndbold',
            'ODE': 'Odense Håndbold',
            'RIN': 'Ringkøbing Håndbold',
            'SVK': 'Silkeborg-Voel KFUM',
            'SKB': 'Skanderborg Håndbold',
            'SJE': 'SønderjyskE Kvindehåndbold',
            'TES': 'Team Esbjerg',
            'VHK': 'Viborg HK',
            'TMS': 'TMS Ringsted'
        }
        
        self.current_herreliga_teams = {
            'AAH': 'Aalborg Håndbold',
            'BSH': 'Bjerringbro-Silkeborg',
            'FHK': 'Fredericia Håndbold Klub',
            'GIF': 'Grindsted GIF Håndbold',
            'GOG': 'GOG',
            'KIF': 'KIF Kolding',
            'MTH': 'Mors-Thy Håndbold',
            'NSH': 'Nordsjælland Håndbold',
            'REH': 'Ribe-Esbjerg HH',
            'SAH': 'SAH - Skanderborg AGF',
            'SKH': 'Skjern Håndbold',
            'SJE': 'SønderjyskE Herrehåndbold',
            'TTH': 'TTH Holstebro'
        }
        
        print("✅ Team Navn Analyzer initialiseret")
        print(f"📂 Kvindeliga directory: {self.kvindeliga_dir}")
        print(f"📂 Herreliga directory: {self.herreliga_dir}")
        print(f"📅 Sæsoner til analyse: {len(self.seasons)}")
        
    def extract_team_names_from_season(self, league: str, season: str) -> Set[str]:
        """
        Ekstraherer alle team navne fra en specifik sæson for en liga
        
        Args:
            league: "Kvindeliga" eller "Herreliga"
            season: f.eks. "2024-2025"
            
        Returns:
            Set af alle unique team navne fundet i den sæson
        """
        
        # Vælg korrekt directory
        if league == "Kvindeliga":
            season_dir = os.path.join(self.kvindeliga_dir, season)
        else:
            season_dir = os.path.join(self.herreliga_dir, season)
            
        team_names = set()
        
        if not os.path.exists(season_dir):
            print(f"  ⚠️ {league} {season}: directory findes ikke")
            return team_names
            
        # Find alle .db filer
        db_files = [f for f in os.listdir(season_dir) if f.endswith('.db')]
        
        if not db_files:
            print(f"  ⚠️ {league} {season}: ingen database filer")
            return team_names
            
        matches_analyzed = 0
        
        for db_file in db_files:
            db_path = os.path.join(season_dir, db_file)
            
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Hent match_info for at få holdnavne
                cursor.execute("SELECT hold_hjemme, hold_ude, turnering FROM match_info LIMIT 1")
                match_info = cursor.fetchone()
                
                if match_info:
                    hold_hjemme, hold_ude, turnering = match_info
                    
                    # Tjek at det er den korrekte liga
                    if turnering:
                        if league == "Kvindeliga" and "Kvindelig" in turnering:
                            if hold_hjemme:
                                team_names.add(hold_hjemme.strip())
                            if hold_ude:
                                team_names.add(hold_ude.strip())
                            matches_analyzed += 1
                        elif league == "Herreliga" and "Herreliga" in turnering:
                            if hold_hjemme:
                                team_names.add(hold_hjemme.strip())
                            if hold_ude:
                                team_names.add(hold_ude.strip())
                            matches_analyzed += 1
                    else:
                        # Hvis turnering er null, tilføj alligevel (kan være data fejl)
                        if hold_hjemme:
                            team_names.add(hold_hjemme.strip())
                        if hold_ude:
                            team_names.add(hold_ude.strip())
                        matches_analyzed += 1
                
                conn.close()
                
            except Exception as e:
                print(f"    ❌ Fejl i {db_file}: {e}")
                
        print(f"  ✅ {league} {season}: {len(team_names)} unique team navne fra {matches_analyzed} kampe")
        return team_names
        
    def analyze_all_seasons(self):
        """
        Analyserer alle sæsoner for både Kvindeliga og Herreliga
        """
        print("\n🔍 ANALYSERER ALLE SÆSONER")
        print("=" * 70)
        
        # Analyser Kvindeliga
        print("\n🏐 KVINDELIGA ANALYSE:")
        print("-" * 40)
        
        for season in self.seasons:
            team_names = self.extract_team_names_from_season("Kvindeliga", season)
            self.kvindeliga_team_names[season] = team_names
            self.kvindeliga_all_names.update(team_names)
            
        # Analyser Herreliga  
        print("\n🏐 HERRELIGA ANALYSE:")
        print("-" * 40)
        
        for season in self.seasons:
            team_names = self.extract_team_names_from_season("Herreliga", season)
            self.herreliga_team_names[season] = team_names
            self.herreliga_all_names.update(team_names)
            
        print(f"\n📊 SAMLET RESULTAT:")
        print(f"   🏐 Kvindeliga: {len(self.kvindeliga_all_names)} unique team navne")
        print(f"   🏐 Herreliga: {len(self.herreliga_all_names)} unique team navne")
        
    def find_similar_team_names(self, team_names: Set[str]) -> Dict[str, List[str]]:
        """
        Finder potentielt lignende team navne der kan være samme klub
        
        Returns:
            Dict hvor key er "base" navn og value er liste af lignende navne
        """
        potential_groups = defaultdict(list)
        
        # Konverter til sorteret liste for consistens
        names_list = sorted(list(team_names))
        
        for i, name1 in enumerate(names_list):
            for j, name2 in enumerate(names_list[i+1:], i+1):
                
                # Forskellige similarity checks
                similarity_score = 0
                
                # 1. Check for fælles ord
                words1 = set(name1.lower().split())
                words2 = set(name2.lower().split())
                common_words = words1.intersection(words2)
                
                if len(common_words) >= 1:
                    similarity_score += len(common_words) * 2
                    
                # 2. Check for substring match
                if name1.lower() in name2.lower() or name2.lower() in name1.lower():
                    similarity_score += 3
                    
                # 3. Check for geographical indicators (bynavn)
                geo_words = {
                    'aalborg', 'aarhus', 'esbjerg', 'odense', 'viborg', 'kolding',
                    'silkeborg', 'horsens', 'skanderborg', 'ringkøbing', 'fredericia',
                    'bjerringbro', 'holstebro', 'skjern', 'ikast', 'nykøbing',
                    'nordsjælland', 'køben', 'københavn', 'grindsted', 'thy', 'mors'
                }
                
                geo_match = False
                for geo in geo_words:
                    if geo in name1.lower() and geo in name2.lower():
                        geo_match = True
                        similarity_score += 4
                        break
                        
                # Hvis høj similarity score, gruppe dem
                if similarity_score >= 4:
                    # Brug det korteste navn som key
                    key = name1 if len(name1) <= len(name2) else name2
                    other = name2 if key == name1 else name1
                    
                    # Tilføj til gruppen
                    if key not in potential_groups:
                        potential_groups[key] = [key]
                    if other not in potential_groups[key]:
                        potential_groups[key].append(other)
                        
        return dict(potential_groups)
        
    def generate_comprehensive_report(self):
        """
        Genererer omfattende rapport med alle fund og anbefalinger
        """
        print("\n📊 GENERERER OMFATTENDE TEAM MAPPING RAPPORT")
        print("=" * 70)
        
        # Find lignende navne for begge ligaer
        kvindeliga_groups = self.find_similar_team_names(self.kvindeliga_all_names)
        herreliga_groups = self.find_similar_team_names(self.herreliga_all_names)
        
        # Generer rapport data
        report_data = {
            'kvindeliga_analysis': {
                'total_unique_names': len(self.kvindeliga_all_names),
                'all_names': sorted(list(self.kvindeliga_all_names)),
                'potential_groups': kvindeliga_groups,
                'current_mapping': self.current_kvindeliga_teams
            },
            'herreliga_analysis': {
                'total_unique_names': len(self.herreliga_all_names),
                'all_names': sorted(list(self.herreliga_all_names)),
                'potential_groups': herreliga_groups,
                'current_mapping': self.current_herreliga_teams
            }
        }
        
        # Print detailed analysis
        print("\n🏐 KVINDELIGA DETALJERET ANALYSE:")
        print("-" * 50)
        print(f"📊 Total unikke navne: {len(self.kvindeliga_all_names)}")
        
        print("\n🔍 ALLE KVINDELIGA TEAM NAVNE:")
        for i, name in enumerate(sorted(list(self.kvindeliga_all_names)), 1):
            print(f"  {i:2d}. {name}")
            
        if kvindeliga_groups:
            print("\n⚠️ POTENTIELLE KVINDELIGA GRUPPERINGER:")
            for base_name, similar_names in kvindeliga_groups.items():
                if len(similar_names) > 1:
                    print(f"  🔗 {base_name}:")
                    for name in similar_names:
                        if name != base_name:
                            print(f"     → {name}")
                            
        print("\n🏐 HERRELIGA DETALJERET ANALYSE:")
        print("-" * 50)
        print(f"📊 Total unikke navne: {len(self.herreliga_all_names)}")
        
        print("\n🔍 ALLE HERRELIGA TEAM NAVNE:")
        for i, name in enumerate(sorted(list(self.herreliga_all_names)), 1):
            print(f"  {i:2d}. {name}")
            
        if herreliga_groups:
            print("\n⚠️ POTENTIELLE HERRELIGA GRUPPERINGER:")
            for base_name, similar_names in herreliga_groups.items():
                if len(similar_names) > 1:
                    print(f"  🔗 {base_name}:")
                    for name in similar_names:
                        if name != base_name:
                            print(f"     → {name}")
                            
        # Gem detaljerede CSV filer
        self.save_analysis_to_csv(report_data)
        
        return report_data
        
    def save_analysis_to_csv(self, report_data: Dict):
        """
        Gemmer analyse resultater til CSV filer for videre arbejde
        """
        print("\n💾 GEMMER ANALYSE RESULTATER:")
        
        # Kvindeliga alle navne
        kvindeliga_df = pd.DataFrame({
            'team_name': report_data['kvindeliga_analysis']['all_names'],
            'league': 'Kvindeliga'
        })
        kvindeliga_df.to_csv('kvindeliga_all_team_names.csv', index=False, encoding='utf-8')
        print(f"  ✅ kvindeliga_all_team_names.csv ({len(kvindeliga_df)} navne)")
        
        # Herreliga alle navne  
        herreliga_df = pd.DataFrame({
            'team_name': report_data['herreliga_analysis']['all_names'],
            'league': 'Herreliga'
        })
        herreliga_df.to_csv('herreliga_all_team_names.csv', index=False, encoding='utf-8')
        print(f"  ✅ herreliga_all_team_names.csv ({len(herreliga_df)} navne)")
        
        # Kombineret oversigt
        combined_df = pd.concat([kvindeliga_df, herreliga_df], ignore_index=True)
        combined_df.to_csv('all_handball_team_names.csv', index=False, encoding='utf-8')
        print(f"  ✅ all_handball_team_names.csv ({len(combined_df)} total navne)")
        
        # Per-sæson analyse
        season_data = []
        
        for season in self.seasons:
            for team_name in self.kvindeliga_team_names.get(season, set()):
                season_data.append({
                    'season': season,
                    'league': 'Kvindeliga', 
                    'team_name': team_name
                })
                
            for team_name in self.herreliga_team_names.get(season, set()):
                season_data.append({
                    'season': season,
                    'league': 'Herreliga',
                    'team_name': team_name
                })
                
        season_df = pd.DataFrame(season_data)
        season_df.to_csv('team_names_by_season.csv', index=False, encoding='utf-8')
        print(f"  ✅ team_names_by_season.csv ({len(season_df)} entries)")
        
    def run_complete_analysis(self):
        """
        🚀 Kører komplet team navn analyse
        """
        print("\n🚀 STARTER KOMPLET TEAM NAVN ANALYSE")
        print("=" * 70)
        
        # Analyser alle sæsoner
        self.analyze_all_seasons()
        
        # Generer omfattende rapport
        report_data = self.generate_comprehensive_report()
        
        print("\n✅ TEAM NAVN ANALYSE KOMPLET!")
        print("=" * 70)
        print("📁 Genererede filer:")
        print("  • kvindeliga_all_team_names.csv")
        print("  • herreliga_all_team_names.csv") 
        print("  • all_handball_team_names.csv")
        print("  • team_names_by_season.csv")
        print("\n🎯 Næste trin:")
        print("  1. Gennemgå de genererede CSV filer")
        print("  2. Identificer klubber med multiple navne")
        print("  3. Rechercher holdhistorik online")
        print("  4. Opret forbedret team mapping")
        
        return report_data


# === MAIN EXECUTION ===
if __name__ == "__main__":
    print("🔍 STARTER HÅNDBOL TEAM NAVN ANALYSE")
    print("=" * 80)
    
    # Opret analyzer instance
    analyzer = TeamNameAnalyzer()
    
    # Kør komplet analyse
    analysis_results = analyzer.run_complete_analysis()
    
    print("\n🎉 TEAM NAVN ANALYSE SYSTEM KOMPLET!")
    print("=" * 80)