#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TEST SCRIPT FOR HERRELIGA FINAL PREDICTIONS
============================================

Dette script forudsiger resultaterne for Herreligaens finale- og 3. pladskampe
fra d. 7. juni 2024, baseret på det medsendte billede.

Det bruger den eksisterende `NextRoundPredictor` til at:
1. Definere de specifikke kampe.
2. Køre forudsigelserne for Herreliga.
3. Vise en overskuelig opsummering af resultaterne.
"""

import sys
from datetime import datetime
from handball_next_round_predictor import NextRoundPredictor

def run_herreliga_final_predictions():
    """
    Kører forudsigelser for Herreligaens finalekampe.
    """
    print("🚀 Starter forudsigelser af Herreligaens finalekampe...")
    print("="*60)

    # Opret en instans af forudsigelses-interfacet.
    try:
        predictor_interface = NextRoundPredictor()
    except Exception as e:
        print(f"❌ Kunne ikke initialisere NextRoundPredictor: {e}")
        return

    # Tjek om Herreliga-modellen er klar.
    if 'Herreliga' not in predictor_interface.predictors or predictor_interface.predictors['Herreliga'] is None:
        print("❌ Herreliga-predictor er ikke tilgængelig. Testen kan ikke fortsætte.")
        print("   Sørg for, at `ultimate_handball_model_herreliga.pkl` findes.")
        return

    # Definer kampene fra billedet.
    # Datoen er sat til den 7. juni 2024.
    # Holdnavnene matcher dem, der findes i datasættet.
    match_date = datetime(2024, 6, 7)

    final_matches = [
        {
            # Finale
            'home_team': 'Skjern Håndbold',
            'away_team': 'Aalborg Håndbold',
            'match_date': match_date
        },
        {
            # 3. Plads
            'home_team': 'TTH Holstebro',
            'away_team': 'GOG',
            'match_date': match_date
        }
    ]

    print("\nDefinerede kampe til forudsigelse:")
    for match in final_matches:
        print(f"  - {match['home_team']} vs {match['away_team']}")

    # Kør forudsigelser for Herreliga.
    print(f"\n🔮 FORUDSIGER {len(final_matches)} KAMPE I HERRELIGA")
    print("=" * 60)

    predictions = predictor_interface.predict_matches('Herreliga', final_matches)

    # Vis resultaterne.
    if predictions.empty:
        print("❌ Ingen forudsigelser blev genereret.")
    else:
        print("\n✅ Forudsigelser er fuldført.")
        predictor_interface.display_round_summary('Herreliga', predictions)

    print("\n="*60)
    print("🎉 Forudsigelser er afsluttet.")

if __name__ == "__main__":
    # Sørg for at den nuværende mappe er i stien, så imports virker.
    sys.path.append('.')
    run_herreliga_final_predictions() 