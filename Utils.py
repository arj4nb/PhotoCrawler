
import os
import shutil
import settings
import time
import hashlib
import logging
from datetime import datetime, timezone
from PIL import Image
from PIL.ExifTags import TAGS

# Global logger instance for the entire application (initialized in main())
gLogger = None


def LOG(level, message, exc_info=False):
    """Log message at specified level and print it with level prefix.
    
    Args:
        level: Logging level - 'DEBUG', 'INFO', 'WARNING', or 'ERROR'
        message: Message to log
        exc_info: If True, include exception info (only used for ERROR level)
    """
    level_upper = level.upper()
    
    if gLogger is not None:
        if level_upper == 'DEBUG':
            gLogger.debug(message)
        elif level_upper == 'INFO':
            gLogger.info(message)
        elif level_upper == 'WARNING':
            gLogger.warning(message)
        elif level_upper == 'ERROR':
            gLogger.error(message, exc_info=exc_info)
    
    #print(f"{level_upper}: {message}")


def NormalizePath(path):
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


def ValidatePath(path, path_type, must_exist=False, must_be_writable=False):
    """Validate a path and return normalized path or raise error."""
    if path is None:
        return None
    
    normalized = NormalizePath(path)
    
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
    
    LOG('DEBUG', f"{path_type} path set to: {normalized}")
    return normalized


def MakeSurePathExists(path):
    import errno
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def MakeDirectorySafe(path):
    MakeSurePathExists(path)

def ComputeFileHash(filepath):
    """Compute MD5 hash of a file for duplicate detection."""
    try:
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        LOG('ERROR', f"Error computing hash for {filepath}: {str(e)}", exc_info=True)
        return None

#from Pillow: https://pillow.readthedocs.io/en/stable/handbook/overview.html#image-archives
def GetEarliestDateCreatedFromExif(image_path):
    """Get Content Created date from EXIF data by checking date/time tags and returning the earliest valid timestamp.
    
    Only checks known date/time EXIF tags: 306 (DateTime), 36867 (DateTimeOriginal), 36868 (DateTimeDigitized).
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Unix timestamp as float of the earliest valid date found, or None if no valid dates found
    """
    try:
        with Image.open(image_path) as image:
            exifdata = image._getexif()
            
            if not exifdata:
                return None
            
            # Only check known date/time EXIF tags
            date_tags = [
                (306, 'DateTime'),
                (36867, 'DateTimeOriginal'),
                (36868, 'DateTimeDigitized')
            ]
            
            # Collect all valid timestamps from date/time tags
            valid_timestamps = []
            
            for tag_id, tag_name in date_tags:
                if tag_id in exifdata:
                    value = exifdata[tag_id]
                    # Check if value is a string that looks like an EXIF date/time
                    if isinstance(value, str):
                        try:
                            # Try to parse it as an EXIF date
                            timestamp = ParseExifDateString(value)
                            if timestamp is not None:
                                valid_timestamps.append(timestamp)
                                # LOG('DEBUG', f"Found valid EXIF date tag {tag_name} ({tag_id}): {value} -> {timestamp}")
                        except Exception:
                            # Not a valid date string, skip
                            # LOG('DEBUG', f"Invalid date string in EXIF tag {tag_name} ({tag_id}): {value}")
                            pass
            
            # Return the earliest (minimum) timestamp found
            if valid_timestamps:
                earliest = min(valid_timestamps)
                # LOG('DEBUG', f"Earliest EXIF timestamp found: {earliest}")
                return earliest
            
    except Exception as e:
        LOG('ERROR', f"Error reading EXIF data from {image_path}: {str(e)}", exc_info=True)
    return None     


def ParseExifDateString(exif_date_string):
    """Parse EXIF date string to Unix timestamp.
    
    Args:
        exif_date_string: Date string in format "YYYY:MM:DD HH:MM:SS"
    
    Returns:
        Unix timestamp as float, or None if parsing fails
    """
    try:
        from datetime import datetime
        # EXIF format uses colons in date: "YYYY:MM:DD HH:MM:SS"
        date_part, time_part = exif_date_string.split(' ', 1)
        date_part = date_part.replace(':', '-')  # Convert to "YYYY-MM-DD"
        dt_string = f"{date_part} {time_part}"
        dt = datetime.strptime(dt_string, "%Y-%m-%d %H:%M:%S")
        return time.mktime(dt.timetuple())
    except Exception as e:
        LOG('DEBUG', f"Failed to parse EXIF date string '{exif_date_string}': {str(e)}")
        return None


