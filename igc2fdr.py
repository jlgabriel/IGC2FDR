
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

# Add the current directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from igc_config import Config
from igc_parser import parseIgcFile, getFiletype
from igc_writer import writeOutputFile
from igc_model import FileType
from igc_constants import DEFAULT_OUT_PATH

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('igc2fdr')

def main():
    parser = argparse.ArgumentParser(
        description='Convert IGC flight logs into X-Plane compatible FDR files',
        epilog='Example: python igc2fdr.py -c igc2fdr.conf vuelo.igc'
    )

    parser.add_argument('-a', '--aircraft', default=None, help='Path to default X-Plane aircraft')
    parser.add_argument('-c', '--config', default=None, help='Path to config file')
    parser.add_argument('-t', '--timezone', default=None, help='An offset to add to all times processed. +/-hh:mm[:ss] or +/-<decimal hours>')
    parser.add_argument('-o', '--outputFolder', default=None, help='Path to write X-Plane compatible FDR v4 output file')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    parser.add_argument('trackfile', default=None, nargs='+', help='Path to one or more IGC files')
    args = parser.parse_args()
    
    # Set log level based on verbose flag
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    config = Config(args)
    for inPath in args.trackfile:
        logger.info(f"Processing {inPath}...")
        try:
            with open(inPath, 'r', encoding='utf-8', errors='ignore') as trackFile:
                filetype = getFiletype(trackFile)
                
                if filetype == FileType.IGC:
                    fdrFlight = parseIgcFile(config, trackFile)
                    if fdrFlight and len(fdrFlight.track) > 0:
                        outPath = Path(inPath).with_suffix('.fdr')
                        if config.outPath and config.outPath != DEFAULT_OUT_PATH:
                            outPath = Path(config.outPath) / outPath.name
                            
                        with open(outPath, 'w', encoding='utf-8') as fdrFile:
                            writeOutputFile(config, fdrFile, fdrFlight)
                        logger.info(f"Successfully generated: {outPath}")
                    else:
                        logger.error(f"No valid track data found in {inPath}")
                else:
                    logger.error(f"{inPath} is not a valid IGC file")
        except Exception as e:
            logger.error(f"Error processing {inPath}: {e}", exc_info=args.verbose)
            
    logger.info("Processing complete.")

if __name__ == "__main__":
    try:
        sys.exit(main())
    except FileNotFoundError as e:
        logger.critical(f"File not found: {e.filename}")
        sys.exit(3)
    except ValueError as e:
        logger.critical(f"Invalid input: {e}")
        sys.exit(2)
    except Exception as e:
        logger.critical(f"Unexpected error: {e}", exc_info=True)
        sys.exit(1)
