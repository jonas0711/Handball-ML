#!/usr/bin/env python3
"""
HÅNDBOL ML MODEL PIPELINE
========================

Dette script implementerer 10 forskellige ML modeller til forudsigelse af håndboldkamp vindere.
Inkluderer temporal cross-validation og feature selection for hver model.

KRITISK: Temporal awareness for at undgå data leakage!
"""

import pandas as pd
import numpy as np
import os
import warnings
from datetime import datetime
from typing import Dict, List, Tuple, Any
import pickle

# ML Libraries
from sklearn.model_selection import TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.feature_selection import (
    SelectKBest, chi2, f_classif, RFE, SelectFromModel,
    VarianceThreshold, mutual_info_classif
)
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.tree import DecisionTreeClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)

# Advanced ML
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    print("⚠️  XGBoost ikke tilgængelig - installer med: pip install xgboost")
    XGBOOST_AVAILABLE = False

try:
    from catboost import CatBoostClassifier
    CATBOOST_AVAILABLE = True
except ImportError:
    print("⚠️  CatBoost ikke tilgængelig - installer med: pip install catboost")
    CATBOOST_AVAILABLE = False

# Visualization
import matplotlib.pyplot as plt
import seaborn as sns

warnings.filterwarnings('ignore')

class HandballMLPipeline:
    """
    Komplet ML pipeline til håndbold kampforudsigelse
    """
    
    def __init__(self, data_path: str = None, league: str = "Herreliga"):
        """
        Initialiserer ML pipeline
        
        Args:
            data_path: Sti til ML dataset CSV fil
            league: "Herreliga" eller "Kvindeliga"
        """
        print(f"🎯 INITIALISERER HÅNDBOL ML PIPELINE - {league}")
        print("=" * 60)
        
        self.league = league
        self.data_path = data_path
        
        # Data containers
        self.raw_data = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        self.feature_names = None
        
        # Model containers
        self.models = {}
        self.model_results = {}
        self.feature_selections = {}
        
        # Scaler
        self.scaler = StandardScaler()
        
        # Output directory
        self.output_dir = f"ML_Results_{league}"
        os.makedirs(self.output_dir, exist_ok=True)
        
    def load_and_prepare_data(self):
        """
        Loader og forbereder data med temporal split
        KRITISK: Temporal awareness for at undgå data leakage
        """
        print("\n📂 LOADER OG FORBEREDER DATA")
        print("-" * 40)
        
        # Auto-detect data path hvis ikke specificeret
        if self.data_path is None:
            possible_paths = [
                f"ML_Datasets/{self.league.lower()}_handball_ml_dataset.csv",
                f"ML_Datasets/handball_ml_dataset.csv",
                f"{self.league.lower()}_handball_ml_dataset.csv"
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    self.data_path = path
                    break
            
            if self.data_path is None:
                raise FileNotFoundError(f"Kunne ikke finde dataset for {self.league}")
        
        # Load data
        print(f"📁 Loader data fra: {self.data_path}")
        self.raw_data = pd.read_csv(self.data_path)
        print(f"📊 Data shape: {self.raw_data.shape}")
        
        # Valider data struktur
        if 'season' not in self.raw_data.columns:
            raise ValueError("Dataset mangler 'season' kolonne for temporal split")
        
        if 'target_home_win' not in self.raw_data.columns:
            raise ValueError("Dataset mangler 'target_home_win' target variable")
        
        # Temporal split baseret på sæson
        print("\n🕐 IMPLEMENTERER TEMPORAL SPLIT")
        
        if self.league == "Herreliga":
            # Træning: 2017-2018 til 2023-2024, Test: 2024-2025
            train_seasons = [
                "2017-2018", "2018-2019", "2019-2020", "2020-2021",
                "2021-2022", "2022-2023", "2023-2024"
            ]
            test_seasons = ["2024-2025"]
        else:  # Kvindeliga
            # Træning: 2018-2019 til 2023-2024, Test: 2024-2025
            train_seasons = [
                "2018-2019", "2019-2020", "2020-2021",
                "2021-2022", "2022-2023", "2023-2024"
            ]
            test_seasons = ["2024-2025"]
        
        # Split data
        train_data = self.raw_data[self.raw_data['season'].isin(train_seasons)]
        test_data = self.raw_data[self.raw_data['season'].isin(test_seasons)]
        
        print(f"📈 Træningsdata: {len(train_data)} kampe ({len(train_seasons)} sæsoner)")
        print(f"📉 Testdata: {len(test_data)} kampe ({len(test_seasons)} sæsoner)")
        
        if len(test_data) == 0:
            print("⚠️  ADVARSEL: Ingen testdata fundet - bruger sidste 20% af træningsdata")
            split_idx = int(len(train_data) * 0.8)
            test_data = train_data.iloc[split_idx:]
            train_data = train_data.iloc[:split_idx]
        
        # Prepare features og targets
        print("\n🎯 FORBEREDER FEATURES OG TARGETS")
        
        # Identificer metadata kolonner der skal ekskluderes
        metadata_cols = [
            'kamp_id', 'season', 'match_date', 'home_team', 'away_team', 
            'venue', 'league'
        ]
        
        # Identificer target kolonner
        target_cols = [col for col in self.raw_data.columns if col.startswith('target_')]
        
        # Feature kolonner = alt andet
        feature_cols = [
            col for col in self.raw_data.columns 
            if col not in metadata_cols + target_cols
        ]
        
        print(f"📋 Features: {len(feature_cols)}")
        print(f"🎯 Targets: {len(target_cols)}")
        print(f"📝 Metadata: {len(metadata_cols)}")
        
        # Extract features og target
        self.X_train = train_data[feature_cols]
        self.X_test = test_data[feature_cols]
        self.y_train = train_data['target_home_win']
        self.y_test = test_data['target_home_win']
        self.feature_names = feature_cols
        
        # Håndter missing values
        print("\n🔧 HÅNDTERER MISSING VALUES")
        
        # Median imputation for numeriske features
        numeric_features = self.X_train.select_dtypes(include=[np.number]).columns
        for col in numeric_features:
            median_val = self.X_train[col].median()
            self.X_train[col].fillna(median_val, inplace=True)
            self.X_test[col].fillna(median_val, inplace=True)
        
        # Mode imputation for kategoriske features
        categorical_features = self.X_train.select_dtypes(exclude=[np.number]).columns
        for col in categorical_features:
            mode_val = self.X_train[col].mode()[0] if len(self.X_train[col].mode()) > 0 else 'unknown'
            self.X_train[col].fillna(mode_val, inplace=True)
            self.X_test[col].fillna(mode_val, inplace=True)
        
        # 🔧 KONVERTER KATEGORISKE DATA TIL NUMERISKE VÆRDIER
        print("\n🔧 KONVERTERER KATEGORISKE DATA")
        
        # Convert boolean features to 0/1
        bool_features = self.X_train.select_dtypes(include=['bool']).columns
        for col in bool_features:
            print(f"   Converting boolean: {col}")
            self.X_train[col] = self.X_train[col].astype(int)
            self.X_test[col] = self.X_test[col].astype(int)
        
        # Handle remaining categorical features
        categorical_features = self.X_train.select_dtypes(include=['object']).columns
        print(f"   Found {len(categorical_features)} object columns to handle")
        
        # Remove or encode categorical features that shouldn't be in features
        for col in categorical_features:
            unique_vals = self.X_train[col].nunique()
            print(f"   Checking {col}: {unique_vals} unique values")
            
            # If too many unique values, likely an ID or text field - remove it
            if unique_vals > 50:
                print(f"     Removing {col} (too many unique values: {unique_vals})")
                self.X_train = self.X_train.drop(columns=[col])
                self.X_test = self.X_test.drop(columns=[col])
                self.feature_names.remove(col)
            else:
                # Label encode categorical features with few unique values
                from sklearn.preprocessing import LabelEncoder
                print(f"     Label encoding {col}")
                le = LabelEncoder()
                
                # Fit on training data
                self.X_train[col] = le.fit_transform(self.X_train[col].astype(str))
                
                # Handle test data with unseen labels
                test_col_str = self.X_test[col].astype(str)
                
                # For any unseen labels in test, replace with most common training label
                unseen_mask = ~test_col_str.isin(le.classes_)
                if unseen_mask.any():
                    most_common_label = self.X_train[col].mode().iloc[0] if len(self.X_train[col].mode()) > 0 else 0
                    print(f"       Found {unseen_mask.sum()} unseen labels in test - replacing with {most_common_label}")
                    test_col_str.loc[unseen_mask] = le.inverse_transform([most_common_label])[0]
                
                self.X_test[col] = le.transform(test_col_str)
        
        # Ensure all features are numeric
        print(f"   Final check: All columns numeric? {self.X_train.dtypes.apply(lambda x: np.issubdtype(x, np.number)).all()}")
        
        # 🔧 KRITISK DATA CLEANING - HÅNDTERING AF EKSTREME VÆRDIER
        print(f"\n🔧 DATA CLEANING - HÅNDTERING AF EKSTREME VÆRDIER:")
        
        # 1. Check for infinite values (dette var problemet!)
        print("  🔍 Checker for uendelige værdier...")
        inf_counts_train = np.isinf(self.X_train).sum()
        inf_counts_test = np.isinf(self.X_test).sum()
        total_inf = inf_counts_train.sum() + inf_counts_test.sum()
        if total_inf > 0:
            print(f"    ⚠️  Fundet {total_inf} uendelige værdier")
            # Replace infinite values med NaN så de kan håndteres
            self.X_train.replace([np.inf, -np.inf], np.nan, inplace=True)
            self.X_test.replace([np.inf, -np.inf], np.nan, inplace=True)
            print("    ✅ Uendelige værdier erstattet med NaN")
        else:
            print("    ✅ Ingen uendelige værdier fundet")
        
        # 2. Check for extremely large values (over 99.9th percentile)
        print("  🔍 Checker for ekstreme værdier...")
        for col in self.X_train.columns:
            if self.X_train[col].dtype in ['float64', 'int64', 'float32']:
                # Beregn percentiler for at identificere outliers
                q999 = self.X_train[col].quantile(0.999)
                q001 = self.X_train[col].quantile(0.001)
                
                # Cap ekstreme værdier til 99.9th percentile
                extreme_high_train = self.X_train[col] > q999
                extreme_low_train = self.X_train[col] < q001
                extreme_high_test = self.X_test[col] > q999
                extreme_low_test = self.X_test[col] < q001
                
                if extreme_high_train.sum() > 0:
                    print(f"    🔧 Capping {extreme_high_train.sum()} høje outliers i {col}")
                    self.X_train.loc[extreme_high_train, col] = q999
                
                if extreme_low_train.sum() > 0:
                    print(f"    🔧 Capping {extreme_low_train.sum()} lave outliers i {col}")
                    self.X_train.loc[extreme_low_train, col] = q001
                    
                if extreme_high_test.sum() > 0:
                    print(f"    🔧 Capping {extreme_high_test.sum()} høje outliers i test {col}")
                    self.X_test.loc[extreme_high_test, col] = q999
                
                if extreme_low_test.sum() > 0:
                    print(f"    🔧 Capping {extreme_low_test.sum()} lave outliers i test {col}")
                    self.X_test.loc[extreme_low_test, col] = q001
        
        # 3. Handle NaN values (fra tidligere infinite replacement)
        print("  🔍 Håndtering af NaN værdier...")
        nan_counts_train = self.X_train.isnull().sum()
        nan_counts_test = self.X_test.isnull().sum()
        total_nans = nan_counts_train.sum() + nan_counts_test.sum()
        if total_nans > 0:
            print(f"    📋 Fundet {total_nans} NaN værdier")
            # Use median imputation for robust handling
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
            print("    ✅ NaN værdier udfyldt med median imputation")
        
        # 4. Final validation
        print("  🔍 Final validation...")
        inf_final_train = np.isinf(self.X_train).sum().sum()
        inf_final_test = np.isinf(self.X_test).sum().sum()
        nan_final_train = self.X_train.isnull().sum().sum()
        nan_final_test = self.X_test.isnull().sum().sum()
        
        if inf_final_train > 0 or inf_final_test > 0 or nan_final_train > 0 or nan_final_test > 0:
            print(f"    ⚠️ Stadig problemer: {inf_final_train + inf_final_test} inf, {nan_final_train + nan_final_test} NaN værdier")
            # Emergency cleanup
            self.X_train.replace([np.inf, -np.inf], np.nan, inplace=True)
            self.X_test.replace([np.inf, -np.inf], np.nan, inplace=True)
            self.X_train.fillna(self.X_train.median(), inplace=True)
            self.X_test.fillna(self.X_test.median(), inplace=True)
        else:
            print("    ✅ Alle ekstreme værdier håndteret succesfuldt!")
        
        print(f"  📊 Features efter cleaning: {len(self.X_train.columns)}")
        
        # Print class distribution
        print(f"\n📊 CLASS DISTRIBUTION:")
        print(f"  Hjemme vinder: {self.y_train.sum()} ({self.y_train.mean():.1%})")
        print(f"  Ikke hjemme vinder: {len(self.y_train) - self.y_train.sum()} ({1-self.y_train.mean():.1%})")
        
        print("✅ Data forberedt og klar til model træning")
        
    def initial_feature_selection(self, max_features: int = 100):
        """
        Initial feature selection for at reducere fra 200+ til omkring 100 features
        """
        print(f"\n🎛️  INITIAL FEATURE SELECTION ({len(self.feature_names)} → {max_features})")
        print("-" * 50)
        
        original_features = self.X_train.copy()
        
        # 1. Variance Threshold - fjern features med lav varians
        print("1️⃣  Variance Threshold...")
        variance_selector = VarianceThreshold(threshold=0.01)
        X_var = variance_selector.fit_transform(self.X_train)
        var_features = self.X_train.columns[variance_selector.get_support()]
        print(f"   Beholdt {len(var_features)} features efter variance filtering")
        
        # 2. Correlation Analysis - fjern højt korrelerede features
        print("2️⃣  Correlation Analysis...")
        X_var_df = pd.DataFrame(X_var, columns=var_features)
        corr_matrix = X_var_df.corr().abs()
        
        # Find højt korrelerede par
        high_corr_pairs = []
        for i in range(len(corr_matrix.columns)):
            for j in range(i+1, len(corr_matrix.columns)):
                if corr_matrix.iloc[i, j] > 0.95:
                    high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j]))
        
        # Fjern en fra hvert højt korreleret par
        features_to_remove = set()
        for feat1, feat2 in high_corr_pairs:
            # Behold ELO features hvis muligt
            if 'elo_' in feat1 and 'elo_' not in feat2:
                features_to_remove.add(feat2)
            elif 'elo_' in feat2 and 'elo_' not in feat1:
                features_to_remove.add(feat1)
            else:
                features_to_remove.add(feat2)  # Arbitrært valg
        
        correlation_features = [f for f in var_features if f not in features_to_remove]
        print(f"   Fjernede {len(features_to_remove)} højt korrelerede features")
        print(f"   Beholdt {len(correlation_features)} features")
        
        # 3. Univariate Selection baseret på mutual information
        print("3️⃣  Mutual Information Selection...")
        X_corr = X_var_df[correlation_features]
        
        # Sikr at vi ikke vælger flere features end vi har
        k_features = min(max_features, len(correlation_features))
        
        mi_selector = SelectKBest(score_func=mutual_info_classif, k=k_features)
        X_final = mi_selector.fit_transform(X_corr, self.y_train)
        final_features = np.array(correlation_features)[mi_selector.get_support()].tolist()
        
        print(f"   Valgte top {len(final_features)} features baseret på mutual information")
        
        # Opdater trænings- og testdata
        self.X_train = pd.DataFrame(
            mi_selector.transform(X_corr),
            columns=final_features
        )
        
        self.X_test = pd.DataFrame(
            mi_selector.transform(
                pd.DataFrame(
                    variance_selector.transform(self.X_test),
                    columns=var_features
                )[correlation_features]
            ),
            columns=final_features
        )
        
        self.feature_names = list(final_features)
        
        # Gem feature selection info
        self.feature_selections['initial'] = {
            'variance_features': list(var_features),
            'correlation_features': correlation_features,
            'final_features': list(final_features),
            'removed_correlated': list(features_to_remove)
        }
        
        print(f"✅ INITIAL SELECTION KOMPLET: {len(self.feature_names)} features")
        
        # Print feature kategorier
        print(f"\n📋 FEATURE KATEGORIER:")
        categories = {
            'ELO Features': len([f for f in self.feature_names if 'elo_' in f]),
            'Team Stats': len([f for f in self.feature_names if f.startswith(('home_', 'away_')) and 'elo_' not in f]),
            'Positional': len([f for f in self.feature_names if 'pos_' in f]),
            'H2H': len([f for f in self.feature_names if 'h2h_' in f]),
            'Temporal': len([f for f in self.feature_names if f in ['day_of_week', 'month', 'is_weekend']]),
            'Other': len([f for f in self.feature_names if not any([
                'elo_' in f, f.startswith(('home_', 'away_')), 'pos_' in f, 'h2h_' in f, 
                f in ['day_of_week', 'month', 'is_weekend']
            ])])
        }
        
        for cat, count in categories.items():
            if count > 0:
                print(f"  {cat}: {count}")
                
    def setup_temporal_cv(self, n_splits: int = 5):
        """
        Setup temporal cross-validation for model evaluation
        KRITISK: Temporal aware CV for at undgå data leakage
        """
        print(f"\n⏰ SETUP TEMPORAL CROSS-VALIDATION ({n_splits} splits)")
        print("-" * 50)
        
        # TimeSeriesSplit sikrer at træning altid kommer før validation
        self.cv = TimeSeriesSplit(n_splits=n_splits)
        
        print("✅ Temporal CV konfigureret - træning kommer altid før validation")
        
    def train_model_1_logistic_regression(self):
        """
        Model 1: Logistic Regression med L1 regularization
        Bruger kun de vigtigste 20 features for simplicitet
        """
        print("\n1️⃣  LOGISTIC REGRESSION")
        print("-" * 30)
        
        # Feature selection: L1 regularization + top K
        print("🎛️  Feature Selection: L1 Regularization + SelectKBest...")
        
        # Først L1 for automatisk feature selection
        l1_selector = SelectFromModel(
            LogisticRegression(penalty='l1', solver='liblinear', random_state=42),
            max_features=25
        )
        l1_selector.fit(self.X_train, self.y_train)
        
        # Derefter vælg top 20 af de resterende
        k_selector = SelectKBest(score_func=f_classif, k=20)
        selected_features = l1_selector.transform(self.X_train)
        k_selector.fit(selected_features, self.y_train)
        
        # Kombiner selections
        X_train_selected = k_selector.transform(selected_features)
        X_test_selected = k_selector.transform(l1_selector.transform(self.X_test))
        
        # Træn model
        model = LogisticRegression(
            penalty='l2',  # L2 for final model
            random_state=42,
            max_iter=1000,
            solver='lbfgs'
        )
        
        model.fit(X_train_selected, self.y_train)
        
        # Evaluér
        y_pred = model.predict(X_test_selected)
        y_prob = model.predict_proba(X_test_selected)[:, 1]
        
        results = self._evaluate_model(y_pred, y_prob, "Logistic Regression")
        
        # Gem
        self.models['logistic'] = {
            'model': model,
            'l1_selector': l1_selector,
            'k_selector': k_selector,
            'n_features': X_train_selected.shape[1]
        }
        self.model_results['logistic'] = results
        
        print(f"✅ Logistic Regression: {results['accuracy']:.3f} accuracy med {X_train_selected.shape[1]} features")
        
    def train_model_2_random_forest(self):
        """
        Model 2: Random Forest med built-in feature importance
        Bruger omkring 40 features
        """
        print("\n2️⃣  RANDOM FOREST")
        print("-" * 30)
        
        # Feature selection: Random Forest feature importance
        print("🎛️  Feature Selection: Random Forest Feature Importance...")
        
        # Træn initial RF for feature importance
        rf_selector = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
            n_jobs=-1
        )
        rf_selector.fit(self.X_train, self.y_train)
        
        # Vælg top 40 features
        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': rf_selector.feature_importances_
        }).sort_values('importance', ascending=False)
        
        top_features = feature_importance.head(40)['feature'].tolist()
        
        X_train_selected = self.X_train[top_features]
        X_test_selected = self.X_test[top_features]
        
        # Træn final model
        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train_selected, self.y_train)
        
        # Evaluér
        y_pred = model.predict(X_test_selected)
        y_prob = model.predict_proba(X_test_selected)[:, 1]
        
        results = self._evaluate_model(y_pred, y_prob, "Random Forest")
        results['feature_importance'] = feature_importance.head(20).to_dict('records')
        
        # Gem
        self.models['random_forest'] = {
            'model': model,
            'selected_features': top_features,
            'n_features': len(top_features)
        }
        self.model_results['random_forest'] = results
        
        print(f"✅ Random Forest: {results['accuracy']:.3f} accuracy med {len(top_features)} features")
        
    def train_model_3_xgboost(self):
        """
        Model 3: XGBoost med permutation importance
        Bruger omkring 50 features
        """
        print("\n3️⃣  XGBOOST")
        print("-" * 30)
        
        if not XGBOOST_AVAILABLE:
            print("❌ XGBoost ikke tilgængelig - springer over")
            return
        
        # Feature selection: XGBoost feature importance
        print("🎛️  Feature Selection: XGBoost Feature Importance...")
        
        # Træn initial XGBoost for feature importance
        xgb_selector = xgb.XGBClassifier(
            n_estimators=100,
            random_state=42,
            eval_metric='logloss'
        )
        xgb_selector.fit(self.X_train, self.y_train)
        
        # Vælg top 50 features
        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': xgb_selector.feature_importances_
        }).sort_values('importance', ascending=False)
        
        top_features = feature_importance.head(50)['feature'].tolist()
        
        X_train_selected = self.X_train[top_features]
        X_test_selected = self.X_test[top_features]
        
        # Træn final model med tuning
        model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42,
            eval_metric='logloss'
        )
        
        model.fit(X_train_selected, self.y_train)
        
        # Evaluér
        y_pred = model.predict(X_test_selected)
        y_prob = model.predict_proba(X_test_selected)[:, 1]
        
        results = self._evaluate_model(y_pred, y_prob, "XGBoost")
        results['feature_importance'] = feature_importance.head(20).to_dict('records')
        
        # Gem
        self.models['xgboost'] = {
            'model': model,
            'selected_features': top_features,
            'n_features': len(top_features)
        }
        self.model_results['xgboost'] = results
        
        print(f"✅ XGBoost: {results['accuracy']:.3f} accuracy med {len(top_features)} features")
        
    def train_model_4_svm(self):
        """
        Model 4: Support Vector Machine med PCA
        Bruger omkring 30 features efter dimensionality reduction
        """
        print("\n4️⃣  SUPPORT VECTOR MACHINE")
        print("-" * 30)
        
        from sklearn.decomposition import PCA
        
        # Feature selection: PCA + SelectKBest
        print("🎛️  Feature Selection: PCA + SelectKBest...")
        
        # Først standardiser data (vigtigt for SVM og PCA)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(self.X_train)
        X_test_scaled = scaler.transform(self.X_test)
        
        # PCA for dimensionality reduction
        pca = PCA(n_components=30, random_state=42)
        X_train_pca = pca.fit_transform(X_train_scaled)
        X_test_pca = pca.transform(X_test_scaled)
        
        # Træn SVM
        model = SVC(
            kernel='rbf',
            C=1.0,
            gamma='scale',
            probability=True,  # For probability estimates
            random_state=42
        )
        
        model.fit(X_train_pca, self.y_train)
        
        # Evaluér
        y_pred = model.predict(X_test_pca)
        y_prob = model.predict_proba(X_test_pca)[:, 1]
        
        results = self._evaluate_model(y_pred, y_prob, "SVM")
        results['explained_variance'] = pca.explained_variance_ratio_.sum()
        
        # Gem
        self.models['svm'] = {
            'model': model,
            'scaler': scaler,
            'pca': pca,
            'n_features': 30
        }
        self.model_results['svm'] = results
        
        print(f"✅ SVM: {results['accuracy']:.3f} accuracy med PCA ({results['explained_variance']:.1%} variance)")
        
    def train_model_5_neural_network(self):
        """
        Model 5: Neural Network med dropout regularization
        Bruger omkring 60 features
        """
        print("\n5️⃣  NEURAL NETWORK")
        print("-" * 30)
        
        # Feature selection: Variance + Mutual Information
        print("🎛️  Feature Selection: Variance + Mutual Information...")
        
        # Vælg 60 features baseret på mutual information
        mi_selector = SelectKBest(score_func=mutual_info_classif, k=60)
        X_train_selected = mi_selector.fit_transform(self.X_train, self.y_train)
        X_test_selected = mi_selector.transform(self.X_test)
        
        # Standardiser (vigtigt for neural networks)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_selected)
        X_test_scaled = scaler.transform(X_test_selected)
        
        # Træn Neural Network
        model = MLPClassifier(
            hidden_layer_sizes=(100, 50),
            activation='relu',
            solver='adam',
            alpha=0.01,  # L2 regularization
            learning_rate='adaptive',
            max_iter=500,
            early_stopping=True,
            validation_fraction=0.1,
            random_state=42
        )
        
        model.fit(X_train_scaled, self.y_train)
        
        # Evaluér
        y_pred = model.predict(X_test_scaled)
        y_prob = model.predict_proba(X_test_scaled)[:, 1]
        
        results = self._evaluate_model(y_pred, y_prob, "Neural Network")
        results['n_iterations'] = model.n_iter_
        
        # Gem
        selected_features = [self.feature_names[i] for i in mi_selector.get_support(indices=True)]
        self.models['neural_network'] = {
            'model': model,
            'mi_selector': mi_selector,
            'scaler': scaler,
            'selected_features': selected_features,
            'n_features': 60
        }
        self.model_results['neural_network'] = results
        
        print(f"✅ Neural Network: {results['accuracy']:.3f} accuracy med {60} features")
        
    def train_model_6_knn(self):
        """
        Model 6: K-Nearest Neighbors med distance-based selection
        Bruger kun 15 features for at undgå curse of dimensionality
        """
        print("\n6️⃣  K-NEAREST NEIGHBORS")
        print("-" * 30)
        
        # Feature selection: SelectKBest med få features
        print("🎛️  Feature Selection: SelectKBest (15 features)...")
        
        # Vælg kun 15 features for at undgå curse of dimensionality
        k_selector = SelectKBest(score_func=f_classif, k=15)
        X_train_selected = k_selector.fit_transform(self.X_train, self.y_train)
        X_test_selected = k_selector.transform(self.X_test)
        
        # Standardiser (vigtigt for distance-based algorithms)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train_selected)
        X_test_scaled = scaler.transform(X_test_selected)
        
        # Træn KNN
        model = KNeighborsClassifier(
            n_neighbors=7,
            weights='distance',
            metric='euclidean'
        )
        
        model.fit(X_train_scaled, self.y_train)
        
        # Evaluér
        y_pred = model.predict(X_test_scaled)
        y_prob = model.predict_proba(X_test_scaled)[:, 1]
        
        results = self._evaluate_model(y_pred, y_prob, "K-NN")
        
        # Gem
        selected_features = [self.feature_names[i] for i in k_selector.get_support(indices=True)]
        self.models['knn'] = {
            'model': model,
            'k_selector': k_selector,
            'scaler': scaler,
            'selected_features': selected_features,
            'n_features': 15
        }
        self.model_results['knn'] = results
        
        print(f"✅ K-NN: {results['accuracy']:.3f} accuracy med {15} features")
        
    def train_model_7_naive_bayes(self):
        """
        Model 7: Naive Bayes med Chi-square feature selection
        Bruger omkring 25 features
        """
        print("\n7️⃣  NAIVE BAYES")
        print("-" * 30)
        
        # Feature selection: Chi-square test
        print("🎛️  Feature Selection: Chi-square test...")
        
        # Sikr at alle features er positive for chi-square (add constant hvis nødvendigt)
        X_train_positive = self.X_train - self.X_train.min() + 1
        X_test_positive = self.X_test - self.X_test.min() + 1
        
        # Chi-square feature selection
        chi2_selector = SelectKBest(score_func=chi2, k=25)
        X_train_selected = chi2_selector.fit_transform(X_train_positive, self.y_train)
        X_test_selected = chi2_selector.transform(X_test_positive)
        
        # Træn Naive Bayes
        model = GaussianNB()
        model.fit(X_train_selected, self.y_train)
        
        # Evaluér
        y_pred = model.predict(X_test_selected)
        y_prob = model.predict_proba(X_test_selected)[:, 1]
        
        results = self._evaluate_model(y_pred, y_prob, "Naive Bayes")
        
        # Gem
        selected_features = [self.feature_names[i] for i in chi2_selector.get_support(indices=True)]
        self.models['naive_bayes'] = {
            'model': model,
            'chi2_selector': chi2_selector,
            'selected_features': selected_features,
            'n_features': 25
        }
        self.model_results['naive_bayes'] = results
        
        print(f"✅ Naive Bayes: {results['accuracy']:.3f} accuracy med {25} features")
        
    def train_model_8_decision_tree(self):
        """
        Model 8: Decision Tree med entropy-based selection
        Bruger omkring 15 features for at undgå overfitting
        """
        print("\n8️⃣  DECISION TREE")
        print("-" * 30)
        
        # Feature selection: Entropy-based + tree feature importance
        print("🎛️  Feature Selection: Entropy-based selection...")
        
        # Vælg 15 features baseret på mutual information (entropy-based)
        mi_selector = SelectKBest(score_func=mutual_info_classif, k=15)
        X_train_selected = mi_selector.fit_transform(self.X_train, self.y_train)
        X_test_selected = mi_selector.transform(self.X_test)
        
        # Træn Decision Tree med pruning
        model = DecisionTreeClassifier(
            criterion='entropy',
            max_depth=8,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42
        )
        
        model.fit(X_train_selected, self.y_train)
        
        # Evaluér
        y_pred = model.predict(X_test_selected)
        y_prob = model.predict_proba(X_test_selected)[:, 1]
        
        results = self._evaluate_model(y_pred, y_prob, "Decision Tree")
        results['tree_depth'] = model.get_depth()
        results['n_leaves'] = model.get_n_leaves()
        
        # Gem
        selected_features = [self.feature_names[i] for i in mi_selector.get_support(indices=True)]
        self.models['decision_tree'] = {
            'model': model,
            'mi_selector': mi_selector,
            'selected_features': selected_features,
            'n_features': 15
        }
        self.model_results['decision_tree'] = results
        
        print(f"✅ Decision Tree: {results['accuracy']:.3f} accuracy (depth: {results['tree_depth']})")
        
    def train_model_9_catboost(self):
        """
        Model 9: CatBoost med Boruta feature selection
        Bruger omkring 50 features
        """
        print("\n9️⃣  CATBOOST")
        print("-" * 30)
        
        if not CATBOOST_AVAILABLE:
            print("❌ CatBoost ikke tilgængelig - springer over")
            return
        
        # Feature selection: CatBoost feature importance
        print("🎛️  Feature Selection: CatBoost Feature Importance...")
        
        # Træn initial CatBoost for feature importance
        cat_selector = CatBoostClassifier(
            iterations=100,
            random_seed=42,
            verbose=False
        )
        cat_selector.fit(self.X_train, self.y_train)
        
        # Vælg top 50 features
        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'importance': cat_selector.feature_importances_
        }).sort_values('importance', ascending=False)
        
        top_features = feature_importance.head(50)['feature'].tolist()
        
        X_train_selected = self.X_train[top_features]
        X_test_selected = self.X_test[top_features]
        
        # Træn final model
        model = CatBoostClassifier(
            iterations=300,
            depth=6,
            learning_rate=0.1,
            random_seed=42,
            verbose=False
        )
        
        model.fit(X_train_selected, self.y_train)
        
        # Evaluér
        y_pred = model.predict(X_test_selected)
        y_prob = model.predict_proba(X_test_selected)[:, 1]
        
        results = self._evaluate_model(y_pred, y_prob, "CatBoost")
        results['feature_importance'] = feature_importance.head(20).to_dict('records')
        
        # Gem
        self.models['catboost'] = {
            'model': model,
            'selected_features': top_features,
            'n_features': len(top_features)
        }
        self.model_results['catboost'] = results
        
        print(f"✅ CatBoost: {results['accuracy']:.3f} accuracy med {len(top_features)} features")
        
    def train_model_10_voting_ensemble(self):
        """
        Model 10: Voting Classifier ensemble af de bedste modeller
        """
        print("\n🔟 VOTING ENSEMBLE")
        print("-" * 30)
        
        # Identificer tilgængelige modeller
        available_models = []
        
        if 'random_forest' in self.models:
            rf_model = self.models['random_forest']['model']
            available_models.append(('rf', rf_model))
            
        if 'xgboost' in self.models and XGBOOST_AVAILABLE:
            xgb_model = self.models['xgboost']['model']
            available_models.append(('xgb', xgb_model))
            
        if 'logistic' in self.models:
            lr_model = self.models['logistic']['model']
            available_models.append(('lr', lr_model))
        
        if len(available_models) < 2:
            print("❌ Ikke nok modeller til ensemble - kræver minimum 2")
            return
        
        print(f"🎛️  Ensemble med {len(available_models)} modeller...")
        
        # For ensemble skal vi bruge samme features for alle modeller
        # Bruger intersection af alle model features
        if 'random_forest' in self.models:
            common_features = set(self.models['random_forest']['selected_features'])
            for model_name in ['xgboost', 'logistic']:
                if model_name in self.models and 'selected_features' in self.models[model_name]:
                    model_features = set(self.models[model_name]['selected_features'])
                    common_features = common_features.intersection(model_features)
        else:
            # Fallback til top 30 features baseret på Random Forest
            rf_temp = RandomForestClassifier(n_estimators=50, random_state=42)
            rf_temp.fit(self.X_train, self.y_train)
            feature_importance = pd.DataFrame({
                'feature': self.feature_names,
                'importance': rf_temp.feature_importances_
            }).sort_values('importance', ascending=False)
            common_features = set(feature_importance.head(30)['feature'].tolist())
        
        common_features = list(common_features)[:30]  # Maksimum 30 features
        
        X_train_common = self.X_train[common_features]
        X_test_common = self.X_test[common_features]
        
        # Træn nye modeller på common features
        ensemble_models = []
        
        # Random Forest
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X_train_common, self.y_train)
        ensemble_models.append(('rf', rf))
        
        # Logistic Regression
        lr = LogisticRegression(random_state=42, max_iter=1000)
        lr.fit(X_train_common, self.y_train)
        ensemble_models.append(('lr', lr))
        
        # XGBoost hvis tilgængeligt
        if XGBOOST_AVAILABLE:
            xgb_model = xgb.XGBClassifier(n_estimators=100, random_state=42, eval_metric='logloss')
            xgb_model.fit(X_train_common, self.y_train)
            ensemble_models.append(('xgb', xgb_model))
        
        # Voting Classifier
        model = VotingClassifier(
            estimators=ensemble_models,
            voting='soft'  # Brug probabilities
        )
        
        model.fit(X_train_common, self.y_train)
        
        # Evaluér
        y_pred = model.predict(X_test_common)
        y_prob = model.predict_proba(X_test_common)[:, 1]
        
        results = self._evaluate_model(y_pred, y_prob, "Voting Ensemble")
        results['ensemble_models'] = [name for name, _ in ensemble_models]
        
        # Gem
        self.models['voting_ensemble'] = {
            'model': model,
            'common_features': common_features,
            'n_features': len(common_features)
        }
        self.model_results['voting_ensemble'] = results
        
        print(f"✅ Voting Ensemble: {results['accuracy']:.3f} accuracy med {len(common_features)} features")
        
    def _evaluate_model(self, y_pred, y_prob, model_name: str) -> Dict:
        """
        Evaluerer model performance med comprehensive metrics
        """
        return {
            'model_name': model_name,
            'accuracy': accuracy_score(self.y_test, y_pred),
            'precision': precision_score(self.y_test, y_pred, average='weighted'),
            'recall': recall_score(self.y_test, y_pred, average='weighted'),
            'f1': f1_score(self.y_test, y_pred, average='weighted'),
            'roc_auc': roc_auc_score(self.y_test, y_prob),
            'confusion_matrix': confusion_matrix(self.y_test, y_pred).tolist(),
            'n_test_samples': len(self.y_test),
            'home_win_rate_actual': self.y_test.mean(),
            'home_win_rate_predicted': y_pred.mean()
        }
        
    def train_all_models(self):
        """
        Træner alle 10 modeller i sekvens
        """
        print("\n🚀 TRÆNER ALLE ML MODELLER")
        print("=" * 60)
        
        # Træn modeller
        self.train_model_1_logistic_regression()
        self.train_model_2_random_forest()
        self.train_model_3_xgboost()
        self.train_model_4_svm()
        self.train_model_5_neural_network()
        self.train_model_6_knn()
        self.train_model_7_naive_bayes()
        self.train_model_8_decision_tree()
        self.train_model_9_catboost()
        self.train_model_10_voting_ensemble()
        
        print(f"\n🎉 ALLE MODELLER TRÆNET!")
        print(f"📊 {len(self.model_results)} modeller evalueret")
        
    def compare_models(self):
        """
        Sammenligner performance på tværs af alle modeller
        """
        print("\n📊 MODEL PERFORMANCE SAMMENLIGNING")
        print("=" * 60)
        
        if not self.model_results:
            print("❌ Ingen modeller at sammenligne - kør træning først")
            return
        
        # Opret sammenligning DataFrame
        comparison_data = []
        for model_name, results in self.model_results.items():
            n_features = self.models[model_name].get('n_features', 'N/A')
            comparison_data.append({
                'Model': results['model_name'],
                'Accuracy': results['accuracy'],
                'Precision': results['precision'],
                'Recall': results['recall'],
                'F1-Score': results['f1'],
                'ROC-AUC': results['roc_auc'],
                'Features': n_features
            })
        
        comparison_df = pd.DataFrame(comparison_data)
        comparison_df = comparison_df.sort_values('Accuracy', ascending=False)
        
        print("\n🏆 PERFORMANCE RANKING:")
        print(comparison_df.to_string(index=False, float_format=lambda x: f'{x:.3f}' if isinstance(x, float) else str(x)))
        
        # Find bedste model
        best_model = comparison_df.iloc[0]
        print(f"\n🥇 BEDSTE MODEL: {best_model['Model']}")
        print(f"   Accuracy: {best_model['Accuracy']:.3f}")
        print(f"   ROC-AUC: {best_model['ROC-AUC']:.3f}")
        print(f"   Features: {best_model['Features']}")
        
        # Gem comparison
        comparison_path = os.path.join(self.output_dir, "model_comparison.csv")
        comparison_df.to_csv(comparison_path, index=False)
        print(f"\n💾 Sammenligning gemt: {comparison_path}")
        
        return comparison_df
        
    def save_models(self):
        """
        Gemmer alle trænede modeller
        """
        print("\n💾 GEMMER MODELLER")
        print("-" * 30)
        
        models_path = os.path.join(self.output_dir, "trained_models.pkl")
        
        with open(models_path, 'wb') as f:
            pickle.dump({
                'models': self.models,
                'results': self.model_results,
                'feature_names': self.feature_names,
                'scaler': self.scaler
            }, f)
        
        print(f"✅ Modeller gemt: {models_path}")
        
    def generate_report(self):
        """
        Genererer detaljeret rapport med anbefalinger
        """
        print("\n📋 GENERERER DETALJERET RAPPORT")
        print("-" * 40)
        
        if not self.model_results:
            print("❌ Ingen resultater at rapportere")
            return
        
        report_lines = [
            f"HÅNDBOL ML MODEL RAPPORT - {self.league}",
            "=" * 60,
            f"Genereret: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "DATASET INFORMATION:",
            f"- Træningsdata: {len(self.y_train)} kampe",
            f"- Testdata: {len(self.y_test)} kampe", 
            f"- Features: {len(self.feature_names)} (efter initial selection)",
            f"- Class balance: {self.y_train.mean():.1%} hjemme wins",
            "",
            "MODEL PERFORMANCE SUMMARY:",
            "-" * 40
        ]
        
        # Sorter modeller efter accuracy
        sorted_results = sorted(
            self.model_results.items(),
            key=lambda x: x[1]['accuracy'],
            reverse=True
        )
        
        for i, (model_key, results) in enumerate(sorted_results, 1):
            n_features = self.models[model_key].get('n_features', 'N/A')
            report_lines.extend([
                f"{i}. {results['model_name']}",
                f"   Accuracy: {results['accuracy']:.3f}",
                f"   ROC-AUC: {results['roc_auc']:.3f}",
                f"   Features: {n_features}",
                ""
            ])
        
        # Anbefalinger
        best_model_key = sorted_results[0][0]
        best_result = sorted_results[0][1]
        
        report_lines.extend([
            "ANBEFALINGER:",
            "-" * 40,
            f"🥇 ANBEFALET MODEL: {best_result['model_name']}",
            f"   - Accuracy: {best_result['accuracy']:.3f}",
            f"   - ROC-AUC: {best_result['roc_auc']:.3f}",
            f"   - Features: {self.models[best_model_key].get('n_features', 'N/A')}",
            "",
            "PERFORMANCE VURDERING:",
        ])
        
        if best_result['accuracy'] > 0.70:
            report_lines.append("✅ EXCELLENT: >70% accuracy - model klar til produktion")
        elif best_result['accuracy'] > 0.65:
            report_lines.append("✅ GODT: 65-70% accuracy - solid performance")
        elif best_result['accuracy'] > 0.60:
            report_lines.append("⚠️  ACCEPTABELT: 60-65% accuracy - kan forbedres")
        else:
            report_lines.append("❌ SVAGT: <60% accuracy - kræver forbedring")
        
        report_lines.extend([
            "",
            "NÆSTE SKRIDT:",
            "- Hyperparameter tuning af bedste model",
            "- Feature engineering baseret på feature importance",
            "- Temporal cross-validation for robusthed",
            "- Evaluering på flere sæsoner hvis tilgængeligt"
        ])
        
        # Gem rapport
        report_text = "\n".join(report_lines)
        report_path = os.path.join(self.output_dir, "ml_model_report.txt")
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(f"✅ Rapport gemt: {report_path}")
        print("\n" + "=" * 60)
        print(report_text)
        
    def run_complete_pipeline(self):
        """
        Kører den komplette ML pipeline
        """
        try:
            # Data preparation
            self.load_and_prepare_data()
            self.initial_feature_selection()
            self.setup_temporal_cv()
            
            # Model training
            self.train_all_models()
            
            # Analysis
            self.compare_models()
            self.save_models()
            self.generate_report()
            
            print(f"\n🎉 ML PIPELINE KOMPLET!")
            print(f"📁 Resultater gemt i: {self.output_dir}")
            
        except Exception as e:
            print(f"❌ FEJL I PIPELINE: {e}")
            import traceback
            traceback.print_exc()


# === MAIN EXECUTION ===
if __name__ == "__main__":
    import sys
    
    # Vælg liga
    league = "Herreliga"
    if len(sys.argv) > 1:
        league = sys.argv[1]
        if league not in ["Herreliga", "Kvindeliga"]:
            print(f"❌ Ugyldig liga: {league}")
            sys.exit(1)
    
    print(f"🎯 STARTER HÅNDBOL ML PIPELINE - {league}")
    print("=" * 70)
    
    # Opret og kør pipeline
    pipeline = HandballMLPipeline(league=league)
    pipeline.run_complete_pipeline()
