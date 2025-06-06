#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import subprocess
import logging
import json
import signal
from pathlib import Path
from datetime import datetime
from tqdm import tqdm 
import threading

# --- KONFIGURATION ---
BASE_PROJECT_PATH = Path(__file__).resolve().parent
LOG_DIR = BASE_PROJECT_PATH / "Logs"
JSON_DIR = BASE_PROJECT_PATH / "JSON"
MASTER_LOG_FILE = LOG_DIR / "master_pipeline.log"
TRACKING_FILE_PATH = JSON_DIR / "pipeline_tracking_status.json"

PDF_DOWNLOADER_SCRIPT = BASE_PROJECT_PATH / "handball_pdf_downloader.py"
PDF_TO_TEXT_SCRIPT = BASE_PROJECT_PATH / "pdf_to_text_converter.py"
DATA_PROCESSOR_SCRIPT = BASE_PROJECT_PATH / "handball_data_processor.py"

try:
    from dotenv import load_dotenv
    dotenv_path = BASE_PROJECT_PATH / ".env"
    if not dotenv_path.exists() and BASE_PROJECT_PATH.parent != BASE_PROJECT_PATH:
        dotenv_path = BASE_PROJECT_PATH.parent / ".env"
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
        print(f"INFO: .env fil indlæst fra: {dotenv_path}")
    else:
        print("INFO: Ingen .env fil fundet.")
except ImportError:
    print("INFO: python-dotenv ikke installeret, .env fil vil ikke blive indlæst automatisk af master-scriptet.")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

PROCESSING_ORDER = []
current_month = datetime.now().month
current_year = datetime.now().year
latest_season_start_year = current_year if current_month >= 7 else current_year - 1

for year_start in range(latest_season_start_year, 2017 - 1, -1):
    season_str = f"{year_start}-{year_start + 1}"
    PROCESSING_ORDER.append(("kvindeligaen", "Kvindeliga", season_str))
    PROCESSING_ORDER.append(("herreligaen", "Herreliga", season_str))
for year_start in range(latest_season_start_year, 2018 - 1, -1):
    season_str = f"{year_start}-{year_start + 1}"
    PROCESSING_ORDER.append(("1-division-damer", "1-Division-Kvinder", season_str))
    PROCESSING_ORDER.append(("1-division-herrer", "1-Division-Herrer", season_str))

shutdown_requested = False
current_task_info = {"description": "Initialiserer...", "sub_process": None}

