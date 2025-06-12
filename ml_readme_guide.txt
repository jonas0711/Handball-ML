# 🏆 HÅNDBOL ML PIPELINE - KOMPLET IMPLEMENTERING

## 📋 OVERVIEW

Dette projekt implementerer 10 forskellige machine learning modeller til forudsigelse af håndboldkamp vindere. Systemet er designet med temporal awareness for at undgå data leakage og inkluderer omfattende feature selection og model evaluation.

### 🎯 PROJEKTMÅL
- Forudsige vinderen af håndboldkampe baseret på historiske data
- Teste 10 forskellige ML algoritmer med optimerede feature selections
- Implementere robust temporal validation for pålidelige resultater
- Levere actionable insights til team management og betting

### 📊 DATASET
- **Herreliga**: Træning 2017-2018 til 2023-2024, Test 2024-2025
- **Kvindeliga**: Træning 2018-2019 til 2023-2024, Test 2024-2025
- **Features**: 200+ features inkl. ELO ratings, spiller stats, positionelle metrics
- **Samples**: ~1500 kampe totalt

---

## 🚀 QUICK START

### 1. SETUP ENVIRONMENT
```bash
# Opret virtual environment
python -m venv handball_ml_env

# Aktiver environment
# Windows:
handball_ml_env\Scripts\activate
# macOS/Linux:
source handball_ml_env/bin/activate

# Installer dependencies
pip install pandas numpy scikit-learn matplotlib seaborn xgboost catboost
```

### 2. BASIC USAGE
```bash
# Kør komplet pipeline for Herreliga
python ml_pipeline.py Herreliga

# Kør komplet pipeline for Kvindeliga  
python ml_pipeline.py Kvindeliga

# Analyser resultater
python ml_analysis.py Herreliga
```

### 3. FORVENTET OUTPUT
```
🎯 ML PIPELINE KOMPLET!
📁 Resultater gemt i: ML_Results_Herreliga
📊 10 modeller evalueret
🥇 BEDSTE MODEL: Random Forest (Accuracy: 0.678)
```

---

## 📁 FILSTRUKTUR

```
project/
├── ml_pipeline.py              # Hovedpipeline med alle 10 modeller
├── ml_analysis.py              # Visualisering og avanceret analyse  
├── ml_temporal_utils.py        # Temporal CV og feature engineering
├── requirements.txt            # Dependencies
├── README.md                   # Denne fil
├── ML_Datasets/               # Input data directory
│   ├── herreliga_handball_ml_dataset.csv
│   └── kvindeliga_handball_ml_dataset.csv
└── ML_Results_[Liga]/         # Output results
    ├── trained_models.pkl     # Gemte modeller
    ├── model_comparison.csv   # Performance sammenligning
    ├── ml_model_report.txt    # Detaljeret rapport
    └── plots/                 # Visualiseringer
        ├── model_comparison.png
        ├── feature_importance.png
        └── confusion_matrices.png
```

---

## 🤖 DE 10 ML MODELLER

| # | Model | Feature Selection | Antal Features | Formål |
|---|-------|------------------|----------------|---------|
| 1 | **Logistic Regression** | L1 Regularization + SelectKBest | 20 | Simpel, interpreterbar baseline |
| 2 | **Random Forest** | Built-in importance | 40 | Robust, feature importance insights |
| 3 | **XGBoost** | XGB importance | 50 | Høj performance, complex patterns |
| 4 | **SVM** | PCA + SelectKBest | 30 | Non-lineære decision boundaries |
| 5 | **Neural Network** | Mutual Information | 60 | Deep learning patterns |
| 6 | **K-NN** | SelectKBest | 15 | Local similarity patterns |
| 7 | **Naive Bayes** | Chi-square test | 25 | Probabilistic baseline |
| 8 | **Decision Tree** | Entropy-based | 15 | Interpreterbare regler |
| 9 | **CatBoost** | CatBoost importance | 50 | Advanced gradient boosting |
| 10 | **Voting Ensemble** | Union af top features | 30 | Kombiner bedste modeller |

---

## 🎛️ FEATURE SELECTION STRATEGIER

### FASE 1: Initial Filtering (200+ → 100 features)
- **Variance Threshold**: Fjern features med lav variabilitet
- **Correlation Analysis**: Eliminer højt korrelerede features (>0.95)
- **Domain Knowledge**: Prioriter ELO og core handball metrics

### FASE 2: Model-Specific Selection (100 → final antal)
- **Logistic Regression**: L1 regularization for sparsity
- **Tree Models**: Built-in feature importance
- **SVM**: PCA for dimensionality reduction
- **Neural Networks**: Mutual information for non-linear dependencies
- **Distance-based**: SelectKBest med få features for KNN

### KRITISKE FEATURE KATEGORIER
1. **ELO Ratings** (højeste prioritet) - Historiske hold styrker
2. **Recent Form** - Performance i seneste 5-10 kampe  
3. **Head-to-Head** - Direkte historik mellem teams
4. **Positionelle** - Styrker/svagheder per position
5. **Temporal** - Sæson timing og hjemmebane fordel

---

## ⏰ TEMPORAL VALIDATION

