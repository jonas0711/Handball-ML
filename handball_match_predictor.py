#!/usr/bin/env python3
"""
HANDBALL MATCH PREDICTOR - FEATURE GENERATION & PREDICTION
===========================================================

Dette system genererer features for nye/kommende kampe og forudsiger resultater
med de trænede Ultimate Handball Models. Bruger SAMME feature generation 
logic som træningsdata for at sikre konsistens.

Funktioner:
1. Generate features for alle nye kampe (ikke trænet på)
2. Forudsig resultater for nye kampe
3. Tilføj nye kampe til systemet
4. Evaluer model performance på reelle test data

Forfatter: AI Assistant
Version: 1.0
"""

import pandas as pd
import numpy as np
import pickle
import os
import sqlite3
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

# Import fra existing system
from ml import HandballMLDatasetGenerator

class HandballMatchPredictor:
    """
    System til at forudsige håndboldkampe med trænede modeller
    Genererer features på samme måde som træningsdata
    """
    
    def __init__(self, league: str = "Herreliga"):
        """
        Initialiserer match predictor
        
        Args:
            league: "Herreliga" eller "Kvindeliga"
        """
        print(f"🏆 HANDBALL MATCH PREDICTOR - {league}")
        print("=" * 60)
        
        self.league = league
        self.base_dir = "."
        
        # Load trained model
        model_file = f"ultimate_handball_model_{league.lower()}.pkl"
        if os.path.exists(model_file):
            print(f"📂 Loading trained model: {model_file}")
            # Import class for loading
            from handball_ultimate_model import UltimateHandballPredictor as UltimateModel
            self.model = UltimateModel.load_model(model_file)
            print("✅ Model loaded successfully!")
        else:
            print(f"❌ Model file ikke fundet: {model_file}")
            self.model = None
        
        # Initialize feature generator (bruger SAMME system som training)
        print("🔧 Initializing feature generator...")
        self.feature_generator = HandballMLDatasetGenerator(
            base_dir=self.base_dir, 
            league=league
        )
        print("✅ Feature generator ready!")
        
        # Define test seasons (data ikke trænet på)
        self.test_seasons = ["2024-2025"]
        
        # Load existing ML dataset for comparison
        dataset_file = f"ML_Datasets/{league.lower()}_handball_ml_dataset.csv"
        if os.path.exists(dataset_file):
            print(f"📊 Loading existing dataset: {dataset_file}")
            self.existing_dataset = pd.read_csv(dataset_file)
            print(f"   Dataset shape: {self.existing_dataset.shape}")
            
            # CRITICAL: Ensure all feature columns are numeric
            feature_cols = [col for col in self.existing_dataset.columns 
                          if not col.startswith(('kamp_id', 'season', 'match_date', 'home_team', 'away_team', 'venue', 'league', 'target_'))]
            
            print(f"   🔧 Ensuring {len(feature_cols)} feature columns are numeric...")
            for col in feature_cols:
                if self.existing_dataset[col].dtype == 'object':
                    print(f"      Converting '{col}' from object to numeric")
                    self.existing_dataset[col] = pd.to_numeric(self.existing_dataset[col], errors='coerce').fillna(0.0)
            
            print(f"   ✅ All features ensured numeric")
        else:
            print(f"❌ Dataset file ikke fundet: {dataset_file}")
            self.existing_dataset = None
        
    def extract_test_data_features(self) -> pd.DataFrame:
        """
        Ekstraherer features for alle kampe i test sæsoner (2024-2025)
        som IKKE er blevet trænet på
        
        Returns:
            DataFrame med features for test kampe
        """
        print(f"\n🔍 EKSTRAHERER TEST DATA FEATURES")
        print("-" * 50)
        
        if self.existing_dataset is None:
            print("❌ Kan ikke ekstraktere test data - ingen existing dataset!")
            return pd.DataFrame()
        
        # Find kampe fra test sæsoner
        test_mask = self.existing_dataset['season'].isin(self.test_seasons)
        test_data = self.existing_dataset[test_mask].copy()
        
        print(f"📊 Test data kampe fundet: {len(test_data)}")
        print(f"📅 Test sæsoner: {self.test_seasons}")
        
        if len(test_data) == 0:
            print("⚠️  Ingen test data fundet!")
            return pd.DataFrame()
        
        # Vis test data statistikker
        print(f"\n📈 TEST DATA OVERSIGT:")
        print(f"   Total kampe: {len(test_data)}")
        print(f"   Hjemme sejr rate: {test_data['target_home_win'].mean():.1%}")
        print(f"   Dato range: {test_data['match_date'].min()} til {test_data['match_date'].max()}")
        
        # Vis hold fordeling
        teams = set(test_data['home_team'].tolist() + test_data['away_team'].tolist())
        print(f"   Involverede hold: {len(teams)} hold")
        
        return test_data
    
    def predict_test_matches(self) -> pd.DataFrame:
        """
        Forudsiger alle test kampe med den trænede model
        
        Returns:
            DataFrame med predictions og faktiske resultater
        """
        print(f"\n🎯 FORUDSIGER TEST KAMPE")
        print("-" * 40)
        
        # Get test data
        test_data = self.extract_test_data_features()
        if test_data.empty:
            print("❌ Ingen test data at forudsige!")
            return pd.DataFrame()
        
        if self.model is None:
            print("❌ Ingen trænet model tilgængelig!")
            return pd.DataFrame()
        
        # Prepare features for prediction
        metadata_cols = ['kamp_id', 'season', 'match_date', 'home_team', 'away_team', 'venue', 'league']
        target_cols = [col for col in test_data.columns if col.startswith('target_')]
        
        # CRITICAL: Model expects ALL original features for preprocessing, then selects 50
        # Use all features except metadata/targets for preprocessing
        all_feature_cols = [col for col in test_data.columns if col not in metadata_cols + target_cols]
        print(f"   🎯 Using all {len(all_feature_cols)} features for preprocessing")
        
        # Ensure all features are present and numeric
        X_test = test_data[all_feature_cols].copy()
        
        # Ensure correct data types for all features
        # CRITICAL: Handle categorical columns that were integers during training
        for col in X_test.columns:
            if X_test[col].dtype == 'object':
                X_test[col] = pd.to_numeric(X_test[col], errors='coerce').fillna(0.0)
            
            # Handle infinite values and convert ALL to float64
            # This ensures consistent data types for categorical encoders
            if np.isinf(X_test[col]).any():
                print(f"      Capping infinite values in '{col}'")
                X_test[col] = X_test[col].replace([np.inf, -np.inf], [1e6, -1e6])
            
            # Convert ALL columns to float64 for consistency
            X_test[col] = X_test[col].astype(np.float64)
        
        # CRITICAL FIX: Convert floats to integers for categorical encoding compatibility
        # The model's categorical encoders expect '0', '1', '2' not '0.0', '1.0', '2.0'
        print(f"   🔧 Converting float values to integers for categorical compatibility...")
        
        for col in X_test.columns:
            # Check if this column has a categorical encoder in the model
            if hasattr(self.model, 'preprocessing_components') and col in self.model.preprocessing_components.get('categorical_encoders', {}):
                # Convert float values to integers if they are whole numbers
                temp_col = X_test[col].copy()
                # Only convert if all non-null values are whole numbers
                if temp_col.dropna().apply(lambda x: x == int(x) if pd.notnull(x) and np.isfinite(x) else True).all():
                    X_test[col] = temp_col.astype('int64').astype('float64')
                    print(f"      Converted '{col}' to integer-float format")
        
        print(f"   📊 Features prepared for model: {X_test.shape}")
        print(f"   📊 Data types after preparation: {dict(X_test.dtypes.value_counts())}")
        print(f"   📊 Model will select {len(self.model.feature_names) if hasattr(self.model, 'feature_names') else 'unknown'} features internally")
        y_test = test_data['target_home_win']
        
        print(f"📊 Prediction features: {X_test.shape}")
        print(f"🎯 Making predictions...")
        
        try:
            # Make predictions with safe categorical encoding
            predictions, probabilities = self._safe_predict(X_test)
            
            # Create results dataframe
            results = test_data[metadata_cols + ['target_home_win']].copy()
            results['predicted_home_win'] = predictions
            results['home_win_probability'] = probabilities
            results['away_win_probability'] = 1 - probabilities
            results['correct_prediction'] = (predictions == y_test).astype(int)
            
            # Calculate performance metrics
            accuracy = (predictions == y_test).mean()
            
            print(f"\n📈 PREDICTION RESULTATER:")
            print(f"   Accuracy: {accuracy:.1%}")
            print(f"   Hjemme sejr predictions: {predictions.sum()}/{len(predictions)} ({predictions.mean():.1%})")
            print(f"   Actual hjemme sejre: {y_test.sum()}/{len(y_test)} ({y_test.mean():.1%})")
            
            # Show some example predictions
            print(f"\n🏆 FØRSTE 10 PREDICTIONS:")
            for i in range(min(10, len(results))):
                row = results.iloc[i]
                prob = row['home_win_probability']
                pred = "HJEMME" if row['predicted_home_win'] == 1 else "UDE"
                actual = "HJEMME" if row['target_home_win'] == 1 else "UDE"
                correct = "✅" if row['correct_prediction'] == 1 else "❌"
                
                print(f"   {row['match_date']}: {row['home_team']} vs {row['away_team']}")
                print(f"      Prediction: {pred} ({prob:.1%}) | Actual: {actual} {correct}")
            
            return results
            
        except Exception as e:
            print(f"❌ Fejl ved prediction: {str(e)}")
            return pd.DataFrame()
    
    def generate_features_for_new_matches(self, matches: List[Dict]) -> pd.DataFrame:
        """
        Genererer features for nye kampe der skal forudsiges
        
        Args:
            matches: List af match dictionaries med:
                - home_team: str
                - away_team: str  
                - match_date: str (YYYY-MM-DD)
                - venue: str (optional)
                - season: str (optional)
        
        Returns:
            DataFrame med features klar til prediction
        """
        print(f"\n🔧 GENERERER FEATURES FOR NYE KAMPE")
        print("-" * 50)
        
        if not matches:
            print("❌ Ingen kampe at generere features for!")
            return pd.DataFrame()
        
        print(f"📊 Antal kampe: {len(matches)}")
        
        # Validate matches
        validated_matches = []
        for i, match in enumerate(matches):
            try:
                # Parse match date
                if isinstance(match['match_date'], str):
                    match_date = datetime.strptime(match['match_date'], "%Y-%m-%d")
                else:
                    match_date = match['match_date']
                
                # Set defaults
                venue = match.get('venue', 'Unknown')
                season = match.get('season', '2024-2025')
                
                validated_match = {
                    'kamp_id': f'PRED_{i+1}_{match["home_team"]}_{match["away_team"]}',
                    'home_team': match['home_team'],
                    'away_team': match['away_team'],
                    'match_date': match_date,
                    'venue': venue,
                    'season': season,
                    'league': self.league
                }
                
                validated_matches.append(validated_match)
                print(f"   ✅ {match['home_team']} vs {match['away_team']} ({match_date.strftime('%Y-%m-%d')})")
                
            except Exception as e:
                print(f"   ❌ Fejl i match {i+1}: {str(e)}")
        
        if not validated_matches:
            print("❌ Ingen gyldige kampe!")
            return pd.DataFrame()
        
        # Generate features for each match
        print(f"\n🏗️  GENERERING AF FEATURES...")
        feature_rows = []
        
        for match in validated_matches:
            try:
                print(f"   Genererer features for: {match['home_team']} vs {match['away_team']}")
                
                # Generate samme features som træningsdata
                features = self._generate_match_features(match)
                feature_rows.append(features)
                
            except Exception as e:
                print(f"   ❌ Fejl ved feature generation: {str(e)}")
        
        if not feature_rows:
            print("❌ Ingen features genereret!")
            return pd.DataFrame()
        
        # Create DataFrame
        features_df = pd.DataFrame(feature_rows)
        print(f"\n✅ Features genereret: {features_df.shape}")
        print(f"   Kolonner: {features_df.shape[1]}")
        
        return features_df
    
    def _generate_match_features(self, match: Dict) -> Dict:
        """
        Genererer ALL features for en enkelt kamp
        Bruger SAMME logic som HandballMLDatasetGenerator
        
        Args:
            match: Match dictionary
            
        Returns:
            Dictionary med alle features
        """
        home_team = match['home_team']
        away_team = match['away_team']
        match_date = match['match_date']
        season = match['season']
        
        # Initialize features dictionary
        features = {
            # Metadata (samme som træningsdata)
            'kamp_id': match['kamp_id'],
            'season': season,
            'match_date': match_date.strftime('%Y-%m-%d'),
            'home_team': home_team,
            'away_team': away_team,
            'venue': match['venue'],
            'league': match['league'],
        }
        
        try:
            # 1. HOLD STATISTIKKER (historiske før kampen)
            print(f"      📊 Calculating team stats...")
            home_stats = self.feature_generator.calculate_team_historical_stats(home_team, match_date)
            away_stats = self.feature_generator.calculate_team_historical_stats(away_team, match_date)
            
            # Add prefix
            for key, value in home_stats.items():
                features[f'home_{key}'] = value
            for key, value in away_stats.items():
                features[f'away_{key}'] = value
        except Exception as e:
            print(f"        ⚠️  Team stats fejl: {str(e)}")
            # Add default stats
            default_stats = self.feature_generator._get_default_team_stats()
            for key, value in default_stats.items():
                features[f'home_{key}'] = value
                features[f'away_{key}'] = value
        
        try:
            # 2. SPILLER FEATURES
            print(f"      🏃 Calculating player features...")
            home_players = self.feature_generator.calculate_player_features(home_team, match_date)
            away_players = self.feature_generator.calculate_player_features(away_team, match_date)
            
            for key, value in home_players.items():
                features[f'home_players_{key}'] = value
            for key, value in away_players.items():
                features[f'away_players_{key}'] = value
        except Exception as e:
            print(f"        ⚠️  Player features fejl: {str(e)}")
            # Add default player features
            default_player_features = {
                'squad_size': 15, 'total_goals_by_players': 0, 'total_assists_by_players': 0,
                'total_saves_by_goalkeepers': 0, 'num_goalkeepers': 2, 'top_scorer_goals': 0,
                'top_assistant_assists': 0, 'top_goalkeeper_saves': 0, 'avg_goals_per_player': 0.0,
                'goals_concentration': 0.0
            }
            for key, value in default_player_features.items():
                features[f'home_players_{key}'] = value
                features[f'away_players_{key}'] = value
        
        try:
            # 3. POSITIONSSPECIFIKKE FEATURES  
            print(f"      🎯 Calculating positional features...")
            home_positions = self.feature_generator.calculate_positional_features(home_team, match_date)
            away_positions = self.feature_generator.calculate_positional_features(away_team, match_date)
            
            for key, value in home_positions.items():
                features[f'home_{key}'] = value
            for key, value in away_positions.items():
                features[f'away_{key}'] = value
        except Exception as e:
            print(f"        ⚠️  Positional features fejl: {str(e)}")
            # Add default positional features
            positions = ['VF', 'HF', 'VB', 'PL', 'HB', 'ST', 'MV', 'Gbr', '1:e', '2:e']
            for team in ['home', 'away']:
                for pos in positions:
                    features[f'{team}_pos_{pos}_total_actions'] = 0
                    features[f'{team}_pos_{pos}_attempts'] = 0
                    features[f'{team}_pos_{pos}_goals'] = 0
                    features[f'{team}_pos_{pos}_assists'] = 0
                    features[f'{team}_pos_{pos}_goal_conversion'] = 0.0
                    features[f'{team}_pos_{pos}_goal_share'] = 0.0
                    features[f'{team}_pos_{pos}_attempt_share'] = 0.0
                    features[f'{team}_pos_{pos}_action_share'] = 0.0
        
        try:
            # 4. ELO FEATURES
            print(f"      ⭐ Calculating ELO features...")
            home_elo = self.feature_generator.calculate_squad_elo_features(home_team, match_date, season)
            away_elo = self.feature_generator.calculate_squad_elo_features(away_team, match_date, season)
            
            for key, value in home_elo.items():
                features[f'home_{key}'] = value
            for key, value in away_elo.items():
                features[f'away_{key}'] = value
        except Exception as e:
            print(f"        ⚠️  ELO features fejl: {str(e)}")
            # Add default ELO features
            default_elo = {
                'elo_squad_avg_rating': 1200, 'elo_squad_median_rating': 1200,
                'elo_squad_max_rating': 1200, 'elo_squad_min_rating': 1200,
                'elo_squad_std_rating': 50, 'elo_squad_experience_ratio': 0.5
            }
            for key, value in default_elo.items():
                features[f'home_{key}'] = value
                features[f'away_{key}'] = value
        
        try:
            # 5. ELO TRENDS
            print(f"      📈 Calculating ELO trends...")
            home_elo_trends = self.feature_generator.calculate_elo_trends(home_team, match_date, season)
            away_elo_trends = self.feature_generator.calculate_elo_trends(away_team, match_date, season)
            
            for key, value in home_elo_trends.items():
                features[f'home_{key}'] = value
            for key, value in away_elo_trends.items():
                features[f'away_{key}'] = value
        except Exception as e:
            print(f"        ⚠️  ELO trends fejl: {str(e)}")
            # Add default ELO trend features
            default_trends = {
                'elo_season_progression': 0.5, 'elo_recent_trend_5': 0.0,
                'elo_season_volatility': 50, 'elo_consistency_score': 0.5
            }
            for key, value in default_trends.items():
                features[f'home_{key}'] = value
                features[f'away_{key}'] = value
        
        try:
            # 6. HEAD-TO-HEAD FEATURES
            print(f"      🤝 Calculating head-to-head...")
            h2h_stats = self.feature_generator.calculate_head_to_head_stats(home_team, away_team, match_date)
            
            for key, value in h2h_stats.items():
                features[f'h2h_{key}'] = value
        except Exception as e:
            print(f"        ⚠️  H2H features fejl: {str(e)}")
            # Add default H2H features
            default_h2h = {
                'games_played': 0, 'team_a_wins': 0, 'team_b_wins': 0, 'draws': 0,
                'team_a_goals': 0, 'team_b_goals': 0, 'avg_total_goals': 25.0,
                'avg_goal_difference': 0.0, 'days_since_last_h2h': 365
            }
            for key, value in default_h2h.items():
                features[f'h2h_{key}'] = value
        
        try:
            # 6B. ELO MATCH CONTEXT FEATURES
            print(f"      🎯 Calculating ELO match context...")
            elo_context = self.feature_generator.get_match_context_elo_features(home_team, away_team, match_date, season)
            
            for key, value in elo_context.items():
                features[key] = value
        except Exception as e:
            print(f"        ⚠️  ELO context fejl: {str(e)}")
            # Add default ELO context features
            default_elo_context = {
                'elo_h2h_home_advantage': 0.0, 'elo_h2h_rating_consistency': 0.0,
                'elo_h2h_avg_quality': 1275.0, 'elo_h2h_competitiveness': 0.5,
                'elo_expected_goal_difference': 0.0, 'elo_blowout_probability': 0.0,
                'elo_close_match_probability': 0.0, 'elo_form_convergence': 0.0,
                'elo_momentum_clash': 0.0, 'elo_peak_vs_peak': 0.0,
                'elo_context_importance': 1.0, 'elo_upset_potential': 0.0,
                'elo_volatility_factor': 1.0
            }
            for key, value in default_elo_context.items():
                features[key] = value
        
        try:
            # 7. TEMPORAL FEATURES
            print(f"      ⏰ Calculating temporal features...")
            temporal = self.feature_generator.calculate_temporal_features(match_date, season)
            features.update(temporal)
        except Exception as e:
            print(f"        ⚠️  Temporal features fejl: {str(e)}")
            # Add default temporal features
            features.update({
                'day_of_week': match_date.weekday(),
                'month': match_date.month,
                'is_weekend': match_date.weekday() >= 5,
                'season_progress': 0.5,
                'days_from_season_start': 100
            })
        
        try:
            # 8. LIGA CONTEXT
            print(f"      🏆 Calculating league context...")
            home_context = self.feature_generator.calculate_league_context_features(home_team, match_date, season)
            away_context = self.feature_generator.calculate_league_context_features(away_team, match_date, season)
            
            for key, value in home_context.items():
                features[f'home_league_{key}'] = value
            for key, value in away_context.items():
                features[f'away_league_{key}'] = value
        except Exception as e:
            print(f"        ⚠️  League context fejl: {str(e)}")
            # Add default league features
            default_league = {
                'league_position': 7, 'total_teams_in_league': 14, 'points_before_match': 15,
                'goal_difference_before_match': 0, 'is_top_half': True, 'is_top_3': False,
                'is_bottom_3': False, 'position_percentile': 0.5
            }
            for key, value in default_league.items():
                features[f'home_league_{key}'] = value
                features[f'away_league_{key}'] = value
        
        # 9. CALCULATED DIFFERENTIALS (samme som træningsdata)
        print(f"      🧮 Calculating differentials...")
        try:
            # Basic differentials
            features['team_strength_diff'] = features.get('home_offensive_strength', 25) - features.get('away_defensive_strength', 10)
            features['defensive_diff'] = features.get('home_defensive_strength', 10) - features.get('away_offensive_strength', 25)
            features['form_diff'] = features.get('home_momentum', 0) - features.get('away_momentum', 0)
            
            # ELO differentials
            features['elo_team_rating_diff'] = features.get('home_elo_squad_avg_rating', 1200) - features.get('away_elo_squad_avg_rating', 1200)
            features['elo_experience_diff'] = features.get('home_elo_squad_experience_ratio', 0.5) - features.get('away_elo_squad_experience_ratio', 0.5)
            
            # Advanced metrics
            features['total_firepower'] = features.get('home_offensive_strength', 25) + features.get('away_offensive_strength', 25)
            features['home_advantage_strength'] = features.get('home_home_win_rate', 0.5) - features.get('away_away_win_rate', 0.3)
            
            # ELO prediction metrics (KRITISKE FEATURES)
            home_elo_rating = features.get('home_elo_squad_avg_rating', 1200)
            away_elo_rating = features.get('away_elo_squad_avg_rating', 1200)
            elo_home_win_prob = 1 / (1 + 10**((away_elo_rating - home_elo_rating)/400))
            features['elo_home_win_probability'] = elo_home_win_prob
            features['elo_away_win_probability'] = 1 - elo_home_win_prob
            features['elo_match_predictability'] = abs(elo_home_win_prob - 0.5) * 2
            
            # Advanced ELO metrics
            features['elo_match_quality'] = (home_elo_rating + away_elo_rating) / 2
            features['elo_combined_elite_talent'] = features.get('home_elo_squad_elite_count', 0) + features.get('away_elo_squad_elite_count', 0)
            features['elo_combined_experience'] = features.get('home_elo_squad_experienced_players', 0) + features.get('away_elo_squad_experienced_players', 0)
            
        except Exception as e:
            print(f"        ⚠️  Differentials fejl: {str(e)}")
            # Add default differentials
            features.update({
                'team_strength_diff': 0, 'defensive_diff': 0, 'form_diff': 0,
                'elo_team_rating_diff': 0, 'total_firepower': 50, 'home_advantage_strength': 0.2,
                'elo_home_win_probability': 0.5, 'elo_away_win_probability': 0.5,
                'elo_match_predictability': 0.0, 'elo_match_quality': 1200,
                'elo_combined_elite_talent': 0, 'elo_combined_experience': 0
            })
        
        print(f"      ✅ Features generated: {len(features)} features")
        return features
    
    def _safe_predict(self, X_test: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Safe prediction that manually handles preprocessing to avoid categorical encoding issues
        """
        X_processed = X_test.copy()
        
        # Step 1: Apply categorical encoding with safe fallbacks
        for col, encoder in self.model.preprocessing_components['categorical_encoders'].items():
            if col in X_processed.columns:
                try:
                    # Convert to string, but handle float->int conversion first
                    col_data = X_processed[col].copy()
                    
                    # Convert 0.0 -> 0, 1.0 -> 1, etc. for consistency
                    if col_data.dtype in ['float64', 'float32']:
                        if col_data.dropna().apply(lambda x: x == int(x) if pd.notnull(x) and np.isfinite(x) else True).all():
                            col_data = col_data.astype('int64')
                    
                    # Convert to string
                    col_strings = col_data.astype(str)
                    
                    # Try encoding with fallback for unseen labels
                    try:
                        X_processed[col] = encoder.transform(col_strings)
                    except ValueError as e:
                        if "unseen labels" in str(e):
                            # Map unseen values to known classes
                            known_classes = set(encoder.classes_)
                            default_class = encoder.classes_[0] if len(encoder.classes_) > 0 else '0'
                            safe_strings = col_strings.apply(lambda x: x if x in known_classes else default_class)
                            X_processed[col] = encoder.transform(safe_strings)
                        else:
                            raise e
                except Exception as e:
                    print(f"      ⚠️  Failed to encode '{col}': {e}")
                    X_processed[col] = 0
        
        # Step 2: Apply outlier bounds
        for col, (lower, upper) in self.model.preprocessing_components['outlier_bounds'].items():
            if col in X_processed.columns:
                X_processed[col] = X_processed[col].clip(lower=lower, upper=upper)
        
        # Step 3: Apply imputation  
        X_processed = pd.DataFrame(
            self.model.preprocessing_components['imputer'].transform(X_processed),
            columns=X_processed.columns,
            index=X_processed.index
        )
        
        # Step 4: Apply feature selection
        X_selected = self.model.feature_selector.transform(X_processed)
        
        # Step 5: Apply scaling
        X_scaled = self.model.scaler.transform(X_selected)
        
        # Step 6: Make predictions
        predictions = self.model.model.predict(X_scaled)
        probabilities = self.model.model.predict_proba(X_scaled)[:, 1]
        
        return predictions, probabilities

    def _handle_unseen_categorical_values(self, X_test: pd.DataFrame) -> pd.DataFrame:
        """
        Håndterer nye kategoriske værdier i test data
        """
        print("🔧 Håndterer nye kategoriske værdier...")
        
        X_test_processed = X_test.copy()
        
        # Konvertér ALLE kolonner til numerisk format
        for col in X_test_processed.columns:
            if X_test_processed[col].dtype == 'object' or X_test_processed[col].dtype.name == 'category':
                print(f"   🔧 Konverterer '{col}': {X_test_processed[col].unique()[:5]}...")
                
                try:
                    # Forsøg at konvertere til float først
                    X_test_processed[col] = pd.to_numeric(X_test_processed[col], errors='coerce')
                except:
                    pass
                
                # Hvis stadig ikke numerisk, lav ordinal encoding
                if X_test_processed[col].dtype == 'object' or X_test_processed[col].dtype.name == 'category':
                    unique_values = X_test_processed[col].dropna().unique()
                    value_map = {val: i for i, val in enumerate(unique_values)}
                    X_test_processed[col] = X_test_processed[col].map(value_map)
                
                # Fyld NaN med 0
                X_test_processed[col] = X_test_processed[col].fillna(0)
                
                # Sørg for at det er numerisk
                X_test_processed[col] = pd.to_numeric(X_test_processed[col], errors='coerce').fillna(0)
        
        # Double check - konvertér alle til float64
        for col in X_test_processed.columns:
            X_test_processed[col] = X_test_processed[col].astype('float64')
        
        print(f"   📊 Alle kolonner konverteret til numeriske: {X_test_processed.shape[1]} kolonner")
        print(f"   📊 Data types efter konvertering: {X_test_processed.dtypes.value_counts().to_dict()}")
        
        return X_test_processed
    
    def predict_single_match(self, home_team: str, away_team: str, match_date) -> Dict:
        """
        Forudsiger en enkelt kamp
        
        Args:
            home_team: Hjemmehold navn
            away_team: Udehold navn
            match_date: Dato for kampen
            
        Returns:
            Dict med prediction, probabilities og confidence
        """
        try:
            # Prepare match data
            if isinstance(match_date, str):
                match_date = datetime.strptime(match_date, "%Y-%m-%d")
            
            match = {
                'home_team': home_team,
                'away_team': away_team,
                'match_date': match_date.strftime("%Y-%m-%d"),
                'venue': 'Unknown',
                'season': '2024-2025'
            }
            
            # Predict using the predict_matches method
            predictions_df = self.predict_matches([match])
            
            if predictions_df.empty:
                return None
            
            # Extract result
            row = predictions_df.iloc[0]
            return {
                'prediction': row['predicted_home_win'],
                'probabilities': [row['away_win_probability'], row['home_win_probability']],
                'confidence': row['prediction_confidence'],
                'home_team': home_team,
                'away_team': away_team
            }
            
        except Exception as e:
            print(f"❌ Prediction error: {str(e)}")
            return None
    
    def predict_matches(self, matches: List[Dict]) -> pd.DataFrame:
        """
        Forudsiger resultater for nye kampe
        
        Args:
            matches: List af kampe at forudsige
            
        Returns:
            DataFrame med predictions
        """
        print(f"\n🎯 FORUDSIGER NYE KAMPE")
        print("-" * 40)
        
        # Generate features
        features_df = self.generate_features_for_new_matches(matches)
        if features_df.empty:
            print("❌ Ingen features at forudsige med!")
            return pd.DataFrame()
        
        if self.model is None:
            print("❌ Ingen trænet model tilgængelig!")
            return pd.DataFrame()
        
        # Prepare features for prediction
        metadata_cols = ['kamp_id', 'season', 'match_date', 'home_team', 'away_team', 'venue', 'league']
        feature_cols = [col for col in features_df.columns if col not in metadata_cols]
        
        X_pred = features_df[feature_cols]
        
        print(f"📊 Prediction features: {X_pred.shape}")
        
        try:
            # Make predictions
            predictions, probabilities = self.model.predict(X_pred)
            
            # Create results
            results = features_df[metadata_cols].copy()
            results['predicted_home_win'] = predictions
            results['home_win_probability'] = probabilities
            results['away_win_probability'] = 1 - probabilities
            
            # Add prediction confidence
            results['prediction_confidence'] = np.abs(probabilities - 0.5) * 2  # 0 = uncertain, 1 = very confident
            
            print(f"\n🏆 PREDICTION RESULTATER:")
            for i in range(len(results)):
                row = results.iloc[i]
                prob = row['home_win_probability']
                conf = row['prediction_confidence']
                pred = "HJEMME SEJR" if row['predicted_home_win'] == 1 else "UDE SEJR"
                
                print(f"   {row['match_date']}: {row['home_team']} vs {row['away_team']}")
                print(f"      Prediction: {pred} ({prob:.1%} confidence)")
                print(f"      Certainty: {conf:.1%}")
            
            return results
            
        except Exception as e:
            print(f"❌ Fejl ved prediction: {str(e)}")
            return pd.DataFrame()
    
    def add_match_to_database(self, match_result: Dict):
        """
        Tilføjer en afsluttet kamp til databasen for fremtidige predictions
        
        Args:
            match_result: Dictionary med kampresultat
        """
        print(f"\n📝 TILFØJER KAMP TIL DATABASE")
        print("-" * 40)
        
        # Dette ville kræve adgang til database struktur
        # For nu logger vi bare kampen
        print(f"📊 Kamp: {match_result.get('home_team')} vs {match_result.get('away_team')}")
        print(f"📅 Dato: {match_result.get('date')}")
        print(f"🎯 Resultat: {match_result.get('result')}")
        print("⚠️  Database update ikke implementeret endnu")
    
    def evaluate_model_on_test_data(self) -> Dict:
        """
        Evaluerer modellen på test data og returnerer detaljerede metrics
        
        Returns:
            Dictionary med performance metrics
        """
        print(f"\n📊 EVALUERER MODEL PÅ TEST DATA")
        print("-" * 50)
        
        results = self.predict_test_matches()
        if results.empty:
            print("❌ Ingen test resultater at evaluere!")
            return {}
        
        # Calculate detailed metrics
        accuracy = results['correct_prediction'].mean()
        
        # Precision/Recall for home wins
        home_predictions = results['predicted_home_win'] == 1
        home_actual = results['target_home_win'] == 1
        
        if home_predictions.sum() > 0:
            home_precision = (home_predictions & home_actual).sum() / home_predictions.sum()
        else:
            home_precision = 0.0
        
        if home_actual.sum() > 0:
            home_recall = (home_predictions & home_actual).sum() / home_actual.sum()
        else:
            home_recall = 0.0
        
        # Away wins
        away_predictions = results['predicted_home_win'] == 0
        away_actual = results['target_home_win'] == 0
        
        if away_predictions.sum() > 0:
            away_precision = (away_predictions & away_actual).sum() / away_predictions.sum()
        else:
            away_precision = 0.0
        
        if away_actual.sum() > 0:
            away_recall = (away_predictions & away_actual).sum() / away_actual.sum()
        else:
            away_recall = 0.0
        
        # Confidence analysis
        high_confidence_mask = results['prediction_confidence'] > 0.6
        if high_confidence_mask.sum() > 0:
            high_conf_accuracy = results[high_confidence_mask]['correct_prediction'].mean()
        else:
            high_conf_accuracy = 0.0
        
        metrics = {
            'total_matches': len(results),
            'overall_accuracy': accuracy,
            'home_precision': home_precision,
            'home_recall': home_recall,
            'away_precision': away_precision,
            'away_recall': away_recall,
            'high_confidence_matches': high_confidence_mask.sum(),
            'high_confidence_accuracy': high_conf_accuracy,
            'average_confidence': results['prediction_confidence'].mean()
        }
        
        print(f"\n📈 DETAILED PERFORMANCE METRICS:")
        print(f"   Total matches: {metrics['total_matches']}")
        print(f"   Overall accuracy: {metrics['overall_accuracy']:.1%}")
        print(f"   Home win precision: {metrics['home_precision']:.1%}")
        print(f"   Home win recall: {metrics['home_recall']:.1%}")
        print(f"   Away win precision: {metrics['away_precision']:.1%}")
        print(f"   Away win recall: {metrics['away_recall']:.1%}")
        print(f"   High confidence matches: {metrics['high_confidence_matches']} ({metrics['high_confidence_matches']/metrics['total_matches']:.1%})")
        print(f"   High confidence accuracy: {metrics['high_confidence_accuracy']:.1%}")
        print(f"   Average prediction confidence: {metrics['average_confidence']:.1%}")
        
        return metrics

def demo_prediction_system():
    """
    Demonstrerer prediction system med eksempel kampe
    """
    print("🎮 DEMO AF PREDICTION SYSTEM")
    print("=" * 60)
    
    # Test begge ligaer
    for league in ["Herreliga", "Kvindeliga"]:
        print(f"\n🏆 TESTING {league.upper()}")
        print("-" * 40)
        
        # Initialize predictor
        predictor = HandballMatchPredictor(league=league)
        
        # 1. Evaluate on test data (real matches not trained on)
        print(f"\n1️⃣  EVALUATING ON REAL TEST DATA...")
        test_metrics = predictor.evaluate_model_on_test_data()
        
        # 2. Example new matches
        if league == "Herreliga":
            example_matches = [
                {
                    'home_team': 'Aalborg Håndbold',
                    'away_team': 'GOG',
                    'match_date': '2025-01-15',
                    'venue': 'Aalborg',
                    'season': '2024-2025'
                },
                {
                    'home_team': 'Fredericia HK',  
                    'away_team': 'Skjern Håndbold',
                    'match_date': '2025-01-16',
                    'venue': 'Fredericia',
                    'season': '2024-2025'
                }
            ]
        else:
            example_matches = [
                {
                    'home_team': 'Team Esbjerg',
                    'away_team': 'Viborg HK',
                    'match_date': '2025-01-15',
                    'venue': 'Esbjerg',
                    'season': '2024-2025'
                }
            ]
        
        print(f"\n2️⃣  EXAMPLE NEW MATCH PREDICTIONS...")
        predictions = predictor.predict_matches(example_matches)
        
        if not predictions.empty:
            print("✅ Example predictions successful!")
        else:
            print("⚠️  Example predictions failed")

if __name__ == "__main__":
    # Run demo
    demo_prediction_system()