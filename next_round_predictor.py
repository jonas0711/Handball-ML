#!/usr/bin/env python3
"""
HÅNDBOL NÆSTE RUNDE PREDICTOR
============================

Brugervenligt interface til at forudsige næste rundes kampe.
"""

from handball_match_predictor import HandballMatchPredictor
from datetime import datetime, timedelta
from typing import List, Dict

class NextRoundPredictor:
    def __init__(self):
        print("🚀 INITIALISERER HÅNDBOL PREDICTIONS...")
        self.predictors = {}
        
        try:
            self.predictors['Herreliga'] = HandballMatchPredictor('Herreliga')
            print("✅ Herreliga model loaded!")
        except Exception as e:
            print(f"❌ Herreliga fejl: {e}")
            self.predictors['Herreliga'] = None
            
        try:
            self.predictors['Kvindeliga'] = HandballMatchPredictor('Kvindeliga')
            print("✅ Kvindeliga model loaded!")
        except Exception as e:
            print(f"❌ Kvindeliga fejl: {e}")
            self.predictors['Kvindeliga'] = None
    
    def get_teams(self, league: str) -> List[str]:
        """Henter holdnavne"""
        if not self.predictors[league]:
            return []
        try:
            teams = set()
            predictor = self.predictors[league]
            if hasattr(predictor.feature_generator, 'historical_data'):
                for match in predictor.feature_generator.historical_data.values():
                    teams.add(match['hold_hjemme'])
                    teams.add(match['hold_ude'])
            return sorted(teams)
        except:
            return []
    
    def show_teams(self, league: str):
        """Viser tilgængelige hold"""
        teams = self.get_teams(league)
        print(f"\n📋 {league.upper()} HOLD:")
        print("-" * 50)
        mid = len(teams) // 2
        for i in range(mid):
            left = teams[i] if i < len(teams) else ""
            right = teams[i + mid] if i + mid < len(teams) else ""
            print(f"{left:<25} {right}")
    
    def input_matches(self, league: str) -> List[Dict]:
        """Input kampe interface"""
        print(f"\n🎯 INDTAST KAMPE - {league.upper()}")
        print("=" * 50)
        print("💡 Op til 7 kampe. ENTER for at stoppe")
        
        matches = []
        for i in range(7):
            print(f"\n🏟️  KAMP {i+1}:")
            home = input("🏠 Hjemmehold: ").strip()
            if not home:
                break
            away = input("🏃 Udehold: ").strip()
            if not away:
                break
                
            match = {
                'home_team': home,
                'away_team': away,
                'match_date': datetime.now() + timedelta(days=7)
            }
            matches.append(match)
            print(f"✅ Tilføjet: {home} vs {away}")
            
            if i < 6:
                cont = input(f"\n➕ Tilføj kamp {i+2}? (ENTER=ja, n=nej): ")
                if cont.lower() == 'n':
                    break
        
        return matches
    
    def predict_matches(self, league: str, matches: List[Dict]) -> List[Dict]:
        """Forudsiger kampe"""
        if not self.predictors[league]:
            return []
            
        predictor = self.predictors[league]
        predictions = []
        
        print(f"\n🔮 FORUDSIGER {len(matches)} KAMPE")
        print("=" * 50)
        
        for i, match in enumerate(matches, 1):
            print(f"\n🎯 KAMP {i}: {match['home_team']} vs {match['away_team']}")
            try:
                result = predictor.predict_single_match(
                    match['home_team'], match['away_team'], match['match_date']
                )
                
                if result:
                    pred = {
                        'match': f"{match['home_team']} vs {match['away_team']}",
                        'winner': 'Hjemme' if result['prediction'] == 1 else 'Ude',
                        'home_prob': result['probabilities'][1],
                        'away_prob': result['probabilities'][0],
                        'confidence': result['confidence']
                    }
                    predictions.append(pred)
                    
                    print(f"🏆 Vinder: {pred['winner']}")
                    print(f"📊 Hjemme: {pred['home_prob']:.1%} | Ude: {pred['away_prob']:.1%}")
                    print(f"🎯 Confidence: {pred['confidence']:.1%}")
                else:
                    print("❌ Fejl i prediction")
            except Exception as e:
                print(f"❌ Fejl: {e}")
        
        return predictions
    
    def show_summary(self, league: str, predictions: List[Dict]):
        """Viser sammenfatning"""
        if not predictions:
            return
            
        print(f"\n📊 SAMMENFATNING - {league.upper()}")
        print("=" * 60)
        print(f"{'Kamp':<25} {'Vinder':<8} {'Prob':<8} {'Conf':<8}")
        print("-" * 60)
        
        for pred in predictions:
            match = pred['match'][:23] + ".." if len(pred['match']) > 25 else pred['match']
            prob = pred['home_prob'] if pred['winner'] == 'Hjemme' else pred['away_prob']
            print(f"{match:<25} {pred['winner']:<8} {prob:<8.1%} {pred['confidence']:<8.1%}")
    
    def run(self):
        """Hovedprogram"""
        print("🎯 HÅNDBOL NÆSTE RUNDE PREDICTOR")
        print("=" * 50)
        
        while True:
            print("\n🔧 VÆLG LIGA:")
            print("1. Herreliga")
            print("2. Kvindeliga")
            print("3. Afslut")
            
            choice = input("\nValg (1-3): ").strip()
            
            if choice == '3':
                break
            elif choice in ['1', '2']:
                league = 'Herreliga' if choice == '1' else 'Kvindeliga'
                
                if not self.predictors[league]:
                    print(f"❌ {league} ikke tilgængelig")
                    continue
                
                self.show_teams(league)
                matches = self.input_matches(league)
                
                if matches:
                    predictions = self.predict_matches(league, matches)
                    self.show_summary(league, predictions)
            else:
                print("❌ Ugyldigt valg")

if __name__ == "__main__":
    try:
        predictor = NextRoundPredictor()
        predictor.run()
    except KeyboardInterrupt:
        print("\n👋 Afbrudt")
    except Exception as e:
        print(f"❌ Fejl: {e}") 