### HVORFOR TEMPORAL VALIDATION?
Standard cross-validation kan skabe **data leakage** ved at bruge fremtidige data til at forudsige fortidige kampe. Vores system bruger:

### TEMPORAL SPLIT STRATEGI
```python
# Herreliga eksempel
Training: 2017-2018 til 2023-2024  # 7 sæsoner
Testing:  2024-2025                # 1 sæson

# Temporal Cross-Validation (under træning)
Split 1: Train [2017-2019] → Validate [2019-2020]
Split 2: Train [2017-2020] → Validate [2020-2021]
Split 3: Train [2017-2021] → Validate [2021-2022]
# osv...
```

### DATA LEAKAGE BESKYTTELSE
- ✅ Kronologisk ordering validation
- ✅ Feature temporal consistency checks  
- ✅ ELO ratings kun fra før kamp
- ✅ Automatisk leakage detection

---

## 📊 PERFORMANCE METRICS

### PRIMARY METRICS
- **Accuracy**: Overall success rate
- **Precision**: Hvor mange predicted home wins der faktisk var home wins
- **Recall**: Hvor mange faktiske home wins der blev predicted
- **F1-Score**: Harmonisk mean af precision og recall
- **ROC-AUC**: Area under ROC curve (classification quality)

### FORVENTET PERFORMANCE
- **Minimum Target**: 60% accuracy (bedre end random)
- **God Performance**: 65-70% accuracy
- **Excellent**: 70%+ accuracy

### BASELINE COMPARISON
- **Random Guessing**: ~50% accuracy
- **Always Predict Home Win**: ~55% accuracy (pga hjemmebane fordel)
- **Simple ELO Model**: ~62% accuracy

---

## 🔧 AVANCEREDE FEATURES

### HYPERPARAMETER TUNING
```python
# Eksempel for Random Forest
rf_params = {
    'n_estimators': [100, 200, 300],
    'max_depth': [5, 10, 15, None],
    'min_samples_split': [2, 5, 10]
}

# Brug temporal-aware search
search = RandomizedSearchCV(
    RandomForestClassifier(),
    rf_params,
    cv=TimeSeriesSplit(5),  # KRITISK: Temporal CV
    scoring='accuracy'
)
```

### FEATURE ENGINEERING
```python
# Interaction features
X['elo_diff'] = X['home_elo'] - X['away_elo']
X['form_diff'] = X['home_recent_form'] - X['away_recent_form']

# Polynomial features
X['elo_squared'] = X['home_elo'] ** 2

# Rolling statistics (kræver temporal pipeline)
X['goals_for_last_5'] = rolling_mean(goals_for, window=5)
```

### MODEL INTERPRETABILITY
```python
# Feature importance plots
plot_feature_importance(random_forest_model)

# SHAP values (hvis installeret)
import shap
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)
```

---

## 📈 RESULTS INTERPRETATION

### MODEL COMPARISON PLOT
Sammenligner alle 10 modeller på tværs af metrics:
- Horizontal bar charts for hver metric
- Color-coded performance (grøn = god, rød = dårlig)
- Identificer top 3 modeller

### FEATURE IMPORTANCE ANALYSIS  
- Hvilke features driver forudsigelserne?
- ELO features typisk mest vigtige
- Recent form og head-to-head også kritiske
- Positionelle features varierer efter liga

### CONFUSION MATRICES
```
Predicted:  Away  Home
Actual:
Away        [ 45    12 ]  # True Negative, False Positive  
Home        [ 18    67 ]  # False Negative, True Positive
```

### ROC CURVES
- Viser trade-off mellem True/False Positive rates
- Området under kurven (AUC) = samlet kvalitet
- Sammenligner alle modeller på samme plot

---

## 🚨 TROUBLESHOOTING

### COMMON ISSUES & SOLUTIONS

#### 1. "Dataset ikke fundet"
```bash
# Løsning: Tjek fil paths
ls ML_Datasets/
# Skal indeholde: *_handball_ml_dataset.csv
```

#### 2. "Ingen testdata fundet"  
```bash
# Problem: Mangler 2024-2025 data
# Løsning: Pipeline bruger automatisk sidste 20% som test
```

#### 3. "XGBoost/CatBoost fejl"
```bash
# Løsning: Installer valgfrie libraries
pip install xgboost catboost
# Eller skip: Pipeline kører uden dem
```

#### 4. "Memory Error"
```bash
# Løsning: Reducer feature antal eller brug mindre dataset
# Edit: max_features parameter i initial_feature_selection()
```

#### 5. "Lav Performance (<55%)"
```bash
# Mulige årsager:
# - Data kvalitetsproblemer
# - Data leakage (tjek validation)
# - Forkert temporal split
# - Ubalanced classes
```

### DEBUGGING TIPS
```python
# Enable verbose output
pipeline = HandballMLPipeline(league="Herreliga")
pipeline.load_and_prepare_data()

# Tjek data kvalitet
print(f"Missing values: {pipeline.X_train.isnull().sum().sum()}")
print(f"Class balance: {pipeline.y_train.mean():.2%}")

# Validate no data leakage
validator = ModelValidator()
validator.validate_no_data_leakage(pipeline.raw_data)
```

