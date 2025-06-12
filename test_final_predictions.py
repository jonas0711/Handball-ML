#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST SCRIPT FOR FINAL PREDICTIONS
==================================

Dette script tester forudsigelserne for Kvindeligaens finale- og 3. pladskampe
fra d. 8. juni 2024.

Det bruger den eksisterende `NextRoundPredictor` til at:
1. Definere kampene med de korrekte holdnavne fra `team_config.py`.
2. Køre forudsigelserne for Kvindeliga.
3. Vise en overskuelig opsummering af resultaterne.
"""

import sys
from datetime import datetime
from handball_next_round_predictor import NextRoundPredictor

def run_final_predictions():
    """
    Kører forudsigelser for finalekampene.
    """
    print("🚀 Starter test af finale-forudsigelser...")
    print("="*50)

    # Opret en instans af den interaktive predictor
    try:
        predictor_interface = NextRoundPredictor()
    except Exception as e:
        print(f"❌ Kunne ikke initialisere NextRoundPredictor: {e}")
        return

    # Tjek om Kvindeliga-modellen er loadet korrekt
    if 'Kvindeliga' not in predictor_interface.predictors or predictor_interface.predictors['Kvindeliga'] is None:
        print("❌ Kvindeliga-predictor er ikke tilgængelig. Testen kan ikke fortsætte.")
        print("   Sørg for, at `ultimate_handball_model_kvindeliga.pkl` findes.")
        return

    # Definer kampene fra billedet med korrekte navne og dato
    # Datoen er sat til den 8. juni 2024
    match_date = datetime(2024, 6, 8)

    final_matches = [
        {
            'home_team': 'Team Esbjerg',
            'away_team': 'Odense Håndbold',
            'match_date': match_date
        },
        {
            'home_team': 'København Håndbold',
            'away_team': 'Ikast Håndbold',
            'match_date': match_date
        }
    ]

    print("\nDefinerede kampe til forudsigelse:")
    for match in final_matches:
        print(f"  - {match['home_team']} vs {match['away_team']}")

    # Kør forudsigelser for de definerede kampe
    print(f"🔮 FORUDSIGER {len(final_matches)} KAMPE I Kvindeliga")
    print("=" * 60)

    predictions = predictor_interface.predict_matches('Kvindeliga', final_matches)

    if predictions.empty:
        print("❌ Ingen forudsigelser blev genereret.")
    else:
        print("\n✅ Forudsigelser er fuldført.")
        predictor_interface.display_round_summary('Kvindeliga', predictions)

    print("\n="*50)
    print("🎉 Testen er afsluttet.")

if __name__ == "__main__":
    # Sørg for at den nuværende mappe er i stien, så imports virker
    sys.path.append('.')
    run_final_predictions() 