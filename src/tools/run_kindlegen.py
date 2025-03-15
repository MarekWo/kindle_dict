#!/usr/bin/env python3
# kindle_dict\src\tools\run_kindlegen.py

import subprocess
import sys
import os

def run_kindlegen(opf_file, output_file=None):
    """
    Run kindlegen.exe through Wine in headless mode, capturing both stdout and stderr.
    
    Args:
        opf_file: Path to the .opf file
        output_file: Optional output file name
    
    Returns:
        True if successful, False otherwise
    """
    import logging
    logger = logging.getLogger(__name__)
    
    # Construct command
    kindlegen_path = os.path.join(os.path.dirname(__file__), 'kindlegen.exe')
    
    # Przygotowanie środowiska dla Wine
    env = os.environ.copy()
    env['DISPLAY'] = '' # Wyłączenie próby połączenia z serwerem X
    env['WINEDEBUG'] = '-all' # Wyłączenie debugowania Wine
    env['WINEDLLOVERRIDES'] = 'mscoree,mshtml=' # Wyłączenie niektórych DLL
    
    # Użycie wine64 zamiast wine, jeśli dostępne
    wine_cmd = 'wine'
    try:
        # Sprawdź, czy wine64 jest dostępne
        subprocess.run(['which', 'wine64'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        wine_cmd = 'wine64'
        logger.info("Using wine64 command")
    except:
        logger.info("Using wine command")
    
    command = [wine_cmd, kindlegen_path]
    command.append(opf_file)
    
    if output_file:
        command.extend(['-o', output_file])
    
    logger.info(f"Running kindlegen command: {' '.join(command)}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Kindlegen path exists: {os.path.exists(kindlegen_path)}")
    
    try:
        # Run command with modified environment and capture both stdout and stderr
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            env=env
        )
        
        # Log the output
        logger.info(f"Kindlegen stdout: {result.stdout}")
        if result.stderr:
            logger.warning(f"Kindlegen stderr: {result.stderr}")
        
        logger.info(f"Kindlegen return code: {result.returncode}")
        
        # Check if output file was created
        if result.returncode <= 1:  # 0 = success, 1 = success with warnings
            mobi_file = output_file if output_file else os.path.splitext(opf_file)[0] + '.mobi'
            mobi_path = os.path.join(os.path.dirname(opf_file), mobi_file)
            
            if os.path.exists(mobi_path):
                logger.info(f"Successfully created MOBI file: {mobi_path}")
                return True
            else:
                logger.error(f"Kindlegen reported success but MOBI file not found at: {mobi_path}")
                return False
        else:
            logger.error(f"Error running kindlegen (code {result.returncode}): {result.stdout}")
            return False
    
    except Exception as e:
        logger.error(f"Exception running kindlegen: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_kindlegen.py <opf_file> [<output_file>]")
        sys.exit(1)
    
    opf_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = run_kindlegen(opf_file, output_file)
    sys.exit(0 if success else 1)
