#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
INTELLIGENTE ELO VÆGTE - BASERET PÅ DATA.MD ANALYSE
=====================================================

Dette system definerer:
1. Basis-vægte for alle hændelser fra data.md
2. Positions-specifikke multipliers
3. Balanceret system så ingen position bliver benadeligt

DESIGN PRINCIPPER:
- Alle 7 standard håndboldpositioner får fair behandling
- Målvogtere får høje vægte for defensive aktioner
- Offensive spillere får vægte for mål og assists  
- Defensive spillere får vægte for erobringer og blokkeringer
- Disciplinære straffe påvirker alle positioner ens
- Positions-specifikke bonuser sikrer balance
"""

class IntelligentEloWeights:
    
    def __init__(self):
        """Initialiserer det intelligente vægtningssystem"""
        
        print("INITIALISERER INTELLIGENTE ELO VÆGTE")
        print("=" * 50)
        
        # === BASIS HÆNDELSESVÆRGTE (fra data.md) ===
        # Designet efter håndboldstrategisk vigtighed
        
        self.base_action_weights = {
            
            # === OFFENSIVE HANDLINGER (POSITIVE) ===
            'Mål': 100,                         # Vigtigste offensive handling
            'Mål på straffe': 85,               # Straffemål (lidt mindre vægt da lettere)
            'Assist': 75,                       # Assist til mål - meget vigtigt
            
            # === DEFENSIVE HANDLINGER (POSITIVE) ===
            'Skud reddet': 90,                  # Målvogter redning - meget vigtigt
            'Straffekast reddet': 120,          # Strafferedning - ekstra vigtigt
            'Bold erobret': 50,                 # Defensiv erobring
            'Blokeret af': 40,                  # Blokering af skud
            'Blok af (ret)': 45,                # Blokering med tilbagevinding
            'Retur': 25,                        # Få returen efter skud
            
            # === MINDRE POSITIVE HANDLINGER ===
            'Tilkendt straffe': 30,             # Provoceret straffekast
            
            # === NEUTRALE/TEKNISKE HANDLINGER ===
            'Skud forbi': -15,                  # Brændt skud (lille negativ)
            'Skud på stolpe': -8,               # Skud på stolpe (næsten mål)
            'Skud blokeret': -5,                # Skud blev blokeret
            'Straffekast forbi': -25,           # Brændt straffe (mere negativt)
            'Straffekast på stolpe': -15,       # Straffe på stolpe
            
            # === TEKNISKE FEJL (NEGATIVE) ===
            'Fejlaflevering': -35,              # Teknisk fejl
            'Tabt bold': -30,                   # Miste bolden
            'Regelfejl': -25,                   # Regelovertrædelse
            'Passivt spil': -20,                # Passivt spil sanktion
            
            # === DISCIPLINÆRE STRAFFE (NEGATIVE) ===
            'Advarsel': -15,                    # Gult kort
            'Udvisning': -50,                   # 2 minutter
            'Udvisning (2x)': -80,              # Dobbelt udvisning
            'Rødt kort': -100,                  # Rødt kort
            'Rødt kort, direkte': -100,         # Direkte rødt kort
            'Blåt kort': -60,                   # Blåt kort
            'Protest': -25,                     # Protest
            
            # === SEKUNDÆRE HANDLINGER ===
            'Forårs. str.': -40,                # Forårsage straffekast (negativt)
            
            # === ADMINISTRATIVE (NEUTRALE) ===
            'Time out': 0,
            'Start 1:e halvleg': 0,
            'Halvleg': 0,
            'Start 2:e halvleg': 0,
            'Fuld tid': 0,
            'Kamp slut': 0,
            'Video Proof': 0,
            'Video Proof slut': 0,
            'Start': 0
        }
        
        # === POSITIONS-SPECIFIKKE MULTIPLIERS ===
        # Design: Hver position får bonuser for deres specialiteter
        
        self.position_multipliers = {
            
            'MV': {  # MÅLVOGTER - Defensiv specialist
                'name': 'Målvogter',
                'role': 'Defensiv specialist, skal redde skud og organisere forsvar',
                
                # MASSIVE BONUSER FOR DEFENSIVE AKTIONER
                'Skud reddet': 2.0,                # Kæmpe bonus for redninger
                'Straffekast reddet': 2.5,          # Endnu større bonus for strafferedning
                
                # MODERATE BONUSER
                'Bold erobret': 1.3,                # Målvogtere kan erobre bolde
                'Mål': 4.0,                         # Målvogter mål er ekstremt sjældne
                'Assist': 2.0,                      # Målvogter assist er speciel
                
                # STRAFFEREDUKTIONER  
                'Fejlaflevering': 1.4,              # Målvogter fejl er kritiske
                'Tabt bold': 1.3,                   # Målvogter skal ikke tabe bolden
                'Regelfejl': 1.2,                   # Målvogter skal være disciplineret
                
                # STANDARD FOR RESTEN
                'default': 1.0
            },
            
            'VF': {  # VENSTRE FLØJ - Hurtig angriber
                'name': 'Venstre fløj',
                'role': 'Hurtig angriber, kontraspil, skal score fra fløjen',
                
                # OFFENSIVE BONUSER
                'Mål': 1.4,                         # Fløjspillere skal score
                'Bold erobret': 1.5,                # Vigtig i kontraspil
                'Assist': 0.9,                      # Mindre assist rolle
                
                # NEGATIVE PÅVIRKNINGER
                'Skud forbi': 1.3,                  # Fløjspillere skal ramme målet
                'Fejlaflevering': 1.1,              # Teknisk presition vigtigt
                
                # STANDARD FOR RESTEN
                'default': 1.0
            },
            
            'HF': {  # HØJRE FLØJ - Hurtig angriber
                'name': 'Højre fløj', 
                'role': 'Hurtig angriber, kontraspil, skal score fra fløjen',
                
                # SAMME SOM VENSTRE FLØJ
                'Mål': 1.4,
                'Bold erobret': 1.5,
                'Assist': 0.9,
                'Skud forbi': 1.3,
                'Fejlaflevering': 1.1,
                'default': 1.0
            },
            
            'VB': {  # VENSTRE BACK - Defensiv organisator
                'name': 'Venstre back',
                'role': 'Defensiv organisator, skal erobre bolde og distribuere spil',
                
                # DEFENSIVE BONUSER
                'Bold erobret': 1.6,                # Backs skal erobre bolde
                'Blokeret af': 1.4,                 # Defensiv rolle
                'Blok af (ret)': 1.4,               # Defensiv blokering
                
                # OPBYGNINGSSPIL BONUSER
                'Assist': 1.3,                      # Vigtig i opbygningsspil
                
                # STRAFFEREDUKTIONER FOR FEJL
                'Fejlaflevering': 1.4,              # Back fejl er kritiske
                'Tabt bold': 1.2,                   # Backs skal ikke tabe bolden
                
                # STANDARD FOR RESTEN
                'default': 1.0
            },
            
            'PL': {  # PLAYMAKER - Kreatív dirigent
                'name': 'Playmaker',
                'role': 'Kreatív dirigent, skal assistere og styre spillet',
                
                # KÆMPE ASSIST BONUS
                'Assist': 1.8,                      # Playmaker skal assistere
                'Tilkendt straffe': 1.4,            # Playmaker kan provocere straffe
                
                # MODERATE SCORING
                'Mål': 0.9,                         # Mindre scoring fokus
                
                # STORE STRAFFEREDUKTIONER FOR FEJL
                'Fejlaflevering': 1.6,              # Playmaker fejl er meget kritiske
                'Tabt bold': 1.4,                   # Playmaker skal ikke tabe bolden
                'Regelfejl': 1.3,                   # Disciplin vigtig for playmaker
                
                # STANDARD FOR RESTEN
                'default': 1.0
            },
            
            'HB': {  # HØJRE BACK - Defensiv organisator
                'name': 'Højre back',
                'role': 'Defensiv organisator, skal erobre bolde og distribuere spil',
                
                # SAMME SOM VENSTRE BACK
                'Bold erobret': 1.6,
                'Blokeret af': 1.4,
                'Blok af (ret)': 1.4,
                'Assist': 1.3,
                'Fejlaflevering': 1.4,
                'Tabt bold': 1.2,
                'default': 1.0
            },
            
            'ST': {  # STREG - Fysisk kriger
                'name': 'Streg',
                'role': 'Fysisk kriger, skal score tæt på mål og spille fysisk',
                
                # OFFENSIVE BONUSER
                'Mål': 1.5,                         # Stregspillere skal score
                'Bold erobret': 1.3,                # Vigtig i fysisk spil
                
                # DEFENSIVE BONUSER
                'Blokeret af': 1.3,                 # Defensiv i zona
                'Blok af (ret)': 1.3,               # Blokering i forsvaret
                
                # ACCEPTERET FYSISK SPIL
                'Udvisning': 0.9,                   # Stregspillere får ofte udvisninger
                'Regelfejl': 0.95,                  # Fysisk spil accepteret
                
                # STANDARD FOR RESTEN
                'default': 1.0
            }
        }
        
        print("Intelligente vægte initialiseret")
        print(f"Basis handlinger: {len(self.base_action_weights)}")
        print(f"Positioner med multipliers: {len(self.position_multipliers)}")
        
        # Valider systemet
        self.validate_system()
        
    def validate_system(self):
        """Validerer at vægtningssystemet er balanceret"""
        print("\nVALIDERER BALANCE I SYSTEMET")
        print("-" * 40)
        
        # Check at alle positioner har fair muligheder
        position_potentials = {}
        
        for position, multipliers in self.position_multipliers.items():
            positive_potential = 0
            negative_impact = 0
            
            # Beregn potentiale for positive handlinger
            for action, base_weight in self.base_action_weights.items():
                if base_weight > 0:
                    multiplier = multipliers.get(action, multipliers.get('default', 1.0))
                    positive_potential += base_weight * multiplier
                    
                elif base_weight < 0:
                    multiplier = multipliers.get(action, multipliers.get('default', 1.0))
                    negative_impact += abs(base_weight) * multiplier
            
            position_potentials[position] = {
                'positive': positive_potential,
                'negative': negative_impact,
                'ratio': positive_potential / negative_impact if negative_impact > 0 else float('inf')
            }
            
            print(f"{position} ({multipliers['name']}):")
            print(f"   Positiv potentiale: {positive_potential:.0f}")
            print(f"   Negativ påvirkning: {negative_impact:.0f}")
            print(f"   Ratio: {position_potentials[position]['ratio']:.2f}")
        
        # Check balance
        ratios = [p['ratio'] for p in position_potentials.values() if p['ratio'] != float('inf')]
        avg_ratio = sum(ratios) / len(ratios)
        ratio_spread = max(ratios) - min(ratios)
        
        print(f"\nBALANCE ANALYSE:")
        print(f"   Gennemsnit ratio: {avg_ratio:.2f}")
        print(f"   Ratio spredning: {ratio_spread:.2f}")
        
        if ratio_spread < 1.0:
            print("SYSTEMET ER GODT BALANCERET!")
        elif ratio_spread < 2.0:
            print("Systemet er rimeligt balanceret")
        else:
            print("Systemet kan have balance problemer")
            
    def get_action_weight(self, action: str, position: str) -> float:
        """
        Beregner den endelige vægt for en handling på en given position
        """
        # Basis vægt
        base_weight = self.base_action_weights.get(action, 0)
        
        if base_weight == 0:
            return 0.0
            
        # Position multiplier
        if position in self.position_multipliers:
            multipliers = self.position_multipliers[position]
            multiplier = multipliers.get(action, multipliers.get('default', 1.0))
        else:
            multiplier = 1.0
            
        # Endelig vægt
        final_weight = base_weight * multiplier
        
        return final_weight
        
    def analyze_position_strengths(self):
        """Analyserer hver positions styrker og svagheder"""
        print("\nPOSITIONS ANALYSE")
        print("=" * 50)
        
        for position, multipliers in self.position_multipliers.items():
            print(f"\n{position} - {multipliers['name']}")
            print(f"Rolle: {multipliers['role']}")
            print("Specialiteter:")
            
            # Find bonuser (multiplier > 1.2)
            bonuses = []
            for action, multiplier in multipliers.items():
                if action not in ['name', 'role', 'default']:
                    if isinstance(multiplier, (int, float)) and multiplier > 1.2:
                        base_weight = self.base_action_weights.get(action, 0)
                        final_weight = base_weight * multiplier
                        bonuses.append((action, multiplier, final_weight))
            
            bonuses.sort(key=lambda x: x[2], reverse=True)
            for action, multiplier, final_weight in bonuses[:5]:
                print(f"   • {action}: {multiplier:.1f}x = {final_weight:.0f} point")
                
    def get_all_actions(self):
        """Returnerer alle mulige handlinger"""
        return list(self.base_action_weights.keys())
        
    def get_all_positions(self):
        """Returnerer alle positioner"""
        return list(self.position_multipliers.keys())


# === DEMONSTRATION ===
def demonstrate_system():
    """Demonstrerer vægtningssystemet"""
    
    weights = IntelligentEloWeights()
    
    # Analyser positioners styrker
    weights.analyze_position_strengths()
    
    print("\nEKSEMPLER PÅ VÆGTNINGER")
    print("=" * 50)
    
    # Test eksempler
    test_cases = [
        ('Mål', 'MV', 'Målvogter scorer mål'),
        ('Mål', 'VF', 'Venstre fløj scorer mål'),  
        ('Mål', 'ST', 'Streg scorer mål'),
        ('Skud reddet', 'MV', 'Målvogter redder skud'),
        ('Assist', 'PL', 'Playmaker laver assist'),
        ('Bold erobret', 'VB', 'Venstre back erobrer bold'),
        ('Fejlaflevering', 'PL', 'Playmaker laver fejlaflevering'),
        ('Udvisning', 'ST', 'Streg bliver udvist'),
    ]
    
    for action, position, description in test_cases:
        weight = weights.get_action_weight(action, position)
        print(f"{description}: {weight:+.0f} point")


if __name__ == "__main__":
    demonstrate_system() 