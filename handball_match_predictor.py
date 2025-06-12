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
            # KALD DEN KORREKTE PREDICT FUNKTION
            # Den centraliserede predict-funktion i UltimateHandballPredictor håndterer
            # selv al preprocessing og sikrer konsistens.
            predictions, probabilities = self.model.predict(X_test)
            
            # Create results dataframe
            results = test_data[metadata_cols + ['target_home_win']].copy()
            results['predicted_home_win'] = predictions
            results['home_win_probability'] = probabilities
            results['away_win_probability'] = 1 - probabilities
            results['confidence'] = abs(probabilities - 0.5) * 2
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
    
    def generate_features_for_new_match(self, match: Dict) -> Optional[pd.DataFrame]:
        """
        Genererer features for en enkelt ny kamp ved at bruge den centrale funktion i HandballMLDatasetGenerator.

        Args:
            match: Dictionary med kampinformation:
                - home_team (str)
                - away_team (str)
                - match_date (datetime)
                - season (str)

        Returns:
            En DataFrame med en enkelt række indeholdende de genererede features, klar til modellen.
            Returnerer None, hvis features ikke kunne genereres.
        """
        print(f"⚙️ Generating features for: {match['home_team']} vs {match['away_team']}")
        
        if not hasattr(self.feature_generator, 'generate_features_for_single_match'):
            print("❌ Kritisk fejl: `generate_features_for_single_match` findes ikke i feature generatoren.")
            print("   Sørg for, at du bruger den nyeste version af `ml.py`.")
            return None

        try:
            # Kald den nye, centrale funktion
            feature_dict = self.feature_generator.generate_features_for_single_match(match)

            if not feature_dict:
                print("⚠️  Kunne ikke generere features for kampen.")
                return None

            # Konverter feature dictionary til en DataFrame
            # Modellen forventer en DataFrame som input
            features_df = pd.DataFrame([feature_dict])
            
            # Drop ikke-feature kolonner som modellen ikke skal se direkte
            metadata_cols = ['kamp_id', 'season', 'match_date', 'home_team', 'away_team', 'venue', 'league']
            feature_cols = [col for col in features_df.columns if col not in metadata_cols]
            
            print(f"✅ Features genereret. Antal: {len(feature_cols)}")
            
            return features_df[feature_cols]

        except Exception as e:
            print(f"❌ En uventet fejl opstod under feature-generering: {e}")
            import traceback
            traceback.print_exc()
            return None

    def predict_single_match(self, home_team: str, away_team: str, match_date: datetime) -> Optional[Dict]:
        """
        Forudsiger en enkelt kamp ved EFFICIENT at generere features kun for denne kamp.
        Dette erstatter den tidligere, langsomme metode, der regenererede hele datasættet.

        Args:
            home_team (str): Hjemmeholdets navn.
            away_team (str): Udeholdets navn.
            match_date (datetime): Kampdato.

        Returns:
            Et dictionary med forudsigelsesresultater, eller None ved fejl.
        """
        # Formål: At forudsige en enkelt kamp hurtigt og effektivt.
        # Hvorfor: Den tidligere metode tog for lang tid. Denne nye metode bruger
        # `generate_features_for_single_match` til kun at beregne de nødvendige features.
        print(f"\n⚡️ EFFICIENT PREDICTION FOR: {home_team} vs {away_team} ⚡️")
        print("---------------------------------------------------------")

        # Tjek om modellen er loadet korrekt. Uden en model kan vi ikke forudsige.
        if self.model is None:
            print("❌ Ingen trænet model tilgængelig. Kan ikke fortsætte.")
            return None

        try:
            # Trin 1: Definer kampinformation.
            # Dette dictionary indeholder de nødvendige data for feature-generatoren.
            # Vi normaliserer holdnavne for at matche dem, der bruges i datasættet.
            print("⚙️  Trin 1: Klargør kampinformation...")
            match_info = {
                'home_team': self.feature_generator.normalize_team_name(home_team),
                'away_team': self.feature_generator.normalize_team_name(away_team),
                'match_date': match_date,
                'season': self.get_season_from_date(match_date)
            }
            print(f"   - Hjemmehold: {match_info['home_team']}")
            print(f"   - Udehold: {match_info['away_team']}")
            print(f"   - Sæson: {match_info['season']}")

            # Trin 2: Generer features specifikt for denne kamp.
            # Dette er den hurtige del. Vi kalder funktionen, der kun fokuserer på
            # de to involverede hold og deres historik.
            print("⚙️  Trin 2: Genererer features for den specifikke kamp...")
            features_df = self.generate_features_for_new_match(match_info)

            # Hvis der ikke kunne genereres features, afbrydes processen.
            if features_df is None or features_df.empty:
                print(f"❌ Kunne ikke generere features for kampen.")
                return None

            # Trin 3: Klargør data til modellen (er nu simplere)
            # Den nye `predict` metode i UltimateHandballPredictor håndterer selv
            # manglende kolonner og den fulde preprocessing-pipeline.
            # Vi sender derfor den genererede feature-DataFrame direkte.
            print("⚙️  Trin 3: Sender features til modellen...")
            X_new = features_df
            print(f"✅ Data klargjort med {len(X_new.columns)} features.")

            # Trin 4: Kør selve forudsigelsen.
            # Modellen tager de klargjorte features og returnerer en forudsigelse og sandsynligheder.
            print("🧠 Trin 4: Model forudsiger kamp...")
            predictions, probabilities = self.model.predict(X_new)

            # Opret et resultat-dictionary for nem adgang.
            prediction_result = {
                'prediction': predictions[0],
                'home_win_probability': probabilities[0],
                'away_win_probability': 1 - probabilities[0],
                'confidence': abs(probabilities[0] - 0.5) * 2
            }
            
            print("✅ Forudsigelse fuldført.")
            return prediction_result

        except Exception as e:
            # Fejlhåndtering, hvis noget går galt undervejs.
            print(f"❌ En uventet fejl opstod under den effektive forudsigelse: {e}")
            import traceback
            traceback.print_exc()
            return None

    def predict_matches(self, matches: List[Dict]) -> pd.DataFrame:
        """
        Forudsiger en liste af kampe ved at kalde predict_single_match for hver.
        
        Args:
            matches: En liste af dictionaries, hver med 'home_team', 'away_team', 'match_date'.
            
        Returns:
            En DataFrame med forudsigelserne.
        """
        print(f"\n🔮 Forudsiger {len(matches)} nye kampe...")
        
        results = []
        for match in matches:
            home_team = match.get('home_team')
            away_team = match.get('away_team')
            match_date = match.get('match_date')

            if not all([home_team, away_team, match_date]):
                print(f"⚠️  Skipping invalid match data: {match}")
                continue

            prediction = self.predict_single_match(home_team, away_team, match_date)
            
            result_row = {
                'home_team': home_team,
                'away_team': away_team,
                'match_date': match_date.strftime('%Y-%m-%d'),
            }

            if prediction:
                result_row['predicted_winner'] = 'Home' if prediction['prediction'] == 1 else 'Away'
                result_row['home_win_probability'] = prediction['home_win_probability']
                result_row['confidence'] = prediction['confidence']
            else:
                result_row['predicted_winner'] = 'Error'
                result_row['home_win_probability'] = -1.0
                result_row['confidence'] = -1.0
            
            results.append(result_row)
        
        print("✅ Alle kampe er blevet behandlet.")
        return pd.DataFrame(results)
    
    def get_season_from_date(self, match_date: datetime) -> str:
        """
        Bestemmer sæsonen (f.eks. "2023-2024") ud fra en given dato.
        Antager at sæsonen skifter omkring juli.
        """
        year = match_date.year
        month = match_date.month
        if month >= 7:
            return f"{year}-{year + 1}"
        else:
            return f"{year - 1}-{year}"
    
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
        high_confidence_mask = results['confidence'] > 0.6
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
            'average_confidence': results['confidence'].mean()
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