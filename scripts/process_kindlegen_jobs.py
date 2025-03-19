#!/usr/bin/env python3
"""
Script to process kindlegen jobs outside of Docker container.

This script monitors the media/kindlegen_jobs directory for new jobs,
processes them using kindlegen, and updates the job status.

Usage:
    python process_kindlegen_jobs.py

The script will run continuously, checking for new jobs every few seconds.
"""

import os
import sys
import json
import time
import logging
import subprocess
import argparse
import shutil
from datetime import datetime
from pathlib import Path

# Konfiguracja logowania
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('kindlegen_processor.log')
    ]
)
logger = logging.getLogger('kindlegen_processor')

def setup_argparse():
    """Setup command line arguments."""
    parser = argparse.ArgumentParser(description='Process kindlegen jobs')
    parser.add_argument('--media-root', type=str, default='./src/media',
                        help='Path to the media root directory')
    parser.add_argument('--kindlegen-path', type=str, default='./src/tools/kindlegen.exe',
                        help='Path to the kindlegen executable')
    parser.add_argument('--interval', type=int, default=5,
                        help='Interval in seconds between job checks')
    parser.add_argument('--wine-path', type=str, default='wine',
                        help='Path to the wine executable')
    parser.add_argument('--one-shot', action='store_true',
                        help='Process pending jobs once and exit')
    return parser.parse_args()

def find_pending_jobs(jobs_dir):
    """Find pending kindlegen jobs in the specified directory."""
    pending_jobs = []
    
    if not os.path.exists(jobs_dir):
        logger.warning(f"Jobs directory does not exist: {jobs_dir}")
        return pending_jobs
    
    for job_dir in os.listdir(jobs_dir):
        job_path = os.path.join(jobs_dir, job_dir)
        
        if not os.path.isdir(job_path):
            continue
        
        job_file = os.path.join(job_path, 'job.json')
        if not os.path.exists(job_file):
            continue
        
        try:
            with open(job_file, 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            
            if job_data.get('status') == 'pending':
                pending_jobs.append((job_path, job_data))
        except Exception as e:
            logger.error(f"Error reading job file {job_file}: {str(e)}")
    
    return pending_jobs

def process_job(job_path, job_data, kindlegen_path, wine_path):
    """Process a kindlegen job."""
    logger.info(f"Processing job in {job_path}")
    
    opf_filename = job_data.get('opf_file')
    opf_file = os.path.join(job_path, opf_filename)
    output_file = job_data.get('output_file')
    
    if not os.path.exists(opf_file):
        update_job_status(job_path, 'failed', f"OPF file not found: {opf_file}")
        return False
    
    try:
        # Determine if we're on Windows or not
        is_windows = os.name == 'nt'
        
        # Zapamiętaj bieżący katalog
        original_dir = os.getcwd()
        
        try:
            # Przejdź do katalogu zadania, aby używać względnych ścieżek
            os.chdir(job_path)
            
            # Construct command based on OS, używając tylko nazwy pliku zamiast pełnej ścieżki
            if is_windows:
                # On Windows, run kindlegen directly
                command = [kindlegen_path, opf_filename]
            else:
                # On Linux/macOS, use wine
                command = [wine_path, kindlegen_path, opf_filename]
            
            # Add output file if specified
            if output_file:
                command.extend(['-o', output_file])
            
            logger.info(f"Running command from directory {job_path}: {' '.join(command)}")
            
            # Run kindlegen
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            
            # Log output
            logger.info(f"Command output: {result.stdout}")
            if result.stderr:
                logger.warning(f"Command error: {result.stderr}")
            
            # Check if successful
            if result.returncode <= 1:  # 0 = success, 1 = success with warnings
                mobi_file = output_file if output_file else os.path.splitext(job_data.get('opf_file'))[0] + '.mobi'
                mobi_path = os.path.join(job_path, mobi_file)
                
                if os.path.exists(mobi_path) and os.path.getsize(mobi_path) > 0:
                    update_job_status(job_path, 'completed', output=mobi_file)
                    logger.info(f"Job completed successfully: {mobi_path}")
                    return True
                else:
                    update_job_status(job_path, 'failed', f"MOBI file not found or empty: {mobi_path}")
                    logger.error(f"MOBI file not found or empty: {mobi_path}")
                    return False
            else:
                update_job_status(job_path, 'failed', f"kindlegen failed with code {result.returncode}: {result.stdout}")
                logger.error(f"kindlegen failed with code {result.returncode}")
                return False
                
        finally:
            # Wróć do oryginalnego katalogu
            os.chdir(original_dir)
    
    except Exception as e:
        update_job_status(job_path, 'failed', f"Exception: {str(e)}")
        logger.error(f"Exception processing job: {str(e)}", exc_info=True)
        return False

def update_job_status(job_path, status, error=None, output=None):
    """Update the status of a job."""
    job_file = os.path.join(job_path, 'job.json')
    
    try:
        with open(job_file, 'r', encoding='utf-8') as f:
            job_data = json.load(f)
        
        job_data['status'] = status
        job_data['updated_at'] = time.time()
        
        if error:
            job_data['error'] = error
        
        if output:
            job_data['output_file'] = output
        
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job_data, f, ensure_ascii=False, indent=4)
        
        logger.info(f"Updated job status to {status}: {job_file}")
        return True
    
    except Exception as e:
        logger.error(f"Error updating job status: {str(e)}")
        return False

