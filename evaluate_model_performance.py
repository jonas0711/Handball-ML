#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EVALUATE MODEL PERFORMANCE ON UNSEEN DATA
=========================================

Dette script udfører en grundig evaluering af de trænede modeller
på testdata, som modellerne ikke har set under træningen.

Formålet er at vurdere modellens reelle ydeevne og identificere
eventuelle tendenser, f.eks. en bias mod at forudsige hjemmesejre.

Scriptet vil:
1. Initialisere `HandballMatchPredictor` for både Herre- og Kvindeliga.
2. Kalde `evaluate_model_on_test_data()` for hver liga.
3. Vise en detaljeret performancerapport.
"""

import sys
from handball_match_predictor import HandballMatchPredictor

def evaluate_performance():
    """
    Kører evalueringen for begge ligaer.
    """
    print("🚀 STARTER EVALUERING AF MODELLER PÅ USYNLIGE TESTDATA")
    print("="*60)
    print("Formål: At tjekke for bias (f.eks. for mange hjemmesejre) og generel nøjagtighed.")
    
    leagues = ["Herreliga", "Kvindeliga"]
    
    for league in leagues:
        print(f"\n\n🏆 EVALUERING AF: {league.upper()}")
        print("-" * 50)
        
        try:
            # Trin 1: Initialiser predictoren for ligaen.
            # Dette indlæser den trænede model og de tilhørende data.
            print(f"⚙️  Initialiserer predictor for {league}...")
            predictor = HandballMatchPredictor(league=league)
            
            if predictor.model is None:
                print(f"❌ Kunne ikke loade modellen for {league}. Springer over.")
                continue

            # Trin 2: Kør den indbyggede evalueringsfunktion.
            # Denne funktion isolerer automatisk test-sæsonen (f.eks. 2024-2025)
            # og beregner en række performance-metrics.
            print(f"🧠 Evaluerer modelperformance på testdata for {league}...")
            metrics = predictor.evaluate_model_on_test_data()
            
            if not metrics:
                print(f"⚠️ Ingen evaluerings-metrics blev returneret for {league}.")
            else:
                print(f"\n✅ Evaluering for {league} fuldført.")

        except Exception as e:
            print(f"❌ En uventet fejl opstod under evaluering af {league}: {e}")
            import traceback
            traceback.print_exc()

    print("\n\n🎉 FULD EVALUERING ER AFSLUTTET.")
    print("="*60)

if __name__ == "__main__":
    # Sørg for at den nuværende mappe er i stien, så imports virker.
    sys.path.append('.')
    evaluate_performance() 