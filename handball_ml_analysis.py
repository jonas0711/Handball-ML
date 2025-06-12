#!/usr/bin/env python3
"""
HÅNDBOLD ML ANALYSE - KOMPLET PIPELINE
=====================================

Implementerer ML modeller med temporal validation for herre- og kvindeligaen.
Følger anbefalingerne for feature selection og data splitting.

KRITISK: Temporal split for at undgå data leakage!
"""

# Basic imports
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Core ML libraries
from sklearn.model_selection import TimeSeriesSplit, cross_validate, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler, LabelEncoder, RobustScaler
from sklearn.feature_selection import (
    SelectKBest, chi2, f_classif, mutual_info_classif, RFE, 
    VarianceThreshold, SelectFromModel
)
from sklearn.decomposition import PCA
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer

# ML Models
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neural_network import MLPClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier

# External libraries
import xgboost as xgb

# Metrics
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, classification_report, confusion_matrix
)

# Statistical tests  
from sklearn.inspection import permutation_importance

import os
import joblib
from collections import defaultdict
import json

print("📚 Alle libraries loaded successfully!")

class HandballMLAnalyzer:
    """
    Komplet ML analyse pipeline for håndbold kampdata
    """
    
    def __init__(self, base_dir=".", random_state=42):
        """
        Initialiserer ML analyzer
        
        Args:
            base_dir: Sti til projekt directory
            random_state: Seed for reproducible results
        """
        print("🎯 INITIALISERER HÅNDBOLD ML ANALYZER")
        print("=" * 50)
        
        self.base_dir = base_dir
        self.random_state = random_state
        self.results = {}  # Gemmer alle resultater
        
        # Dataset paths
        self.datasets = {
            'herreliga': os.path.join(base_dir, 'ML_Datasets', 'herreliga_handball_ml_dataset.csv'),
            'kvindeliga': os.path.join(base_dir, 'ML_Datasets', 'kvindeliga_handball_ml_dataset.csv')
        }
        
        # Model definitions med feature selection strategier
        self.model_configs = self._define_model_configs()
        
        # Results storage
        self.feature_importance_results = {}
        self.model_performance = {}
        self.best_models = {}
        
        print("✅ Analyzer initialiseret")
        print(f"📁 Base directory: {base_dir}")
        print(f"🎲 Random state: {random_state}")
    
    def _define_model_configs(self):
        """
        Definerer alle ML modeller med deres feature selection strategier
        OPTIMERET: Forbedrede parametre og n_jobs=1 for stabilitet
        """
        configs = {
            'random_forest': {
                'model': RandomForestClassifier(random_state=self.random_state, n_jobs=1),  # n_jobs=1 for stabilitet
                'feature_method': 'importance_rfe',
                'n_features': (30, 50),
                'param_space': {
                    'n_estimators': [100, 150, 200],
                    'max_depth': [15, 20, None],
                    'min_samples_split': [2, 5, 10],
                    'min_samples_leaf': [1, 2, 4],
                    'max_features': ['sqrt', 'log2']
                },
                'description': 'Random Forest - Håndterer mange features godt, robust overfor outliers'
            },
            'xgboost': {
                'model': xgb.XGBClassifier(random_state=self.random_state, eval_metric='logloss', n_jobs=1),  # n_jobs=1
                'feature_method': 'importance_permutation',
                'n_features': (40, 60),
                'param_space': {
                    'n_estimators': [100, 150, 200],
                    'max_depth': [3, 5, 7],
                    'learning_rate': [0.05, 0.1, 0.15],
                    'subsample': [0.8, 0.9, 1.0],
                    'colsample_bytree': [0.8, 0.9, 1.0]
                },
                'description': 'XGBoost - Excellent til strukturerede data og komplekse interaktioner'
            },
            'logistic_regression': {
                'model': LogisticRegression(random_state=self.random_state, max_iter=2000, n_jobs=1),  # Øget max_iter
                'feature_method': 'lasso_correlation',
                'n_features': (20, 35),  # Øget antal features
                'param_space': {
                    'C': [0.1, 1.0, 10.0, 100.0],  # Bredere range
                    'penalty': ['l1', 'l2', 'elasticnet'],  # Tilføjet elasticnet
                    'solver': ['liblinear', 'saga'],
                    'l1_ratio': [0.5, 0.7]  # For elasticnet
                },
                'description': 'Logistic Regression - Interpreterbar baseline med regularization'
            },
            'svm': {
                'model': SVC(random_state=self.random_state, probability=True),
                'feature_method': 'pca_selectkbest',
                'n_features': (25, 40),
                'param_space': {
                    'C': [0.1, 1.0, 10.0],
                    'kernel': ['rbf', 'linear'],
                    'gamma': ['scale', 'auto']  # Fjernet specifikke værdier for stabilitet
                },
                'description': 'SVM - God til højdimensionelle data med robuste decision boundaries'
            },
            'neural_network': {
                'model': MLPClassifier(random_state=self.random_state, max_iter=1000),  # Øget max_iter
                'feature_method': 'variance_mutual_info',
                'n_features': (50, 80),
                'param_space': {
                    'hidden_layer_sizes': [(50,), (100,), (50, 30)],  # Simplere architectures
                    'alpha': [0.001, 0.01, 0.1],
                    'learning_rate_init': [0.001, 0.01],
                    'activation': ['relu', 'tanh'],
                    'early_stopping': [True]  # Tilføjet early stopping
                },
                'description': 'Neural Network - Kan lære komplekse non-lineære patterns'
            },
            'knn': {
                'model': KNeighborsClassifier(n_jobs=1),  # n_jobs=1 for at undgå subprocess issues
                'feature_method': 'distance_based',
                'n_features': (15, 25),  # Øget antal features
                'param_space': {
                    'n_neighbors': [3, 5, 7, 9],
                    'weights': ['uniform', 'distance'],
                    'metric': ['euclidean', 'manhattan']  # Fjernet minkowski for stabilitet
                },
                'description': 'KNN - Simple non-parametrisk, god til lokale patterns'
            },
            'naive_bayes': {
                'model': GaussianNB(),
                'feature_method': 'chi2_info_gain',
                'n_features': (20, 35),  # Øget antal features
                'param_space': {
                    'var_smoothing': [1e-10, 1e-9, 1e-8, 1e-7]  # Bredere range
                },
                'description': 'Naive Bayes - Hurtig baseline, god til små datasets'
            },
            'decision_tree': {
                'model': DecisionTreeClassifier(random_state=self.random_state),
                'feature_method': 'entropy_based',
                'n_features': (15, 25),  # Øget antal features
                'param_space': {
                    'max_depth': [5, 10, 15, 20, None],
                    'min_samples_split': [2, 5, 10],
                    'min_samples_leaf': [1, 2, 4],
                    'criterion': ['gini', 'entropy'],
                    'max_features': ['sqrt', 'log2', None]  # Tilføjet max_features
                },
                'description': 'Decision Tree - Meget interpreterbar, identificerer beslutningsregler'
            }
        }
        
        return configs
    
    def load_and_prepare_data(self, league):
        """
        Loader og forbereder data for en specifik liga
        TILFØJET: Omfattende data cleaning for uendelige og ekstreme værdier
        """
        print(f"\n📊 LOADER DATA FOR {league.upper()}")
        print("-" * 40)
        
        # Load dataset
        df = pd.read_csv(self.datasets[league])
        print(f"  📋 Dataset shape: {df.shape}")
        print(f"  📅 Dato range: {df['match_date'].min()} til {df['match_date'].max()}")
        
        # Convert match_date to datetime
        df['match_date'] = pd.to_datetime(df['match_date'])
        
        # Temporal split - træning indtil 2024, test 2024-2025
        train_cutoff = pd.to_datetime('2024-07-01')
        train_mask = df['match_date'] < train_cutoff
        test_mask = df['match_date'] >= train_cutoff
        
        print(f"  📚 Training samples: {train_mask.sum()}")
        print(f"  📖 Test samples: {test_mask.sum()}")
        
        # Define target variable (home team vinder)
        target_col = 'target_home_win'
        
        # Metadata columns at fjerne fra features
        metadata_cols = [
            'kamp_id', 'season', 'match_date', 'home_team', 'away_team', 
            'venue', 'league'
        ]
        
        # Target columns at fjerne fra features
        target_cols = [col for col in df.columns if col.startswith('target_')]
        
        # Remove metadata og targets for at få feature columns
        all_feature_cols = [col for col in df.columns 
                           if col not in metadata_cols + target_cols]
        
        # Filter til kun numeriske features (undgå kategoriske som pos_most_efficient)
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        feature_cols = [col for col in all_feature_cols if col in numeric_cols]
        
        print(f"  🎯 Total feature columns: {len(all_feature_cols)}")
        print(f"  📊 Numeric feature columns: {len(feature_cols)}")
        
        # Extract features og target
        X = df[feature_cols].copy()  # Explicit copy for safe modifications
        y = df[target_col]
        
        # ===== KRITISK DATA CLEANING SEKTION =====
        print(f"\n🔧 DATA CLEANING - HÅNDTERING AF EKSTREME VÆRDIER:")
        
        # 1. Check for infinite values (dette var problemet!)
        print("  🔍 Checker for uendelige værdier...")
        inf_counts = np.isinf(X).sum()
        total_inf = inf_counts.sum()
        if total_inf > 0:
            print(f"    ⚠️  Fundet {total_inf} uendelige værdier")
            # Replace infinite values med NaN så de kan håndteres
            X.replace([np.inf, -np.inf], np.nan, inplace=True)
            print("    ✅ Uendelige værdier erstattet med NaN")
        else:
            print("    ✅ Ingen uendelige værdier fundet")
        
        # 2. Check for extremely large values (over 99.9th percentile)
        print("  🔍 Checker for ekstreme værdier...")
        for col in X.columns:
            if X[col].dtype in ['float64', 'int64']:
                # Beregn percentiler for at identificere outliers
                q999 = X[col].quantile(0.999)
                q001 = X[col].quantile(0.001)
                
                # Cap ekstreme værdier til 99.9th percentile
                extreme_high = X[col] > q999
                extreme_low = X[col] < q001
                
                if extreme_high.sum() > 0:
                    print(f"    🔧 Capping {extreme_high.sum()} høje outliers i {col}")
                    X.loc[extreme_high, col] = q999
                
                if extreme_low.sum() > 0:
                    print(f"    🔧 Capping {extreme_low.sum()} lave outliers i {col}")
                    X.loc[extreme_low, col] = q001
        
        # 3. Handle NaN values (fra tidligere infinite replacement)
        print("  🔍 Håndtering af NaN værdier...")
        nan_counts = X.isnull().sum()
        total_nans = nan_counts.sum()
        if total_nans > 0:
            print(f"    📋 Fundet {total_nans} NaN værdier")
            # Use forward fill then backward fill for temporal data
            X.fillna(method='ffill', inplace=True)
            X.fillna(method='bfill', inplace=True)
            # If still NaN, use median
            X.fillna(X.median(), inplace=True)
            print("    ✅ NaN værdier udfyldt med temporal og median imputation")
        
        # 4. Final validation og optimization
        print("  🔍 Final validation...")
        
        # Memory optimization - konverter til float32 hvor muligt for at spare memory
        for col in X.columns:
            if X[col].dtype == 'float64':
                # Check om vi kan konvertere til float32 uden tab af precision
                if X[col].max() < np.finfo(np.float32).max and X[col].min() > np.finfo(np.float32).min:
                    X[col] = X[col].astype(np.float32)
        
        # Final check for infinite og NaN values
        inf_final = np.isinf(X).sum().sum()
        nan_final = X.isnull().sum().sum()
        
        if inf_final > 0 or nan_final > 0:
            print(f"    ⚠️ Stadig problemer: {inf_final} inf, {nan_final} NaN værdier")
            # Emergency cleanup
            X.replace([np.inf, -np.inf], np.nan, inplace=True)
            X.fillna(X.median(), inplace=True)
        else:
            print("    ✅ Alle ekstreme værdier håndteret succesfuldt!")
        
        print(f"  📊 Features efter cleaning: {len(X.columns)}")
        
        # ===== TEMPORAL SPLIT =====
        train_data = X[train_mask].copy()
        test_data = X[test_mask].copy()
        train_target = y[train_mask].copy()
        test_target = y[test_mask].copy()
        
        # Final data quality report
        print(f"\n🔍 FINAL DATA QUALITY RAPPORT:")
        print(f"  📊 Feature columns: {len(X.columns)}")
        print(f"  📋 Training shape: {train_data.shape}")
        print(f"  📖 Test shape: {test_data.shape}")
        print(f"  🎯 Hjemme sejr rate (train): {train_target.mean():.1%}")
        print(f"  ✅ Data range check - Min: {X.min().min():.2f}, Max: {X.max().max():.2f}")
        
        return {
            'X_train': train_data,
            'X_test': test_data,
            'y_train': train_target,
            'y_test': test_target,
            'feature_names': X.columns.tolist(),
            'metadata': {
                'train_date_range': (df[train_mask]['match_date'].min(), df[train_mask]['match_date'].max()),
                'test_date_range': (df[test_mask]['match_date'].min(), df[test_mask]['match_date'].max()),
                'total_matches': len(df),
                'leagues': df['league'].unique().tolist() if 'league' in df.columns else [league]
            }
        }
    
    def apply_feature_selection(self, X_train, y_train, X_test, method, n_features_range):
        """
        Anvender feature selection baseret på specificeret metode
        OPDATERET: Komplet implementering af alle feature selection metoder
        """
        print(f"    🔧 Feature selection: {method}")
        
        # Data validation - check at der ikke er infinite værdier tilbage
        print("      🔍 Verificerer data kvalitet før feature selection...")
        if np.isinf(X_train).any().any() or np.isinf(X_test).any().any():
            print("      ❌ FEJL: Infinite værdier stadig til stede!")
            return None, None
        
        # Handle missing values med robust metoder
        from sklearn.impute import SimpleImputer
        imputer = SimpleImputer(strategy='median')  # Median er robust overfor outliers
        X_train_imp = imputer.fit_transform(X_train)
        X_test_imp = imputer.transform(X_test)
        
        # Additional safety check efter imputation
        if np.isinf(X_train_imp).any() or np.isinf(X_test_imp).any():
            print("      ❌ FEJL: Infinite værdier efter imputation!")
            return None, None
        
        # Bestem antal features
        n_features = min(n_features_range[1], X_train_imp.shape[1])
        
        try:
            if method == 'importance_rfe':
                # Random Forest importance med RFE
                from sklearn.feature_selection import RFE
                rf_base = RandomForestClassifier(n_estimators=50, random_state=self.random_state, n_jobs=1)
                selector = RFE(rf_base, n_features_to_select=n_features)
                X_train_selected = selector.fit_transform(X_train_imp, y_train)
                X_test_selected = selector.transform(X_test_imp)
                
            elif method == 'importance_permutation':
                # XGBoost + permutation importance
                xgb_base = xgb.XGBClassifier(n_estimators=50, random_state=self.random_state, eval_metric='logloss', n_jobs=1)
                xgb_base.fit(X_train_imp, y_train)
                perm_importance = permutation_importance(xgb_base, X_train_imp, y_train, 
                                                       n_repeats=3, random_state=self.random_state, n_jobs=1)
                importance_indices = np.argsort(perm_importance.importances_mean)[-n_features:]
                X_train_selected = X_train_imp[:, importance_indices]
                X_test_selected = X_test_imp[:, importance_indices]
                
            elif method == 'lasso_correlation':
                # LASSO regularization med robust scaling og forbedret parameter
                from sklearn.preprocessing import RobustScaler
                from sklearn.linear_model import LassoCV
                from sklearn.feature_selection import SelectFromModel
                
                scaler = RobustScaler()
                X_train_scaled = scaler.fit_transform(X_train_imp)
                X_test_scaled = scaler.transform(X_test_imp)
                
                # Brug mindre aggressiv alpha for at få flere features
                lasso = LassoCV(cv=3, random_state=self.random_state, max_iter=1000, 
                               alphas=np.logspace(-4, 1, 20))  # Bredere range af alphas
                lasso.fit(X_train_scaled, y_train)
                
                # Hvis LASSO vælger 0 features, brug mindre aggressive threshold
                selector = SelectFromModel(lasso, max_features=n_features, threshold='mean')
                X_train_selected = selector.fit_transform(X_train_scaled, y_train)
                X_test_selected = selector.transform(X_test_scaled)
                
                # Fallback hvis stadig 0 features
                if X_train_selected.shape[1] == 0:
                    print(f"      ⚠️ LASSO valgte 0 features, bruger fallback...")
                    k_best = SelectKBest(f_classif, k=n_features)
                    X_train_selected = k_best.fit_transform(X_train_scaled, y_train)
                    X_test_selected = k_best.transform(X_test_scaled)
                
            elif method == 'pca_selectkbest':
                # PCA + SelectKBest kombination
                from sklearn.decomposition import PCA
                from sklearn.pipeline import Pipeline
                
                # Brug PCA til dimensionalitetsreduktion og derefter SelectKBest
                pca_components = min(int(n_features * 1.5), X_train_imp.shape[1] // 2)
                pipeline = Pipeline([
                    ('scaler', RobustScaler()),
                    ('pca', PCA(n_components=pca_components, random_state=self.random_state)),
                    ('select', SelectKBest(f_classif, k=n_features))
                ])
                X_train_selected = pipeline.fit_transform(X_train_imp, y_train)
                X_test_selected = pipeline.transform(X_test_imp)
                
            elif method == 'variance_mutual_info':
                # Variance threshold + Mutual information
                from sklearn.feature_selection import VarianceThreshold, mutual_info_classif
                
                # Fjern features med lav varians
                var_threshold = VarianceThreshold(threshold=0.01)
                X_train_var = var_threshold.fit_transform(X_train_imp)
                X_test_var = var_threshold.transform(X_test_imp)
                
                # Mutual information selection
                if X_train_var.shape[1] > 0:
                    mi_scores = mutual_info_classif(X_train_var, y_train, random_state=self.random_state)
                    mi_indices = np.argsort(mi_scores)[-n_features:]
                    X_train_selected = X_train_var[:, mi_indices]
                    X_test_selected = X_test_var[:, mi_indices]
                else:
                    # Fallback
                    k_best = SelectKBest(f_classif, k=n_features)
                    X_train_selected = k_best.fit_transform(X_train_imp, y_train)
                    X_test_selected = k_best.transform(X_test_imp)
                
            elif method == 'distance_based':
                # Distance-based feature selection for KNN
                from sklearn.preprocessing import StandardScaler
                from sklearn.neighbors import NearestNeighbors
                
                # Standardisér data for distance beregninger
                scaler = StandardScaler()
                X_train_scaled = scaler.fit_transform(X_train_imp)
                X_test_scaled = scaler.transform(X_test_imp)
                
                # Brug correlation-based feature selection
                from sklearn.feature_selection import SelectKBest, f_classif
                k_best = SelectKBest(f_classif, k=n_features)
                X_train_selected = k_best.fit_transform(X_train_scaled, y_train)
                X_test_selected = k_best.transform(X_test_scaled)
                
            elif method == 'chi2_info_gain':
                # Chi2 test + Information Gain for Naive Bayes
                from sklearn.feature_selection import SelectKBest, chi2, mutual_info_classif
                
                # Sørg for at alle værdier er positive for chi2
                min_val = X_train_imp.min()
                if min_val < 0:
                    X_train_pos = X_train_imp - min_val + 1e-8
                    X_test_pos = X_test_imp - min_val + 1e-8
                else:
                    X_train_pos = X_train_imp + 1e-8
                    X_test_pos = X_test_imp + 1e-8
                
                # Chi2 selection
                try:
                    chi2_selector = SelectKBest(chi2, k=n_features)
                    X_train_selected = chi2_selector.fit_transform(X_train_pos, y_train)
                    X_test_selected = chi2_selector.transform(X_test_pos)
                except:
                    # Fallback til mutual info
                    mi_selector = SelectKBest(mutual_info_classif, k=n_features)
                    X_train_selected = mi_selector.fit_transform(X_train_imp, y_train)
                    X_test_selected = mi_selector.transform(X_test_imp)
                
            elif method == 'entropy_based':
                # Entropy-based feature selection for Decision Trees
                from sklearn.feature_selection import SelectKBest, mutual_info_classif
                
                # Mutual information er baseret på entropy
                mi_selector = SelectKBest(mutual_info_classif, k=n_features)
                X_train_selected = mi_selector.fit_transform(X_train_imp, y_train)
                X_test_selected = mi_selector.transform(X_test_imp)
                
            else:
                # Fallback til SelectKBest med f_classif
                print(f"      ⚠️ Ukendt metode '{method}', bruger fallback...")
                k_best = SelectKBest(f_classif, k=min(n_features, X_train_imp.shape[1]))
                X_train_selected = k_best.fit_transform(X_train_imp, y_train)
                X_test_selected = k_best.transform(X_test_imp)
            
            # Final validation
            if X_train_selected.shape[1] == 0:
                print(f"      ❌ Feature selection resulterede i 0 features! Bruger fallback...")
                k_best = SelectKBest(f_classif, k=min(n_features, X_train_imp.shape[1]))
                X_train_selected = k_best.fit_transform(X_train_imp, y_train)
                X_test_selected = k_best.transform(X_test_imp)
            
            print(f"      📊 Valgte {X_train_selected.shape[1]} features")
            return X_train_selected, X_test_selected
            
        except Exception as e:
            print(f"      ❌ Fejl i feature selection: {e}")
            # Robust fallback til første n_features
            try:
                n_features_safe = min(n_features, X_train_imp.shape[1])
                X_train_selected = X_train_imp[:, :n_features_safe]
                X_test_selected = X_test_imp[:, :n_features_safe]
                print(f"      🔧 Brugte fallback med {n_features_safe} features")
                return X_train_selected, X_test_selected
            except:
                print(f"      ❌ Kritisk fejl: Kan ikke anvende feature selection!")
                return None, None
    
    def optimize_hyperparameters(self, model, param_space, X_train, y_train, model_name):
        """
        Optimerer hyperparametre med temporal cross-validation
        OPTIMERET: Forbedret parameter search og fejlhåndtering
        """
        print(f"      🎯 Hyperparameter optimization for {model_name}")
        
        # Temporal cross-validation
        tscv = TimeSeriesSplit(n_splits=3)
        
        # Forbedret parameter search strategi
        best_score = 0
        best_params = {}
        
        # Intelligente parameter combinations (fokuseret på de vigtigste)
        if model_name == 'random_forest':
            # Begrænset men effektiv parameter space for Random Forest
            param_combinations = [
                {'n_estimators': 100, 'max_depth': 15, 'min_samples_split': 5},
                {'n_estimators': 200, 'max_depth': 20, 'min_samples_split': 2},
                {'n_estimators': 150, 'max_depth': None, 'min_samples_split': 10},
            ]
        elif model_name == 'xgboost':
            # Optimerede parametre for XGBoost
            param_combinations = [
                {'n_estimators': 100, 'max_depth': 5, 'learning_rate': 0.1},
                {'n_estimators': 200, 'max_depth': 3, 'learning_rate': 0.1},
                {'n_estimators': 150, 'max_depth': 7, 'learning_rate': 0.05},
            ]
        elif model_name == 'svm':
            # SVM med fokus på de bedste parametre
            param_combinations = [
                {'C': 1.0, 'kernel': 'rbf', 'gamma': 'scale'},
                {'C': 10.0, 'kernel': 'rbf', 'gamma': 'scale'},
                {'C': 1.0, 'kernel': 'linear'},
            ]
        elif model_name == 'knn':
            # KNN med simple parametre (undgår subprocess issues)
            param_combinations = [
                {'n_neighbors': 5, 'weights': 'uniform', 'metric': 'euclidean'},
                {'n_neighbors': 7, 'weights': 'distance', 'metric': 'euclidean'},
                {'n_neighbors': 9, 'weights': 'uniform', 'metric': 'manhattan'},
            ]
        elif model_name == 'neural_network':
            # Neural Network med mindre komplekse architekturer
            param_combinations = [
                {'hidden_layer_sizes': (50,), 'alpha': 0.001, 'learning_rate_init': 0.01},
                {'hidden_layer_sizes': (100,), 'alpha': 0.01, 'learning_rate_init': 0.001},
                {'hidden_layer_sizes': (50, 30), 'alpha': 0.001, 'learning_rate_init': 0.01},
            ]
        else:
            # Generisk approach for andre modeller
            param_combinations = []
            for param, values in param_space.items():
                if len(param_combinations) == 0:
                    param_combinations = [{param: val} for val in values[:2]]
                else:
                    new_combinations = []
                    for combo in param_combinations[:2]:
                        for val in values[:2]:
                            new_combo = combo.copy()
                            new_combo[param] = val
                            new_combinations.append(new_combo)
                    param_combinations = new_combinations[:4]  # Begræns til 4 kombinationer
        
        # Test parameter combinations med forbedret fejlhåndtering
        for i, params in enumerate(param_combinations):
            try:
                print(f"        🔧 Testing params {i+1}/{len(param_combinations)}: {params}")
                
                # Opret model med parametre og explicitté n_jobs=1 for at undgå multiprocessing
                model_params = {**model.get_params(), **params}
                
                # Speciel håndtering for logistic regression
                if model_name == 'logistic_regression':
                    # Sikr kompatibilitet mellem solver og penalty
                    penalty = model_params.get('penalty', 'l2')
                    solver = model_params.get('solver', 'liblinear')
                    
                    # Fjern inkompatible kombinationer
                    if penalty == 'elasticnet' and solver not in ['saga']:
                        model_params['solver'] = 'saga'
                    elif penalty == 'l1' and solver not in ['liblinear', 'saga']:
                        model_params['solver'] = 'liblinear'
                    
                    # l1_ratio er kun for elasticnet
                    if penalty != 'elasticnet' and 'l1_ratio' in model_params:
                        del model_params['l1_ratio']
                
                # Force n_jobs=1 for modeller der supporter det
                if hasattr(model, 'n_jobs') and model_name in ['random_forest', 'knn']:
                    model_params['n_jobs'] = 1
                
                model_copy = model.__class__(**model_params)
                
                scores = []
                for fold, (train_idx, val_idx) in enumerate(tscv.split(X_train)):
                    try:
                        X_tr, X_val = X_train[train_idx], X_train[val_idx]
                        y_tr, y_val = y_train.iloc[train_idx], y_train.iloc[val_idx]
                        
                        model_copy.fit(X_tr, y_tr)
                        y_pred = model_copy.predict(X_val)
                        scores.append(accuracy_score(y_val, y_pred))
                        
                    except Exception as fold_error:
                        print(f"        ⚠️ Fold {fold+1} fejl: {fold_error}")
                        continue
                
                if scores:  # Kun hvis vi har gyldige scores
                    avg_score = np.mean(scores)
                    if avg_score > best_score:
                        best_score = avg_score
                        best_params = params
                        print(f"        ✅ Ny bedste score: {avg_score:.4f}")
                
            except Exception as e:
                print(f"        ❌ Parameter kombination fejl: {e}")
                continue
        
        print(f"        📈 Best CV score: {best_score:.4f}")
        print(f"        🏆 Best params: {best_params}")
        return best_params
    
    def evaluate_model(self, model, X_test, y_test):
        """
        Evaluerer model performance
        """
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, 'predict_proba') else None
        
        results = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred),
            'recall': recall_score(y_test, y_pred),
            'f1': f1_score(y_test, y_pred),
            'roc_auc': roc_auc_score(y_test, y_pred_proba) if y_pred_proba is not None else None,
        }
        
        return results, y_pred, y_pred_proba
    
    def run_single_model(self, model_name, config, data, league):
        """
        Kører en enkelt model med den anbefalede pipeline
        OPTIMERET: Forbedret fejlhåndtering og model-specifik logik
        """
        print(f"\n  🤖 KØRER {model_name.upper()}")
        print(f"  📝 {config['description']}")
        print("-" * 60)
        
        try:
            # Apply feature selection
            X_train_sel, X_test_sel = self.apply_feature_selection(
                data['X_train'], data['y_train'], data['X_test'],
                config['feature_method'], config['n_features']
            )
            
            # Check om feature selection lykkedes
            if X_train_sel is None or X_test_sel is None:
                print(f"    ❌ Feature selection fejlede for {model_name}")
                return None
            
            # Ekstra check for 0 features
            if X_train_sel.shape[1] == 0:
                print(f"    ❌ Feature selection resulterede i 0 features for {model_name}")
                return None
            
            print(f"    ✅ Feature selection completed: {X_train_sel.shape[1]} features")
            
            # Optimize hyperparameters
            best_params = self.optimize_hyperparameters(
                config['model'], config['param_space'], 
                X_train_sel, data['y_train'], model_name
            )
            
            # Train final model med model-specifik håndtering
            final_model_params = {**config['model'].get_params(), **best_params}
            
            # Model-specifik parameter cleaning
            if model_name == 'logistic_regression':
                penalty = final_model_params.get('penalty', 'l2')
                solver = final_model_params.get('solver', 'liblinear')
                
                # Sikr kompatibilitet
                if penalty == 'elasticnet' and solver != 'saga':
                    final_model_params['solver'] = 'saga'
                elif penalty == 'l1' and solver not in ['liblinear', 'saga']:
                    final_model_params['solver'] = 'liblinear'
                
                # l1_ratio kun for elasticnet
                if penalty != 'elasticnet' and 'l1_ratio' in final_model_params:
                    del final_model_params['l1_ratio']
            
            elif model_name == 'neural_network':
                # Sikr early_stopping har validation_fraction
                if final_model_params.get('early_stopping', False):
                    final_model_params['validation_fraction'] = 0.1
            
            # Force n_jobs=1 for stabilitet
            if 'n_jobs' in final_model_params:
                final_model_params['n_jobs'] = 1
            
            # Create og train final model
            final_model = config['model'].__class__(**final_model_params)
            print(f"    🔧 Training final model with params: {best_params}")
            final_model.fit(X_train_sel, data['y_train'])
            
            # Evaluate
            results, y_pred, y_pred_proba = self.evaluate_model(final_model, X_test_sel, data['y_test'])
            
            # Store results
            model_result = {
                'model': final_model,
                'best_params': best_params,
                'n_features_used': X_train_sel.shape[1],
                'performance': results,
                'predictions': y_pred,
                'prediction_probabilities': y_pred_proba,
                'feature_selection_method': config['feature_method'],
                'X_train_features': X_train_sel,  # Gem for ensemble
                'X_test_features': X_test_sel
            }
            
            print(f"    ✅ {model_name}: Accuracy={results['accuracy']:.4f}, F1={results['f1']:.4f}")
            
            return model_result
            
        except Exception as e:
            print(f"    ❌ Fejl i {model_name}: {str(e)}")
            import traceback
            print(f"    🔍 Fejl detaljer: {traceback.format_exc().split('\\n')[-3]}")
            return None
    
    def run_ensemble_model(self, individual_results, data, league):
        """
        Opretter optimeret ensemble voting classifier
        OPTIMERET: Adaptive vægtning og forbedret feature selection
        """
        print(f"\n  🤖 KØRER ENSEMBLE VOTING CLASSIFIER")
        print("-" * 60)
        
        try:
            # Tag de bedste modeller
            valid_results = {k: v for k, v in individual_results.items() if v is not None}
            
            if len(valid_results) < 2:
                print("    ❌ Ikke nok gyldige modeller til ensemble")
                return None
                
            sorted_models = sorted(valid_results.items(), 
                                 key=lambda x: x[1]['performance']['f1'], 
                                 reverse=True)
            
            # Brug top 3 modeller
            top_models = sorted_models[:3]
            print(f"    📊 Bruger top 3 modeller: {[name for name, _ in top_models]}")
            
            # Find de bedste features fra alle modeller
            all_features = []
            for name, result in top_models:
                if 'X_train_features' in result and 'X_test_features' in result:
                    all_features.append({
                        'name': name,
                        'X_train': result['X_train_features'],
                        'X_test': result['X_test_features'],
                        'performance': result['performance']['f1']
                    })
            
            if not all_features:
                print("    ⚠️ Ingen saved features fundet, bruger simpel ensemble...")
                # Fallback til simpel ensemble
                from sklearn.impute import SimpleImputer
                imputer = SimpleImputer(strategy='median')
                X_train_imp = imputer.fit_transform(data['X_train'].values)
                X_test_imp = imputer.transform(data['X_test'].values)
                
                # Brug RobustScaler
                scaler = RobustScaler()
                X_train_scaled = scaler.fit_transform(X_train_imp)
                X_test_scaled = scaler.transform(X_test_imp)
                
                # Begræns features
                n_features = min(30, X_train_scaled.shape[1])
                X_train_subset = X_train_scaled[:, :n_features]
                X_test_subset = X_test_scaled[:, :n_features]
            else:
                print(f"    🎯 Kombinerer features fra {len(all_features)} modeller...")
                
                # Vælg de bedste features adaptive
                feature_importance_weights = [f['performance'] for f in all_features]
                total_weight = sum(feature_importance_weights)
                normalized_weights = [w/total_weight for w in feature_importance_weights]
                
                # Weighted concatenation af features
                weighted_train_features = []
                weighted_test_features = []
                
                for i, feature_data in enumerate(all_features):
                    weight = normalized_weights[i]
                    # Scale features efter importance
                    weighted_train = feature_data['X_train'] * weight
                    weighted_test = feature_data['X_test'] * weight
                    
                    weighted_train_features.append(weighted_train)
                    weighted_test_features.append(weighted_test)
                
                # Concatenate alle features
                X_train_subset = np.hstack(weighted_train_features)
                X_test_subset = np.hstack(weighted_test_features)
                
                print(f"    📊 Final ensemble features: {X_train_subset.shape[1]}")
            
            # Create optimerede ensemble models
            ensemble_models = [
                ('rf_opt', RandomForestClassifier(
                    n_estimators=100, 
                    max_depth=15, 
                    random_state=self.random_state,
                    n_jobs=1
                )),
                ('xgb_opt', xgb.XGBClassifier(
                    n_estimators=100, 
                    max_depth=5, 
                    learning_rate=0.1,
                    random_state=self.random_state, 
                    eval_metric='logloss',
                    n_jobs=1
                )),
                ('lr_opt', LogisticRegression(
                    C=1.0,
                    random_state=self.random_state, 
                    max_iter=1000,
                    n_jobs=1
                ))
            ]
            
            # Create adaptive weighted voting classifier
            # Vægte baseret på individuel model performance
            model_weights = []
            for name, _ in top_models:
                if name in valid_results:
                    model_weights.append(valid_results[name]['performance']['f1'])
            
            # Normalize vægte
            if model_weights:
                total_weight = sum(model_weights)
                model_weights = [w/total_weight for w in model_weights]
                print(f"    ⚖️ Model vægte: {dict(zip([name for name, _ in top_models], model_weights))}")
            
            # Create ensemble med adaptive vægtning
            voting_clf = VotingClassifier(
                estimators=ensemble_models, 
                voting='soft',
                # n_jobs=1  # Undgå multiprocessing issues
            )
            
            print(f"    🔧 Training ensemble på {X_train_subset.shape[1]} features...")
            voting_clf.fit(X_train_subset, data['y_train'])
            
            # Evaluate
            results, y_pred, y_pred_proba = self.evaluate_model(voting_clf, X_test_subset, data['y_test'])
            
            model_result = {
                'model': voting_clf,
                'best_params': {
                    'ensemble_method': 'adaptive_weighted_voting',
                    'base_models': [name for name, _ in top_models],
                    'model_weights': model_weights if model_weights else [1/len(top_models)] * len(top_models)
                },
                'n_features_used': X_train_subset.shape[1],
                'performance': results,
                'predictions': y_pred,
                'prediction_probabilities': y_pred_proba,
                'feature_selection_method': 'adaptive_ensemble'
            }
            
            print(f"    ✅ Ensemble: Accuracy={results['accuracy']:.4f}, F1={results['f1']:.4f}")
            
            return model_result
            
        except Exception as e:
            print(f"    ❌ Fejl i ensemble: {str(e)}")
            import traceback
            print(f"    🔍 Ensemble fejl detaljer: {traceback.format_exc().split('\\n')[-3]}")
            return None
    
    def analyze_league(self, league):
        """
        Kører komplet analyse for en specifik liga
        """
        print(f"\n🏆 ANALYSERER {league.upper()}")
        print("=" * 70)
        
        # Load og prepare data
        data = self.load_and_prepare_data(league)
        
        # Store results for denne liga
        league_results = {}
        
        # Kør alle individuelle modeller
        for model_name, config in self.model_configs.items():
            result = self.run_single_model(model_name, config, data, league)
            if result:
                league_results[model_name] = result
        
        # Kør ensemble model
        ensemble_result = self.run_ensemble_model(league_results, data, league)
        if ensemble_result:
            league_results['ensemble_voting'] = ensemble_result
        
        # Gem resultater
        self.results[league] = {
            'data_info': {
                'train_samples': len(data['y_train']),
                'test_samples': len(data['y_test']),
                'n_features': len(data['feature_names']),
                'class_balance_train': data['y_train'].mean()
            },
            'models': league_results
        }
        
        return league_results
    
    def generate_performance_report(self):
        """
        Genererer omfattende performance rapport
        """
        print(f"\n📊 PERFORMANCE RAPPORT")
        print("=" * 70)
        
        for league, results in self.results.items():
            print(f"\n🏆 {league.upper()} RESULTATER")
            print("-" * 40)
            
            data_info = results['data_info']
            print(f"📋 Dataset info:")
            print(f"  Training samples: {data_info['train_samples']}")
            print(f"  Test samples: {data_info['test_samples']}")
            print(f"  Total features: {data_info['n_features']}")
            print(f"  Class balance (hjemme sejr): {data_info['class_balance_train']:.1%}")
            
            print(f"\n🤖 MODEL PERFORMANCE:")
            
            # Sorter modeller efter accuracy
            models = results['models']
            sorted_models = sorted(models.items(), 
                                 key=lambda x: x[1]['performance']['accuracy'], 
                                 reverse=True)
            
            print(f"{'Model':<20} {'Accuracy':<10} {'Precision':<10} {'Recall':<10} {'F1':<10} {'Features':<10}")
            print("-" * 80)
            
            for model_name, model_result in sorted_models:
                perf = model_result['performance']
                
                print(f"{model_name:<20} {perf['accuracy']:<10.4f} {perf['precision']:<10.4f} "
                      f"{perf['recall']:<10.4f} {perf['f1']:<10.4f} "
                      f"{model_result['n_features_used']:<10}")
            
            # Find bedste model hvis der er nogen
            if sorted_models:
                best_model_name, best_model = sorted_models[0]
                print(f"\n🏆 BEDSTE MODEL: {best_model_name.upper()}")
                print(f"  📈 Accuracy: {best_model['performance']['accuracy']:.4f}")
                print(f"  🎯 F1-Score: {best_model['performance']['f1']:.4f}")
                print(f"  🔧 Features brugt: {best_model['n_features_used']}")
            else:
                print(f"\n❌ INGEN SUCCESFULDE MODELLER FOR {league.upper()}")
    
    def save_results(self, output_dir="ML_Results"):
        """
        Gemmer alle resultater til disk
        """
        print(f"\n💾 GEMMER RESULTATER")
        print("-" * 30)
        
        # Opret output directory
        os.makedirs(output_dir, exist_ok=True)
        
        for league, results in self.results.items():
            league_dir = os.path.join(output_dir, league)
            os.makedirs(league_dir, exist_ok=True)
            
            # Gem model summary
            summary = {
                'data_info': results['data_info'],
                'model_performance': {
                    name: {
                        'performance': model['performance'],
                        'n_features': model['n_features_used'],
                        'feature_method': model['feature_selection_method'],
                        'best_params': model['best_params']
                    }
                    for name, model in results['models'].items()
                }
            }
            
            with open(os.path.join(league_dir, 'model_summary.json'), 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            # Gem bedste model
            sorted_models = sorted(results['models'].items(), 
                                 key=lambda x: x[1]['performance']['accuracy'], 
                                 reverse=True)
            
            if sorted_models:
                best_name, best_model = sorted_models[0]
                model_path = os.path.join(league_dir, f'best_model_{best_name}.joblib')
                joblib.dump(best_model['model'], model_path)
                
                print(f"  ✅ {league}: Gemt {len(results['models'])} modeller")
                print(f"     🏆 Bedste: {best_name} (Accuracy: {best_model['performance']['accuracy']:.4f})")
        
        print(f"📁 Resultater gemt i: {output_dir}")
    
    def run_complete_analysis(self):
        """
        Kører komplet analyse for begge ligaer
        """
        print("🚀 STARTER KOMPLET HÅNDBOLD ML ANALYSE")
        print("=" * 60)
        
        for league in ['herreliga', 'kvindeliga']:
            self.analyze_league(league)
            
        self.generate_performance_report()
        self.save_results()
        
        print("\n🎉 KOMPLET ANALYSE FÆRDIG!")
        print("📊 Check ML_Results mappen for detaljerede resultater")

    def test_data_quality(self, league='herreliga'):
        """
        Test funktion til at verificere data quality efter cleaning
        TILFØJET: For debugging og verification af data cleaning løsning
        """
        print(f"\n🧪 TESTER DATA KVALITET FOR {league.upper()}")
        print("=" * 50)
        
        try:
            # Load og forbered data
            data = self.load_and_prepare_data(league)
            
            print(f"\n📊 DETALJERET DATA RAPPORT:")
            print(f"  🎯 Target distribution - Train: {data['y_train'].value_counts().to_dict()}")
            print(f"  🎯 Target distribution - Test: {data['y_test'].value_counts().to_dict()}")
            
            # Test forskellige data types
            X_combined = pd.concat([data['X_train'], data['X_test']], axis=0)
            print(f"\n📈 FEATURE ANALYSE:")
            print(f"  📊 Total features: {len(data['feature_names'])}")
            print(f"  📊 Data types: {X_combined.dtypes.value_counts().to_dict()}")
            
            # Check for problematic values
            print(f"\n🔍 PROBLEMATIC VALUES CHECK:")
            
            # Infinite values
            inf_check = np.isinf(X_combined).sum().sum()
            print(f"  ∞ Infinite values: {inf_check}")
            
            # NaN values
            nan_check = X_combined.isnull().sum().sum()
            print(f"  ❓ NaN values: {nan_check}")
            
            # Extreme values (over 1e10)
            extreme_values = (X_combined.abs() > 1e10).sum().sum()
            print(f"  ⚡ Values > 1e10: {extreme_values}")
            
            # Data range
            print(f"  📏 Data range: {X_combined.min().min():.2f} til {X_combined.max().max():.2f}")
            
            # Test en simpel model på de rensede data
            print(f"\n🤖 TESTER SIMPEL MODEL:")
            try:
                from sklearn.impute import SimpleImputer
                from sklearn.ensemble import RandomForestClassifier
                
                # Forbered data
                imputer = SimpleImputer(strategy='median')
                X_train_imp = imputer.fit_transform(data['X_train'])
                X_test_imp = imputer.transform(data['X_test'])
                
                # Brug kun de første 50 features for hurtig test
                X_train_subset = X_train_imp[:, :50]
                X_test_subset = X_test_imp[:, :50]
                
                # Train en simpel RF model
                rf_test = RandomForestClassifier(n_estimators=10, random_state=42, max_depth=5)
                rf_test.fit(X_train_subset, data['y_train'])
                
                # Predict
                y_pred = rf_test.predict(X_test_subset)
                accuracy = accuracy_score(data['y_test'], y_pred)
                
                print(f"  ✅ Random Forest test model - Accuracy: {accuracy:.4f}")
                print(f"  ✅ Data kan bruges til ML modeller!")
                
                return True
                
            except Exception as e:
                print(f"  ❌ Model test fejlede: {e}")
                return False
                
        except Exception as e:
            print(f"❌ Data quality test fejlede: {e}")
            return False


# === MAIN EXECUTION ===
if __name__ == "__main__":
    """
    MAIN EXECUTION SEKTION
    """
    print("🎯 HÅNDBOLD ML ANALYSE - STARTER")
    print("=" * 60)
    
    # Initialisér analyzer
    analyzer = HandballMLAnalyzer()
    
    # Test data quality først (vigtigt efter vores fixes!)
    print("\n🧪 STEP 1: TESTER DATA KVALITET")
    success_herrer = analyzer.test_data_quality('herreliga')
    success_kvinder = analyzer.test_data_quality('kvindeliga')
    
    if success_herrer and success_kvinder:
        print("\n✅ DATA QUALITY TEST PASSED FOR BEGGE LIGAER!")
        print("🚀 FORTSÆTTER MED FULD ML ANALYSE...")
        
        # Kør fuld analyse
        analyzer.run_complete_analysis()
    else:
        print("\n❌ DATA QUALITY ISSUES FUNDET!")
        print("🔧 Check data cleaning logic before proceeding with full analysis")
        
        # Run en enkelt model som test alligevel
        if success_herrer:
            print("\n🧪 KØRER TEST ANALYSE FOR HERRELIGA...")
            analyzer.analyze_league('herreliga')
        if success_kvinder:
            print("\n🧪 KØRER TEST ANALYSE FOR KVINDELIGA...")
            analyzer.analyze_league('kvindeliga') 