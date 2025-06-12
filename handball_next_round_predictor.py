#!/usr/bin/env python3
"""
HÅNDBOL NÆSTE RUNDE PREDICTOR
============================

Brugervenligt interface til at forudsige næste rundes kampe.
Man indtaster op til 7 kampe med holdnavne, og systemet genererer
features fra historiske data og forudsiger resultater.

FUNKTIONER:
- Input interface for både Herreliga og Kvindeliga
- Automatisk feature generation fra historiske data  
- Real-time prediction med confidence scores
- Detaljeret match analysis
- Gem predictions til fil

Forfatter: AI Assistant
Version: 1.0
"""

import os
import sys
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from handball_match_predictor import HandballMatchPredictor

class NextRoundPredictor:
    """
    Interface til at forudsige næste rundes kampe
    """
    
    def __init__(self):
        """Initialize predictor med begge ligaer"""
        print("🚀 INITIALISERER HÅNDBOL PREDICTIONS...")
        print("=" * 60)
        
        # Initialize predictors for both leagues
        self.predictors = {}
        
        try:
            print("📂 Loading Herreliga model...")
            self.predictors['Herreliga'] = HandballMatchPredictor('Herreliga')
            print("✅ Herreliga model loaded!")
        except Exception as e:
            print(f"❌ Fejl ved loading af Herreliga: {e}")
            self.predictors['Herreliga'] = None
            
        try:
            print("📂 Loading Kvindeliga model...")
            self.predictors['Kvindeliga'] = HandballMatchPredictor('Kvindeliga')
            print("✅ Kvindeliga model loaded!")
        except Exception as e:
            print(f"❌ Fejl ved loading af Kvindeliga: {e}")
            self.predictors['Kvindeliga'] = None
    
    def get_available_teams(self, league: str) -> List[str]:
        """
        Henter tilgængelige holdnavne for en liga
        """
        if league not in self.predictors or self.predictors[league] is None:
            return []
            
        try:
            predictor = self.predictors[league]
            # Get unique team names from database
            teams = set()
            
            # Check if feature generator has historical data
            if hasattr(predictor.feature_generator, 'historical_data'):
                for match_data in predictor.feature_generator.historical_data.values():
                    teams.add(match_data['hold_hjemme'])
                    teams.add(match_data['hold_ude'])
            
            return sorted(list(teams))
        except Exception as e:
            print(f"❌ Fejl ved hentning af holdnavne: {e}")
            return []
    
    def show_available_teams(self, league: str):
        """
        Viser tilgængelige holdnavne for en liga
        """
        teams = self.get_available_teams(league)
        
        if not teams:
            print(f"❌ Ingen holdnavne fundet for {league}")
            return
            
        print(f"\n📋 TILGÆNGELIGE HOLD I {league.upper()}:")
        print("-" * 50)
        
        # Split into columns for better readability
        mid = len(teams) // 2
        left_teams = teams[:mid]
        right_teams = teams[mid:]
        
        for i in range(max(len(left_teams), len(right_teams))):
            left = left_teams[i] if i < len(left_teams) else ""
            right = right_teams[i] if i < len(right_teams) else ""
            print(f"{left:<25} {right}")
    
    def input_next_round_matches(self, league: str) -> List[Dict]:
        """
        Interface til at indtaste næste rundes kampe
        """
        print(f"\n🎯 INDTAST NÆSTE RUNDES KAMPE - {league.upper()}")
        print("=" * 60)
        print("💡 Du kan indtaste op til 7 kampe")
        print("💡 Tryk bare ENTER for at stoppe")
        print("💡 Brug præcise holdnavne (tjek listen ovenfor)")
        
        matches = []
        match_count = 0
        max_matches = 7
        
        while match_count < max_matches:
            print(f"\n🏟️  KAMP {match_count + 1}:")
            print("-" * 30)
            
            # Get home team
            home_team = input("🏠 Hjemmehold: ").strip()
            if not home_team:
                break
                
            # Get away team  
            away_team = input("🏃 Udehold: ").strip()
            if not away_team:
                break
            
            # Validate team names
            available_teams = self.get_available_teams(league)
            
            if home_team not in available_teams:
                print(f"⚠️  Warning: '{home_team}' ikke fundet i database")
                confirm = input("   Fortsæt alligevel? (y/n): ")
                if confirm.lower() != 'y':
                    continue
                    
            if away_team not in available_teams:
                print(f"⚠️  Warning: '{away_team}' ikke fundet i database")
                confirm = input("   Fortsæt alligevel? (y/n): ")
                if confirm.lower() != 'y':
                    continue
            
            # Add match
            match = {
                'home_team': home_team,
                'away_team': away_team,
                'match_date': datetime.now() + timedelta(days=7),  # Next week
                'round_number': match_count + 1
            }
            
            matches.append(match)
            match_count += 1
            
            print(f"✅ Kamp {match_count} tilføjet: {home_team} vs {away_team}")
            
            # Ask if user wants to continue
            if match_count < max_matches:
                continue_input = input(f"\n➕ Tilføj kamp {match_count + 1}? (ENTER for ja, 'n' for nej): ")
                if continue_input.lower() == 'n':
                    break
        
        print(f"\n✅ {len(matches)} kampe indtastet for {league}")
        return matches
    
    def predict_matches(self, league: str, matches: List[Dict]) -> List[Dict]:
        """
        Forudsiger en liste af kampe
        """
        if league not in self.predictors or self.predictors[league] is None:
            print(f"❌ {league} predictor ikke tilgængelig")
            return []
        
        predictor = self.predictors[league]
        predictions = []
        
        print(f"\n🔮 FORUDSIGER {len(matches)} KAMPE I {league.upper()}")
        print("=" * 60)
        
        for i, match in enumerate(matches, 1):
            print(f"\n🎯 KAMP {i}: {match['home_team']} vs {match['away_team']}")
            print("-" * 50)
            
            try:
                # Generate prediction
                result = predictor.predict_single_match(
                    home_team=match['home_team'],
                    away_team=match['away_team'],
                    match_date=match['match_date']
                )
                
                if result:
                    # Extract key metrics
                    prediction = {
                        'match_number': i,
                        'home_team': match['home_team'],
                        'away_team': match['away_team'],
                        'predicted_winner': 'Hjemme' if result['prediction'] == 1 else 'Ude',
                        'home_win_probability': result['probabilities'][1],
                        'away_win_probability': result['probabilities'][0],
                        'confidence': result['confidence'],
                        'prediction_strength': 'Høj' if result['confidence'] > 0.7 else 'Medium' if result['confidence'] > 0.6 else 'Lav'
                    }
                    
                    predictions.append(prediction)
                    
                    # Display prediction
                    print(f"🏆 Forudsagt vinder: {prediction['predicted_winner']}")
                    print(f"📊 Hjemme sejr: {prediction['home_win_probability']:.1%}")
                    print(f"📊 Ude sejr: {prediction['away_win_probability']:.1%}")
                    print(f"🎯 Confidence: {prediction['confidence']:.1%} ({prediction['prediction_strength']})")
                    
                else:
                    print("❌ Kunne ikke generere prediction")
                    
            except Exception as e:
                print(f"❌ Fejl ved prediction: {e}")
                continue
        
        return predictions
    
    def display_round_summary(self, league: str, predictions: List[Dict]):
        """
        Viser sammenfatning af rundens predictions
        """
        if not predictions:
            print("❌ Ingen predictions at vise")
            return
            
        print(f"\n📊 SAMMENFATNING - {league.upper()} NÆSTE RUNDE")
        print("=" * 70)
        
        # Summary table
        print(f"{'Nr':<3} {'Kamp':<30} {'Vinder':<8} {'Prob':<8} {'Conf':<8}")
        print("-" * 70)
        
        total_confidence = 0
        high_confidence_count = 0
        
        for pred in predictions:
            match_str = f"{pred['home_team']} vs {pred['away_team']}"
            if len(match_str) > 28:
                match_str = match_str[:25] + "..."
                
            winner_prob = pred['home_win_probability'] if pred['predicted_winner'] == 'Hjemme' else pred['away_win_probability']
            
            print(f"{pred['match_number']:<3} {match_str:<30} {pred['predicted_winner']:<8} {winner_prob:<8.1%} {pred['confidence']:<8.1%}")
            
            total_confidence += pred['confidence']
            if pred['confidence'] > 0.7:
                high_confidence_count += 1
        
        print("-" * 70)
        
        # Statistics
        avg_confidence = total_confidence / len(predictions)
        print(f"\n📈 STATISTICS:")
        print(f"  Gennemsnitlig confidence: {avg_confidence:.1%}")
        print(f"  Høj confidence predictions: {high_confidence_count}/{len(predictions)}")
        print(f"  Hjemme sejre forudsagt: {sum(1 for p in predictions if p['predicted_winner'] == 'Hjemme')}")
        print(f"  Ude sejre forudsagt: {sum(1 for p in predictions if p['predicted_winner'] == 'Ude')}")
    
    def save_predictions(self, league: str, predictions: List[Dict]):
        """
        Gemmer predictions til fil
        """
        if not predictions:
            return
            
        filename = f"next_round_predictions_{league.lower()}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"HÅNDBOL PREDICTIONS - {league.upper()} NÆSTE RUNDE\n")
                f.write("=" * 60 + "\n")
                f.write(f"Genereret: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
                
                for pred in predictions:
                    f.write(f"KAMP {pred['match_number']}: {pred['home_team']} vs {pred['away_team']}\n")
                    f.write(f"  Forudsagt vinder: {pred['predicted_winner']}\n")
                    f.write(f"  Hjemme sejr: {pred['home_win_probability']:.1%}\n")
                    f.write(f"  Ude sejr: {pred['away_win_probability']:.1%}\n")
                    f.write(f"  Confidence: {pred['confidence']:.1%}\n")
                    f.write("-" * 50 + "\n")
            
            print(f"\n💾 Predictions gemt: {filename}")
            
        except Exception as e:
            print(f"❌ Fejl ved gem af predictions: {e}")
    
    def run_interactive_session(self):
        """
        Kører interaktiv session til prediction af næste runde
        """
        print("🎯 HÅNDBOL NÆSTE RUNDE PREDICTOR")
        print("=" * 60)
        print("🏆 Forudsig resultater for næste rundes kampe!")
        print("📊 Bruger historiske data og ML modeller")
        
        while True:
            print("\n🔧 VÆLG LIGA:")
            print("1. Herreliga")
            print("2. Kvindeliga") 
            print("3. Afslut")
            
            choice = input("\nDit valg (1-3): ").strip()
            
            if choice == '3':
                print("👋 Farvel!")
                break
            elif choice in ['1', '2']:
                league = 'Herreliga' if choice == '1' else 'Kvindeliga'
                
                if self.predictors[league] is None:
                    print(f"❌ {league} model ikke tilgængelig")
                    continue
                
                # Show available teams
                self.show_available_teams(league)
                
                # Input matches
                matches = self.input_next_round_matches(league)
                
                if not matches:
                    print("❌ Ingen kampe indtastet")
                    continue
                
                # Predict matches
                predictions = self.predict_matches(league, matches)
                
                if predictions:
                    # Display summary
                    self.display_round_summary(league, predictions)
                    
                    # Ask to save
                    save_choice = input("\n💾 Gem predictions til fil? (y/n): ")
                    if save_choice.lower() == 'y':
                        self.save_predictions(league, predictions)
                
            else:
                print("❌ Ugyldigt valg")


def main():
    """
    Main function til at køre prediction interface
    """
    try:
        predictor = NextRoundPredictor()
        predictor.run_interactive_session()
    except KeyboardInterrupt:
        print("\n\n👋 Afbrudt af bruger")
    except Exception as e:
        print(f"\n❌ Uventet fejl: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 