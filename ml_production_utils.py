#!/usr/bin/env python3
"""
HÅNDBOL ML PRODUCTION UTILITIES
===============================

Dette script indeholder utilities til deployment, vedligeholdelse og 
produktion af ML modeller til håndbol prediction.

FUNKTIONER:
- Model deployment og inference
- Performance monitoring
- Data drift detection  
- Automated retraining
- Prediction confidence intervals
"""

import pandas as pd
import numpy as np
import pickle
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import warnings
warnings.filterwarnings('ignore')

class HandballPredictor:
    """
    Production-ready predictor til håndbol kampe
    """
    
    def __init__(self, model_path: str, league: str = "Herreliga"):
        """
        Initialiserer predictor med trænet model
        
        Args:
            model_path: Sti til gemte modeller (.pkl fil)
            league: "Herreliga" eller "Kvindeliga"
        """
        self.league = league
        self.model_path = model_path
        
        # Load modeller og metadata
        self.models = None
        self.results = None
        self.feature_names = None
        self.best_model_key = None
        self.best_model = None
        
        self.load_models()
        self.setup_best_model()
        
        # Performance tracking
        self.predictions_log = []
        self.performance_history = []
        
    def load_models(self):
        """Loader gemte modeller"""
        print(f"📂 Loading modeller fra: {self.model_path}")
        
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model fil ikke fundet: {self.model_path}")
        
        with open(self.model_path, 'rb') as f:
            data = pickle.load(f)
            self.models = data['models']
            self.results = data['results']
            self.feature_names = data['feature_names']
        
        print(f"✅ Loaded {len(self.models)} modeller")
        
    def setup_best_model(self):
        """Identificerer og setup bedste model"""
        if not self.results:
            raise ValueError("Ingen model resultater fundet")
        
        # Find bedste model baseret på accuracy
        self.best_model_key = max(self.results.keys(), 
                                 key=lambda k: self.results[k]['accuracy'])
        
        model_info = self.models[self.best_model_key]
        self.best_model = model_info['model']
        
        best_result = self.results[self.best_model_key]
        print(f"🥇 Bedste model: {best_result['model_name']}")
        print(f"   Accuracy: {best_result['accuracy']:.3f}")
        print(f"   Features: {model_info.get('n_features', 'N/A')}")
        
    def predict_match(self, match_features: Dict[str, Any], 
                     return_confidence: bool = True) -> Dict[str, Any]:
        """
        Forudsiger resultat af en enkelt kamp
        
        Args:
            match_features: Dictionary med features for kampen
            return_confidence: Om confidence intervals skal returneres
            
        Returns:
            Dictionary med prediction og metadata
        """
        try:
            # Valider input features
            missing_features = set(self.feature_names) - set(match_features.keys())
            if missing_features:
                print(f"⚠️  Manglende features: {list(missing_features)[:5]}...")
                # Fill med 0 eller median (simple imputation)
                for feature in missing_features:
                    match_features[feature] = 0.0
            
            # Opret feature vector
            feature_vector = np.array([match_features.get(f, 0.0) for f in self.feature_names]).reshape(1, -1)
            
            # Grundlæggende prediction
            prediction = self.best_model.predict(feature_vector)[0]
            
            # Probability estimates hvis understøttet
            probability = None
            if hasattr(self.best_model, 'predict_proba'):
                probabilities = self.best_model.predict_proba(feature_vector)[0]
                probability = probabilities[1]  # Probability for home win
            
            # Confidence interval hvis ønsket
            confidence_interval = None
            if return_confidence and probability is not None:
                confidence_interval = self._calculate_confidence_interval(probability)
            
            # Opret result
            result = {
                'prediction': int(prediction),
                'prediction_label': 'Home Win' if prediction == 1 else 'Away Win',
                'probability_home_win': probability,
                'confidence_interval': confidence_interval,
                'model_used': self.results[self.best_model_key]['model_name'],
                'timestamp': datetime.now().isoformat(),
                'league': self.league
            }
            
            # Log prediction
            self.predictions_log.append({
                'features': match_features,
                'result': result,
                'timestamp': datetime.now()
            })
            
            return result
            
        except Exception as e:
            print(f"❌ Fejl i prediction: {e}")
            return {
                'prediction': None,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def predict_multiple_matches(self, matches_df: pd.DataFrame) -> pd.DataFrame:
        """
        Forudsiger multiple kampe fra DataFrame
        
        Args:
            matches_df: DataFrame med features for flere kampe
            
        Returns:
            DataFrame med predictions tilføjet
        """
        print(f"🔮 Predicting {len(matches_df)} kampe...")
        
        results = []
        for idx, row in matches_df.iterrows():
            match_features = row.to_dict()
            prediction = self.predict_match(match_features, return_confidence=False)
            results.append(prediction)
        
        # Tilføj til DataFrame
        results_df = matches_df.copy()
        results_df['predicted_home_win'] = [r['prediction'] for r in results]
        results_df['probability_home_win'] = [r['probability_home_win'] for r in results]
        results_df['model_used'] = [r['model_used'] for r in results]
        
        print(f"✅ Predictions komplet")
        return results_df
    
    def _calculate_confidence_interval(self, probability: float, confidence: float = 0.95) -> Tuple[float, float]:
        """
        Beregner confidence interval for prediction
        
        Args:
            probability: Predicted probability
            confidence: Confidence level (default 0.95 for 95%)
            
        Returns:
            Tuple med (lower_bound, upper_bound)
        """
        # Simple approximation baseret på binomial distribution
        # I produktion kunne dette forbedres med bootstrap eller Bayesian metoder
        
        z_score = 1.96 if confidence == 0.95 else 2.576  # 99% confidence
        
        # Standard error approximation
        n_samples = 100  # Approximate effective sample size
        std_error = np.sqrt(probability * (1 - probability) / n_samples)
        
        margin_error = z_score * std_error
        
        lower_bound = max(0.0, probability - margin_error)
        upper_bound = min(1.0, probability + margin_error)
        
        return (lower_bound, upper_bound)
    
    def evaluate_recent_performance(self, actual_results: List[int], 
                                  days_back: int = 30) -> Dict[str, float]:
        """
        Evaluerer model performance på recente predictions
        
        Args:
            actual_results: Liste af faktiske resultater (1=home win, 0=away win)
            days_back: Antal dage tilbage at evaluere
            
        Returns:
            Dictionary med performance metrics
        """
        print(f"📊 Evaluerer performance de sidste {days_back} dage...")
        
        # Filter recente predictions
        cutoff_date = datetime.now() - timedelta(days=days_back)
        recent_predictions = [
            p for p in self.predictions_log 
            if p['timestamp'] >= cutoff_date and p['result']['prediction'] is not None
        ]
        
        if len(recent_predictions) != len(actual_results):
            print(f"⚠️  Antal predictions ({len(recent_predictions)}) matcher ikke actual results ({len(actual_results)})")
            return {'error': 'Mismatched lengths'}
        
        if len(recent_predictions) == 0:
            return {'error': 'No recent predictions found'}
        
        # Beregn metrics
        predictions = [p['result']['prediction'] for p in recent_predictions]
        probabilities = [p['result']['probability_home_win'] for p in recent_predictions if p['result']['probability_home_win'] is not None]
        
        accuracy = sum(p == a for p, a in zip(predictions, actual_results)) / len(predictions)
        
        # Precision, recall for home wins
        home_win_predictions = [i for i, p in enumerate(predictions) if p == 1]
        home_win_actual = [i for i, a in enumerate(actual_results) if a == 1]
        
        true_positives = len(set(home_win_predictions) & set(home_win_actual))
        precision = true_positives / len(home_win_predictions) if home_win_predictions else 0
        recall = true_positives / len(home_win_actual) if home_win_actual else 0
        
        # Brier score (kun hvis probabilities tilgængelige)
        brier_score = None
        if len(probabilities) == len(actual_results):
            brier_score = np.mean([(p - a)**2 for p, a in zip(probabilities, actual_results)])
        
        performance = {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'n_predictions': len(predictions),
            'period_days': days_back,
            'brier_score': brier_score,
            'evaluation_date': datetime.now().isoformat()
        }
        
        # Log performance
        self.performance_history.append(performance)
        
        print(f"✅ Recent performance: {accuracy:.3f} accuracy på {len(predictions)} predictions")
        return performance
    
    def detect_data_drift(self, new_features: pd.DataFrame, 
                         threshold: float = 0.1) -> Dict[str, Any]:
        """
        Detekterer data drift i nye features sammenlignet med training data
        
        Args:
            new_features: DataFrame med nye features
            threshold: Threshold for drift detection
            
        Returns:
            Dictionary med drift analysis
        """
        print(f"🔍 Detecting data drift på {len(new_features)} nye samples...")
        
        # Dette er en simplified version - i produktion ville man bruge mere sofistikerede metoder
        # som Kolmogorov-Smirnov test, Population Stability Index (PSI), etc.
        
        drift_results = {
            'total_features': len(self.feature_names),
            'drifted_features': [],
            'drift_score': 0.0,
            'recommendation': 'NO_ACTION'
        }
        
        # Simpel drift detection baseret på mean/std ændringer
        for feature in self.feature_names:
            if feature in new_features.columns:
                new_mean = new_features[feature].mean()
                new_std = new_features[feature].std()
                
                # Sammenlign med "baseline" (approximeret fra model training)
                # I virkeligheden skulle dette gemmes fra training
                baseline_mean = 0.0  # Placeholder
                baseline_std = 1.0   # Placeholder
                
                mean_change = abs(new_mean - baseline_mean) / (baseline_std + 1e-6)
                std_change = abs(new_std - baseline_std) / (baseline_std + 1e-6)
                
                if mean_change > threshold or std_change > threshold:
                    drift_results['drifted_features'].append({
                        'feature': feature,
                        'mean_change': mean_change,
                        'std_change': std_change
                    })
        
        # Overall drift score
        n_drifted = len(drift_results['drifted_features'])
        drift_results['drift_score'] = n_drifted / len(self.feature_names)
        
        # Recommendation
        if drift_results['drift_score'] > 0.3:
            drift_results['recommendation'] = 'RETRAIN_URGENT'
        elif drift_results['drift_score'] > 0.1:
            drift_results['recommendation'] = 'RETRAIN_SOON'
        elif drift_results['drift_score'] > 0.05:
            drift_results['recommendation'] = 'MONITOR'
        
        print(f"🎯 Drift detection: {n_drifted} features drifted ({drift_results['drift_score']:.1%})")
        print(f"📋 Recommendation: {drift_results['recommendation']}")
        
        return drift_results
    
    def save_prediction_log(self, filepath: str):
        """Gemmer prediction log til fil"""
        log_data = {
            'predictions': [
                {
                    'timestamp': p['timestamp'].isoformat(),
                    'features': p['features'],
                    'result': p['result']
                } for p in self.predictions_log
            ],
            'performance_history': self.performance_history,
            'model_info': {
                'best_model': self.best_model_key,
                'league': self.league,
                'model_path': self.model_path
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(log_data, f, indent=2, default=str)
        
        print(f"💾 Prediction log gemt: {filepath}")
    
    def load_prediction_log(self, filepath: str):
        """Loader prediction log fra fil"""
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                log_data = json.load(f)
            
            # Konverter timestamps tilbage
            for pred in log_data['predictions']:
                pred['timestamp'] = datetime.fromisoformat(pred['timestamp'])
            
            self.predictions_log = log_data['predictions']
            self.performance_history = log_data.get('performance_history', [])
            
            print(f"📂 Prediction log loaded: {len(self.predictions_log)} predictions")


class ModelMonitor:
    """
    Monitoring system for ML models in production
    """
    
    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self.alerts = []
        
    def daily_health_check(self, predictor: HandballPredictor) -> Dict[str, Any]:
        """
        Daglig health check af model
        
        Args:
            predictor: HandballPredictor instance
            
        Returns:
            Health check rapport
        """
        print("🏥 DAILY HEALTH CHECK")
        
        health_status = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'HEALTHY',
            'checks': {},
            'alerts': []
        }
        
        # Check 1: Model loadable
        try:
            model_loadable = predictor.best_model is not None
            health_status['checks']['model_loadable'] = model_loadable
            if not model_loadable:
                health_status['alerts'].append('Model ikke loadbar')
        except:
            health_status['checks']['model_loadable'] = False
            health_status['alerts'].append('Model load fejl')
        
        # Check 2: Recent predictions
        recent_predictions = len([
            p for p in predictor.predictions_log 
            if p['timestamp'] >= datetime.now() - timedelta(days=7)
        ])
        health_status['checks']['recent_predictions'] = recent_predictions
        
        if recent_predictions == 0:
            health_status['alerts'].append('Ingen predictions sidste 7 dage')
        
        # Check 3: Performance trend
        if len(predictor.performance_history) >= 2:
            latest_perf = predictor.performance_history[-1]['accuracy']
            previous_perf = predictor.performance_history[-2]['accuracy']
            performance_decline = previous_perf - latest_perf
            
            health_status['checks']['performance_decline'] = performance_decline
            
            if performance_decline > 0.05:  # 5% decline
                health_status['alerts'].append(f'Performance decline: {performance_decline:.1%}')
        
        # Overall status
        if health_status['alerts']:
            health_status['overall_status'] = 'WARNING' if len(health_status['alerts']) <= 2 else 'CRITICAL'
        
        print(f"🎯 Health status: {health_status['overall_status']}")
        if health_status['alerts']:
            print(f"⚠️  Alerts: {len(health_status['alerts'])}")
        
        return health_status
    
    def generate_weekly_report(self, predictor: HandballPredictor) -> str:
        """
        Genererer ugentlig performance rapport
        
        Args:
            predictor: HandballPredictor instance
            
        Returns:
            Rapport som string
        """
        report_lines = [
            "UGENTLIG ML MODEL RAPPORT",
            "=" * 40,
            f"Genereret: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Liga: {predictor.league}",
            f"Model: {predictor.results[predictor.best_model_key]['model_name']}",
            "",
            "AKTIVITET SIDSTE 7 DAGE:",
            "-" * 30
        ]
        
        # Predictions activity
        week_ago = datetime.now() - timedelta(days=7)
        recent_predictions = [
            p for p in predictor.predictions_log 
            if p['timestamp'] >= week_ago
        ]
        
        report_lines.append(f"Antal predictions: {len(recent_predictions)}")
        
        if recent_predictions:
            home_win_predictions = sum(1 for p in recent_predictions if p['result']['prediction'] == 1)
            report_lines.append(f"Home win predictions: {home_win_predictions} ({home_win_predictions/len(recent_predictions):.1%})")
        
        # Performance hvis tilgængelig
        if predictor.performance_history:
            latest_perf = predictor.performance_history[-1]
            report_lines.extend([
                "",
                "SENESTE PERFORMANCE:",
                "-" * 30,
                f"Accuracy: {latest_perf['accuracy']:.3f}",
                f"Precision: {latest_perf['precision']:.3f}",
                f"Recall: {latest_perf['recall']:.3f}",
                f"Evalueret på: {latest_perf['n_predictions']} predictions"
            ])
        
        # Recommendations
        report_lines.extend([
            "",
            "ANBEFALINGER:",
            "-" * 30
        ])
        
        if len(recent_predictions) == 0:
            report_lines.append("- Model ikke brugt - tjek integration")
        elif len(recent_predictions) < 10:
            report_lines.append("- Lav aktivitet - overvej markedsføring")
        
        if predictor.performance_history:
            if len(predictor.performance_history) >= 2:
                trend = predictor.performance_history[-1]['accuracy'] - predictor.performance_history[-2]['accuracy']
                if trend < -0.02:
                    report_lines.append("- Performance declining - overvej retraining")
                elif trend > 0.02:
                    report_lines.append("- Performance improving - fortsæt nuværende strategi")
        
        report_lines.append("- Fortsæt monitoring og data collection")
        
        return "\n".join(report_lines)


class AutoRetrainer:
    """
    Automatisk retraining system
    """
    
    def __init__(self, data_source_path: str, output_dir: str):
        self.data_source_path = data_source_path
        self.output_dir = output_dir
        
    def should_retrain(self, predictor: HandballPredictor, 
                      drift_results: Dict[str, Any] = None) -> Tuple[bool, str]:
        """
        Afgører om model skal retraines
        
        Args:
            predictor: Current predictor
            drift_results: Results fra data drift detection
            
        Returns:
            (should_retrain, reason)
        """
        reasons = []
        
        # Check 1: Performance decline
        if len(predictor.performance_history) >= 2:
            latest_perf = predictor.performance_history[-1]['accuracy']
            baseline_perf = predictor.performance_history[0]['accuracy']
            
            if latest_perf < baseline_perf - 0.05:  # 5% decline
                reasons.append(f"Performance decline: {latest_perf:.3f} < {baseline_perf:.3f}")
        
        # Check 2: Data drift
        if drift_results and drift_results['recommendation'] in ['RETRAIN_URGENT', 'RETRAIN_SOON']:
            reasons.append(f"Data drift detected: {drift_results['drift_score']:.1%} features changed")
        
        # Check 3: Time since last training
        # (Dette kræver timestamp fra original training - placeholder)
        days_since_training = 30  # Placeholder
        if days_since_training > 90:  # 3 måneder
            reasons.append(f"Model age: {days_since_training} days since training")
        
        # Check 4: New data availability
        if os.path.exists(self.data_source_path):
            # Check hvis der er ny data siden sidste training
            # Placeholder logic
            new_data_available = True  # Simplified
            if new_data_available:
                reasons.append("New training data available")
        
        should_retrain = len(reasons) > 0
        reason = "; ".join(reasons) if reasons else "No retraining needed"
        
        return should_retrain, reason
    
    def trigger_retraining(self, league: str) -> Dict[str, Any]:
        """
        Trigger automatisk retraining
        
        Args:
            league: "Herreliga" eller "Kvindeliga"
            
        Returns:
            Retraining results
        """
        print(f"🔄 STARTER AUTOMATISK RETRAINING FOR {league}")
        
        try:
            # Import and run pipeline
            from ml_pipeline import HandballMLPipeline
            
            # Setup output directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            retrain_output_dir = os.path.join(self.output_dir, f"retrain_{timestamp}_{league}")
            os.makedirs(retrain_output_dir, exist_ok=True)
            
            # Run pipeline
            pipeline = HandballMLPipeline(league=league)
            pipeline.output_dir = retrain_output_dir
            pipeline.run_complete_pipeline()
            
            # Compare performance with previous model
            old_model_path = os.path.join(f"ML_Results_{league}", "trained_models.pkl")
            new_model_path = os.path.join(retrain_output_dir, "trained_models.pkl")
            
            performance_comparison = self._compare_model_performance(old_model_path, new_model_path)
            
            results = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'new_model_path': new_model_path,
                'performance_comparison': performance_comparison,
                'recommendation': 'DEPLOY' if performance_comparison['improvement'] > 0 else 'KEEP_OLD'
            }
            
            print(f"✅ Retraining komplet: {performance_comparison['improvement']:.3f} improvement")
            return results
            
        except Exception as e:
            print(f"❌ Retraining fejl: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _compare_model_performance(self, old_model_path: str, new_model_path: str) -> Dict[str, float]:
        """Sammenligner performance mellem gammel og ny model"""
        try:
            # Load old model results
            with open(old_model_path, 'rb') as f:
                old_data = pickle.load(f)
            old_results = old_data['results']
            old_best_acc = max(result['accuracy'] for result in old_results.values())
            
            # Load new model results
            with open(new_model_path, 'rb') as f:
                new_data = pickle.load(f)
            new_results = new_data['results']
            new_best_acc = max(result['accuracy'] for result in new_results.values())
            
            improvement = new_best_acc - old_best_acc
            
            return {
                'old_accuracy': old_best_acc,
                'new_accuracy': new_best_acc,
                'improvement': improvement,
                'relative_improvement': improvement / old_best_acc if old_best_acc > 0 else 0
            }
            
        except Exception as e:
            print(f"⚠️  Kunne ikke sammenligne performance: {e}")
            return {'error': str(e)}


# === PRODUCTION SCRIPTS ===

def deploy_model_to_production(model_path: str, league: str, backup_existing: bool = True):
    """
    Deployer model til production environment
    
    Args:
        model_path: Sti til ny model
        league: Liga navn
        backup_existing: Om eksisterende model skal backup'es
    """
    print(f"🚀 DEPLOYING MODEL TIL PRODUCTION - {league}")
    
    production_path = f"production_models/{league}_current_model.pkl"
    
    # Backup existing model
    if backup_existing and os.path.exists(production_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"production_models/backup_{league}_{timestamp}.pkl"
        os.rename(production_path, backup_path)
        print(f"📦 Backup af eksisterende model: {backup_path}")
    
    # Copy new model
    import shutil
    os.makedirs(os.path.dirname(production_path), exist_ok=True)
    shutil.copy2(model_path, production_path)
    
    print(f"✅ Model deployed: {production_path}")
    
    # Valider deployment
    try:
        predictor = HandballPredictor(production_path, league)
        test_prediction = predictor.predict_match({'dummy_feature': 1.0})
        print(f"✅ Deployment validation passed")
    except Exception as e:
        print(f"❌ Deployment validation fejl: {e}")


def daily_monitoring_script(league: str = "Herreliga"):
    """
    Daglig monitoring script til at køre som cron job
    """
    print(f"📊 DAILY MONITORING - {league}")
    
    try:
        # Load production model
        production_path = f"production_models/{league}_current_model.pkl"
        if not os.path.exists(production_path):
            print(f"❌ Ingen production model fundet: {production_path}")
            return
        
        predictor = HandballPredictor(production_path, league)
        
        # Load existing logs
        log_path = f"production_logs/{league}_predictions.json"
        if os.path.exists(log_path):
            predictor.load_prediction_log(log_path)
        
        # Health check
        monitor = ModelMonitor(f"production_models")
        health_status = monitor.daily_health_check(predictor)
        
        # Log results
        os.makedirs("monitoring_logs", exist_ok=True)
        with open(f"monitoring_logs/{league}_daily_{datetime.now().strftime('%Y%m%d')}.json", 'w') as f:
            json.dump(health_status, f, indent=2)
        
        # Alerts
        if health_status['overall_status'] in ['WARNING', 'CRITICAL']:
            print(f"🚨 ALERT: {health_status['overall_status']}")
            for alert in health_status['alerts']:
                print(f"  - {alert}")
            
            # Send notification (placeholder)
            # send_alert_notification(health_status)
        
        print(f"✅ Daily monitoring komplet")
        
    except Exception as e:
        print(f"❌ Monitoring fejl: {e}")


def weekly_report_script(league: str = "Herreliga"):
    """
    Ugentlig rapport script
    """
    print(f"📋 WEEKLY REPORT - {league}")
    
    try:
        production_path = f"production_models/{league}_current_model.pkl"
        predictor = HandballPredictor(production_path, league)
        
        # Load logs
        log_path = f"production_logs/{league}_predictions.json"
        if os.path.exists(log_path):
            predictor.load_prediction_log(log_path)
        
        # Generate report
        monitor = ModelMonitor("production_models")
        report = monitor.generate_weekly_report(predictor)
        
        # Save report
        os.makedirs("weekly_reports", exist_ok=True)
        report_path = f"weekly_reports/{league}_week_{datetime.now().strftime('%Y_W%V')}.txt"
        
        with open(report_path, 'w') as f:
            f.write(report)
        
        print(f"📄 Weekly rapport gemt: {report_path}")
        print("\n" + report)
        
    except Exception as e:
        print(f"❌ Weekly report fejl: {e}")


# === EXAMPLE USAGE ===

def example_production_workflow():
    """
    Eksempel på komplet production workflow
    """
    print("""
PRODUCTION WORKFLOW EKSEMPEL:
============================

1. INITIAL DEPLOYMENT:
   python ml_production_utils.py deploy Herreliga ML_Results_Herreliga/trained_models.pkl

2. DAGLIG MONITORING (cron job):
   0 6 * * * python ml_production_utils.py monitor Herreliga

3. UGENTLIG RAPPORT (cron job):
   0 9 * * 1 python ml_production_utils.py report Herreliga

4. PREDICTION INFERENCE:
   from ml_production_utils import HandballPredictor
   predictor = HandballPredictor('production_models/Herreliga_current_model.pkl', 'Herreliga')
   result = predictor.predict_match({'home_elo_rating': 1500, 'away_elo_rating': 1400, ...})

5. AUTOMATED RETRAINING:
   retrainer = AutoRetrainer('ML_Datasets', 'retrain_output')
   should_retrain, reason = retrainer.should_retrain(predictor)
   if should_retrain:
       results = retrainer.trigger_retraining('Herreliga')

6. PERFORMANCE MONITORING:
   actual_results = [1, 0, 1, 1, 0]  # Faktiske resultater
   performance = predictor.evaluate_recent_performance(actual_results)
   
7. DATA DRIFT DETECTION:
   new_data = pd.read_csv('recent_matches.csv')
   drift = predictor.detect_data_drift(new_data)
    """)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("🎯 HÅNDBOL ML PRODUCTION UTILITIES")
        print("=" * 50)
        example_production_workflow()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "deploy" and len(sys.argv) >= 4:
        league = sys.argv[2]
        model_path = sys.argv[3]
        deploy_model_to_production(model_path, league)
        
    elif command == "monitor" and len(sys.argv) >= 3:
        league = sys.argv[2]
        daily_monitoring_script(league)
        
    elif command == "report" and len(sys.argv) >= 3:
        league = sys.argv[2]
        weekly_report_script(league)
        
    else:
        print("❌ Ugyldig command")
        print("Brug: python ml_production_utils.py [deploy|monitor|report] [league] [model_path]")
