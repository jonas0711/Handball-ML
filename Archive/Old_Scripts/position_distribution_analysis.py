#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎯 POSITION DISTRIBUTION & BIAS ANALYSE
=====================================

UNDERSØGER POSITIONAL BIAS I ELO SYSTEMET:
✅ Finder bedste spiller per position
✅ Analyserer overall ranking for hver positions top-spiller  
✅ Identificerer systematisk bias mod bestemte positioner
✅ Sammenligner på tværs af sæsoner
✅ Beregner position balance coefficients
✅ Foreslår justeringer hvis nødvendigt

FORMÅL:
- Sikre fair ELO ratings uafhængigt af position
- Identifikere hvis målvogtere eller andre positioner er undervurderet
- Balancere systemet så position ikke påvirker rating potentiale

Jonas' Positional Analysis Tool - December 2024
"""

import pandas as pd
import numpy as np
import glob
from collections import defaultdict
import matplotlib.pyplot as plt

def analyze_positional_bias_comprehensive():
    """
    🔍 OMFATTENDE POSITIONAL BIAS ANALYSE
    """
    print("🎯 POSITION DISTRIBUTION & BIAS ANALYSE")
    print("=" * 70)
    
    # Find alle herreliga seasonal CSV filer
    csv_files = sorted([f for f in glob.glob("*.csv") if f.startswith('herreliga_seasonal_elo_')])
    
    if not csv_files:
        print("❌ Ingen herreliga seasonal CSV filer fundet!")
        return
    
    print(f"📁 Fundet {len(csv_files)} sæson filer")
    
    # Analyse per sæson og samlet
    all_seasons_data = []
    season_analysis = {}
    
    for csv_file in csv_files:
        print(f"\n📊 ANALYSERER: {csv_file}")
        print("-" * 50)
        
        try:
            df = pd.read_csv(csv_file)
            
            # Extract season from filename
            season = csv_file.replace('herreliga_seasonal_elo_', '').replace('.csv', '').replace('_', '-')
            
            # Valider at vi har de rigtige kolonner
            required_cols = ['player', 'final_rating', 'primary_position', 'position_name']
            missing_cols = [col for col in required_cols if col not in df.columns]
            
            if missing_cols:
                print(f"⚠️  Mangler kolonner: {missing_cols} - springer over")
                continue
            
            # Sort by final_rating for overall ranking
            df_sorted = df.sort_values('final_rating', ascending=False).reset_index(drop=True)
            df_sorted['overall_rank'] = df_sorted.index + 1
            
            # Analyser per position
            position_stats = {}
            
            # Find unikke positioner
            positions = df['primary_position'].unique()
            
            print(f"🏐 Positioner fundet: {sorted(positions)}")
            print(f"📊 Total spillere: {len(df)}")
            
            position_results = []
            
            for position in sorted(positions):
                pos_players = df[df['primary_position'] == position].copy()
                
                if len(pos_players) == 0:
                    continue
                
                # Find bedste spiller for denne position
                best_player = pos_players.loc[pos_players['final_rating'].idxmax()]
                
                # Find overall ranking for denne spiller
                overall_rank = df_sorted[df_sorted['player'] == best_player['player']]['overall_rank'].iloc[0]
                
                # Position statistikker
                pos_stats = {
                    'position': position,
                    'position_name': best_player.get('position_name', 'Unknown'),
                    'count': len(pos_players),
                    'best_player': best_player['player'],
                    'best_rating': best_player['final_rating'],
                    'overall_rank': overall_rank,
                    'avg_rating': pos_players['final_rating'].mean(),
                    'median_rating': pos_players['final_rating'].median(),
                    'std_rating': pos_players['final_rating'].std(),
                    'min_rating': pos_players['final_rating'].min(),
                    'max_rating': pos_players['final_rating'].max(),
                    'season': season
                }
                
                position_results.append(pos_stats)
                position_stats[position] = pos_stats
            
            # Print sæson resultater
            print(f"\n🏆 BEDSTE SPILLERE PER POSITION - {season}:")
            
            # Sort positions by best player's overall rank
            sorted_positions = sorted(position_results, key=lambda x: x['overall_rank'])
            
            for pos_data in sorted_positions:
                rank_status = "🥇" if pos_data['overall_rank'] <= 10 else "🥈" if pos_data['overall_rank'] <= 30 else "🥉" if pos_data['overall_rank'] <= 50 else "📊"
                
                print(f"  {rank_status} {pos_data['position']} ({pos_data['position_name']:<12}): "
                      f"#{pos_data['overall_rank']:3d} - {pos_data['best_player']} "
                      f"({pos_data['best_rating']:.0f}) [{pos_data['count']:2d} spillere]")
            
            # Beregn balance metrics
            position_ranks = [p['overall_rank'] for p in position_results]
            position_ratings = [p['best_rating'] for p in position_results]
            
            if len(position_ranks) > 1:
                rank_spread = max(position_ranks) - min(position_ranks)
                rating_spread = max(position_ratings) - min(position_ratings)
                rank_std = np.std(position_ranks)
                rating_std = np.std(position_ratings)
                
                print(f"\n📊 BALANCE METRICS - {season}:")
                print(f"   🎯 Ranking spread: {rank_spread} positions (lavere = bedre balance)")
                print(f"   📈 Rating spread: {rating_spread:.0f} points")
                print(f"   📊 Ranking std dev: {rank_std:.1f}")
                print(f"   📊 Rating std dev: {rating_std:.1f}")
                
                # Balance vurdering
                if rank_spread <= 30:
                    balance_status = "✅ EXCELLENT"
                elif rank_spread <= 60:
                    balance_status = "✅ GOOD"
                elif rank_spread <= 100:
                    balance_status = "⚠️ NEEDS ATTENTION"
                else:
                    balance_status = "❌ POOR BALANCE"
                    
                print(f"   🏆 Balance status: {balance_status}")
            
            # Gem til samlet analyse
            season_analysis[season] = {
                'position_results': position_results,
                'balance_metrics': {
                    'rank_spread': rank_spread if len(position_ranks) > 1 else 0,
                    'rating_spread': rating_spread if len(position_ratings) > 1 else 0,
                    'rank_std': rank_std if len(position_ranks) > 1 else 0,
                    'rating_std': rating_std if len(position_ratings) > 1 else 0
                }
            }
            
            # Tilføj til all seasons data
            for pos_data in position_results:
                all_seasons_data.append(pos_data)
            
        except Exception as e:
            print(f"❌ Fejl i {csv_file}: {e}")
            continue
    
    # === SAMLET ANALYSE PÅ TVÆRS AF SÆSONER ===
    if all_seasons_data:
        print(f"\n🌟 SAMLET ANALYSE PÅ TVÆRS AF ALLE SÆSONER")
        print("=" * 70)
        
        # Konverter til DataFrame for lettere analyse
        all_df = pd.DataFrame(all_seasons_data)
        
        # Grupper per position på tværs af sæsoner
        position_summary = {}
        
        for position in all_df['position'].unique():
            pos_data = all_df[all_df['position'] == position]
            
            position_summary[position] = {
                'position_name': pos_data['position_name'].iloc[0],
                'seasons': len(pos_data),
                'avg_rank': pos_data['overall_rank'].mean(),
                'best_rank': pos_data['overall_rank'].min(),
                'worst_rank': pos_data['overall_rank'].max(),
                'avg_best_rating': pos_data['best_rating'].mean(),
                'total_players': pos_data['count'].sum(),
                'avg_players_per_season': pos_data['count'].mean()
            }
        
        print(f"📊 POSITION SUMMARY PÅ TVÆRS AF {len(season_analysis)} SÆSONER:")
        print()
        
        # Sort by average rank (lavere = bedre)
        sorted_positions = sorted(position_summary.items(), key=lambda x: x[1]['avg_rank'])
        
        for position, data in sorted_positions:
            rank_trend = "🔥" if data['avg_rank'] <= 20 else "⭐" if data['avg_rank'] <= 40 else "📊" if data['avg_rank'] <= 60 else "⚠️"
            
            print(f"  {rank_trend} {position} ({data['position_name']:<12}): "
                  f"Avg #{data['avg_rank']:4.1f} (#{data['best_rank']:2d}-#{data['worst_rank']:2d}) "
                  f"| Rating: {data['avg_best_rating']:4.0f} "
                  f"| {data['avg_players_per_season']:4.1f} spillere/sæson")
        
        # === BIAS DETECTION ===
        print(f"\n🔍 POSITIONAL BIAS DETECTION:")
        print("-" * 50)
        
        avg_ranks = [data['avg_rank'] for data in position_summary.values()]
        overall_avg_rank = np.mean(avg_ranks)
        rank_variance = np.var(avg_ranks)
        
        print(f"📊 Gennemsnitlig position rank: {overall_avg_rank:.1f}")
        print(f"📊 Rank variance: {rank_variance:.1f}")
        
        # Identifikér systematisk bias
        biased_positions = []
        
        for position, data in position_summary.items():
            deviation = data['avg_rank'] - overall_avg_rank
            
            if abs(deviation) > 20:  # Betydelig afvigelse
                bias_type = "undervurderet" if deviation > 0 else "overvurderet"
                biased_positions.append({
                    'position': position,
                    'position_name': data['position_name'],
                    'bias_type': bias_type,
                    'deviation': deviation,
                    'avg_rank': data['avg_rank']
                })
        
        if biased_positions:
            print(f"\n⚠️  FUNDET {len(biased_positions)} POSITIONER MED SYSTEMATISK BIAS:")
            
            for bias in sorted(biased_positions, key=lambda x: abs(x['deviation']), reverse=True):
                bias_icon = "📉" if bias['bias_type'] == "undervurderet" else "📈"
                print(f"   {bias_icon} {bias['position']} ({bias['position_name']}): "
                      f"{bias['bias_type']} (avg #{bias['avg_rank']:.1f}, "
                      f"afvigelse: {bias['deviation']:+.1f})")
        else:
            print("✅ INGEN SYSTEMATISK POSITIONAL BIAS DETEKTERET!")
        
        # === ANBEFALINGER ===
        print(f"\n💡 ANBEFALINGER:")
        print("-" * 50)
        
        if rank_variance > 400:  # Høj variance indikerer ubalance
            print("❌ HØJ POSITIONAL VARIANCE - SYSTEMETISKE JUSTERINGER NØDVENDIGE:")
            
            for bias in biased_positions:
                if bias['bias_type'] == "undervurderet":
                    print(f"   🔧 Øg action vægte for {bias['position']} ({bias['position_name']})")
                    print(f"       Forslag: Øg position multiplier fra 1.0 til 1.1-1.2")
                elif bias['bias_type'] == "overvurderet":
                    print(f"   🔧 Reducer action vægte for {bias['position']} ({bias['position_name']})")
                    print(f"       Forslag: Reducer position multiplier fra 1.0 til 0.9-0.8")
        
        elif rank_variance > 200:
            print("⚠️ MODERAT POSITIONAL VARIANCE - MINDRE JUSTERINGER:")
            
            if biased_positions:
                most_biased = max(biased_positions, key=lambda x: abs(x['deviation']))
                print(f"   🎯 Fokuser på {most_biased['position']} ({most_biased['position_name']})")
                print(f"       {most_biased['bias_type']} med {most_biased['deviation']:+.1f} afvigelse")
        
        else:
            print("✅ EXCELLENT POSITIONAL BALANCE!")
            print("   Systemet behandler alle positioner fair")
            print("   Ingen systematiske justeringer nødvendige")
        
        # === GEM RESULTATER ===
        print(f"\n💾 GEMMER ANALYSE RESULTATER...")
        
        # Detaljeret sæson analyse
        season_df = pd.DataFrame(all_seasons_data)
        season_df.to_csv('positional_bias_detailed_analysis.csv', index=False)
        
        # Position summary
        summary_data = []
        for pos, data in position_summary.items():
            summary_data.append({
                'position': pos,
                'position_name': data['position_name'],
                'avg_rank': round(data['avg_rank'], 1),
                'best_rank': data['best_rank'],
                'worst_rank': data['worst_rank'],
                'avg_best_rating': round(data['avg_best_rating'], 1),
                'seasons_analyzed': data['seasons'],
                'total_players': data['total_players'],
                'avg_players_per_season': round(data['avg_players_per_season'], 1),
                'bias_status': 'undervurderet' if data['avg_rank'] > overall_avg_rank + 20 
                             else 'overvurderet' if data['avg_rank'] < overall_avg_rank - 20 
                             else 'balanced'
            })
        
        summary_df = pd.DataFrame(summary_data)
        summary_df = summary_df.sort_values('avg_rank')
        summary_df.to_csv('positional_balance_summary.csv', index=False)
        
        print("✅ Analyse gemt:")
        print("   📁 positional_bias_detailed_analysis.csv")
        print("   📁 positional_balance_summary.csv")
        
    else:
        print("❌ Ingen data til samlet analyse")

if __name__ == "__main__":
    analyze_positional_bias_comprehensive() 