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

# --- DEPRECATED MAPPINGS (DO NOT USE) ---
# TEAM_NAME_MAPPINGS = { ... } 