def cleanup_old_jobs(jobs_dir, max_age_hours=24):
    """
    Clean up old job directories.
    
    Args:
        jobs_dir: Path to the jobs directory
        max_age_hours: Maximum age of job directories in hours
    """
    if not os.path.exists(jobs_dir):
        return
    
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    
    for job_dir_name in os.listdir(jobs_dir):
        job_dir = os.path.join(jobs_dir, job_dir_name)
        
        if not os.path.isdir(job_dir):
            continue
        
        job_file = os.path.join(job_dir, 'job.json')
        if not os.path.exists(job_file):
            continue
        
        try:
            with open(job_file, 'r', encoding='utf-8') as f:
                job_data = json.load(f)
            
            # Sprawdzamy, czy zadanie zostało zakończone (sukces lub błąd)
            if job_data.get('status') in ['completed', 'failed']:
                # Sprawdzamy, czy zadanie jest wystarczająco stare
                created_at = job_data.get('created_at', 0)
                age_seconds = current_time - created_at
                
                if age_seconds > max_age_seconds:
                    logger.info(f"Removing old job directory: {job_dir} (age: {age_seconds/3600:.1f} hours)")
                    try:
                        shutil.rmtree(job_dir)
                    except Exception as e:
                        logger.warning(f"Could not remove job directory {job_dir}: {str(e)}")
        
        except Exception as e:
            logger.warning(f"Error processing job file {job_file}: {str(e)}")

def main():
    """Main function."""
    args = setup_argparse()
    
    # Resolve paths
    media_root = os.path.abspath(args.media_root)
    kindlegen_path = os.path.abspath(args.kindlegen_path)
    jobs_dir = os.path.join(media_root, 'kindlegen_jobs')
    
    logger.info(f"Starting kindlegen job processor")
    logger.info(f"Media root: {media_root}")
    logger.info(f"Jobs directory: {jobs_dir}")
    logger.info(f"Kindlegen path: {kindlegen_path}")
    logger.info(f"Wine path: {args.wine_path}")
    logger.info(f"Check interval: {args.interval} seconds")
    
    # Create jobs directory if it doesn't exist
    os.makedirs(jobs_dir, exist_ok=True)
    
    # Process jobs once or continuously
    if args.one_shot:
        logger.info("Running in one-shot mode")
        
        # Czyścimy stare katalogi zadań
        cleanup_old_jobs(jobs_dir)
        
        # Przetwarzamy oczekujące zadania
        pending_jobs = find_pending_jobs(jobs_dir)
        logger.info(f"Found {len(pending_jobs)} pending jobs")
        
        for job_path, job_data in pending_jobs:
            process_job(job_path, job_data, kindlegen_path, args.wine_path)
        
        logger.info("One-shot processing completed")
    else:
        logger.info("Running in continuous mode")
        
        # Licznik do okresowego czyszczenia
        cleanup_counter = 0
        cleanup_interval = 12  # Czyszczenie co 12 cykli (przy domyślnym interwale 5s to będzie co minutę)
        
        try:
            while True:
                # Przetwarzamy oczekujące zadania
                pending_jobs = find_pending_jobs(jobs_dir)
                
                if pending_jobs:
                    logger.info(f"Found {len(pending_jobs)} pending jobs")
                    
                    for job_path, job_data in pending_jobs:
                        process_job(job_path, job_data, kindlegen_path, args.wine_path)
                
                # Okresowo czyścimy stare katalogi zadań
                cleanup_counter += 1
                if cleanup_counter >= cleanup_interval:
                    cleanup_old_jobs(jobs_dir)
                    cleanup_counter = 0
                
                time.sleep(args.interval)
        
        except KeyboardInterrupt:
            logger.info("Received keyboard interrupt, shutting down")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
