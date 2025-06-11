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

# ==============================================================================
# LIGA-SPECIFIKKE BESKYTTEDE MARKSPILLERE
# ==============================================================================
# Disse lister indeholder spillere, der er identificeret som primære markspillere,
# men som fejlagtigt kan optræde i målvogter-data. Ved at adskille listerne
# undgår vi, at en fejlklassifikation i den ene liga påvirker den anden.

# ------------------------------------------------------------------------------
# HERRELIGA BESKYTTEDE MARKSPILLERE
# ------------------------------------------------------------------------------
# Spillere fra Herreligaen, der ikke skal klassificeres som målvogtere.
HERRELIGA_PROTECTED_PLAYERS = {
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
    'Peter BALLING',              # Kendt problematisk spiller
}

# ------------------------------------------------------------------------------
# KVINDELIGA BESKYTTEDE MARKSPILLERE
# ------------------------------------------------------------------------------
# Denne liste er bevidst tom. Den fælles analyse i detect_misclassified_goalkeepers.py
# har fejlagtigt klassificeret mange legitime Kvindeliga-målvogtere som markspillere.
# Indtil detektionsalgoritmen er forbedret og kan køre liga-separat, vil vi
# ikke anvende nogen beskyttelse for Kvindeligaen for at undgå at blokere
# ægte målvogtere.
KVINDELIGA_PROTECTED_PLAYERS = {
    # 'Camilla DEGN',               # VF - Fejlagtigt klassificeret
    # 'Annika JAKOBSEN',            # HF - Fejlagtigt klassificeret
    # 'Daniela GUSTIN',             # HF - Fejlagtigt klassificeret
    # 'Birna BERG HARALDSDOTTIR',   # PL - Fejlagtigt klassificeret
    # 'Frederikke Glavind HEDEGAARD', # HF - Fejlagtigt klassificeret
    # 'Emma NIELSEN',               # HF - Fejlagtigt klassificeret
    # 'Sofie Brems ØSTERGAARD',     # HF - Fejlagtigt klassificeret
    # 'Mathilde ORKILD',            # HF - Fejlagtigt klassificeret
    # 'Line Gyldenløve KRISTENSEN', # PL - Fejlagtigt klassificeret
    # 'Ida ANDERSEN',               # VF - Fejlagtigt klassificeret
    # 'Sofie NIELSEN',              # HF - Fejlagtigt klassificeret
    # 'Josefine THORSTED',          # HF - Fejlagtigt klassificeret
    # 'Melina KRISTENSEN',          # HF - Fejlagtigt klassificeret
    # 'Christina Jacobsen HANSEN',   # ST - Fejlagtigt klassificeret
    # 'Ida-Louise ANDERSEN',        # VF - Fejlagtigt klassificeret
    # 'Emilie BECH',                # HF - Fejlagtigt klassificeret
    # 'Sanne Beck HANSEN',          # HF - Fejlagtigt klassificeret
    # 'Tania Bilde KNUDSEN',        # HF - Fejlagtigt klassificeret
    # 'Frederikke HEDEGAARD',       # HF - Fejlagtigt klassificeret
    # 'Anne-Sofie Møldrup Filtenborg NIELSEN', # HF - Fejlagtigt klassificeret
    # 'Rikke VORGAARD',             # HF - Fejlagtigt klassificeret
    # 'Laura Maria Borg THESTRUP',  # PL - Fejlagtigt klassificeret
    # 'Liv NAVNE',                  # HB - Fejlagtigt klassificeret
    # 'Rosa SCHMIDT',               # HF - Fejlagtigt klassificeret
    # 'Trine MORTENSEN',            # VF - Fejlagtigt klassificeret
    # 'Maria HØJGAARD',             # VF - Fejlagtigt klassificeret
    # 'Emilie BANGSHØI',            # VF - Fejlagtigt klassificeret
    # 'Louise HALD',                # HF - Fejlagtigt klassificeret
    # 'Mathilde PIIL',              # VF - Fejlagtigt klassificeret
    # 'Sofie ØSTERGAARD',           # HF - Fejlagtigt klassificeret
    # 'Katarzyna PORTASINSKA',      # HF - Fejlagtigt klassificeret
    # 'Sille Cecilie SORTH',        # HF - Fejlagtigt klassificeret
    # 'Julie RASMUSSEN',            # HF - Fejlagtigt klassificeret
    # 'Emilie Nørgaard BECH',       # HF - Fejlagtigt klassificeret
    # 'Camilla THORHAUGE',          # ST - Fejlagtigt klassificeret
    # 'Maiken SKOV',                # HF - Fejlagtigt klassificeret
    # 'Ditte BACH',                 # HF - Fejlagtigt klassificeret
}

# --- GAMMEL FÆLLES LISTE (DEPRECATED) ---
# PROTECTED_FIELD_PLAYERS = { ... }

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
    for protected_name in HERRELIGA_PROTECTED_PLAYERS:
        if normalized_name == " ".join(protected_name.strip().upper().split()):
            return True
            
    # Check aliaser
    canonical_name = PLAYER_NAME_ALIASES.get(player_name)
    if canonical_name and canonical_name in HERRELIGA_PROTECTED_PLAYERS:
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
    
    print(f"\n📊 Total beskyttede spillere: {len(HERRELIGA_PROTECTED_PLAYERS)}")
    print(f"📝 Spillernavn aliaser: {len(PLAYER_NAME_ALIASES)}") 