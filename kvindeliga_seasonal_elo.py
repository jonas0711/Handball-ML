#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🏆 KVINDELIGA SÆSON-BASERET HÅNDBOL ELO SYSTEM (Wrapper)
=======================================================

Denne wrapper sikrer, at Kvindeliga-beregninger bruger PRÆCIS samme logik som
`herreliga_seasonal_elo.py`. Den eneste forskel er:
  • database-stien (`Kvindeliga-database`)
  • CSV-filernes navne-prefix (kvindeliga_*)

Dermed opfylder vi DRY-princippet og garanterer 100 % kode-paritet.
"""

# --------------------------------------------------
# 1) Fælles importer
# --------------------------------------------------
import os
from typing import Dict, Optional
import builtins  # <--- tilføj

# Genbrug ALT logik fra herreliga-modulet
from herreliga_seasonal_elo import (
    HerreligaSeasonalEloSystem as _BaseSeasonalEloSystem,
    PositionAnalyzer as _BasePositionAnalyzer,
)

# --------------------------------------------------
# PATCH print-funktionen så alle base-klasses udskrifter konverteres fra
# "Herreliga" til "Kvindeliga" automatisk.
# --------------------------------------------------
_orig_print = builtins.print

def _kvinde_print(*args, **kwargs):
    new_args = []
    for arg in args:
        if isinstance(arg, str):
            new_args.append(arg.replace("Herreliga", "Kvindeliga"))
        else:
            new_args.append(arg)
    _orig_print(*new_args, **kwargs)

builtins.print = _kvinde_print

# --------------------------------------------------
# 2) PositionAnalyzer – kun sti-override
# --------------------------------------------------
class PositionAnalyzer(_BasePositionAnalyzer):
    """Analyzer der læser Kvindeliga-databaserne uanset input."""

    def __init__(self, base_dir: str = ".", *_ignored, **_kwignored):
        # Tving league_dir til "Kvindeliga-database" uanset hvad basiskoden sender.
        super().__init__(base_dir, league_dir="Kvindeliga-database")

# Monkey-patch basemodulets reference så eksisterende kode bruger denne class
import herreliga_seasonal_elo as _herre_mod
_herre_mod.PositionAnalyzer = PositionAnalyzer

# --------------------------------------------------
# 3) KvindeligaSeasonalEloSystem – arver alt
# --------------------------------------------------
class KvindeligaSeasonalEloSystem(_BaseSeasonalEloSystem):
    """Samme funktionalitet som base, men peger på Kvindeliga-data."""
    
    def __init__(self, base_dir: str = "."):
        # Initier basisklassen først
        super().__init__(base_dir)
        
        # Overstyr stier/labels
        self.league_name = "Kvindeliga"
        self.kvindeliga_dir = os.path.join(base_dir, "Kvindeliga-database")
        # Peg den arvede attribut herreliga_dir til samme mappe, så base-metoder
        # (der henviser til self.herreliga_dir) virker uændret.
        self.herreliga_dir = self.kvindeliga_dir

        # Genvalider sæsoner ud fra kvinde-dir
        self.validate_herreliga_seasons()
        print("✅ Kvindeliga ELO system (wrapper) initialiseret")

    # ---------- Filnavne-override ----------
    def save_herreliga_season_csv(self, season_results: Dict, season: str):  # type: ignore
        """Gemmer CSV-data med kvindeliga-prefix."""
        if not season_results:
            print(f"❌ Ingen data at gemme for {season}")
            return
            
        # Kald basismetoden for at få DataFrame-logik, men med lokalt filnavn
        import pandas as pd
        output_dir = os.path.join("ELO_Results", "Player_Seasonal_CSV")
        os.makedirs(output_dir, exist_ok=True)
        
        df = pd.DataFrame([v for v in season_results.values()]).sort_values("final_rating", ascending=False)
        filename = f"kvindeliga_seasonal_elo_{season.replace('-', '_')}.csv"
        filepath = os.path.join(output_dir, filename)
        df.to_csv(filepath, index=False, encoding="utf-8")

        avg = df["final_rating"].mean(); spread = df["final_rating"].max() - df["final_rating"].min()
        elite = len(df[df["elite_status"] == "ELITE"]); legend = len(df[df["elite_status"] == "LEGENDARY"])
        print(f"💾 Gemt: {filepath}")
        print(f"📊 {len(df)} Kvindeliga spillere, avg rating: {avg:.1f}")
        print(f"📏 Rating spread: {spread:.0f} points")
        print(f"🏆 Elite spillere: {elite}, Legendary: {legend}")

    # ------- Aliasmetoder (kalder base) -------
    def run_kvindeliga_season(self, season: str, start_ratings: Dict = None, position_analyzer: Optional[PositionAnalyzer] = None):
        return super().run_herreliga_season(season, start_ratings, position_analyzer)

    def run_complete_kvindeliga_analysis(self):
        print("\n🚀 STARTER KOMPLET KVINDELIGA SÆSON-ANALYSE (Wrapper)")
        print("=" * 70)
        super().run_complete_herreliga_analysis()


# --------------------------------------------------
# 4) Kør hvis direkte
# --------------------------------------------------
if __name__ == "__main__":
    system = KvindeligaSeasonalEloSystem()
    system.run_complete_kvindeliga_analysis() 