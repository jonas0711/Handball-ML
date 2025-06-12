#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HANDBALL PREDICTIONS API BACKEND
================================

Dette script opretter en Flask API til at servere håndboldmodelforudsigelser
for frontend UI'en. Den håndterer både Herreliga og Kvindeliga predictions.

Funktioner:
1. Serverer alle test-kampe med predictions
2. Returnerer detaljerede modelinformationer
3. Håndterer CORS for frontend integration
4. Leverer strukturerede JSON responses

Forfatter: AI Assistant
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import pandas as pd
import numpy as np
from datetime import datetime
import traceback
import warnings
warnings.filterwarnings('ignore')

# Import fra existing system
from handball_match_predictor import HandballMatchPredictor

# Opretter Flask applikation med CORS support for frontend
app = Flask(__name__)
CORS(app)  # Tillader requests fra alle domæner (nødvendigt for Next.js udvikling)

# Global variabler til at cache model predictions for performance
predictions_cache = {}
last_update = {}

print("🚀 STARTING HANDBALL PREDICTIONS API SERVER")
print("=" * 60)

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint til at verificere at API'en kører korrekt
    
    Returns:
        JSON response med server status
    """
    print("🔍 Health check endpoint called")
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "message": "Handball Predictions API is running"
    })

@app.route('/api/predictions/<league>', methods=['GET'])
def get_predictions(league):
    """
    Henter alle modelforudsigelser for en specifik liga
    
    Args:
        league (str): "herreliga" eller "kvindeliga"
        
    Returns:
        JSON response med alle predictions og metadata
    """
    print(f"📊 Predictions requested for league: {league}")
    
    try:
        # Normalize league name (case insensitive)
        league_normalized = league.lower()
        if league_normalized == "herreliga":
            league_proper = "Herreliga"
        elif league_normalized == "kvindeliga":
            league_proper = "Kvindeliga"
        else:
            print(f"❌ Invalid league: {league}")
            return jsonify({"error": f"Invalid league: {league}. Use 'herreliga' or 'kvindeliga'"}), 400
        
        # Check cache for performance (cache predictions for 5 minutes)
        cache_key = league_proper
        current_time = datetime.now()
        
        if (cache_key in predictions_cache and 
            cache_key in last_update and 
            (current_time - last_update[cache_key]).seconds < 300):  # 5 minutes cache
            print(f"✅ Returning cached predictions for {league_proper}")
            return jsonify(predictions_cache[cache_key])
        
        print(f"🔄 Generating fresh predictions for {league_proper}")
        
        # Initialize predictor for this league
        predictor = HandballMatchPredictor(league=league_proper)
        
        # Get all test predictions
        results_df = predictor.predict_test_matches()
        
        if results_df is None or results_df.empty:
            print(f"⚠️ No test data found for {league_proper}")
            return jsonify({
                "league": league_proper,
                "total_matches": 0,
                "predictions": [],
                "summary": {
                    "error": f"No test data available for {league_proper}"
                }
            })
        
        # Convert DataFrame to JSON-serializable format
        predictions_list = []
        for index, row in results_df.iterrows():
            # Create prediction object with all relevant information
            prediction = {
                "id": int(index),
                "match_date": str(row['match_date']),
                "home_team": str(row['home_team']),
                "away_team": str(row['away_team']),
                "season": str(row['season']),
                "venue": str(row.get('venue', 'Unknown')),
                "predicted_home_win": bool(row['predicted_home_win']),
                "actual_home_win": bool(row['target_home_win']),
                "home_win_probability": float(row['home_win_probability']),
                "away_win_probability": float(row['away_win_probability']),
                "confidence": float(row['confidence']),
                "correct_prediction": bool(row['correct_prediction']),
                "predicted_winner": str(row['home_team']) if row['predicted_home_win'] else str(row['away_team']),
                "actual_winner": str(row['home_team']) if row['target_home_win'] else str(row['away_team']),
                "prediction_accuracy": "correct" if row['correct_prediction'] else "incorrect"
            }
            predictions_list.append(prediction)
        
        # Calculate summary statistics
        total_matches = len(results_df)
        correct_predictions = results_df['correct_prediction'].sum()
        accuracy = correct_predictions / total_matches if total_matches > 0 else 0
        
        # Home win statistics
        predicted_home_wins = results_df['predicted_home_win'].sum()
        actual_home_wins = results_df['target_home_win'].sum()
        
        # Confidence analysis
        high_confidence_mask = results_df['confidence'] > 0.3  # More than 80% probability for one side
        high_confidence_matches = results_df[high_confidence_mask]
        high_confidence_accuracy = high_confidence_matches['correct_prediction'].mean() if len(high_confidence_matches) > 0 else 0
        
        summary = {
            "total_matches": int(total_matches),
            "correct_predictions": int(correct_predictions),
            "accuracy": float(accuracy),
            "accuracy_percentage": f"{accuracy:.1%}",
            "predicted_home_wins": int(predicted_home_wins),
            "actual_home_wins": int(actual_home_wins),
            "predicted_home_win_rate": float(predicted_home_wins / total_matches) if total_matches > 0 else 0,
            "actual_home_win_rate": float(actual_home_wins / total_matches) if total_matches > 0 else 0,
            "high_confidence_matches": int(len(high_confidence_matches)),
            "high_confidence_accuracy": float(high_confidence_accuracy),
            "average_confidence": float(results_df['confidence'].mean()),
            "date_range": {
                "start": str(results_df['match_date'].min()),
                "end": str(results_df['match_date'].max())
            }
        }
        
        # Prepare response
        response_data = {
            "league": league_proper,
            "total_matches": total_matches,
            "predictions": predictions_list,
            "summary": summary,
            "last_updated": current_time.isoformat()
        }
        
        # Cache the response
        predictions_cache[cache_key] = response_data
        last_update[cache_key] = current_time
        
        print(f"✅ Successfully generated predictions for {league_proper}")
        print(f"   Total matches: {total_matches}")
        print(f"   Accuracy: {accuracy:.1%}")
        
        return jsonify(response_data)
        
    except Exception as e:
        error_msg = f"Error generating predictions for {league}: {str(e)}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        return jsonify({"error": error_msg}), 500

@app.route('/api/predictions', methods=['GET'])
def get_all_predictions():
    """
    Henter predictions for begge ligaer kombineret
    
    Returns:
        JSON response med predictions for både Herreliga og Kvindeliga
    """
    print("📊 All predictions requested")
    
    try:
        # Get predictions for both leagues
        herreliga_response = get_predictions("herreliga")
        kvindeliga_response = get_predictions("kvindeliga")
        
        # Extract data from responses
        herreliga_data = herreliga_response.get_json() if hasattr(herreliga_response, 'get_json') else herreliga_response
        kvindeliga_data = kvindeliga_response.get_json() if hasattr(kvindeliga_response, 'get_json') else kvindeliga_response
        
        # Combine data
        combined_response = {
            "herreliga": herreliga_data,
            "kvindeliga": kvindeliga_data,
            "combined_summary": {
                "total_matches": herreliga_data.get("total_matches", 0) + kvindeliga_data.get("total_matches", 0),
                "herreliga_accuracy": herreliga_data.get("summary", {}).get("accuracy", 0),
                "kvindeliga_accuracy": kvindeliga_data.get("summary", {}).get("accuracy", 0),
                "last_updated": datetime.now().isoformat()
            }
        }
        
        print("✅ Successfully combined predictions for both leagues")
        return jsonify(combined_response)
        
    except Exception as e:
        error_msg = f"Error generating combined predictions: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

@app.route('/api/team-performance/<league>', methods=['GET'])
def get_team_performance(league):
    """
    Analyserer modelperformance for individuelle hold
    
    Args:
        league (str): "herreliga" eller "kvindeliga"
        
    Returns:
        JSON response med team-specific performance metrics
    """
    print(f"🏆 Team performance analysis requested for: {league}")
    
    try:
        # Get predictions first
        response = get_predictions(league)
        data = response.get_json() if hasattr(response, 'get_json') else response
        
        if "error" in data:
            return jsonify(data), 500
        
        predictions = data["predictions"]
        
        # Analyze performance per team
        team_stats = {}
        
        for pred in predictions:
            home_team = pred["home_team"]
            away_team = pred["away_team"]
            correct = pred["correct_prediction"]
            
            # Initialize team stats if not exists
            for team in [home_team, away_team]:
                if team not in team_stats:
                    team_stats[team] = {
                        "team_name": team,
                        "total_matches": 0,
                        "correct_predictions": 0,
                        "accuracy": 0.0,
                        "home_matches": 0,
                        "away_matches": 0,
                        "home_correct": 0,
                        "away_correct": 0
                    }
            
            # Update stats for home team
            team_stats[home_team]["total_matches"] += 1
            team_stats[home_team]["home_matches"] += 1
            if correct:
                team_stats[home_team]["correct_predictions"] += 1
                team_stats[home_team]["home_correct"] += 1
            
            # Update stats for away team
            team_stats[away_team]["total_matches"] += 1
            team_stats[away_team]["away_matches"] += 1
            if correct:
                team_stats[away_team]["correct_predictions"] += 1
                team_stats[away_team]["away_correct"] += 1
        
        # Calculate accuracy for each team
        team_performance = []
        for team, stats in team_stats.items():
            if stats["total_matches"] > 0:
                stats["accuracy"] = stats["correct_predictions"] / stats["total_matches"]
                stats["home_accuracy"] = stats["home_correct"] / stats["home_matches"] if stats["home_matches"] > 0 else 0
                stats["away_accuracy"] = stats["away_correct"] / stats["away_matches"] if stats["away_matches"] > 0 else 0
            team_performance.append(stats)
        
        # Sort by accuracy
        team_performance.sort(key=lambda x: x["accuracy"], reverse=True)
        
        response_data = {
            "league": league,
            "team_performance": team_performance,
            "summary": {
                "total_teams": len(team_performance),
                "best_predicted_team": team_performance[0]["team_name"] if team_performance else None,
                "worst_predicted_team": team_performance[-1]["team_name"] if team_performance else None,
                "average_accuracy": sum(t["accuracy"] for t in team_performance) / len(team_performance) if team_performance else 0
            }
        }
        
        print(f"✅ Team performance analysis completed for {league}")
        return jsonify(response_data)
        
    except Exception as e:
        error_msg = f"Error analyzing team performance for {league}: {str(e)}"
        print(f"❌ {error_msg}")
        return jsonify({"error": error_msg}), 500

if __name__ == '__main__':
    """
    Starter Flask development server
    """
    print("🌐 Starting Flask development server...")
    print("📡 API endpoints available:")
    print("   - GET /api/health")
    print("   - GET /api/predictions/<league>")
    print("   - GET /api/predictions")
    print("   - GET /api/team-performance/<league>")
    print("")
    print("🔗 Access at: http://localhost:5000")
    print("=" * 60)
    
    # Start server in debug mode for development
    app.run(host='localhost', port=5000, debug=True) 