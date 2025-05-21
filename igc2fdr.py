#!/usr/bin/env python3
"""
IGC to FDR Converter

This script converts IGC flight logs to X-Plane FDR format.
Based on 42fdr.py by MadReasonable.

Usage:
    python igc2fdr.py [-c config] [-a aircraft] [-t timezone] [-o outputFolder] file.igc [file2.igc ...]
"""

import os
import argparse
import sys
import logging
from pathlib import Path
from typing import List, Optional

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from igc_config import Config
from igc_parser import IgcParser, getFiletype
from igc_writer import writeOutputFile
from igc_model import FileType
from igc_constants import DEFAULT_OUT_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def process_file(config: Config, file_path: str) -> bool:
    """
    Process a single IGC file and convert it to FDR format
    Returns True if successful, False otherwise
    """
    try:
        file_name = os.path.basename(file_path)
        base_name = os.path.splitext(file_name)[0]
        out_file_path = os.path.join(config.outPath, f"{base_name}.fdr")
        
        logger.info(f"Processing {file_path}")
        
        # Open input file
        with open(file_path, 'r') as track_file:
            # Detect file type
            file_type = getFiletype(track_file)
            
            if file_type == FileType.IGC:
                # Create parser
                parser = IgcParser(config)
                
                # Parse IGC file
                track_file.seek(0)  # Reset file position
                fdr_flight = parser.parse_file(track_file)
                
                # Write output file
                with open(out_file_path, 'w') as fdr_file:
                    writeOutputFile(config, fdr_file, fdr_flight)
                
                logger.info(f"Created {out_file_path}")
                return True
            else:
                logger.error(f"Unsupported file type: {file_type}")
                return False
    
    except Exception as e:
        logger.error(f"Error processing {file_path}: {e}", exc_info=True)
        return False


def process_files(config: Config, file_paths: List[str]) -> None:
    """Process multiple files and report success/failure"""
    if not file_paths:
        logger.error("No input files provided")
        return
    
    # Create output directory if it doesn't exist
    if not os.path.exists(config.outPath):
        os.makedirs(config.outPath)
        logger.info(f"Created output directory: {config.outPath}")
    
    # Process each file
    success_count = 0
    failure_count = 0
    
    for file_path in file_paths:
        if process_file(config, file_path):
            success_count += 1
        else:
            failure_count += 1
    
    # Report summary
    total = success_count + failure_count
    logger.info(f"Processed {total} files: {success_count} succeeded, {failure_count} failed")


def main() -> None:
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Convert IGC files to X-Plane FDR format')
    
    parser.add_argument('-c', '--config', dest='config', default='igc2fdr.conf',
                        help='Path to configuration file')
    parser.add_argument('-a', '--aircraft', dest='aircraft', 
                        help='Default aircraft model')
    parser.add_argument('-t', '--timezone', dest='timezone', 
                        help='Default timezone offset in hours or format ±HH:MM:SS')
    parser.add_argument('-o', '--output', dest='output', default=DEFAULT_OUT_PATH,
                        help='Output folder')
    parser.add_argument('files', nargs='+', help='IGC files to convert')
    
    args = parser.parse_args()
    
    # Create configuration
    config = Config(args)
    
    # Process files
    process_files(config, args.files)


if __name__ == "__main__":
    main()
