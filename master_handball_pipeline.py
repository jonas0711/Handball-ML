#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Master Handball Data Pipeline (OPTIMERET VERSION)

Dette script orchestrerer hele handball data pipeline processen:
1. Download PDFs og konverter til TXT (handball_pdf_downloader.py)
2. Konverter TXT til databaser (handball_data_processor.py)

OPTIMERINGER:
- Reduceret sleep time for hurtigere processering
- Bedre terminal feedback med detaljeret progress
- Intelligent batch processering
- Enhanced error tracking og recovery

Rækkefølge:
- Liga kampe først (Herreliga + Kvindeliga): 2024-2025 → 2017-2018 (nyeste først)
- For hver sæson: både herrer og kvinder behandles før næste sæson
- Derefter 1. Division (1-division-herrer + 1-division-damer): 2024-2025 → 2018-2019 (nyeste først)

Brug:
    python master_handball_pipeline.py
"""

import subprocess
import sys
import time
import os
from datetime import datetime
from pathlib import Path
import re

class HandballPipeline:
    """Master pipeline coordinator for handball data processing (OPTIMERET)"""
    
    def __init__(self):
        # Ligaer og deres rækkefølge
        self.liga_sequences = {
            # Første Liga kampe (2017-2018 til 2024-2025)
            "liga": {
                "ligaer": ["herreligaen", "kvindeligaen"],
                "start_year": 2024,
                "end_year": 2017,
                "description": "Liga kampe (Herreliga & Kvindeliga)"
            },
            # Så 1. Division (2018-2019 til 2024-2025)
            "division": {
                "ligaer": ["1-division-herrer", "1-division-damer"],
                "start_year": 2024,
                "end_year": 2018,
                "description": "1. Division kampe"
            }
        }
        
        # Progress tracking
        self.total_jobs = 0
        self.completed_jobs = 0
        self.failed_jobs = 0
        self.start_time = None
        
        # Enhanced progress tracking
        self.current_phase = ""
        self.current_season = ""
        self.current_liga = ""
        self.jobs_in_current_phase = 0
        self.completed_jobs_in_phase = 0
        
        # Performance tracking
        self.phase_start_times = {}
        self.job_durations = []
        
        # Terminal output styling
        self.colors = {
            'header': '\033[95m',
            'blue': '\033[94m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'red': '\033[91m',
            'end': '\033[0m',
            'bold': '\033[1m',
            'cyan': '\033[96m'
        }
    
    def log(self, message, level="INFO"):
        """Logger meddelelse med farver og tidsstempel"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        if level == "HEADER":
            color = self.colors['header'] + self.colors['bold']
        elif level == "SUCCESS":
            color = self.colors['green']
        elif level == "WARNING":
            color = self.colors['yellow']
        elif level == "ERROR":
            color = self.colors['red']
        elif level == "PROGRESS":
            color = self.colors['blue']
        elif level == "DETAIL":
            color = self.colors['cyan']
        else:
            color = ""
        
        print(f"{color}[{timestamp}] {message}{self.colors['end']}")
    
    def print_banner(self):
        """Print welcome banner"""
        banner = """
╔══════════════════════════════════════════════════════════════════════════════╗
║                   🏐 HANDBALL DATA PIPELINE (OPTIMERET) 🏐                 ║
║                                                                              ║
║  Master script der håndterer komplet data pipeline:                         ║
║  📥 PDF Download → 📄 TXT Konvertering → 🗄️ Database Oprettelse            ║
║                                                                              ║
║  OPTIMERINGER: Hurtigere processering, bedre feedback, intelligent skip     ║
║                                                                              ║
║  Processering rækkefølge:                                                    ║
║  1️⃣ Liga kampe (2024-2025 → 2017-2018)                                     ║
║  2️⃣ 1. Division (2024-2025 → 2018-2019)                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        print(self.colors['header'] + banner + self.colors['end'])
    
    def calculate_total_jobs(self):
        """Beregn totalt antal jobs der skal køres"""
        total = 0
        for phase_name, config in self.liga_sequences.items():
            seasons_count = config['start_year'] - config['end_year'] + 1
            ligaer_count = len(config['ligaer'])
            total += seasons_count * ligaer_count
        self.total_jobs = total * 2  # *2 fordi hver liga/sæson har både PDF+TXT fase
        return self.total_jobs
    
    def print_execution_plan(self):
        """Print oversigt over hvad der skal køres"""
        self.log("📋 EKSEKUTIONSPLAN:", "HEADER")
        
        total_jobs = self.calculate_total_jobs()
        
        for phase_name, config in self.liga_sequences.items():
            seasons = []
            for year in range(config['start_year'], config['end_year'] - 1, -1):
                seasons.append(f"{year}-{year + 1}")
            
            ligaer_str = " + ".join(config['ligaer'])
            
            self.log(f"🎯 {config['description']}:")
            self.log(f"   📅 Sæsoner: {', '.join(seasons)} ({len(seasons)} sæsoner)")
            self.log(f"   🏆 Ligaer: {ligaer_str} ({len(config['ligaer'])} ligaer)")
            self.log(f"   📊 Jobs: {len(seasons)} × {len(config['ligaer'])} × 2 faser = {len(seasons) * len(config['ligaer']) * 2} jobs")
            print()
        
        self.log(f"📈 TOTAL: {total_jobs} jobs vil blive kørt", "PROGRESS")
        
        # Estimeret tid baseret på 1-3 minutter per job
        min_time = total_jobs * 1  # 1 min per job minimum
        max_time = total_jobs * 3  # 3 min per job maximum
        self.log(f"⏱️ Estimeret køretid: {min_time//60}h {min_time%60}m - {max_time//60}h {max_time%60}m", "PROGRESS")
        print()
    
    def extract_detailed_output(self, result_output):
        """Udtræk detaljeret information fra script output"""
        details = {
            "pdfs_downloaded": 0,
            "pdfs_skipped": 0,
            "txt_converted": 0,
            "files_processed": 0,
            "matches_processed": 0
        }
        
        if not result_output:
            return details
        
        # Parse output for nøgletal
        lines = result_output.split('\n')
        for line in lines:
            # PDF download statistik
            if "Gyldige filer downloadet:" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    details["pdfs_downloaded"] = int(match.group(1))
            
            # Skipped files
            elif "Sprunget over" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    details["pdfs_skipped"] = int(match.group(1))
            
            # TXT conversion
            elif "Nye TXT filer:" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    details["txt_converted"] = int(match.group(1))
            
            # Database processing
            elif "nye filer processeret til database" in line:
                match = re.search(r'(\d+)', line)
                if match:
                    details["files_processed"] = int(match.group(1))
        
        return details
    
    def run_pdf_downloader(self, liga, season):
        """Kør handball_pdf_downloader.py for en specifik liga/sæson"""
        self.log(f"📥 Download PDFs + TXT konvertering: {liga} {season}", "PROGRESS")
        
        cmd = [sys.executable, "handball_pdf_downloader.py", "--liga", liga, "--sæson", season]
        
        try:
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            end_time = time.time()
            duration = end_time - start_time
            self.job_durations.append(duration)
            
            if result.returncode == 0:
                # Udtræk detaljeret statistik fra output
                details = self.extract_detailed_output(result.stdout)
                detail_msg = f"PDFs: {details['pdfs_downloaded']} downloaded, {details['pdfs_skipped']} skipped | TXT: {details['txt_converted']} converted"
                
                self.log(f"✅ PDF+TXT fase færdig: {liga} {season} ({duration:.1f}s)", "SUCCESS")
                self.log(f"   📊 {detail_msg}", "DETAIL")
                return True
            else:
                self.log(f"❌ PDF+TXT fase fejlede: {liga} {season} (exit code: {result.returncode})", "ERROR")
                if result.stderr:
                    error_preview = result.stderr[:150].replace('\n', ' ')
                    self.log(f"   Fejl: {error_preview}...", "ERROR")
                if result.stdout:
                    # Log også noget af stdout for debugging
                    stdout_preview = result.stdout[-200:].replace('\n', ' ')
                    self.log(f"   Output: {stdout_preview}...", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Undtagelse i PDF+TXT fase: {liga} {season} - {str(e)}", "ERROR")
            return False
    
    def run_txt_to_db_processor(self, liga, season):
        """Kør handball_data_processor.py for en specifik liga/sæson"""
        self.log(f"🗄️ TXT → Database konvertering: {liga} {season}", "PROGRESS")
        
        cmd = [sys.executable, "handball_data_processor.py", "--liga", liga, "--sæson", season]
        
        try:
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            end_time = time.time()
            duration = end_time - start_time
            self.job_durations.append(duration)
            
            if result.returncode == 0:
                # Udtræk detaljeret statistik fra output
                details = self.extract_detailed_output(result.stdout)
                detail_msg = f"Filer: {details['files_processed']} processed to database"
                
                self.log(f"✅ TXT→DB fase færdig: {liga} {season} ({duration:.1f}s)", "SUCCESS")
                self.log(f"   📊 {detail_msg}", "DETAIL")
                return True
            else:
                self.log(f"❌ TXT→DB fase fejlede: {liga} {season} (exit code: {result.returncode})", "ERROR")
                if result.stderr:
                    error_preview = result.stderr[:150].replace('\n', ' ')
                    self.log(f"   Fejl: {error_preview}...", "ERROR")
                if result.stdout:
                    # Log også noget af stdout for debugging
                    stdout_preview = result.stdout[-200:].replace('\n', ' ')
                    self.log(f"   Output: {stdout_preview}...", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"❌ Undtagelse i TXT→DB fase: {liga} {season} - {str(e)}", "ERROR")
            return False
    
    def process_liga_season(self, liga, season, phase_description):
        """Kør komplet pipeline for en liga/sæson"""
        self.current_liga = liga
        self.current_season = season
        
        self.log(f"🔄 Starter komplet pipeline: {liga} {season} ({phase_description})", "HEADER")
        
        # Fase 1: PDF Download + TXT konvertering
        pdf_success = self.run_pdf_downloader(liga, season)
        self.completed_jobs += 1
        self.completed_jobs_in_phase += 1
        if not pdf_success:
            self.failed_jobs += 1
        
        self.print_enhanced_progress()
        
        # OPTIMERET: Reduceret pause mellem faser fra 1s til 0.3s
        time.sleep(0.3)
        
        # Fase 2: TXT → Database
        db_success = self.run_txt_to_db_processor(liga, season)
        self.completed_jobs += 1
        self.completed_jobs_in_phase += 1
        if not db_success:
            self.failed_jobs += 1
        
        self.print_enhanced_progress()
        
        # Samlet resultat for denne liga/sæson
        if pdf_success and db_success:
            self.log(f"🎉 Komplet: {liga} {season} - begge faser succesfulde!", "SUCCESS")
        elif pdf_success:
            self.log(f"⚠️ Delvis: {liga} {season} - PDF OK, database fejlede", "WARNING")
        else:
            self.log(f"💥 Fejl: {liga} {season} - PDF fase fejlede", "ERROR")
        
        print("─" * 80)
        return pdf_success and db_success
    
    def print_enhanced_progress(self):
        """Print enhanced progression med estimater"""
        percentage = (self.completed_jobs / self.total_jobs) * 100 if self.total_jobs > 0 else 0
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        # Beregn ETA baseret på gennemsnitlig job tid
        if self.job_durations:
            avg_job_time = sum(self.job_durations) / len(self.job_durations)
            remaining_jobs = self.total_jobs - self.completed_jobs
            eta_seconds = remaining_jobs * avg_job_time
            eta_hours = int(eta_seconds // 3600)
            eta_minutes = int((eta_seconds % 3600) // 60)
            eta_str = f"{eta_hours}h {eta_minutes}m" if eta_hours > 0 else f"{eta_minutes}m"
        else:
            eta_str = "beregner..."
        
        phase_percentage = (self.completed_jobs_in_phase / self.jobs_in_current_phase * 100) if self.jobs_in_current_phase > 0 else 0
        
        self.log(f"📊 Overall: {self.completed_jobs}/{self.total_jobs} jobs ({percentage:.1f}%) | "
                f"⏱️ Elapsed: {elapsed_time/60:.1f}min | 🕐 ETA: {eta_str} | ❌ Fejl: {self.failed_jobs}", "PROGRESS")
        
        self.log(f"🎯 {self.current_phase}: {self.completed_jobs_in_phase}/{self.jobs_in_current_phase} ({phase_percentage:.1f}%) | "
                f"Current: {self.current_liga} {self.current_season}", "DETAIL")
    
    def run_pipeline(self):
        """Kør hele pipeline i korrekt rækkefølge"""
        self.print_banner()
        self.print_execution_plan()
        
        # Bekræftelse fra bruger
        user_input = input("🤔 Vil du starte pipeline? (y/N): ").strip().lower()
        if user_input != 'y':
            self.log("❌ Pipeline afbrudt af bruger", "WARNING")
            return
        
        print("\n" + "="*80)
        self.log("🚀 STARTER HANDBALL DATA PIPELINE", "HEADER")
        self.start_time = time.time()
        
        total_successful = 0
        total_failed = 0
        
        # Proces hver phase (liga, så division)
        for phase_name, config in self.liga_sequences.items():
            # Sæt phase tracking
            self.current_phase = config['description']
            self.completed_jobs_in_phase = 0
            
            # Beregn jobs for denne fase
            seasons_count = config['start_year'] - config['end_year'] + 1
            self.jobs_in_current_phase = seasons_count * len(config['ligaer']) * 2  # *2 for begge faser
            
            phase_start = time.time()
            self.phase_start_times[phase_name] = phase_start
            
            self.log(f"🎯 STARTER FASE: {config['description'].upper()}", "HEADER")
            self.log(f"📊 Fase info: {self.jobs_in_current_phase} jobs i denne fase", "DETAIL")
            
            # Generer sæsoner (nyeste først)
            seasons = []
            for year in range(config['start_year'], config['end_year'] - 1, -1):
                seasons.append(f"{year}-{year + 1}")
            
            # For hver sæson, kør alle ligaer før næste sæson
            for season in seasons:
                self.log(f"📅 Behandler sæson: {season}", "HEADER")
                
                for liga in config['ligaer']:
                    success = self.process_liga_season(liga, season, config['description'])
                    if success:
                        total_successful += 1
                    else:
                        total_failed += 1
                    
                    # OPTIMERET: Reduceret pause mellem jobs fra 2s til 1s
                    time.sleep(1)
                
                print("═" * 80)
            
            # Fase statistik
            phase_duration = time.time() - phase_start
            self.log(f"✅ FASE FÆRDIG: {config['description']} på {phase_duration/60:.1f} minutter", "SUCCESS")
        
        # Samlet resultat
        total_time = time.time() - self.start_time
        self.print_final_summary(total_successful, total_failed, total_time)
    
    def print_final_summary(self, successful, failed, total_time):
        """Print samlet resultatorium"""
        total_operations = successful + failed
        success_rate = (successful / total_operations * 100) if total_operations > 0 else 0
        
        # Performance statistik
        avg_job_time = sum(self.job_durations) / len(self.job_durations) if self.job_durations else 0
        
        summary = f"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                            🏁 PIPELINE FÆRDIG                              ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  ⏱️  Total tid: {total_time/60:.1f} minutter ({total_time:.0f} sekunder)     
║  📊 Success rate: {success_rate:.1f}% ({successful}/{total_operations})       
║  ✅ Succesfulde: {successful} liga/sæson kombinationer                       
║  ❌ Fejlede: {failed} liga/sæson kombinationer                              
║  📈 Jobs kørt: {self.completed_jobs}/{self.total_jobs}                      
║  ⚡ Gennemsnitlig job tid: {avg_job_time:.1f} sekunder                       
╚══════════════════════════════════════════════════════════════════════════════╝
"""
        
        if failed == 0:
            self.log(summary, "SUCCESS")
            self.log("🎉 ALLE OPERATIONER SUCCESFULDE! 🎉", "SUCCESS")
        else:
            self.log(summary, "WARNING")
            self.log(f"⚠️ {failed} operationer fejlede - tjek logs for detaljer", "WARNING")

def main():
    """Hovedfunktion"""
    pipeline = HandballPipeline()
    
    try:
        pipeline.run_pipeline()
    except KeyboardInterrupt:
        pipeline.log("\n❌ Pipeline afbrudt af bruger (Ctrl+C)", "ERROR")
        # Print partial progress
        if pipeline.start_time:
            elapsed = time.time() - pipeline.start_time
            pipeline.log(f"📊 Partial progress: {pipeline.completed_jobs}/{pipeline.total_jobs} jobs på {elapsed/60:.1f} minutter", "WARNING")
        sys.exit(1)
    except Exception as e:
        pipeline.log(f"\n💥 Uventet fejl: {str(e)}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main() 