#copy image to new folder. retain timestamps and basename
def CopyImage(filename, destinationpath, new_filename=None):
    """Copy image file to destination path.
    
    Args:
        filename: Source file path
        destinationpath: Destination directory path
        new_filename: Optional new filename to use (defaults to source basename)
    """
    if new_filename is None:
        new_filename = os.path.basename(filename)
    destname = os.path.join(destinationpath, new_filename)
    shutil.copy2(filename, destname)

def IsImageFile(filename):
    lowered_filename = filename.lower()
    for image_ext in settings.gImageExtensions:
        if lowered_filename.endswith(image_ext):
            return True
    return False

#is this a zipfile    
def IsZipFile(filename):
    return filename.lower().endswith('zip')



#see if we actually want to parse this folder, iphoto libraries have all kind of junk
def IsValidSubDirectory(filename):
    for ignorefolder in settings.gIgnoreFolders:
        if ignorefolder in filename:
            return False
    return True



#organize path
def OrganizePath(path, timestamp_float):
    base = os.path.basename(path)
    dirn = os.path.dirname(path)

    timestr = time.localtime(timestamp_float)
    year = time.strftime("%Y", timestr)
    month = time.strftime("%m", timestr)
    day = time.strftime("%d", timestr)

    newpath = os.path.join(settings.gOutputPath, year, month, day)
    return newpath


def AddPhoto(fullpath, new_filename, timestamp_float):
    """Add a photo to the library.
    
    Args:
        fullpath: Full path to the source image file
        new_filename: Filename to use when copying (may be original filename from database)
        timestamp_float: Timestamp to use for organization
    """
    # LOG('DEBUG', f"AddPhoto: {fullpath} (new filename: {new_filename})")

    # compute file hash for duplicate detection
    file_hash = ComputeFileHash(fullpath)
    if file_hash is None:
        LOG('ERROR', f"Skipping {fullpath} (failed to compute hash)")
        return

    # check if photo already exists in database
    if settings.gDatabase.PhotoExists(new_filename, file_hash):
        settings.gSkippedDatabaseCount += 1
        LOG('WARNING', f"Skipping {fullpath} (already in database)")
        return

    organization_timestamp = timestamp_float  # Default to file mtime

    # Try to get EXIF date for better organization (only for supported formats)
    file_ext = os.path.splitext(new_filename)[1].lstrip('.').lower()
    if file_ext in settings.gExifImageExtensions:
        exif_timestamp = GetEarliestDateCreatedFromExif(fullpath)
        if exif_timestamp:
            organization_timestamp = exif_timestamp
            LOG('DEBUG', f"Using EXIF date for organization: {exif_timestamp}")

    # organize pictures into nicer paths based on date
    structured_path = OrganizePath(fullpath, organization_timestamp)

    MakeSurePathExists(structured_path)

    # Check for filename conflict and compare files
    dest_path = os.path.join(structured_path, new_filename)
    should_copy = True
    
    if os.path.exists(dest_path):
        try:
           
            # Get file stats for comparison
            source_stat = os.stat(fullpath)
            dest_stat = os.stat(dest_path)
            
            source_mtime = source_stat.st_mtime
            dest_mtime = dest_stat.st_mtime
            source_size = source_stat.st_size
            dest_size = dest_stat.st_size
            
            # Compare: newer file wins, if same time then larger file wins
            if dest_mtime > source_mtime:
                should_copy = False
                settings.gSkippedBetterCount += 1
                LOG('WARNING', f"Skipping {fullpath} - existing file {dest_path} is newer")
            if dest_size >= source_size:
                should_copy = False
                settings.gSkippedBetterCount += 1
                LOG('WARNING', f"Skipping {fullpath} - existing file {dest_path} is larger or equal size")
        except OSError as e:
            LOG('ERROR', f"Error comparing files {fullpath} and {dest_path}: {str(e)}", exc_info=True)
            # On error, proceed with copy to be safe
            should_copy = True
    
    # copy image in a structured location (only if should_copy is True)
    if should_copy:
        CopyImage(fullpath, structured_path, new_filename)
        # add to database with hash
        settings.gDatabase.AddPhoto(new_filename, fullpath, timestamp_float, file_hash)
    else:
        LOG('DEBUG', f"Not copying {fullpath} - existing file is better")