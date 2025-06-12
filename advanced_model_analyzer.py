#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AVANCERET MODEL ANALYSATOR
==========================

Dette script udfører en dybdegående analyse af håndboldmodellernes ydeevne.
Det går et spadestik dybere end den almindelige evaluering og undersøger:
- Performance for individuelle hold.
- Pålideligheden af modellens confidence score.
- De største fejl, modellen begår.
- Dybdegående bias-analyse.

Resultaterne gemmes i en letlæselig tekstrapport.
"""

import pandas as pd
import numpy as np
from datetime import datetime
from handball_match_predictor import HandballMatchPredictor

class AdvancedModelAnalyzer:
    """Klasse til at udføre og indeholde den avancerede analyse."""
    
    def __init__(self, league: str):
        """Initialiserer analysatoren for en specifik liga."""
        self.league = league
        self.results_df = None
        # Opretter en instans af predictoren for at få adgang til testresultater
        self.predictor = HandballMatchPredictor(league=self.league)
        print("-" * 60)

    def run_full_analysis(self) -> dict:
        """
        Kører hele analyse-pipelinen og returnerer en dictionary med resultater.
        """
        print(f"🚀 Starter avanceret analyse for: {self.league.upper()}")
        
        # Hent forudsigelserne for test-sættet
        self.results_df = self.predictor.predict_test_matches()
        
        if self.results_df is None or self.results_df.empty:
            print(f"❌ Ingen testdata fundet for {self.league}. Kan ikke fortsætte.")
            return None
        
        print(f"📊 Analyserer {len(self.results_df)} kampe...")

        # Udfør de forskellige del-analyser
        analysis_data = {
            "overall_accuracy": self.results_df['correct_prediction'].mean(),
            "bias_analysis": self._analyze_bias(),
            "confidence_analysis": self._analyze_confidence(),
            "team_performance": self._analyze_team_performance(),
            "error_analysis": self._analyze_errors()
        }
        
        print(f"✅ Analyse for {self.league.upper()} er fuldført.")
        return analysis_data

    def _analyze_bias(self) -> dict:
        """Analyserer for bias mod hjemme- eller udehold."""
        actual_home_rate = self.results_df['target_home_win'].mean()
        predicted_home_rate = self.results_df['predicted_home_win'].mean()
        
        return {
            'actual_home_win_rate': actual_home_rate,
            'predicted_home_win_rate': predicted_home_rate
        }

    def _analyze_confidence(self) -> pd.DataFrame:
        """Analyserer modellens nøjagtighed ved forskellige confidence-niveauer."""
        # Opdel confidence i intervaller (f.eks. 0-20%, 20-40%, etc.)
        bins = np.linspace(0, 1.0, 6)
        labels = [f"{bins[i]:.0%}-{bins[i+1]:.0%}" for i in range(len(bins)-1)]
        
        # Opret en ny kolonne med det tildelte interval
        self.results_df['confidence_bin'] = pd.cut(self.results_df['confidence'], bins=bins, labels=labels, include_lowest=True, right=True)
        
        # Gruppér efter interval og beregn nøjagtighed og antal kampe
        confidence_summary = self.results_df.groupby('confidence_bin')['correct_prediction'].agg(['mean', 'count']).reset_index()
        confidence_summary.rename(columns={'mean': 'accuracy', 'count': 'match_count'}, inplace=True)
        
        return confidence_summary

    def _analyze_team_performance(self) -> pd.DataFrame:
        """Analyserer modellens nøjagtighed for hvert enkelt hold."""
        # Find alle unikke hold i datasættet
        all_teams = pd.concat([self.results_df['home_team'], self.results_df['away_team']]).unique()
        
        team_stats = []
        for team in all_teams:
            # Find alle kampe, hvor holdet enten var hjemme eller ude
            team_matches = self.results_df[(self.results_df['home_team'] == team) | (self.results_df['away_team'] == team)]
            
            if not team_matches.empty:
                # Beregn nøjagtighed for det specifikke hold
                accuracy = team_matches['correct_prediction'].mean()
                total_games = len(team_matches)
                team_stats.append({'Hold': team, 'Nøjagtighed': accuracy, 'Antal kampe': total_games})
        
        # Opret en DataFrame og sorter den efter nøjagtighed
        stats_df = pd.DataFrame(team_stats).sort_values(by='Nøjagtighed', ascending=False).reset_index(drop=True)
        return stats_df

    def _analyze_errors(self) -> pd.DataFrame:
        """Identificerer de kampe, hvor modellen var mest sikker, men tog fejl."""
        # Filtrer for kun at se på forkerte forudsigelser
        errors_df = self.results_df[self.results_df['correct_prediction'] == 0].copy()
        
        # Sorter efter confidence for at finde de største fejl
        biggest_misses = errors_df.sort_values(by='confidence', ascending=False)
        
        # Vælg de relevante kolonner til rapporten
        report_cols = ['match_date', 'home_team', 'away_team', 'predicted_home_win', 'target_home_win', 'confidence']
        return biggest_misses[report_cols].head(5)

def format_report_section(league_name: str, analysis: dict) -> str:
    """Formaterer den komplette analyserapport for en enkelt liga til en streng."""
    
    if not analysis:
        return f"## {league_name.upper()} ANALYSE\n\nKunne ikke generere analyse.\n\n"

    # Helper til at formatere DataFrames pænt
    def df_to_string(df, index=False):
        return df.to_string(index=index, formatters={'Nøjagtighed': '{:.1%}'.format, 'confidence': '{:.1%}'.format})

    report = f"## {league_name.upper()} ANALYSE\n"
    report += "--------------------------------------------------\n\n"

    # 1. Samlet Nøjagtighed
    report += f"**1. Samlet Nøjagtighed:** {analysis['overall_accuracy']:.1%}\n\n"

    # 2. Hjemme/Ude-bias
    bias = analysis['bias_analysis']
    report += "**2. Hjemme/Ude-bias Analyse**\n"
    report += f"   - Faktisk hjemmesejrsrate:   {bias['actual_home_win_rate']:.1%}\n"
    report += f"   - Forudsagt hjemmesejrsrate: {bias['predicted_home_win_rate']:.1%}\n"
    diff = bias['predicted_home_win_rate'] - bias['actual_home_win_rate']
    bias_text = f"en lille tendens til at favorisere HJEMMEHOLD ({abs(diff):.1%})" if diff > 0 else f"en lille tendens til at favorisere UDEHOLD ({abs(diff):.1%})"
    report += f"   - Konklusion: Modellen har {bias_text}.\n\n"

    # 3. Confidence Analyse
    conf_df = analysis['confidence_analysis']
    report += "**3. Analyse af Modellens Selvtillid (Confidence)**\n"
    report += "   Modellens nøjagtighed fordelt på, hvor sikker den er i sin sag.\n\n"
    report += df_to_string(conf_df) + "\n\n"
    high_conf_accuracy = conf_df[conf_df['confidence_bin'].isin(['80%-100%', '60%-80%'])]['accuracy'].mean()
    report += f"   - Konklusion: Modellens selvtillid er en stærk indikator. Når den er over 60% sikker, er nøjagtigheden i gennemsnit {high_conf_accuracy:.1%}.\n\n"

    # 4. Team Performance
    team_df = analysis['team_performance']
    report += "**4. Performance for Individuelle Hold**\n"
    report += "   Hvor godt klarer modellen sig for hvert enkelt hold?\n\n"
    report += df_to_string(team_df) + "\n\n"
    report += f"   - Bedst forudsagte hold: {team_df.iloc[0]['Hold']} ({team_df.iloc[0]['Nøjagtighed']:.1%})\n"
    report += f"   - Dårligst forudsagte hold: {team_df.iloc[-1]['Hold']} ({team_df.iloc[-1]['Nøjagtighed']:.1%})\n\n"

    # 5. Fejlanalyse
    errors_df = analysis['error_analysis']
    errors_df['Vinder'] = errors_df.apply(lambda row: row['home_team'] if row['target_home_win'] else row['away_team'], axis=1)
    errors_df['Forudsagt'] = errors_df.apply(lambda row: row['home_team'] if row['predicted_home_win'] else row['away_team'], axis=1)
    
    report += "**5. Analyse af Største Fejl**\n"
    report += "   De 5 kampe, hvor modellen var mest sikker, men alligevel tog fejl.\n\n"
    for _, row in errors_df.iterrows():
        report += f"   - Kamp: {row['home_team']} vs {row['away_team']}\n"
        report += f"     - Forudsagt: {row['Forudsagt']}, Faktisk vinder: {row['Vinder']}\n"
        report += f"     - Confidence i forkert vinder: {row['confidence']:.1%}\n"

    report += "\n"
    return report

def main():
    """Hovedfunktionen, der kører analysen for begge ligaer og skriver rapporten."""
    
    # Start rapporten med en overskrift og dato
    report_content = f"AVANCERET DYBDEGÅENDE ANALYSERAPPORT\n"
    report_content += "=========================================\n"
    report_content += f"Dato: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
    report_content += "Denne rapport analyserer de trænede modellers performance i detaljer.\n\n"

    # Kør analyse for begge ligaer
    for league in ["Herreliga", "Kvindeliga"]:
        try:
            analyzer = AdvancedModelAnalyzer(league)
            analysis_results = analyzer.run_full_analysis()
            report_content += format_report_section(league, analysis_results)
        except Exception as e:
            report_content += f"## {league.upper()} ANALYSE\n\n"
            report_content += f"FEJL: Kunne ikke gennemføre analysen på grund af en fejl: {e}\n\n"
    
    # Gem den færdige rapport til en fil
    report_filename = "avanceret_analyse_rapport.txt"
    try:
        with open(report_filename, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"\n✅ Færdig! Den avancerede analyserapport er blevet gemt som: '{report_filename}'")
    except Exception as e:
        print(f"\n❌ Kunne ikke gemme rapportfil: {e}")

if __name__ == "__main__":
    main() 