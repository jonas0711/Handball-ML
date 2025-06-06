#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
POSITION DISTRIBUTION & BIAS ANALYSE
"""

import pandas as pd
import numpy as np
import glob

def analyze_positional_bias():
    print("🎯 POSITION DISTRIBUTION & BIAS ANALYSE")
    print("=" * 70)
    
    csv_files = sorted([f for f in glob.glob("*.csv") if f.startswith("herreliga_seasonal_elo_")])
    
    if not csv_files:
        print("❌ Ingen herreliga seasonal CSV filer fundet!")
        return
    
    print(f"📁 Fundet {len(csv_files)} sæson filer")
    
    all_seasons_data = []
    
    for csv_file in csv_files:
        print(f"\n📊 ANALYSERER: {csv_file}")
        print("-" * 50)
        
        try:
            df = pd.read_csv(csv_file)
            season = csv_file.replace("herreliga_seasonal_elo_", "").replace(".csv", "").replace("_", "-")
            
            df_sorted = df.sort_values("final_rating", ascending=False).reset_index(drop=True)
            df_sorted["overall_rank"] = df_sorted.index + 1
            
            positions = df["primary_position"].unique()
            print(f"🏐 Positioner: {sorted(positions)}")
            print(f"📊 Total spillere: {len(df)}")
            
            position_results = []
            
            for position in sorted(positions):
                pos_players = df[df["primary_position"] == position].copy()
                
                if len(pos_players) == 0:
                    continue
                
                best_player = pos_players.loc[pos_players["final_rating"].idxmax()]
                overall_rank = df_sorted[df_sorted["player"] == best_player["player"]]["overall_rank"].iloc[0]
                
                pos_stats = {
                    "position": position,
                    "position_name": best_player.get("position_name", "Unknown"),
                    "count": len(pos_players),
                    "best_player": best_player["player"],
                    "best_rating": best_player["final_rating"],
                    "overall_rank": overall_rank,
                    "avg_rating": pos_players["final_rating"].mean(),
                    "season": season
                }
                
                position_results.append(pos_stats)
            
            print(f"\n🏆 BEDSTE SPILLERE PER POSITION - {season}:")
            
            sorted_positions = sorted(position_results, key=lambda x: x["overall_rank"])
            
            for pos_data in sorted_positions:
                if pos_data["overall_rank"] <= 10:
                    rank_status = "🥇"
                elif pos_data["overall_rank"] <= 30:
                    rank_status = "🥈"
                elif pos_data["overall_rank"] <= 50:
                    rank_status = "🥉"
                else:
                    rank_status = "📊"
                
                print(f"  {rank_status} {pos_data['position']} ({pos_data['position_name']:<12}): "
                      f"#{pos_data['overall_rank']:3d} - {pos_data['best_player']} "
                      f"({pos_data['best_rating']:.0f}) [{pos_data['count']:2d} spillere]")
            
            position_ranks = [p["overall_rank"] for p in position_results]
            
            if len(position_ranks) > 1:
                rank_spread = max(position_ranks) - min(position_ranks)
                rank_std = np.std(position_ranks)
                
                print(f"\n📊 BALANCE METRICS - {season}:")
                print(f"   🎯 Ranking spread: {rank_spread} positions")
                print(f"   📊 Ranking std dev: {rank_std:.1f}")
                
                if rank_spread <= 30:
                    balance_status = "✅ EXCELLENT"
                elif rank_spread <= 60:
                    balance_status = "✅ GOOD"
                elif rank_spread <= 100:
                    balance_status = "⚠️ NEEDS ATTENTION"
                else:
                    balance_status = "❌ POOR BALANCE"
                    
                print(f"   🏆 Balance status: {balance_status}")
            
            for pos_data in position_results:
                all_seasons_data.append(pos_data)
            
        except Exception as e:
            print(f"❌ Fejl i {csv_file}: {e}")
            continue
    
    if all_seasons_data:
        print(f"\n🌟 SAMLET ANALYSE PÅ TVÆRS AF ALLE SÆSONER")
        print("=" * 70)
        
        all_df = pd.DataFrame(all_seasons_data)
        
        position_summary = {}
        
        for position in all_df["position"].unique():
            pos_data = all_df[all_df["position"] == position]
            
            position_summary[position] = {
                "position_name": pos_data["position_name"].iloc[0],
                "seasons": len(pos_data),
                "avg_rank": pos_data["overall_rank"].mean(),
                "best_rank": pos_data["overall_rank"].min(),
                "worst_rank": pos_data["overall_rank"].max(),
                "avg_best_rating": pos_data["best_rating"].mean(),
                "total_players": pos_data["count"].sum(),
                "avg_players_per_season": pos_data["count"].mean()
            }
        
        print(f"📊 POSITION SUMMARY:")
        print()
        
        sorted_positions = sorted(position_summary.items(), key=lambda x: x[1]["avg_rank"])
        
        for position, data in sorted_positions:
            if data["avg_rank"] <= 20:
                rank_trend = "🔥"
            elif data["avg_rank"] <= 40:
                rank_trend = "⭐"
            elif data["avg_rank"] <= 60:
                rank_trend = "📊"
            else:
                rank_trend = "⚠️"
            
            print(f"  {rank_trend} {position} ({data['position_name']:<12}): "
                  f"Avg #{data['avg_rank']:4.1f} (#{data['best_rank']:2d}-#{data['worst_rank']:2d}) "
                  f"| Rating: {data['avg_best_rating']:4.0f} "
                  f"| {data['avg_players_per_season']:4.1f} spillere/sæson")
        
        avg_ranks = [data["avg_rank"] for data in position_summary.values()]
        overall_avg_rank = np.mean(avg_ranks)
        rank_variance = np.var(avg_ranks)
        
        print(f"\n🔍 POSITIONAL BIAS DETECTION:")
        print(f"📊 Gennemsnitlig position rank: {overall_avg_rank:.1f}")
        print(f"📊 Rank variance: {rank_variance:.1f}")
        
        biased_positions = []
        
        for position, data in position_summary.items():
            deviation = data["avg_rank"] - overall_avg_rank
            
            if abs(deviation) > 20:
                bias_type = "undervurderet" if deviation > 0 else "overvurderet"
                biased_positions.append({
                    "position": position,
                    "position_name": data["position_name"],
                    "bias_type": bias_type,
                    "deviation": deviation,
                    "avg_rank": data["avg_rank"]
                })
        
        if biased_positions:
            print(f"\n⚠️  FUNDET {len(biased_positions)} POSITIONER MED SYSTEMATISK BIAS:")
            
            for bias in sorted(biased_positions, key=lambda x: abs(x["deviation"]), reverse=True):
                bias_icon = "📉" if bias["bias_type"] == "undervurderet" else "📈"
                print(f"   {bias_icon} {bias['position']} ({bias['position_name']}): "
                      f"{bias['bias_type']} (avg #{bias['avg_rank']:.1f}, "
                      f"afvigelse: {bias['deviation']:+.1f})")
        else:
            print("✅ INGEN SYSTEMATISK POSITIONAL BIAS DETEKTERET!")
        
        print(f"\n💡 ANBEFALINGER:")
        print("-" * 50)
        
        if rank_variance > 400:
            print("❌ HØJ POSITIONAL VARIANCE - SYSTEMETISKE JUSTERINGER NØDVENDIGE")
            for bias in biased_positions:
                if bias["bias_type"] == "undervurderet":
                    print(f"   🔧 Øg action vægte for {bias['position']} ({bias['position_name']})")
                elif bias["bias_type"] == "overvurderet":
                    print(f"   🔧 Reducer action vægte for {bias['position']} ({bias['position_name']})")
        elif rank_variance > 200:
            print("⚠️ MODERAT POSITIONAL VARIANCE - MINDRE JUSTERINGER")
        else:
            print("✅ EXCELLENT POSITIONAL BALANCE!")
        
        season_df = pd.DataFrame(all_seasons_data)
        season_df.to_csv("positional_bias_analysis.csv", index=False)
        print(f"\n💾 Analyse gemt: positional_bias_analysis.csv")

if __name__ == "__main__":
    analyze_positional_bias() 