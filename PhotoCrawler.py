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


def ParseArguments():
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
    parser.add_argument('--debug',
                        action='store_true',
                        help='Enable debug logging (default: off)')
    
    return parser.parse_args()


def SetupLogging(database_path, debug=False):
    """Initialize logging with file and console handlers.
    
    Args:
        database_path: Path to database directory where Logs folder will be created
        debug: If True, enable DEBUG level logging to console; otherwise WARNING
    
    Returns:
        The configured logger instance
    """
    import Utils
    
    # Create Logs directory in database path
    logs_dir = os.path.join(database_path, "Logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    # Create logger with file handler
    gLogger = logging.getLogger('PhotoCrawler')
    gLogger.setLevel(logging.DEBUG)  # Set to DEBUG to capture all levels, filter with handlers
    
    # Remove existing handlers to avoid duplicates
    gLogger.handlers = []
    
    # Create file handler
    log_file = os.path.join(logs_dir, 'photocrawler.log')
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    
    # Set logger level based on debug flag
    if debug:
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(logging.WARNING)
    
    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # Add handlers to logger
    gLogger.addHandler(file_handler)
    gLogger.addHandler(console_handler)
    
    # Set the logger in Utils module so all functions can use it
    Utils.gLogger = gLogger
    
    return gLogger


def Main():
    import Utils
    
    LOG('INFO', "Starting Photo Crawler")

    # Parse command-line arguments
    args = ParseArguments()
    
    # Get default paths based on platform
    from os.path import expanduser
    userpath = expanduser("~")
    from sys import platform as _platform

    # Set scan path (default or from argument)
    scanpath = args.scan_path or os.path.join(userpath, "PhotoTest")
    scanpath = ValidatePath(scanpath, "Scan", must_exist=True)

    # Set output path (default or from argument)
    settings.gOutputPath = args.output_path or os.path.join(userpath, "PhotoExportTest/")
    settings.gOutputPath = ValidatePath(settings.gOutputPath, "Output", must_be_writable=True)

    # Set temp path (default to output/Temp/ or from argument)
    settings.gTempPath = args.temp_path or os.path.join(settings.gOutputPath, "Temp/")
    settings.gTempPath = ValidatePath(settings.gTempPath, "Temp", must_be_writable=True)

    # Set database path (default to output path or from argument)
    settings.gDatabasePath = args.database_path or settings.gOutputPath
    settings.gDatabasePath = ValidatePath(settings.gDatabasePath, "Database", must_be_writable=True)
    
    # Initialize logging
    SetupLogging(settings.gDatabasePath, args.debug)
    
    #initialize database
    LOG('DEBUG', f"Initializing database at: {settings.gDatabasePath}")
    
    try:
        settings.gDatabase = DataBase(settings.gDatabasePath)
        LOG('INFO', "Database initialized successfully")
    except Exception as e:
        error_msg = f"Failed to initialize database at {settings.gDatabasePath}: {str(e)}"
        LOG('ERROR', error_msg, exc_info=True)
        raise
    
    # show database status for incremental mode
    LOG('DEBUG', "Getting photo count from database...")
    initial_count = 0
    try:
        initial_count = settings.gDatabase.GetPhotoCount()
        if initial_count > 0:
            LOG('INFO', f"Incremental mode: Found {initial_count} existing photos in database")
            LOG('INFO', "Skipping duplicates, only processing new files...")
        else:
            LOG('INFO', "Starting fresh scan (no existing photos in database)")
    except Exception as e:
        error_msg = f"Error getting photo count: {str(e)}"
        LOG('ERROR', error_msg)
        # Continue with scan even if count fails
        LOG('WARNING', "Continuing with scan despite count error")
    
    #recurseiveley analyze folder
    Crawl.AnalyzeFolder(scanpath)

    #export database
    LOG('DEBUG', "Starting database export")
    
    try:
        result = settings.gDatabase.ExportDatabase(initial_count)
        # Result is already logged in ExportDatabase method
    except Exception as e:
        error_msg = f"Error exporting database: {str(e)}"
        LOG('ERROR', error_msg, exc_info=True)
        # Export failure is not critical, continue
        LOG('WARNING', "Database export failed, but scan completed")

    # Display import statistics
    LOG('INFO', "="*60)
    LOG('INFO', "Import complete")
    LOG('INFO', "="*60)
    LOG('INFO', f"Images scanned in folders:     {settings.gFolderImageCount}")
    LOG('INFO', f"Images scanned in ZIP files:   {settings.gZipImageCount}")
    LOG('INFO', f"Files skipped (better version): {settings.gSkippedBetterCount}")
    LOG('INFO', "="*60)
    LOG('INFO', f"Import complete - Folders: {settings.gFolderImageCount}, ZIPs: {settings.gZipImageCount}, Skipped: {settings.gSkippedBetterCount}")


    

if __name__ == '__main__':
    Main()
    