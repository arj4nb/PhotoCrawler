#my first python program!
import os
import scandir
import sys
import argparse
import logging
import sqlite3
import dataset
import settings
from Utils import *
from DataBase import *
import Crawl


def parse_arguments():
    """Parse command-line arguments for configurable paths."""
    parser = argparse.ArgumentParser(
        description='Photo Crawler - Extract and organize photos from directories and ZIP files',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--scan-path', '-s',
                        help='Directory to start scanning for photos (default: platform-specific)')
    parser.add_argument('--output-path', '-o',
                        help='Directory where photos are copied (default: platform-specific)')
    parser.add_argument('--temp-path', '-t',
                        help='Temporary directory for ZIP extraction (default: output-path/Temp/)')
    parser.add_argument('--database-path', '-d',
                        help='Directory where database file is stored (default: output-path)')
    
    return parser.parse_args()


def normalize_path(path):
    """Normalize a path by expanding user directory and normalizing separators."""
    if path is None:
        return None
    expanded = os.path.expanduser(path)
    normalized = os.path.normpath(expanded)
    # Ensure directory paths end with separator for consistency
    # Only add separator if it's a directory or doesn't exist (assumed to be directory)
    if os.path.exists(normalized):
        if os.path.isdir(normalized):
            return normalized + os.sep if not normalized.endswith(os.sep) else normalized
    else:
        # Path doesn't exist, assume it's a directory path
        return normalized + os.sep if not normalized.endswith(os.sep) else normalized
    return normalized


def validate_path(path, path_type, must_exist=False, must_be_writable=False):
    """Validate a path and return normalized path or raise error."""
    if path is None:
        return None
    
    normalized = normalize_path(path)
    
    if must_exist:
        if not os.path.exists(normalized):
            raise ValueError(f"{path_type} path does not exist: {normalized}")
        if not os.path.isdir(normalized):
            raise ValueError(f"{path_type} path is not a directory: {normalized}")
        if must_be_writable and not os.access(normalized, os.W_OK):
            raise ValueError(f"{path_type} path is not writable: {normalized}")
    else:
        # For paths that don't need to exist, create the directory
        # Strip trailing separators before creating (os.makedirs handles them, but cleaner this way)
        path_to_create = normalized.rstrip(os.sep).rstrip('/')
        if not path_to_create:
            raise ValueError(f"{path_type} path is invalid: {normalized}")
        
        try:
            os.makedirs(path_to_create, exist_ok=True)
            # Verify directory was created
            if not os.path.exists(path_to_create) or not os.path.isdir(path_to_create):
                raise ValueError(f"{path_type} directory could not be created: {path_to_create}")
            # Add trailing separator back for consistency
            normalized = path_to_create + os.sep
            if must_be_writable and not os.access(normalized, os.W_OK):
                raise ValueError(f"{path_type} path is not writable: {normalized}")
        except OSError as e:
            raise ValueError(f"Cannot create {path_type} directory: {e}")
    
    print(f"DEBUG: {path_type} path set to: {normalized}")
    return normalized


def main():
    Log = logging.getLogger('myLogger')
    level = logging.getLevelName('WARNING')
    Log.setLevel(level)

    # Parse command-line arguments
    args = parse_arguments()

    # Get default paths based on platform
    from os.path import expanduser
    userpath = expanduser("~")
    from sys import platform as _platform

    # Set scan path (default or from argument)
    scanpath = args.scan_path or os.path.join(userpath, "PhotoTest")
    scanpath = validate_path(scanpath, "Scan", must_exist=True)

    # Set output path (default or from argument)
    settings.gOutputPath = args.output_path or os.path.join(userpath, "PhotoExportTest/")
    settings.gOutputPath = validate_path(settings.gOutputPath, "Output", must_be_writable=True)

    # Set temp path (default to output/Temp/ or from argument)
    settings.gTempPath = args.temp_path or os.path.join(settings.gOutputPath, "Temp/")
    settings.gTempPath = validate_path(settings.gTempPath, "Temp", must_be_writable=True)

    # Set database path (default to output path or from argument)
    settings.gDatabasePath = args.database_path or settings.gOutputPath
    settings.gDatabasePath = validate_path(settings.gDatabasePath, "Database", must_be_writable=True)

    # All directories (output, temp, database) are now created via validate_path
    print ("Starting Photo Crawler")

    #initialize database
    settings.gDatabase = DataBase(settings.gDatabasePath)
    
    # show database status for incremental mode
    existing_count = settings.gDatabase.GetPhotoCount()
    if existing_count > 0:
        print ("Incremental mode: Found", existing_count, "existing photos in database")
        print ("Skipping duplicates, only processing new files...")
    else:
        print ("Starting fresh scan (no existing photos in database)")
    
    #recurseiveley analyze folder
    Crawl.AnalyzeFolder(scanpath)

    #export database
    settings.gDatabase.ExportDatabase()

    

if __name__ == '__main__':
    main()
    