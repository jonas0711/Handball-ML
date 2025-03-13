#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test Konvertering Script

Dette script konverterer en enkelt handball match tekstfil til en database.
Bruges til at teste konverteringsprocessen.
"""

import os
import sys
import logging
# Brug handball_data_processor i stedet for handball_converter
from handball_data_processor import process_file, load_system_prompt
# Tilføj dotenv for at indlæse .env filen
from dotenv import load_dotenv

# Indlæs miljøvariabler fra .env filen
load_dotenv()

# Konfiguration
LOG_FILE = "test_conversion.log"

# Sikrer at log-mappen eksisterer
log_dir = os.path.dirname(LOG_FILE)
if log_dir:  # Kun kald makedirs hvis der faktisk er en sti
    os.makedirs(log_dir, exist_ok=True)

# Konfigurer logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Tilføj separat logger for API kald for bedre debugging
api_logger = logging.getLogger('api_calls')
api_logger.setLevel(logging.DEBUG)
if not api_logger.handlers:  # Undgå duplikerede handlere
    api_handler = logging.FileHandler('test_api_calls.log')
    api_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    api_logger.addHandler(api_handler)

def test_conversion(file_path):
    """
    Test konvertering af en enkelt fil
    
    Args:
        file_path: Sti til tekstfilen der skal behandles
    """
    # Kontroller at filen eksisterer
    if not os.path.exists(file_path):
        logger.error(f"Filen blev ikke fundet: {file_path}")
        return
    
    # Kontroller at system prompt filen eksisterer
    try:
        system_prompt = load_system_prompt()
        logger.info("System prompt (gemini_api_instructions.txt) indlæst korrekt")
    except Exception as e:
        logger.error(f"Fejl ved indlæsning af system prompt (gemini_api_instructions.txt): {str(e)}")
        return
    
    # Hent API-nøgle fra miljøvariabel
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.error("GEMINI_API_KEY miljøvariabel ikke fundet")
        logger.info("Tjekker om API-nøglen findes i .env filen...")
        return
    else:
        logger.info("GEMINI_API_KEY fundet og indlæst korrekt")
    
    # Log API-nøglens længde (men ikke selve nøglen af sikkerhedsmæssige årsager)
    logger.info(f"API-nøglen har en længde på {len(api_key)} tegn")
    
    # Konverter filen
    logger.info(f"Starter konvertering af: {os.path.basename(file_path)}")
    db_path = process_file(file_path, api_key)
    
    if db_path:
        logger.info(f"Konvertering lykkedes! Database gemt som: {db_path}")
        
        # Foreslå at køre database_validator.py for at validere resultatet
        logger.info("\nFor at validere resultatet, kør:")
        logger.info(f"python database_validator.py {db_path}")
    else:
        logger.error("Konverteringen fejlede.")

def main():
    """Hovedfunktion"""
    if len(sys.argv) < 2:
        print("Brug: python single_file_tester.py <sti_til_tekstfil>")
        print("Eksempel: python single_file_tester.py Kvindeliga-txt-tabel/2024-2025/match_748182_a.txt")
        return
    
    file_path = sys.argv[1]
    test_conversion(file_path)

if __name__ == "__main__":
    main() 