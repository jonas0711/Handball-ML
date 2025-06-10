#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
📦 CENTRAL TEAM CONFIGURATION (REFACTORED)
===========================================

This file serves as the single source of truth for all team-related data.

REFACTOR HIGHLIGHTS:
- Separated team name mappings into `HERRELIGA_NAME_MAPPINGS` and
  `KVINDELIGA_NAME_MAPPINGS` to eliminate ambiguity between leagues.
- This prevents conflicts where team names like 'SønderjyskE' or 'TMS Ringsted'
  exist in both leagues, ensuring each script uses the correct context.
- The old, shared `TEAM_NAME_MAPPINGS` has been deprecated and removed.

Jonas' Custom System - December 2024
"""

# Teams to skip during processing (problematic or invalid codes)
SKIP_TEAMS = {
    'UNKNOWN', 'UNK', 'NULL', 'N/A', 'HIH', 'OHC', 'RHK', 'HB', 'VF', 'HOJ'
}

# === GLOBAL ANALYSIS PARAMETERS ===
MIN_GAMES_FOR_TEAM_INCLUSION = 5  # Min games for a player's team to be considered primary

# Herreliga team mappings - Using new, specific codes
HERRELIGA_TEAMS = {
    'AAH': 'Aalborg Håndbold',
    'BSH': 'Bjerringbro-Silkeborg',
    'FHK': 'Fredericia Håndbold Klub',
    'GIF': 'Grindsted GIF Håndbold',
    'GOG': 'GOG',
    'KIF': 'KIF Kolding',
    'MTH': 'Mors-Thy Håndbold',
    'NSH': 'Nordsjælland Håndbold',
    'REH': 'Ribe-Esbjerg HH',
    'SAH': 'SAH - Skanderborg AGF',
    'SKH': 'Skjern Håndbold',
    'SJH': 'SønderjyskE Herrehåndbold',
    'TTH': 'TTH Holstebro',
    'TMH': 'TMS Ringsted',
    'LTH': 'Lemvig-Thyborøn Håndbold',
    'ARH': 'Århus Håndbold',
    'SFH': 'Skive fH',
    'AJH': 'Ajax København',
    'HØJ': 'HØJ Elite',
    'HCM': 'HC Midtjylland',
    'TSY': 'Team Sydhavsøerne',
    'TMT': 'TM Tønder Håndbold',
}

# Kvindeliga team mappings - Using new, specific codes
KVINDELIGA_TEAMS = {
    'AHB': 'Aarhus Håndbold Kvinder',
    'AAU': 'Aarhus United',
    'BFH': 'Bjerringbro FH',
    'EHA': 'EH Aalborg',
    'HHE': 'Horsens Håndbold Elite',
    'IKA': 'Ikast Håndbold',
    'KBH': 'København Håndbold',
    'NFH': 'Nykøbing F. Håndbold',
    'ODE': 'Odense Håndbold',
    'RIN': 'Ringkøbing Håndbold',
    'SVK': 'Silkeborg-Voel KFUM',
    'SKB': 'Skanderborg Håndbold',
    'SJK': 'SønderjyskE Kvindehåndbold',
    'TES': 'Team Esbjerg',
    'VHK': 'Viborg HK',
    'TMK': 'TMS Ringsted',
    'VEN': 'Vendsyssel Håndbold',
    'RAN': 'Randers HK',
    'HOL': 'Holstebro Håndbold',
    'AJK': 'Ajax København',
}

# Combined teams dictionary for general lookup
ALL_TEAMS = {**HERRELIGA_TEAMS, **KVINDELIGA_TEAMS}

# === HERRELIGA-SPECIFIC NAME MAPPINGS ===
HERRELIGA_NAME_MAPPINGS = {
    'aalborg håndbold': 'AAH', 'aalborg': 'AAH', 'aah': 'AAH',
    'bjerringbro-silkeborg': 'BSH', 'bjerringbro-silkeborg håndbold': 'BSH', 'bjerringbro silkeborg': 'BSH', 'bsh': 'BSH',
    'bsv': 'BSH',
    'fredericia håndbold': 'FHK', 'fredericia hk': 'FHK', 'fredericia': 'FHK', 'fhk': 'FHK',
    'grindsted gif håndbold': 'GIF', 'grindsted gif': 'GIF', 'grindsted': 'GIF',
    'gog': 'GOG',
    'gog håndbold': 'GOG',
    'høj elite': 'HOJ',
    'høj': 'HOJ',
    'kif kolding': 'KIF', 'kif kolding københavn': 'KIF', 'kif': 'KIF',
    'mors-thy håndbold': 'MTH', 'mors thy': 'MTH', 'mth': 'MTH',
    'nordsjælland håndbold': 'NSH', 'nordsjælland': 'NSH', 'nsh': 'NSH',
    'ribe-esbjerg hh': 'REH', 'ribe esbjerg': 'REH', 'reh': 'REH',
    'skanderborg håndbold': 'SAH', 'skanderborg agf': 'SAH', 'sah - skanderborg agf': 'SAH', 'sah': 'SAH', 'skanderborg-århus': 'SAH',
    'sbh': 'SAH',
    'skjern håndbold': 'SKH', 'skjern': 'SKH', 'skh': 'SKH',
    'sønderjyske herrehåndbold': 'SJH', 'sønderjyske herrer': 'SJH', 'sønderjyske': 'SJH', 'sønderjyske håndbold': 'SJH', 'sje': 'SJH',
    'tth holstebro': 'TTH', 'tth': 'TTH',
    'tms ringsted': 'TMH', 'tms ringsted herrer': 'TMH', 'tms': 'TMH',
    'lemvig-thyborøn håndbold': 'LTH', 'lemvig': 'LTH',
    'århus håndbold': 'ARH', 'aarhus håndbold': 'ARH',
    'skive fh': 'SFH', 'skive': 'SFH',
    'ajax københavn': 'AJH', 'ajax': 'AJH',
    'hc midtjylland': 'HCM',
    'team sydhavsøerne': 'TSY', 'sydhavsøerne': 'TSY', 'syd': 'TSY',
    'tm tønder håndbold': 'TMT', 'tm tønder': 'TMT',
}

# === KVINDELIGA-SPECIFIC NAME MAPPINGS ===
KVINDELIGA_NAME_MAPPINGS = {
    'aarhus united': 'AAU', 'aau': 'AAU',
    'aarhus håndbold kvinder': 'AHB',
    'ajax københavn': 'AJK', 'ajax kvinder': 'AJK', 'ajax': 'AJK',
    'ajx': 'AJK',
    'bjerringbro fh': 'BFH', 'bjerringbro': 'BFH',
    'eh aalborg': 'EHA',
    'horsens håndbold elite': 'HHE', 'horsens': 'HHE',

    'ikast håndbold': 'IKA', 'ikast': 'IKA', 'fc midtjylland': 'IKA', 'fcm': 'IKA', # Predecessor
    'københavn håndbold': 'KBH', 'københavn': 'KBH',
    'nykøbing f. håndbold': 'NFH', 'nykøbing': 'NFH',
    'odense håndbold': 'ODE', 'odense': 'ODE',
    'ringkøbing håndbold': 'RIN', 'ringkøbing': 'RIN',
    'silkeborg-voel kfum': 'SVK', 'silkeborg voel': 'SVK', 'voel kfum': 'SVK', 'voel': 'SVK', 'sil': 'SVK',
    'skanderborg håndbold': 'SKB', 'skanderborg': 'SKB',
    'sønderjyske kvindehåndbold': 'SJK', 'sønderjyske kvinder': 'SJK', 'sønderjyske': 'SJK', 'sje': 'SJK',
    'team esbjerg': 'TES', 'esbjerg': 'TES',
    'viborg hk': 'VHK', 'viborg': 'VHK',
    'tms ringsted': 'TMK', 'tms ringsted kvinder': 'TMK', 'tms': 'TMK',

    'vendsyssel håndbold': 'VEN',
    'randers hk': 'RAN', 'randers': 'RAN',
    'holstebro håndbold': 'HOL', 'holstebro': 'HOL',
    'ajax københavn': 'AJK', 'ajax kvinder': 'AJK', 'ajax': 'AJK',
    'ajx': 'AJK', # Added likely typo
}

# === PLAYER NAME ALIASES (FIX FOR HISTORICAL INCONSISTENCIES) ===
# This mapping helps bridge major name changes or persistent typos across seasons.
# The key is the ALIAS (old or incorrect name), and the value is the CANONICAL name.
# The system will normalize all aliases to the canonical name before processing.
PLAYER_NAME_ALIASES = {
    # Alias -> Canonical Name
    "Marinus MUNK": "Marinus Grandahl MUNK",
    "Mads HOXER": "Mads Hoxer HANGAARD",
    # Handles the extra space issue for Line Larsen programmatically, but an alias could be a backup
}

# --- DEPRECATED MAPPINGS (DO NOT USE) ---
# TEAM_NAME_MAPPINGS = { ... }

# BESKYTTEDE MARKSPILLERE - Spillere der ALDRIG skal klassificeres som målvogtere
# Baseret på detection script resultater - disse spillere er primært markspillere 
# men har fejlagtigt optrådt i målvogter-data
PROTECTED_FIELD_PLAYERS = {
    # HERRELIGA - Fejlklassificerede markspillere
    'Minik Dahl HØEGH',           # PL - 60.3% markspiller aktioner
    'Thomas Schultz CLAUSEN',      # HF - 62.5% markspiller aktioner  
    'Jonas EICHWALD',             # HF - 61.9% markspiller aktioner
    'Mathias Gliese JENSEN',      # HF - 60.7% markspiller aktioner
    'Jens Dolberg PLOUGSTRUP',    # PL - 60.6% markspiller aktioner
    'Frederik IVERSEN',           # VF - 60.1% markspiller aktioner
    'Anders MØLLER',              # HF - 61.7% markspiller aktioner
    'Mathias BITSCH',             # PL - 61.6% markspiller aktioner
    'Michael Krohn THØGERSEN',    # HF - 70.4% markspiller aktioner
    'Mathias DAUGÅRD',            # VF - 65.4% markspiller aktioner
    'Johan Thesbjerg KOFOED',     # PL - 60.6% markspiller aktioner
    'Árni Bragi EYJÓLFSSON',      # HF - 65.4% markspiller aktioner
    'Simon Damgaard JENSEN',      # VF - 60.0% markspiller aktioner
    'Mikkel SANDHOLM',            # HF - 63.7% markspiller aktioner
    'Anders FLÆNG',               # HF - 71.1% markspiller aktioner
    'Magnus SØNNICHSEN',          # HF - 60.9% markspiller aktioner
    'Oliver Sonne WOSNIAK',       # PL - 70.8% markspiller aktioner
    'Andreas Søgaard RASMUSSENAssist',  # ST - 72.7% markspiller aktioner
    'Andreas DYSSEHOLM',          # HF - 62.5% markspiller aktioner
    'Fredrik CLEMENTSEN',         # ST - 73.7% markspiller aktioner
    'Jens Kromann MØLLER',        # HF - 67.6% markspiller aktioner
    'Victor WOLF',                # VF - 62.2% markspiller aktioner
    'Mats GORDON',                # VF - 60.0% markspiller aktioner
    'Thomas THEILGAARD',          # HF - 62.7% markspiller aktioner
    'Hjalmar ANDERSEN',           # ST - 68.4% markspiller aktioner
    
    # KVINDELIGA - Fejlklassificerede markspillere
    'Camilla DEGN',               # VF - 60.8% markspiller aktioner
    'Annika JAKOBSEN',            # HF - 70.6% markspiller aktioner
    'Daniela GUSTIN',             # HF - 67.5% markspiller aktioner
    'Birna BERG HARALDSDOTTIR',   # PL - 70.0% markspiller aktioner
    'Frederikke Glavind HEDEGAARD', # HF - 67.7% markspiller aktioner
    'Emma NIELSEN',               # HF - 64.5% markspiller aktioner
    'Sofie Brems ØSTERGAARD',     # HF - 66.2% markspiller aktioner
    'Mathilde ORKILD',            # HF - 60.1% markspiller aktioner
    'Line Gyldenløve KRISTENSEN', # PL - 63.3% markspiller aktioner
    'Ida ANDERSEN',               # VF - 60.5% markspiller aktioner
    'Sofie NIELSEN',              # HF - 60.0% markspiller aktioner
    'Josefine THORSTED',          # HF - 64.3% markspiller aktioner
    'Melina KRISTENSEN',          # HF - 67.6% markspiller aktioner
    'Christina Jacobsen HANSEN',   # ST - 68.6% markspiller aktioner
    'Ida-Louise ANDERSEN',        # VF - 67.6% markspiller aktioner
    'Emilie BECH',                # HF - 67.0% markspiller aktioner
    'Sanne Beck HANSEN',          # HF - 60.4% markspiller aktioner
    'Tania Bilde KNUDSEN',        # HF - 67.8% markspiller aktioner
    'Frederikke HEDEGAARD',       # HF - 67.4% markspiller aktioner
    'Anne-Sofie Møldrup Filtenborg NIELSEN', # HF - 62.1% markspiller aktioner
    'Rikke VORGAARD',             # HF - 65.5% markspiller aktioner
    'Laura Maria Borg THESTRUP',  # PL - 65.9% markspiller aktioner
    'Liv NAVNE',                  # HB - 60.5% markspiller aktioner
    'Rosa SCHMIDT',               # HF - 63.7% markspiller aktioner
    'Trine MORTENSEN',            # VF - 61.6% markspiller aktioner
    'Maria HØJGAARD',             # VF - 62.2% markspiller aktioner
    'Emilie BANGSHØI',            # VF - 68.0% markspiller aktioner
    'Louise HALD',                # HF - 73.4% markspiller aktioner
    'Mathilde PIIL',              # VF - 61.5% markspiller aktioner
    'Sofie ØSTERGAARD',           # HF - 66.5% markspiller aktioner
    'Katarzyna PORTASINSKA',      # HF - 62.5% markspiller aktioner
    'Sille Cecilie SORTH',        # HF - 70.1% markspiller aktioner
    'Julie RASMUSSEN',            # HF - 68.0% markspiller aktioner
    'Emilie Nørgaard BECH',       # HF - 65.4% markspiller aktioner
    'Camilla THORHAUGE',          # ST - 65.0% markspiller aktioner
    'Maiken SKOV',                # HF - 65.1% markspiller aktioner
    'Ditte BACH',                 # HF - 61.0% markspiller aktioner
    
    # KENDTE PROBLEMATISKE SPILLERE (selv om de ikke optræder i aktuelle data)
    'Peter BALLING',              # Den originale problematiske spiller - HB/højreback
}

# SPILLERNAVN ALIASER
# Mapper variationer af spillernavne til deres kanoniske form
# Nyttigt for robust matching på tværs af sæsoner
PLAYER_NAME_ALIASES = {
    # Eksempler på aliases - kan udbygges efter behov
    'Peter Balling': 'Peter BALLING',
    'peter balling': 'Peter BALLING',
    'PETER BALLING': 'Peter BALLING',
    
    # Andreas Søgaard har et "Assist" i navnet i nogle filer
    'Andreas Søgaard RASMUSSEN': 'Andreas Søgaard RASMUSSENAssist',
    'Andreas Søgaard RASMUSSENAssist': 'Andreas Søgaard RASMUSSENAssist',
    
    # Tilføj flere aliases efter behov når vi finder inconsistente navne
}

# TEAM MAPPINGS (kan udbygges)
TEAM_ALIASES = {
    'AAH': 'Aalborg Håndbold',
    'BSH': 'Bjerringbro-Silkeborg',
    'GOG': 'GOG',
    # Tilføj flere efter behov
}

def is_protected_field_player(player_name: str) -> bool:
    """
    Kontrollerer om en spiller er på listen over beskyttede markspillere
    
    Args:
        player_name: Spillerens navn
        
    Returns:
        True hvis spilleren er beskyttet, False ellers
    """
    if not player_name:
        return False
        
    # Normaliser navnet til store bogstaver for comparison
    normalized_name = " ".join(player_name.strip().upper().split())
    
    # Check både det givne navn og eventuelle aliaser
    for protected_name in PROTECTED_FIELD_PLAYERS:
        if normalized_name == " ".join(protected_name.strip().upper().split()):
            return True
            
    # Check aliaser
    canonical_name = PLAYER_NAME_ALIASES.get(player_name)
    if canonical_name and canonical_name in PROTECTED_FIELD_PLAYERS:
        return True
        
    return False

def get_canonical_player_name(player_name: str) -> str:
    """
    Returnerer det kanoniske navn for en spiller
    
    Args:
        player_name: Spillerens navn (kan være et alias)
        
    Returns:
        Kanonisk navn eller det originale navn hvis ingen alias findes
    """
    return PLAYER_NAME_ALIASES.get(player_name, player_name)

if __name__ == "__main__":
    # Test funktioner
    print("TEAM CONFIGURATION TEST")
    print("=" * 40)
    
    # Test beskyttede spillere
    test_players = ['Peter BALLING', 'peter balling', 'Minik Dahl HØEGH', 'Random Player']
    for player in test_players:
        is_protected = is_protected_field_player(player)
        print(f"✅ {player}: {'BESKYTTET' if is_protected else 'ikke beskyttet'}")
    
    print(f"\n📊 Total beskyttede spillere: {len(PROTECTED_FIELD_PLAYERS)}")
    print(f"📝 Spillernavn aliaser: {len(PLAYER_NAME_ALIASES)}") 