#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FORBEDRET INTELLIGENT ELO VÆGTNINGSSYSTEM
=========================================

FORBEDRINGER:
✅ Alle spillere påvirkes af ALLE hændelser
✅ Alle hændelser fra data.md er dækket
✅ Tilstrækkelige negative vægte for minus ELO ved dårlige kampe
✅ Balanceret så ingen position er benadeligt
✅ Dybere balance analyse med flere metriker

VIGTIGE PRINCIPPER:
- "Forårs. str." = NEGATIVT (du forårsager modstanderens straffe)
- "Tilkendt straffe" = POSITIVT (dit hold får straffe)
- Negative handlinger skal kunne give minus ELO ved dårlige kampe
- Alle positioner skal have samme muligheder over mange kampe
"""

import numpy as np
from collections import defaultdict

class ImprovedEloWeights:
    
    def __init__(self):
        """Initialiserer det forbedrede vægtningssystem"""
        
        print("FORBEDRET INTELLIGENT ELO VÆGTNINGSSYSTEM")
        print("=" * 60)
        
        # === KOMPLETTE BASIS VÆGTE (ALLE HÆNDELSER FRA DATA.MD) ===
        
        self.base_action_weights = {
            
            # === STORE POSITIVE HANDLINGER ===
            'Mål': 100,                         # Hovedmål i spillet
            'Assist': 75,                       # Direkte bidrag til mål
            'Straffekast reddet': 120,          # Målvogter redder straffe (meget sjældent)
            'Skud reddet': 90,                  # Målvogter redning
            'Mål på straffe': 85,               # Straffemål (lidt lettere end almindeligt mål)
            
            # === MODERATE POSITIVE HANDLINGER ===
            'Bold erobret': 55,                 # Defensiv erobring
            'Blok af (ret)': 50,                # Blokering med tilbagevinding
            'Blokeret af': 45,                  # Blokering af skud
            'Tilkendt straffe': 35,             # Dit hold får straffe
            'Retur': 30,                        # Får returen efter skud
            
            # === LILLE POSITIVE/NEUTRALE ===
            'Skud på stolpe': -5,               # Næsten mål (lille negativ)
            'Straffekast på stolpe': -10,       # Straffe på stolpe (større negativ)
            
            # === MODERATE NEGATIVE HANDLINGER ===
            'Skud forbi': -20,                  # Brændt skud
            'Skud blokeret': -15,               # Skud blev blokeret
            'Straffekast forbi': -35,           # Brændt straffe (stor negativ)
            'Passivt spil': -25,                # Passivt spil sanktion
            'Regelfejl': -30,                   # Teknisk regelovertrædelse
            'Tabt bold': -35,                   # Miste bolden
            'Fejlaflevering': -40,              # Teknisk fejl
            'Forårs. str.': -45,                # NEGATIVT: Du forårsager modstanderens straffe
            
            # === STORE NEGATIVE HANDLINGER (DISCIPLINÆRE) ===
            'Advarsel': -20,                    # Gult kort
            'Udvisning': -60,                   # 2 minutter udvisning
            'Udvisning (2x)': -100,             # Dobbelt udvisning
            'Blåt kort': -80,                   # Blåt kort (alvorligt)
            'Rødt kort': -120,                  # Rødt kort
            'Rødt kort, direkte': -120,         # Direkte rødt kort
            'Protest': -30,                     # Protest
            
            # === ADMINISTRATIVE (NEUTRALE) ===
            'Time out': 0, 'Start 1:e halvleg': 0, 'Halvleg': 0,
            'Start 2:e halvleg': 0, 'Fuld tid': 0, 'Kamp slut': 0,
            'Video Proof': 0, 'Video Proof slut': 0, 'Start': 0
        }
        
        # === POSITIONS-SPECIFIKKE MULTIPLIERS ===
        # VIGTIGT: Alle positioner påvirkes af ALLE hændelser!
        # Multipliers justerer kun styrken, fjerner ikke handlinger
        
        self.position_multipliers = {
            
            'MV': {  # MÅLVOGTER
                'name': 'Målvogter',
                'role': 'Defensiv specialist og sidste forsvarslinje',
                
                # STORE BONUSER FOR MÅLVOGTER HANDLINGER
                'Skud reddet': 2.2,                # Deres hovedopgave
                'Straffekast reddet': 2.8,          # Ekstremt vigtigt
                'Mål': 5.0,                         # Målvogter mål er legendariske
                'Assist': 2.5,                      # Målvogter assist er speciel
                'Bold erobret': 1.4,                # Godt når målvogtere erobrer
                
                # MODERATE PÅVIRKNINGER
                'Blokeret af': 1.2,                 # Kan blokere i zona
                'Blok af (ret)': 1.2,               # Defensiv rolle
                'Retur': 1.3,                       # Vigtig at få returen
                
                # STØRRE STRAFFE FOR MÅLVOGTER FEJL
                'Fejlaflevering': 1.5,              # Målvogter fejl er kritiske
                'Tabt bold': 1.4,                   # Kan ikke tabe bolden
                'Regelfejl': 1.3,                   # Skal være disciplineret
                'Passivt spil': 1.2,                # Mindre påvirkning
                
                # STANDARD FOR ALLE ANDRE HANDLINGER
                'default': 1.0
            },
            
            'VF': {  # VENSTRE FLØJ
                'name': 'Venstre fløj',
                'role': 'Hurtig angriber og kontraspil specialist',
                
                # OFFENSIVE BONUSER
                'Mål': 1.5,                         # Fløjspillere skal score
                'Bold erobret': 1.6,                # Vigtig i kontraspil
                'Retur': 1.3,                       # Vigtig at få rebounds
                
                # MODERATE BONUSER
                'Assist': 0.8,                      # Mindre assist rolle end backs
                'Tilkendt straffe': 1.2,            # Kan provocere straffe
                
                # STØRRE STRAFFE FOR BRÆNDTE CHANCER
                'Skud forbi': 1.4,                  # Fløjspillere skal ramme
                'Straffekast forbi': 1.3,           # Skal score straffe
                'Skud blokeret': 1.2,               # Skal finde bedre vinkel
                
                # STANDARD FOR ANDRE
                'default': 1.0
            },
            
            'HF': {  # HØJRE FLØJ
                'name': 'Højre fløj',
                'role': 'Hurtig angriber og kontraspil specialist',
                
                # SAMME SOM VENSTRE FLØJ
                'Mål': 1.5, 'Bold erobret': 1.6, 'Retur': 1.3,
                'Assist': 0.8, 'Tilkendt straffe': 1.2,
                'Skud forbi': 1.4, 'Straffekast forbi': 1.3, 'Skud blokeret': 1.2,
                'default': 1.0
            },
            
            'VB': {  # VENSTRE BACK
                'name': 'Venstre back',
                'role': 'Defensiv organisator og opbygningsspiller',
                
                # DEFENSIVE BONUSER
                'Bold erobret': 1.7,                # Hovedopgave
                'Blokeret af': 1.5,                 # Defensiv rolle
                'Blok af (ret)': 1.5,               # Vigtig defensiv handling
                
                # OPBYGNINGS BONUSER
                'Assist': 1.4,                      # Vigtig rolle
                'Tilkendt straffe': 1.3,            # Kan provocere
                
                # STØRRE STRAFFE FOR BACK FEJL
                'Fejlaflevering': 1.5,              # Back fejl er meget kritiske
                'Tabt bold': 1.3,                   # Skal ikke tabe bolden
                'Forårs. str.': 1.3,                # Back fejl giver ofte straffe
                
                # MODERATE PÅVIRKNING AF SCORING
                'Mål': 0.9,                         # Mindre scoring fokus
                
                'default': 1.0
            },
            
            'PL': {  # PLAYMAKER
                'name': 'Playmaker',
                'role': 'Kreatív dirigent og spillets hjerne',
                
                # KÆMPE ASSIST BONUS
                'Assist': 2.0,                      # Deres hovedopgave
                'Tilkendt straffe': 1.5,            # Vigtig at provocere
                
                # MODERATE SCORING
                'Mål': 0.8,                         # Mindre scoring rolle
                'Bold erobret': 1.2,                # Vigtig i omstillinger
                
                # STORE STRAFFE FOR PLAYMAKER FEJL
                'Fejlaflevering': 1.8,              # MEGET kritiske fejl
                'Tabt bold': 1.6,                   # Skal kontrollere spillet
                'Forårs. str.': 1.5,                # Playmaker fejl er dyre
                'Regelfejl': 1.4,                   # Skal være disciplineret
                'Passivt spil': 1.3,                # Deres ansvar at drive spil
                
                'default': 1.0
            },
            
            'HB': {  # HØJRE BACK
                'name': 'Højre back',
                'role': 'Defensiv organisator og opbygningsspiller',
                
                # SAMME SOM VENSTRE BACK
                'Bold erobret': 1.7, 'Blokeret af': 1.5, 'Blok af (ret)': 1.5,
                'Assist': 1.4, 'Tilkendt straffe': 1.3,
                'Fejlaflevering': 1.5, 'Tabt bold': 1.3, 'Forårs. str.': 1.3,
                'Mål': 0.9,
                'default': 1.0
            },
            
            'ST': {  # STREG
                'name': 'Streg',
                'role': 'Fysisk kriger og målfarlig spiller',
                
                # OFFENSIVE BONUSER
                'Mål': 1.6,                         # Skal score mange mål
                'Bold erobret': 1.4,                # Fysisk spil
                'Tilkendt straffe': 1.4,            # Provokerer ofte straffe
                
                # DEFENSIVE BONUSER
                'Blokeret af': 1.4,                 # Defensiv i zona
                'Blok af (ret)': 1.4,               # Vigtig i forsvar
                
                # ACCEPTERET FYSISK SPIL (mindre straffe)
                'Udvisning': 0.8,                   # Stregspillere bliver ofte udvist
                'Regelfejl': 0.9,                   # Fysisk spil er accepteret
                'Forårs. str.': 0.9,                # Fysisk kontakt normal
                
                # MODERATE ANDRE
                'Assist': 0.7,                      # Mindre assist rolle
                
                'default': 1.0
            }
        }
        
        print(f"✅ {len(self.base_action_weights)} handlinger defineret")
        print(f"🎯 {len(self.position_multipliers)} positioner med multipliers")
        print("⚖️ ALLE positioner påvirkes af ALLE handlinger!")
        
        # Valider systemet
        self.validate_comprehensive_balance()
        
    def validate_comprehensive_balance(self):
        """Omfattende balance validering med flere metriker"""
        print("\n🔍 OMFATTENDE BALANCE VALIDERING")
        print("=" * 60)
        
        # Beregn potentialer for alle positioner
        position_stats = {}
        
        for position, multipliers in self.position_multipliers.items():
            stats = {
                'positive_actions': [],
                'negative_actions': [],
                'neutral_actions': [],
                'total_positive': 0,
                'total_negative': 0,
                'action_count': 0
            }
            
            # Gennemgå ALLE handlinger
            for action, base_weight in self.base_action_weights.items():
                multiplier = multipliers.get(action, multipliers.get('default', 1.0))
                final_weight = base_weight * multiplier
                
                stats['action_count'] += 1
                
                if final_weight > 0:
                    stats['positive_actions'].append(final_weight)
                    stats['total_positive'] += final_weight
                elif final_weight < 0:
                    stats['negative_actions'].append(abs(final_weight))
                    stats['total_negative'] += abs(final_weight)
                else:
                    stats['neutral_actions'].append(0)
            
            position_stats[position] = stats
        
        # Analyser balance med flere metriker
        print("📊 BALANCE METRIKER PER POSITION:")
        print("-" * 60)
        
        ratios = []
        positive_potentials = []
        negative_impacts = []
        
        for position, stats in position_stats.items():
            pos_info = self.position_multipliers[position]
            
            # Beregn forskellige metriker
            positive_mean = np.mean(stats['positive_actions']) if stats['positive_actions'] else 0
            positive_std = np.std(stats['positive_actions']) if len(stats['positive_actions']) > 1 else 0
            positive_max = max(stats['positive_actions']) if stats['positive_actions'] else 0
            
            negative_mean = np.mean(stats['negative_actions']) if stats['negative_actions'] else 0
            negative_std = np.std(stats['negative_actions']) if len(stats['negative_actions']) > 1 else 0
            negative_max = max(stats['negative_actions']) if stats['negative_actions'] else 0
            
            ratio = stats['total_positive'] / stats['total_negative'] if stats['total_negative'] > 0 else float('inf')
            
            ratios.append(ratio if ratio != float('inf') else 0)
            positive_potentials.append(stats['total_positive'])
            negative_impacts.append(stats['total_negative'])
            
            print(f"\n{position} - {pos_info['name']}:")
            print(f"  📈 Positivt potentiale: {stats['total_positive']:.0f}")
            print(f"     • Gennemsnit: {positive_mean:.1f}, Max: {positive_max:.0f}, Std: {positive_std:.1f}")
            print(f"  📉 Negativt impact: {stats['total_negative']:.0f}")
            print(f"     • Gennemsnit: {negative_mean:.1f}, Max: {negative_max:.0f}, Std: {negative_std:.1f}")
            print(f"  ⚖️ Ratio: {ratio:.2f}")
            print(f"  🎯 Handlinger dækket: {stats['action_count']}/{len(self.base_action_weights)}")
        
        # Samlet balance analyse
        print(f"\n🎯 SAMLET BALANCE ANALYSE:")
        print("-" * 40)
        
        ratio_mean = np.mean(ratios)
        ratio_std = np.std(ratios)
        ratio_range = max(ratios) - min(ratios)
        
        pos_mean = np.mean(positive_potentials)
        pos_std = np.std(positive_potentials)
        pos_cv = pos_std / pos_mean if pos_mean > 0 else 0  # Coefficient of variation
        
        neg_mean = np.mean(negative_impacts)
        neg_std = np.std(negative_impacts)
        neg_cv = neg_std / neg_mean if neg_mean > 0 else 0
        
        print(f"Ratio balance:")
        print(f"  • Gennemsnit: {ratio_mean:.2f}")
        print(f"  • Standardafvigelse: {ratio_std:.2f}")
        print(f"  • Range: {ratio_range:.2f}")
        
        print(f"Positivt potentiale:")
        print(f"  • Gennemsnit: {pos_mean:.0f}")
        print(f"  • Variation koefficient: {pos_cv:.2%}")
        
        print(f"Negativt impact:")
        print(f"  • Gennemsnit: {neg_mean:.0f}")
        print(f"  • Variation koefficient: {neg_cv:.2%}")
        
        # Balance konklusion
        print(f"\n🏆 BALANCE VURDERING:")
        
        excellent_balance = ratio_range < 0.5 and pos_cv < 0.15 and neg_cv < 0.15
        good_balance = ratio_range < 1.0 and pos_cv < 0.25 and neg_cv < 0.25
        
        if excellent_balance:
            print("✅ FREMRAGENDE BALANCE! Alle positioner har næsten identiske muligheder")
        elif good_balance:
            print("✅ GOD BALANCE! Systemet er fair for alle positioner")
        else:
            print("⚠️ BALANCE PROBLEMER! Nogle positioner kan være benadeligt")
            
        # Tjek negative vægte styrke
        print(f"\n⚠️ NEGATIVE VÆGTE ANALYSE:")
        total_negative_weight = sum(abs(w) for w in self.base_action_weights.values() if w < 0)
        total_positive_weight = sum(w for w in self.base_action_weights.values() if w > 0)
        negative_ratio = total_negative_weight / total_positive_weight
        
        print(f"  • Total negative vægt: {total_negative_weight:.0f}")
        print(f"  • Total positive vægt: {total_positive_weight:.0f}")
        print(f"  • Negative/Positive ratio: {negative_ratio:.2%}")
        
        if negative_ratio > 0.6:
            print("✅ Negative vægte er tilstrækkelige for minus ELO ved dårlige kampe")
        elif negative_ratio > 0.4:
            print("⚖️ Negative vægte er moderate - kan give mindre ELO tab")
        else:
            print("⚠️ Negative vægte kan være for svage!")
            
    def get_action_weight(self, action: str, position: str) -> float:
        """Beregner endelig vægt for handling på position"""
        base_weight = self.base_action_weights.get(action, 0)
        
        if base_weight == 0:
            return 0.0
            
        if position in self.position_multipliers:
            multipliers = self.position_multipliers[position]
            multiplier = multipliers.get(action, multipliers.get('default', 1.0))
        else:
            multiplier = 1.0
            
        return base_weight * multiplier
        
    def analyze_negative_impact(self):
        """Analyserer hvor meget negative handlinger kan påvirke ELO"""
        print("\n⚠️ NEGATIVE IMPACT ANALYSE")
        print("=" * 50)
        
        print("Eksempler på negative påvirkninger per position:")
        
        # Simuler en dårlig kamp for hver position
        bad_game_scenarios = {
            'MV': ['Fejlaflevering', 'Tabt bold', 'Regelfejl', 'Advarsel'],
            'VF': ['Skud forbi', 'Skud forbi', 'Fejlaflevering', 'Udvisning'],
            'HF': ['Skud forbi', 'Straffekast forbi', 'Fejlaflevering', 'Advarsel'],
            'VB': ['Fejlaflevering', 'Tabt bold', 'Forårs. str.', 'Regelfejl'],
            'PL': ['Fejlaflevering', 'Fejlaflevering', 'Tabt bold', 'Forårs. str.'],
            'HB': ['Fejlaflevering', 'Tabt bold', 'Forårs. str.', 'Advarsel'],
            'ST': ['Skud forbi', 'Udvisning', 'Regelfejl', 'Forårs. str.']
        }
        
        for position, bad_actions in bad_game_scenarios.items():
            total_negative = 0
            pos_info = self.position_multipliers[position]
            
            print(f"\n{position} - {pos_info['name']} (dårlig kamp):")
            for action in bad_actions:
                weight = self.get_action_weight(action, position)
                total_negative += weight
                print(f"  • {action}: {weight:+.0f} point")
            
            print(f"  💥 Total impact: {total_negative:+.0f} point")
            
    def test_balance_scenarios(self):
        """Tester balance med typiske kamp scenarier"""
        print("\n🎮 BALANCE TEST MED TYPISKE KAMPE")
        print("=" * 50)
        
        # Typiske kampe for hver position
        typical_games = {
            'MV': [('Skud reddet', 8), ('Mål', 0), ('Assist', 1), ('Fejlaflevering', 1)],
            'VF': [('Mål', 2), ('Assist', 1), ('Bold erobret', 3), ('Skud forbi', 2)],
            'HF': [('Mål', 2), ('Assist', 1), ('Bold erobret', 3), ('Skud forbi', 2)],
            'VB': [('Mål', 1), ('Assist', 3), ('Bold erobret', 4), ('Fejlaflevering', 2)],
            'PL': [('Mål', 1), ('Assist', 5), ('Tilkendt straffe', 2), ('Fejlaflevering', 3)],
            'HB': [('Mål', 1), ('Assist', 3), ('Bold erobret', 4), ('Fejlaflevering', 2)],
            'ST': [('Mål', 3), ('Assist', 1), ('Bold erobret', 2), ('Udvisning', 1)]
        }
        
        print("Typisk kamp ELO påvirkning per position:")
        for position, actions in typical_games.items():
            total_impact = 0
            pos_info = self.position_multipliers[position]
            
            print(f"\n{position} - {pos_info['name']}:")
            for action, count in actions:
                weight = self.get_action_weight(action, position)
                impact = weight * count
                total_impact += impact
                print(f"  • {action} x{count}: {impact:+.0f} point")
            
            print(f"  🎯 Total kamp impact: {total_impact:+.0f} point")


# === TEST SYSTEM ===
def test_improved_system():
    """Tester det forbedrede system"""
    
    weights = ImprovedEloWeights()
    
    # Test negative impact
    weights.analyze_negative_impact()
    
    # Test typiske kampe
    weights.test_balance_scenarios()
    
    print("\n📋 EKSEMPEL VÆGTNINGER:")
    print("=" * 50)
    
    examples = [
        ('Mål', 'MV', 'Målvogter scorer'),
        ('Mål', 'ST', 'Streg scorer'),
        ('Assist', 'PL', 'Playmaker assisterer'),
        ('Fejlaflevering', 'PL', 'Playmaker fejl'),
        ('Udvisning', 'ST', 'Streg udvist'),
        ('Skud reddet', 'MV', 'Målvogter redder'),
        ('Bold erobret', 'VB', 'Back erobrer'),
        ('Forårs. str.', 'VB', 'Back forårsager straffe'),
    ]
    
    for action, position, desc in examples:
        weight = weights.get_action_weight(action, position)
        print(f"{desc}: {weight:+.0f} point")


if __name__ == "__main__":
    test_improved_system() 