---

## 📚 ADVANCED USAGE

### CUSTOM FEATURE SELECTION
```python
# Tilføj custom feature selection
def custom_feature_selector(X, y, n_features=30):
    # Din logic her
    selected_features = your_selection_logic(X, y)
    return X[selected_features]

# Integrer i pipeline
pipeline.custom_feature_selection = custom_feature_selector
```

### ENSEMBLE STACKING
```python
# Stack top 3 modeller
from sklearn.ensemble import StackingClassifier

base_models = [
    ('rf', pipeline.models['random_forest']['model']),
    ('xgb', pipeline.models['xgboost']['model']),
    ('lr', pipeline.models['logistic']['model'])
]

stacked_model = StackingClassifier(
    estimators=base_models,
    final_estimator=LogisticRegression(),
    cv=TimeSeriesSplit(5)  # Temporal CV
)
```

### HYPERPARAMETER TUNING PIPELINE
```python
# Automatisk tuning af top model
from sklearn.model_selection import RandomizedSearchCV

best_model_name = 'random_forest'  # Fra results
param_grid = {...}  # Model-specific parameters

tuned_model = RandomizedSearchCV(
    pipeline.models[best_model_name]['model'],
    param_grid,
    cv=TimeSeriesSplit(5),
    n_iter=50,
    scoring='accuracy',
    n_jobs=-1
)
```

---

## 📊 PERFORMANCE BENCHMARKS

### EXPECTED RESULTS (baseret på lignende sportsdata)

| Liga | Model Type | Expected Accuracy | Notes |
|------|------------|------------------|--------|
| Herreliga | Random Forest | 65-70% | Stabil performance |
| Herreliga | XGBoost | 67-72% | Bedste single model |
| Herreliga | Ensemble | 69-74% | Kombination af top 3 |
| Kvindeliga | Random Forest | 63-68% | Mindre data |
| Kvindeliga | XGBoost | 65-70% | Stadig god |

### INDUSTRY BENCHMARKS
- **Betting Markets**: ~65% accuracy på closing odds
- **Simple ELO Models**: ~62% accuracy  
- **Advanced ML Systems**: 70-75% accuracy
- **Human Experts**: 60-65% accuracy

---

## 🔄 CONTINUOUS IMPROVEMENT

### MODEL MAINTENANCE
1. **Ugentlig**: Opdater med nye kampe
2. **Månedlig**: Re-evaluer feature importance
3. **Sæsonmæssigt**: Retrain alle modeller
4. **Årligt**: Review og opdater feature engineering

### FEATURE ENGINEERING IDEAS
- **Spillerskader**: Injurity reports impact
- **Vejrforhold**: Udendørs kampe påvirkning  
- **Travel Distance**: Away team rejse distance
- **Rest Days**: Dage siden sidste kamp
- **Motivation**: Liga position og playoff implications

### MODEL ENHANCEMENT
- **Deep Learning**: LSTM for sequential patterns
- **Gradient Boosting**: LightGBM, CatBoost tuning
- **Ensemble Methods**: Advanced stacking strategies
- **Real-time Updates**: Live betting odds integration

---

## 🎯 BUSINESS APPLICATIONS

### TEAM MANAGEMENT
- **Taktisk Planlægning**: Identificer modstander svagheder
- **Spillerrotation**: Optimal lineup baseret på matchup
- **Træningsfokus**: Forbedring af svage positioner

### BETTING & PREDICTIONS  
- **Value Betting**: Find odds med positive expected value
- **Risk Management**: Confidence intervals på predictions
- **Market Analysis**: Sammenlign med betting market odds

### SPORTS ANALYTICS
- **Performance Analysis**: Kvantificér team forbedringer
- **Scouting**: Identificer underværderede spillere/teams
- **League Analysis**: Meta-game trends og udvikling

---

## 🤝 SUPPORT & CONTRIBUTION

### GET HELP
- **Documentation**: Læs kode kommentarer for detaljer
- **Debugging**: Brug verbose output og validation functions
- **Issues**: Check troubleshooting section først

### CONTRIBUTION GUIDELINES
1. Fork repository
2. Lav feature branch: `git checkout -b feature/awesome-feature`
3. Test thoroughly med temporal validation
4. Submit pull request med clear beskrivelse

### ROADMAP
- [ ] Hyperparameter auto-tuning
- [ ] Real-time data integration  
- [ ] Web interface for predictions
- [ ] Advanced ensemble methods
- [ ] Model interpretability dashboard

---

## 📄 LICENSE & DISCLAIMER

Dette projekt er lavet til uddannelses- og forskningsformål på Aalborg Universitet.

**DISCLAIMER**: Denne software er til analyse og uddannelse. Brug ikke til kommerciel betting uden grundig validering og risikoevaluering. Tidligere performance garanterer ikke fremtidige resultater.

---

## 📞 CONTACT

**Udvikler**: AAU Design og Anvendelse af Kunstig Intelligens  
**Projekt**: Håndbol ML Pipeline  
**Version**: 1.0  
**Sidste Opdatering**: December 2024

---

*God modellering! 🏆*
