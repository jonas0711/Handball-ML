#!/usr/bin/env python3
"""
QUICK PERFORMANCE BOOST FOR HANDBALL ML
======================================

Implementerer hurtige performance forbedringer:
- Optimeret feature selection
- Bedre scaling strategies
- Smart ensemble weights
- Cross-validation optimization

Author: AI Assistant  
"""

import pandas as pd
import numpy as np
import pickle
from sklearn.model_selection import cross_val_score, TimeSeriesSplit
from sklearn.preprocessing import RobustScaler, StandardScaler, MinMaxScaler
from sklearn.feature_selection import SelectKBest, mutual_info_classif, f_classif, SelectFromModel
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, roc_auc_score, f1_score
import warnings

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

warnings.filterwarnings('ignore')

class QuickPerformanceBooster:
    """
    Hurtige performance forbedringer til eksisterende modeller
    """
    
    def __init__(self, league: str = "Herreliga"):
        print(f"⚡ QUICK PERFORMANCE BOOST - {league}")
        print("=" * 50)
        
        self.league = league
        self.baseline_results = None
        self.improved_results = {}
        
    def load_baseline_models(self):
        """
        Load baseline modeller fra ml_pipeline_main.py
        """
        print("\n📂 LOADER BASELINE MODELLER")
        
        try:
            with open(f"ML_Results_{self.league}/trained_models.pkl", 'rb') as f:
                self.baseline_models = pickle.load(f)
            print(f"✅ Loaded {len(self.baseline_models)} baseline modeller")
            
            # Load comparison data
            self.baseline_results = pd.read_csv(f"ML_Results_{self.league}/model_comparison.csv")
            print("✅ Loaded baseline performance data")
            
        except FileNotFoundError:
            print("❌ Baseline modeller ikke fundet - kør ml_pipeline_main.py først")
            return False
            
        return True
        
    def load_data(self):
        """
        Load og prep data samme måde som baseline
        """
        print("\n📊 LOADER DATA")
        
        # Load dataset
        data_path = f"ML_Datasets/{self.league.lower()}_handball_ml_dataset.csv"
        df = pd.read_csv(data_path)
        
        # Temporal split (samme som baseline)
        if self.league == "Herreliga":
            train_seasons = ["2017-2018", "2018-2019", "2019-2020", "2020-2021",
                           "2021-2022", "2022-2023", "2023-2024"]
            test_seasons = ["2024-2025"]
        else:
            train_seasons = ["2018-2019", "2019-2020", "2020-2021",
                           "2021-2022", "2022-2023", "2023-2024"] 
            test_seasons = ["2024-2025"]
        
        train_data = df[df['season'].isin(train_seasons)]
        test_data = df[df['season'].isin(test_seasons)]
        
        # Extract features
        metadata_cols = ['kamp_id', 'season', 'match_date', 'home_team', 'away_team', 'venue', 'league']
        target_cols = [col for col in df.columns if col.startswith('target_')]
        feature_cols = [col for col in df.columns if col not in metadata_cols + target_cols]
        
        self.X_train = train_data[feature_cols].copy()
        self.X_test = test_data[feature_cols].copy()
        self.y_train = train_data['target_home_win'].copy()
        self.y_test = test_data['target_home_win'].copy()
        
        # Apply samma data cleaning som baseline
        self._apply_baseline_cleaning()
        
        print(f"✅ Data loaded: {self.X_train.shape}")
        
    def _apply_baseline_cleaning(self):
        """
        Samme cleaning som baseline pipeline
        """
        # Convert boolean to int
        bool_cols = self.X_train.select_dtypes(include=['bool']).columns
        for col in bool_cols:
            self.X_train[col] = self.X_train[col].astype(int)
            self.X_test[col] = self.X_test[col].astype(int)
        
        # Handle categorical features
        cat_cols = self.X_train.select_dtypes(include=['object']).columns
        for col in cat_cols:
            unique_vals = self.X_train[col].nunique()
            if unique_vals <= 10:
                from sklearn.preprocessing import LabelEncoder
                le = LabelEncoder()
                self.X_train[col] = le.fit_transform(self.X_train[col].astype(str))
                # Handle test data
                test_col_str = self.X_test[col].astype(str)
                unseen_mask = ~test_col_str.isin(le.classes_)
                if unseen_mask.any():
                    most_common = self.X_train[col].mode().iloc[0] if len(self.X_train[col].mode()) > 0 else 0
                    test_col_str.loc[unseen_mask] = le.inverse_transform([most_common])[0]
                self.X_test[col] = le.transform(test_col_str)
            else:
                # Drop high cardinality
                self.X_train = self.X_train.drop(columns=[col])
                self.X_test = self.X_test.drop(columns=[col])
        
        # Handle infinite values and outliers
        self.X_train.replace([np.inf, -np.inf], np.nan, inplace=True)
        self.X_test.replace([np.inf, -np.inf], np.nan, inplace=True)
        
        # Outlier capping
        for col in self.X_train.select_dtypes(include=[np.number]).columns:
            q999 = self.X_train[col].quantile(0.999)
            q001 = self.X_train[col].quantile(0.001)
            self.X_train[col] = self.X_train[col].clip(lower=q001, upper=q999)
            self.X_test[col] = self.X_test[col].clip(lower=q001, upper=q999)
        
        # Impute NaN
        from sklearn.impute import SimpleImputer
        imputer = SimpleImputer(strategy='median')
        self.X_train = pd.DataFrame(
            imputer.fit_transform(self.X_train),
            columns=self.X_train.columns,
            index=self.X_train.index
        )
        self.X_test = pd.DataFrame(
            imputer.transform(self.X_test),
            columns=self.X_test.columns,
            index=self.X_test.index
        )
        
    def optimize_feature_selection(self):
        """
        Optimeret feature selection strategies
        """
        print("\n🎛️  OPTIMERET FEATURE SELECTION")
        print("-" * 40)
        
        results = {}
        
        # 1. Test forskellige feature selection metoder
        selectors = {
            'mutual_info_50': SelectKBest(score_func=mutual_info_classif, k=50),
            'mutual_info_75': SelectKBest(score_func=mutual_info_classif, k=75),
            'mutual_info_100': SelectKBest(score_func=mutual_info_classif, k=100),
            'f_classif_50': SelectKBest(score_func=f_classif, k=50),
            'f_classif_75': SelectKBest(score_func=f_classif, k=75),
            'rf_importance': SelectFromModel(RandomForestClassifier(n_estimators=100, random_state=42), max_features=75)
        }
        
        # Test med baseline Neural Network
        base_nn = MLPClassifier(
            hidden_layer_sizes=(100,),
            learning_rate_init=0.001,
            alpha=0.01,
            max_iter=300,
            random_state=42,
            early_stopping=True
        )
        
        cv = TimeSeriesSplit(n_splits=3)
        scaler = RobustScaler()
        
        for name, selector in selectors.items():
            print(f"   Testing {name}...")
            try:
                # Select features
                X_train_selected = selector.fit_transform(self.X_train, self.y_train)
                
                # Scale
                X_train_scaled = scaler.fit_transform(X_train_selected)
                
                # Cross-validate
                scores = cross_val_score(base_nn, X_train_scaled, self.y_train, cv=cv, scoring='roc_auc')
                mean_score = scores.mean()
                
                results[name] = {
                    'selector': selector,
                    'cv_score': mean_score,
                    'n_features': X_train_selected.shape[1]
                }
                
                print(f"     ROC-AUC: {mean_score:.4f} ({X_train_selected.shape[1]} features)")
                
            except Exception as e:
                print(f"     Failed: {str(e)}")
        
        # Find bedste feature selection
        best_selector_name = max(results.keys(), key=lambda x: results[x]['cv_score'])
        best_selector_data = results[best_selector_name]
        
        print(f"\n🏆 Bedste feature selection: {best_selector_name}")
        print(f"   CV Score: {best_selector_data['cv_score']:.4f}")
        print(f"   Features: {best_selector_data['n_features']}")
        
        self.best_selector = best_selector_data['selector']
        return best_selector_data
        
    def optimize_scaling(self):
        """
        Test forskellige scaling strategier
        """
        print("\n⚖️  OPTIMERET SCALING STRATEGIES")
        print("-" * 40)
        
        # Use bedste feature selection
        X_train_selected = self.best_selector.fit_transform(self.X_train, self.y_train)
        
        scalers = {
            'RobustScaler': RobustScaler(),
            'StandardScaler': StandardScaler(),
            'MinMaxScaler': MinMaxScaler(),
            'No_Scaling': None
        }
        
        # Test med Neural Network
        base_nn = MLPClassifier(
            hidden_layer_sizes=(100,),
            learning_rate_init=0.001,
            alpha=0.01,
            max_iter=300,
            random_state=42,
            early_stopping=True
        )
        
        cv = TimeSeriesSplit(n_splits=3)
        results = {}
        
        for name, scaler in scalers.items():
            print(f"   Testing {name}...")
            
            if scaler is None:
                X_train_scaled = X_train_selected
            else:
                X_train_scaled = scaler.fit_transform(X_train_selected)
            
            scores = cross_val_score(base_nn, X_train_scaled, self.y_train, cv=cv, scoring='roc_auc')
            mean_score = scores.mean()
            
            results[name] = {
                'scaler': scaler,
                'cv_score': mean_score
            }
            
            print(f"     ROC-AUC: {mean_score:.4f}")
        
        # Find bedste scaler
        best_scaler_name = max(results.keys(), key=lambda x: results[x]['cv_score'])
        best_scaler_data = results[best_scaler_name]
        
        print(f"\n🏆 Bedste scaling: {best_scaler_name}")
        print(f"   CV Score: {best_scaler_data['cv_score']:.4f}")
        
        self.best_scaler = best_scaler_data['scaler']
        return best_scaler_data
        
    def create_optimized_models(self):
        """
        Create optimerede versioner af baseline modeller
        """
        print("\n🚀 OPTIMEREDE MODELLER")
        print("-" * 40)
        
        # Prepare optimized data
        X_train_selected = self.best_selector.fit_transform(self.X_train, self.y_train)
        X_test_selected = self.best_selector.transform(self.X_test)
        
        if self.best_scaler is not None:
            X_train_scaled = self.best_scaler.fit_transform(X_train_selected)
            X_test_scaled = self.best_scaler.transform(X_test_selected)
        else:
            X_train_scaled = X_train_selected
            X_test_scaled = X_test_selected
        
        # 1. Optimized Neural Network
        print("1️⃣  Optimized Neural Network...")
        nn_opt = MLPClassifier(
            hidden_layer_sizes=(150, 50),  # Deeper architecture
            learning_rate_init=0.001,
            alpha=0.001,  # Less regularization 
            activation='relu',
            max_iter=500,  # More iterations
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1,
            n_iter_no_change=20
        )
        
        nn_opt.fit(X_train_scaled, self.y_train)
        y_pred_nn = nn_opt.predict(X_test_scaled)
        y_proba_nn = nn_opt.predict_proba(X_test_scaled)[:, 1]
        
        nn_accuracy = accuracy_score(self.y_test, y_pred_nn)
        nn_roc_auc = roc_auc_score(self.y_test, y_proba_nn)
        
        print(f"   Accuracy: {nn_accuracy:.4f}")
        print(f"   ROC-AUC: {nn_roc_auc:.4f}")
        
        # 2. Optimized Random Forest
        print("2️⃣  Optimized Random Forest...")
        rf_opt = RandomForestClassifier(
            n_estimators=300,  # More trees
            max_depth=15,  # Deeper trees
            min_samples_split=3,
            min_samples_leaf=1,
            max_features='sqrt',
            random_state=42,
            n_jobs=-1
        )
        
        rf_opt.fit(X_train_selected, self.y_train)  # RF doesn't need scaling
        y_pred_rf = rf_opt.predict(X_test_selected)
        y_proba_rf = rf_opt.predict_proba(X_test_selected)[:, 1]
        
        rf_accuracy = accuracy_score(self.y_test, y_pred_rf)
        rf_roc_auc = roc_auc_score(self.y_test, y_proba_rf)
        
        print(f"   Accuracy: {rf_accuracy:.4f}")
        print(f"   ROC-AUC: {rf_roc_auc:.4f}")
        
        # 3. Optimized XGBoost
        if XGBOOST_AVAILABLE:
            print("3️⃣  Optimized XGBoost...")
            xgb_opt = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=6,
                learning_rate=0.1,
                subsample=0.9,
                colsample_bytree=0.9,
                random_state=42,
                eval_metric='logloss'
            )
            
            xgb_opt.fit(X_train_selected, self.y_train)
            y_pred_xgb = xgb_opt.predict(X_test_selected)
            y_proba_xgb = xgb_opt.predict_proba(X_test_selected)[:, 1]
            
            xgb_accuracy = accuracy_score(self.y_test, y_pred_xgb)
            xgb_roc_auc = roc_auc_score(self.y_test, y_proba_xgb)
            
            print(f"   Accuracy: {xgb_accuracy:.4f}")
            print(f"   ROC-AUC: {xgb_roc_auc:.4f}")
        
        # 4. Optimized Ensemble med weights
        print("4️⃣  Weighted Ensemble...")
        
        estimators = [
            ('nn_opt', nn_opt),
            ('rf_opt', rf_opt)
        ]
        
        if XGBOOST_AVAILABLE:
            estimators.append(('xgb_opt', xgb_opt))
        
        # Create voting classifier med soft voting
        ensemble_opt = VotingClassifier(
            estimators=estimators,
            voting='soft'
        )
        
        # Train on appropriate data for each model
        if self.best_scaler is not None:
            # Neural network needs scaled data, others don't
            # For simplicity, use scaled data for all
            ensemble_opt.fit(X_train_scaled, self.y_train)
            y_pred_ens = ensemble_opt.predict(X_test_scaled)
            y_proba_ens = ensemble_opt.predict_proba(X_test_scaled)[:, 1]
        else:
            ensemble_opt.fit(X_train_selected, self.y_train)
            y_pred_ens = ensemble_opt.predict(X_test_selected)
            y_proba_ens = ensemble_opt.predict_proba(X_test_selected)[:, 1]
        
        ens_accuracy = accuracy_score(self.y_test, y_pred_ens)
        ens_roc_auc = roc_auc_score(self.y_test, y_proba_ens)
        
        print(f"   Accuracy: {ens_accuracy:.4f}")
        print(f"   ROC-AUC: {ens_roc_auc:.4f}")
        
        # Store results
        self.improved_results = {
            'neural_network': {'accuracy': nn_accuracy, 'roc_auc': nn_roc_auc},
            'random_forest': {'accuracy': rf_accuracy, 'roc_auc': rf_roc_auc},
            'optimized_ensemble': {'accuracy': ens_accuracy, 'roc_auc': ens_roc_auc}
        }
        
        if XGBOOST_AVAILABLE:
            self.improved_results['xgboost'] = {'accuracy': xgb_accuracy, 'roc_auc': xgb_roc_auc}
        
        return self.improved_results
        
    def compare_improvements(self):
        """
        Sammenlign forbedringer med baseline
        """
        print("\n📊 PERFORMANCE FORBEDRINGER")
        print("-" * 50)
        
        # Baseline performance
        baseline_best = self.baseline_results.loc[self.baseline_results['Accuracy'].idxmax()]
        
        print("🔹 BASELINE BEDSTE:")
        print(f"   Model: {baseline_best['Model']}")
        print(f"   Accuracy: {baseline_best['Accuracy']:.1%}")
        print(f"   ROC-AUC: {baseline_best['ROC-AUC']:.1%}")
        
        # Improved performance
        if self.improved_results:
            improved_best = max(self.improved_results.items(), key=lambda x: x[1]['accuracy'])
            improved_name, improved_metrics = improved_best
            
            print("\n🔸 OPTIMERET BEDSTE:")
            print(f"   Model: {improved_name}")
            print(f"   Accuracy: {improved_metrics['accuracy']:.1%}")
            print(f"   ROC-AUC: {improved_metrics['roc_auc']:.1%}")
            
            # Calculate improvements
            acc_improvement = improved_metrics['accuracy'] - baseline_best['Accuracy']
            roc_improvement = improved_metrics['roc_auc'] - baseline_best['ROC-AUC']
            
            print(f"\n📈 FORBEDRINGER:")
            print(f"   Accuracy: {acc_improvement:+.1%}")
            print(f"   ROC-AUC: {roc_improvement:+.1%}")
            
            if acc_improvement > 0:
                print("✅ PERFORMANCE FORBEDRET!")
            else:
                print("⚠️  Ingen signifikant forbedring")
        
    def run_quick_boost(self):
        """
        Kør komplet quick boost pipeline
        """
        print("⚡ STARTER QUICK PERFORMANCE BOOST")
        print("=" * 50)
        
        # Load baseline models og data
        if not self.load_baseline_models():
            return
            
        self.load_data()
        
        # Optimize feature selection og scaling
        self.optimize_feature_selection()
        self.optimize_scaling()
        
        # Create optimized models
        self.create_optimized_models()
        
        # Compare results
        self.compare_improvements()
        
        print("\n⚡ QUICK BOOST KOMPLET!")

def main():
    """
    Main function
    """
    import sys
    league = sys.argv[1] if len(sys.argv) > 1 else "Herreliga"
    
    booster = QuickPerformanceBooster(league)
    booster.run_quick_boost()

if __name__ == "__main__":
    main() 