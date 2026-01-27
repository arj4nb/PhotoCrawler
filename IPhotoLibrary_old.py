import os
import sys
import settings
import sqlite3
import time
from enum import Enum
from Utils import *

class IPhotoLibraryVersion(Enum):
    NONE = 0
    OLD = 1
    MODERN = 2

def IsPhotosLibraryPackage(path):
    """Check if a path is an Apple Photos library package."""
    if os.path.isdir(path):
        if path.lower().endswith('.photoslibrary'):
            LOG('DEBUG', f"Found modern iPhoto library: {path}")
            return IPhotoLibraryVersion.MODERN
        try:
            LOG('DEBUG', f"Checking if path contains iPhoto files : {path}")
            for entry in os.scandir(path):
                if entry.name.lower().endswith('.iPhoto'):
                    LOG('DEBUG', f"Found old iPhoto library: {entry.path}")
                    return IPhotoLibraryVersion.OLD
        except Exception as e:
            LOG('ERROR', f"Error scanning {path}: {str(e)}", exc_info=True)
    return IPhotoLibraryVersion.NONE


def ReadPhotosDatabase(library_path):
    """Read Photos.sqlite database and extract path->(timestamp, original_filename) mappings.
    
    Args:
        library_path: Path to the Photos library package
        
    Returns:
        dict[str, tuple[float, str]]: Mapping of file paths (relative to library root) to 
            (Unix timestamp, original_filename) tuples. original_filename may be None if not found.
        None: If database is locked or unreadable
    """
    db_path = os.path.join(library_path, "database", "Photos.sqlite")
    
    if not os.path.exists(db_path):
        LOG('DEBUG', f"Photos.sqlite not found at {db_path}")
        return {}
    
    metadata_dict = {}
    
    try:
        # Open database in read-only immutable mode to handle locks
        db_uri = f"file:{db_path}?immutable=1"
        conn = sqlite3.connect(db_uri, uri=True, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Query for file paths, creation dates, and original filenames
        # Try ZGENERICASSET first (modern Photos), fallback to ZASSET if needed
        # Files are stored in originals/ folder with UUID names
        # We need to match by constructing the path: originals/[UUID]
        # Join with ZCLOUDMASTER to get original filename
        query = """
        SELECT 
            ZGENERICASSET.ZFILENAME as filename,
            ZGENERICASSET.ZDATECREATED as date_created,
            ZGENERICASSET.ZTRASHEDSTATE as trashed,
            ZCLOUDMASTER.ZORIGINALFILENAME as original_filename
        FROM ZGENERICASSET
        LEFT JOIN ZCLOUDMASTER ON ZGENERICASSET.ZMASTER = ZCLOUDMASTER.Z_PK
        WHERE ZGENERICASSET.ZFILENAME IS NOT NULL
        AND (ZGENERICASSET.ZTRASHEDSTATE IS NULL OR ZGENERICASSET.ZTRASHEDSTATE = 0)
        """
        
        try:
            cursor.execute(query)
            rows = cursor.fetchall()
        except sqlite3.OperationalError:
            # ZGENERICASSET table might not exist, try ZASSET instead
            query = """
            SELECT 
                ZASSET.ZFILENAME as filename,
                ZASSET.ZDATECREATED as date_created,
                ZASSET.ZTRASHEDSTATE as trashed,
                ZCLOUDMASTER.ZORIGINALFILENAME as original_filename
            FROM ZASSET
            LEFT JOIN ZCLOUDMASTER ON ZASSET.ZMASTER = ZCLOUDMASTER.Z_PK
            WHERE ZASSET.ZFILENAME IS NOT NULL
            AND (ZASSET.ZTRASHEDSTATE IS NULL OR ZASSET.ZTRASHEDSTATE = 0)
            """
            cursor.execute(query)
            rows = cursor.fetchall()

        # this does not seem to give valid results. Keeping for later use        
        # Also check for files in other locations (Masters, etc.)
        # Try alternative query for files in different locations
        alt_query = """
        SELECT 
            ZGENERICASSET.ZFILENAME as filename,
            ZGENERICASSET.ZDATECREATED as date_created,
            ZINTERNALRESOURCE.ZDIRECTORY as directory,
            ZCLOUDMASTER.ZORIGINALFILENAME as original_filename
        FROM ZGENERICASSET
        LEFT JOIN ZINTERNALRESOURCE ON ZGENERICASSET.Z_PK = ZINTERNALRESOURCE.ZASSET
        LEFT JOIN ZCLOUDMASTER ON ZGENERICASSET.ZMASTER = ZCLOUDMASTER.Z_PK
        WHERE ZGENERICASSET.ZFILENAME IS NOT NULL
        AND (ZGENERICASSET.ZTRASHEDSTATE IS NULL OR ZGENERICASSET.ZTRASHEDSTATE = 0)
        """
        try:
            cursor.execute(alt_query)
            alt_rows = cursor.fetchall()

            if alt_rows is not None:
                LOG('DEBUG', f"Alt rows: {len(alt_rows)}")
                for alt_row in alt_rows:
                    for key in alt_row.keys():
                        LOG('DEBUG', f"Key: {key}, Value: {alt_row[key]}")
        except sqlite3.OperationalError:
            # ZINTERNALRESOURCE table might not exist in all versions
            pass

        # now process the results
        for row in rows:
            for key in row.keys():
                LOG('DEBUG', f"Key: {key}, Value: {row[key]}")

            filename = row['filename']
            date_created = row['date_created']
            directory = row['directory'] if 'directory' in row else None
            original_filename = row['original_filename']

            if original_filename:
                LOG('DEBUG', f"Original filename for {filename} is {original_filename}")


            if filename and date_created:
                # Construct path with directory if available
                if directory:
                    file_path = os.path.join(directory, filename).replace(os.sep, '/').lower()
                else:
                    # Files in originals/ are organized by first character of filename
                    first_char = filename[0] if filename else ''
                    file_path = os.path.join("originals", first_char, filename).replace(os.sep, '/').lower()
                
                unix_timestamp = date_created + 978307200.0
                
                # Only add if not already in dict (prefer originals path)
                if file_path not in metadata_dict:
                    metadata_dict[file_path] = (unix_timestamp, original_filename)

        
        conn.close()
        LOG('DEBUG', f"Read {len(metadata_dict)} entries from Photos.sqlite")
        
    except sqlite3.OperationalError as e:
        if "locked" in str(e).lower() or "database is locked" in str(e):
            LOG('WARNING', f"Photos.sqlite database is locked (Photos app may be open): {db_path}")
            return None
        else:
            LOG('ERROR', f"Error reading Photos.sqlite: {str(e)}", exc_info=True)
            return None
    except sqlite3.DatabaseError as e:
        LOG('ERROR', f"Database error reading Photos.sqlite: {str(e)}", exc_info=True)
        return None
    except Exception as e:
        LOG('ERROR', f"Unexpected error reading Photos.sqlite: {str(e)}", exc_info=True)
        return None
    
    return metadata_dict


def InitializePhotosLibrary(library_path):
    """Initialize a Photos library by determining version and reading database if applicable.
    
    Args:
        library_path: Path to the Photos library package
        
    Returns:
        tuple[IPhotoLibraryVersion, dict|None]: (version, metadata_dict) if successful
            metadata_dict maps file paths to (timestamp, original_filename) tuples
        None: If database is locked (caller should skip library)
    """
    version = IsPhotosLibraryPackage(library_path)
    
    if version == IPhotoLibraryVersion.NONE:
        return None
    
    if version == IPhotoLibraryVersion.MODERN:
        # Read database for modern libraries
        metadata_dict = ReadPhotosDatabase(library_path)
        if metadata_dict is None:
            # Database is locked - return None to skip library
            return None
        return (version, metadata_dict)
    elif version == IPhotoLibraryVersion.OLD:
        # Old libraries don't use Photos.sqlite, return None for metadata
        return (version, None)
    
    return None


def AnalyzeIphotoFolder(path, library_root=None, metadata_dict=None, library_version=None):
    """Analyze Photos library folder recursively.
    
    Args:
        path: Current path being analyzed
        library_root: Root path of the Photos library (for path matching)
        metadata_dict: Dictionary mapping file paths to (timestamp, original_filename) tuples (from database)
        library_version: IPhotoLibraryVersion enum value (OLD or MODERN)
    """
    try:
        LOG('DEBUG', f"Processing Apple Photos library path : {path}")
        
        # Set library_root to path if not provided (first call)
        if library_root is None:
            library_root = path
        
        # Determine library version if not provided
        if library_version is None:
            library_version = IsPhotosLibraryPackage(library_root)
        
        for entry in os.scandir(path):
            # Skip "Data" folder for old iPhoto libraries (contains thumbnails)
            if library_version == IPhotoLibraryVersion.OLD and entry.is_dir() and entry.name.lower() == "data":
                LOG('DEBUG', f"Skipping Data folder (thumbnails) in old iPhoto library: {entry.path}")
                continue
            
            if entry.is_dir() and IsValidSubDirectory(entry.path):
                AnalyzeIphotoFolder(entry.path, library_root, metadata_dict, library_version)
            elif IsImageFile(entry.name):
                settings.gFolderImageCount += 1
                
                # Try to get timestamp and original filename from metadata database
                fullpath = entry.path
                timestamp = entry.stat().st_mtime  # Default to file mtime
                new_filename = entry.name  # Default to current filename
                
                if metadata_dict is not None:
                    # Calculate relative path from library root
                    try:
                        rel_path = os.path.relpath(entry.path, library_root)
                        # Normalize to forward slashes and convert to lowercase for lookup
                        rel_path_normalized = rel_path.replace(os.sep, '/').lower()
                        
                        # Look up in metadata_dict (keys are already lowercase)
                        if rel_path_normalized in metadata_dict:
                            timestamp, original_filename = metadata_dict[rel_path_normalized]
                            if original_filename:
                                new_filename = original_filename
                                LOG('DEBUG', f"Using database timestamp and original filename for {entry.path}: {original_filename}")
                            else:
                                LOG('DEBUG', f"Using database timestamp for {entry.path}")
                    except ValueError:
                        # Paths are on different drives or relpath fails
                        pass
                
                AddPhoto(fullpath, new_filename, timestamp)
            elif entry.is_file():
                settings.gNonImageFileCount += 1
                LOG('DEBUG', f"Skipping non-image file: {entry.path}")
    except PermissionError:
        LOG('WARNING', f"Permission denied accessing Photos library (macOS may restrict access): {path}")
    except OSError as e:
        if e.errno == 1:  # Operation not permitted
            LOG('WARNING', f"Operation not permitted accessing Photos library (macOS may restrict access): {path}")
        else:
            raise
    except Exception as e:
        LOG('ERROR', f"Error scanning {path}: {str(e)}", exc_info=True)