LOG_DIR.mkdir(parents=True, exist_ok=True)
JSON_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)-8s] %(message)s (%(filename)s:%(lineno)d)',
    handlers=[
        logging.FileHandler(MASTER_LOG_FILE, mode='a', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("MasterPipeline")

def signal_handler(sig, frame):
    global shutdown_requested, current_task_info
    if not shutdown_requested:
        desc = current_task_info.get("description", "ukendt opgave")
        logger.warning(f"Ctrl+C modtaget! Anmoder om pæn nedlukning efter nuværende opgave: {desc}")
        print(f"\nINFO: Ctrl+C modtaget! Forsøger at afslutte pænt efter '{desc}'. Vent venligst...")
    shutdown_requested = True
    sub_proc = current_task_info.get("sub_process")
    if sub_proc and sub_proc.poll() is None:
        logger.info("Sender SIGTERM til subprocess...")
        sub_proc.terminate()

signal.signal(signal.SIGINT, signal_handler)

def load_tracking_data():
    if TRACKING_FILE_PATH.exists():
        try:
            with open(TRACKING_FILE_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            logger.warning(f"Kunne ikke læse tracking-fil ({TRACKING_FILE_PATH}). Starter med tom tracking.")
            data = {}
    else:
        data = {}
    data.setdefault("file_status", {})
    data.setdefault("pipeline_progress", {"last_completed_task_index": -1})
    data.setdefault("kamp_id_to_file_key", {})
    return data

def save_tracking_data(data):
    try:
        temp_path = TRACKING_FILE_PATH.with_suffix(".tmp")
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_path, TRACKING_FILE_PATH)
        logger.debug("Tracking data gemt.")
    except Exception as e:
        logger.error(f"Fejl ved gemning af tracking data: {e}", exc_info=True)

def update_file_status(tracking_data, liga_folder, season, pdf_filename, status, txt_path=None, db_path=None, kamp_id=None):
    key = f"{liga_folder}/{season}/{pdf_filename}"
    tracking_data["file_status"].setdefault(key, {})
    tracking_data["file_status"][key]["status"] = status
    tracking_data["file_status"][key]["last_update"] = datetime.now().isoformat()
    if txt_path: tracking_data["file_status"][key]["txt_path"] = str(Path(txt_path).name)
    if db_path: tracking_data["file_status"][key]["db_path"] = str(Path(db_path).name)
    if kamp_id:
        kamp_id_str = str(kamp_id)
        tracking_data["file_status"][key]["kamp_id"] = kamp_id_str
        if status == "db_created":
            if kamp_id_str in tracking_data["kamp_id_to_file_key"] and tracking_data["kamp_id_to_file_key"][kamp_id_str] != key:
                logger.warning(f"Duplikat kamp_id {kamp_id_str}! Original DB fra: {tracking_data['kamp_id_to_file_key'][kamp_id_str]}. Ny (denne) PDF: {key}.")
            elif kamp_id_str not in tracking_data["kamp_id_to_file_key"]:
                 tracking_data["kamp_id_to_file_key"][kamp_id_str] = key
    save_tracking_data(tracking_data)

def get_file_status_info(tracking_data, liga_folder, season, pdf_filename):
    key = f"{liga_folder}/{season}/{pdf_filename}"
    return tracking_data["file_status"].get(key, {})

def update_pipeline_progress(tracking_data, task_index):
    tracking_data["pipeline_progress"]["last_completed_task_index"] = task_index
    tracking_data["pipeline_progress"]["timestamp"] = datetime.now().isoformat()
    save_tracking_data(tracking_data)

def _stream_reader(stream, log_func, line_buffer, script_name_for_log, error_stream=False):
    try:
        for line in iter(stream.readline, ''):
            if shutdown_requested: break
            line_strip = line.strip()
            if line_strip:
                is_tqdm_line = "%|" in line_strip and ("it/s" in line_strip or "/s" in line_strip or "ETA" in line_strip)
                if error_stream and is_tqdm_line:
                    # Undgå at logge tqdm til stderr som fejl, medmindre det er det eneste output.
                    # Hvis du vil se det, log det som debug.
                    # logger.debug(f"  [{script_name_for_log} TQDM_STDERR] {line_strip}")
                    pass
                else:
                    log_func(f"  [{script_name_for_log}{(' ERR' if error_stream else '')}] {line_strip}")
                line_buffer.append(line_strip)
    except IOError:
        logger.debug(f"IOError på stream for {script_name_for_log}")
    except ValueError: # Kan ske hvis stream lukkes mens readline venter
        logger.debug(f"ValueError (stream closed?) for {script_name_for_log}")
    finally:
        if not stream.closed:
            try:
                stream.close()
            except Exception:
                pass

def run_script_step(script_path, step_args_list, task_desc_for_log, timeout_seconds=3600):
    global current_task_info
    liga_arg_match = next((s for s in step_args_list if s.startswith("--liga=")), None)
    season_arg_match = next((s for s in step_args_list if s.startswith("--sæson=")), None)
    
    liga_val = liga_arg_match.split('=')[1] if liga_arg_match else "ukendt_liga"
    season_val = season_arg_match.split('=')[1] if season_arg_match else "ukendt_sæson"
    current_task_info["description"] = f"{liga_val} {season_val} - {script_path.name}"
    
    full_command = [sys.executable, str(script_path)] + step_args_list
    logger.info(f"Kører: {' '.join(map(str, full_command))} (for {task_desc_for_log})")
    print(f"INFO: [{task_desc_for_log}] Kører {script_path.name}...")

    env = os.environ.copy()
    if GEMINI_API_KEY: env["GEMINI_API_KEY"] = GEMINI_API_KEY
    env["PYTHONUNBUFFERED"] = "1"

    process = None # Initialiser process variablen
    try:
        process = subprocess.Popen(full_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   text=True, encoding='utf-8', errors='replace', bufsize=1, env=env)
        current_task_info["sub_process"] = process

        stdout_lines = []
        stderr_lines = []

        stdout_thread = threading.Thread(target=_stream_reader, args=(process.stdout, logger.info, stdout_lines, script_path.name, False))
        stderr_thread = threading.Thread(target=_stream_reader, args=(process.stderr, logger.error, stderr_lines, script_path.name, True))
        
        stdout_thread.start()
        stderr_thread.start()

        start_wait_time = time.time()
        
        while stdout_thread.is_alive() or stderr_thread.is_alive():
            if shutdown_requested:
                logger.warning(f"Shutdown anmodet under {script_path.name}, venter på tråde...")
                stdout_thread.join(timeout=10) # Kortere timeout da processen allerede er bedt om at stoppe
                stderr_thread.join(timeout=10)
                if process.poll() is None: # Hvis processen stadig kører efter trådene (teoretisk)
                    logger.warning(f"Subprocess {script_path.name} stadig aktiv efter tråd-join. Tvinger kill.")
                    process.kill()
                process.wait() # Sikr processen er helt afsluttet
                return "interrupted"

            if timeout_seconds and (time.time() - start_wait_time > timeout_seconds):
                logger.error(f"Timeout ({timeout_seconds}s) overskredet for {script_path.name}. Terminerer.")
                process.terminate()
                stdout_thread.join(timeout=10)
                stderr_thread.join(timeout=10)
                if process.poll() is None: process.kill()
                process.wait()
                return False

            # Tjek om processen er afsluttet uafhængigt af trådene
            if process.poll() is not None:
                # Vent på at trådene færdiggør læsning af resterende output
                stdout_thread.join(timeout=5)
                stderr_thread.join(timeout=5)
                break 
            
            time.sleep(0.1)
        
        # Sikr at processen er helt færdig og få return code
        if process.poll() is None: # Hvis den af en eller anden grund ikke er afsluttet
            process.wait(timeout=5) # Giv den en sidste chance
            if process.poll() is None: # Stadig ikke?
                logger.warning(f"Subprocess {script_path.name} var svær at afslutte. Tvinger kill.")
                process.kill()
                process.wait()

        returncode = process.returncode
        
        is_actual_error = False
        if returncode != 0:
            is_actual_error = True
            logger.error(f"{script_path.name} afsluttede med non-zero exit code: {returncode}")
        
        # Tjek stderr for reelle fejl, selv hvis exit code er 0
        # tqdm kan skrive til stderr, så vi skal filtrere det.
        actual_stderr_messages = [line for line in stderr_lines if not ("%|" in line and ("it/s" in line or "/s" in line or "ETA" in line))]
        if actual_stderr_messages:
            is_actual_error = True # Selv hvis returncode var 0, betragt det som en fejl
            logger.error(f"{script_path.name} havde følgende fejlbeskeder på stderr (selvom exit code var {returncode}):")
            for err_line in actual_stderr_messages:
                logger.error(f"  >>> {err_line}")
        
        success = not is_actual_error
        
        log_level = logger.info if success else logger.error
        log_level(f"{script_path.name} afsluttet {'succesfuldt' if success else 'med fejl'} (kode {returncode}) for {task_desc_for_log}.")
        return success

    except FileNotFoundError:
        logger.error(f"Script ikke fundet: {script_path}")
        return False
    except Exception as e:
        logger.error(f"Uventet fejl ved kørsel af {script_path}: {e}", exc_info=True)
        # Sørg for at processen bliver ryddet op, hvis den blev startet
        if process and process.poll() is None:
            process.kill()
            process.wait()
        return False
    finally:
        current_task_info["sub_process"] = None
        current_task_info["description"] = "Afventer næste opgave..."

def is_pdf_content_valid(pdf_path):
    MIN_PDF_SIZE_VALID = 40000 
    MIN_TEXT_CONTENT_VALID = 300
    try: import PyPDF2
    except ImportError:
        logger.error(f"PyPDF2 mangler. Kan ikke validere PDF-indhold for {pdf_path.name}. Antager valid.")
        return True

    if not pdf_path.exists():
        logger.debug(f"PDF {pdf_path.name} findes ikke.")
        return False
    if pdf_path.stat().st_size < MIN_PDF_SIZE_VALID:
        logger.debug(f"PDF {pdf_path.name} er for lille ({pdf_path.stat().st_size} bytes).")
        return False
    
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            if not reader.pages:
                logger.debug(f"PDF {pdf_path.name} har ingen sider.")
                return False
            
            text_content = ""
            for i in range(min(len(reader.pages), 3)): 
                page_text = reader.pages[i].extract_text()
                if page_text: text_content += page_text
            
            if len(text_content.strip()) < MIN_TEXT_CONTENT_VALID:
                logger.debug(f"PDF {pdf_path.name} har for lidt tekstindhold ({len(text_content.strip())} tegn).")
                return False
            
            keywords = ["KAMPHÆNDELSER", "Tid", "Mål", "Hold", "Hændelse", "Kampfakta", "Dommere"]
            found_keywords_count = sum(1 for keyword in keywords if keyword.lower() in text_content.lower()) # Case-insensitive
            if found_keywords_count < 2:
                logger.debug(f"PDF {pdf_path.name} mangler tilstrækkeligt antal nøgleord (fandt {found_keywords_count}).")
                return False
        logger.debug(f"PDF {pdf_path.name} valideret OK.")
        return True
    except PyPDF2.errors.PdfReadError:
        logger.warning(f"PDF {pdf_path.name} er korrupt (PdfReadError).")
        return False
    except Exception as e:
        logger.error(f"Fejl under PDF validering af {pdf_path.name}: {e}", exc_info=True)
        return False


def main_master_pipeline():
    global shutdown_requested, current_task_info

    logger.info("="*70)
    logger.info("=== MASTER HÅNDBOLD DATA PROCESSERINGS PIPELINE (v2.2) ===")
    logger.info(f"Starttidspunkt: {datetime.now().isoformat()}")
    logger.info(f"Projektsti: {BASE_PROJECT_PATH}")
    logger.info(f"Antal tasks i kø: {len(PROCESSING_ORDER)}")
    logger.info("="*70)
    print("INFO: Starter Master Pipeline (v2.2). Ctrl+C for at anmode om pæn nedlukning.")

    if not GEMINI_API_KEY:
        logger.critical("GEMINI_API_KEY er ikke sat! Kontroller .env fil eller miljøvariabler. Afslutter.")
        print("FEJL: GEMINI_API_KEY er ikke sat. Pipeline kan ikke fortsætte.")
        return

    if not all(s.exists() for s in [PDF_DOWNLOADER_SCRIPT, PDF_TO_TEXT_SCRIPT, DATA_PROCESSOR_SCRIPT]):
        missing = [s.name for s in [PDF_DOWNLOADER_SCRIPT, PDF_TO_TEXT_SCRIPT, DATA_PROCESSOR_SCRIPT] if not s.exists()]
        logger.critical(f"Et eller flere underscripts blev ikke fundet: {', '.join(missing)}! Kontroller stier.")
        print(f"FEJL: Et eller flere nødvendige underscripts mangler: {', '.join(missing)}. Afslutter.")
        sys.exit(1)

    tracking_data = load_tracking_data()
    start_task_index = tracking_data["pipeline_progress"].get("last_completed_task_index", -1) + 1
    total_tasks = len(PROCESSING_ORDER)
    logger.info(f"Genoptager fra task index {start_task_index + 1} (ud af {total_tasks} tasks).")

    for task_idx in range(start_task_index, total_tasks):
        if shutdown_requested:
            logger.info("Shutdown anmodning modtaget, afbryder loop over tasks.")
            break

        liga_url_name, liga_folder_name, season_str = PROCESSING_ORDER[task_idx]
        task_progress_str = f"Task [{task_idx + 1}/{total_tasks}]"
        
        logger.info(f"\n{'-'*60}\n{task_progress_str} START: {liga_folder_name} Sæson {season_str}\n{'-'*60}")
        print(f"\n>>> {task_progress_str} START: {liga_folder_name} Sæson {season_str}")

        pdf_dir = BASE_PROJECT_PATH / liga_folder_name / season_str
        txt_dir = BASE_PROJECT_PATH / f"{liga_folder_name}-txt-tabel" / season_str
        db_dir  = BASE_PROJECT_PATH / f"{liga_folder_name}-database" / season_str
        
        for d_path in [pdf_dir, txt_dir, db_dir]: d_path.mkdir(parents=True, exist_ok=True)

        script_args = [f"--liga={liga_url_name}", f"--sæson={season_str}", f"--base_project_dir={str(BASE_PROJECT_PATH)}"]

        # Trin 1: Download PDF'er
        current_step_desc = f"{task_progress_str} Trin 1: PDF Download"
        logger.info(f"{current_step_desc} starter...")
        pdf_dl_res = run_script_step(PDF_DOWNLOADER_SCRIPT, script_args, f"{liga_folder_name} {season_str}")
        if pdf_dl_res == "interrupted" or shutdown_requested: break
        if not pdf_dl_res:
            logger.error(f"{current_step_desc} fejlede. Fortsætter med næste overordnede task.")
            update_pipeline_progress(tracking_data, task_idx)
            continue
        logger.info(f"{current_step_desc} afsluttet for {liga_folder_name} {season_str}.")

        # Trin 1.5: PDF Validering
        current_step_desc = f"{task_progress_str} Trin 1.5: PDF Validering"
        logger.info(f"{current_step_desc} starter for {liga_folder_name} {season_str}...")
        if pdf_dir.exists():
            pdfs_to_validate = list(pdf_dir.glob("*.pdf"))
            logger.info(f"Fandt {len(pdfs_to_validate)} PDF-filer i {pdf_dir} til validering.")
            validated_this_run, invalid_this_run = 0, 0
            for pdf_file in tqdm(pdfs_to_validate, desc=f"Validerer PDF'er ({liga_folder_name} {season_str})", unit="pdf", file=sys.stdout, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]'):
                if shutdown_requested: break
                pdf_fn = pdf_file.name
                file_info = get_file_status_info(tracking_data, liga_folder_name, season_str, pdf_fn)
                if file_info.get("status") not in ['pdf_validated', 'txt_converted', 'db_created', 'db_duplicate_skipped']:
                    is_valid = is_pdf_content_valid(pdf_file)
                    if is_valid:
                        update_file_status(tracking_data, liga_folder_name, season_str, pdf_fn, "pdf_validated")
                        validated_this_run += 1
                    else:
                        logger.warning(f"PDF {pdf_fn} er ugyldig. Slettes.")
                        update_file_status(tracking_data, liga_folder_name, season_str, pdf_fn, "pdf_downloaded_invalid")
                        invalid_this_run += 1
                        try: pdf_file.unlink()
                        except OSError as e: logger.error(f"Kunne ikke slette ugyldig PDF {pdf_fn}: {e}")
            logger.info(f"{current_step_desc} afsluttet. {validated_this_run} ny-valideret, {invalid_this_run} markeret ugyldig/slettet.")
        else: logger.warning(f"PDF mappe {pdf_dir} ikke fundet for validering.")
        if shutdown_requested: break

        # Trin 2: PDF til TXT
        current_step_desc = f"{task_progress_str} Trin 2: PDF til TXT"
        txt_conv_res = run_script_step(PDF_TO_TEXT_SCRIPT, script_args, f"{liga_folder_name} {season_str}")
        if txt_conv_res == "interrupted" or shutdown_requested: break
        if not txt_conv_res:
            logger.error(f"{current_step_desc} fejlede. Fortsætter med næste overordnede task.")
            update_pipeline_progress(tracking_data, task_idx)
            continue
        logger.info(f"{current_step_desc} afsluttet for {liga_folder_name} {season_str}.")

        # Trin 3: TXT til DB
        current_step_desc = f"{task_progress_str} Trin 3: TXT til DB"
        db_create_res = run_script_step(DATA_PROCESSOR_SCRIPT, script_args, f"{liga_folder_name} {season_str}")
        if db_create_res == "interrupted" or shutdown_requested: break
        if not db_create_res:
            logger.error(f"{current_step_desc} fejlede. Fortsætter med næste overordnede task.")
            update_pipeline_progress(tracking_data, task_idx)
            continue
        logger.info(f"{current_step_desc} afsluttet for {liga_folder_name} {season_str}.")

        logger.info(f"{task_progress_str} FULDFØRT: {liga_folder_name} Sæson {season_str}")
        update_pipeline_progress(tracking_data, task_idx)

    if shutdown_requested:
        logger.info("Master Pipeline afsluttet pænt efter brugeranmodning.")
        print("\nINFO: Master Pipeline afsluttet pænt.")
    elif start_task_index >= total_tasks and total_tasks > 0:
         logger.info("Alle tasks var allerede fuldført fra tidligere kørsel.")
         print("\nINFO: Alle tasks var allerede fuldført.")
    elif total_tasks == 0:
        logger.info("Ingen tasks defineret i PROCESSING_ORDER.")
        print("\nINFO: Ingen tasks at udføre.")
    else:
        final_task_idx = locals().get('task_idx', start_task_index - 1)
        if final_task_idx + 1 < total_tasks:
            logger.info(f"Pipeline stoppede ved task index {final_task_idx + 1}. Genstart for at fortsætte.")
            print(f"\nINFO: Pipeline stoppet. Genstart for at fortsætte fra task {final_task_idx + 2}.")
        else:
            logger.info("Alle specificerede tasks i Master Pipeline er blevet kørt igennem.")
            print("\nINFO: Alle tasks i Master Pipeline er blevet kørt igennem.")
            update_pipeline_progress(tracking_data, total_tasks) # Marker alle som færdige

    logger.info(f"Sluttidspunkt: {datetime.now().isoformat()}")
    logger.info("="*70)

if __name__ == "__main__":
    main_master_pipeline()