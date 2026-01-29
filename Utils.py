
import os
import re
import shutil
import settings
import time
import xxhash
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
    """Compute full xxHash (xxh64) of a file for duplicate detection.
    
    Uses xxHash which is 3-5x faster than MD5 while providing excellent
    hash distribution for duplicate detection purposes.
    
    Note: For most use cases, prefer ComputeQuickFileHash() which is much faster
    and provides excellent duplicate detection for photo files.
    """
    try:
        hasher = xxhash.xxh64()
        with open(filepath, "rb") as f:
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        LOG('ERROR', f"Error computing hash for {filepath}: {str(e)}", exc_info=True)
        return None


# Default chunk size for partial hashing (64KB)
QUICK_HASH_CHUNK_SIZE = 65536


def ComputeQuickFileHash(filepath, chunk_size=QUICK_HASH_CHUNK_SIZE):
    """Compute a quick hash of a file for fast duplicate detection.
    
    Uses xxHash (xxh64) with file size plus first and last chunks for identification.
    xxHash is 3-5x faster than MD5 while providing excellent hash distribution.
    
    This is much faster than hashing the entire file while still providing
    excellent duplicate detection for photos (collisions are extremely rare).
    
    Performance: For a 50MB RAW file, this reads ~128KB instead of 50MB,
    reducing I/O by ~400x. Combined with xxHash, total speedup is significant.
    
    For files smaller than 2*chunk_size (128KB by default), reads the entire file.
    
    Args:
        filepath: Path to the file
        chunk_size: Size of chunks to read from start and end (default 64KB)
        
    Returns:
        Hash string or None on error
    """
    try:
        file_stat = os.stat(filepath)
        file_size = file_stat.st_size
        
        hasher = xxhash.xxh64()
        
        # Include file size in the hash for extra collision resistance
        # Using a prefix to ensure size doesn't collide with file content
        hasher.update(f"quickhash:size={file_size}:".encode('utf-8'))
        
        with open(filepath, "rb") as f:
            if file_size <= chunk_size * 2:
                # Small file - read the whole thing (same as full hash for small files)
                hasher.update(f.read())
            else:
                # Read first chunk
                first_chunk = f.read(chunk_size)
                hasher.update(first_chunk)
                
                # Seek to last chunk and read
                f.seek(-chunk_size, 2)  # 2 = SEEK_END
                last_chunk = f.read(chunk_size)
                hasher.update(last_chunk)
        
        return hasher.hexdigest()
    except Exception as e:
        LOG('ERROR', f"Error computing quick hash for {filepath}: {str(e)}", exc_info=True)
        return None

#from Pillow: https://pillow.readthedocs.io/en/stable/handbook/overview.html#image-archives
def GetEarliestDateCreatedFromExif(image_path):
    """Get Content Created date from EXIF data by checking date/time tags and returning the earliest valid timestamp.
    
    Only checks known date/time EXIF tags: 306 (DateTime), 36867 (DateTimeOriginal), 36868 (DateTimeDigitized).
    For TIFF-based files (CR2, NEF, TIF, TIFF), uses custom binary parser first for reliable EXIF reading.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Unix timestamp as float of the earliest valid date found, or None if no valid dates found
    """
    # TIFF-based formats: use custom parser first (Pillow may not read EXIF reliably for RAW/some TIFF)
    if image_path.lower().endswith(TIFF_BASED_EXIF_EXTENSIONS):
        return GetTiffBasedExifPhotoTakenTime(image_path)

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
        LOG('WARNING', f"No EXIF data in {image_path}: {str(e)}", exc_info=True)
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
        # LOG('DEBUG', f"Failed to parse EXIF date string '{exif_date_string}': {str(e)}")
        return None


# TIFF-based EXIF reading (CR2, NEF, TIF, TIFF) - parse binary structure to extract date/time
# EXIF date tag IDs: 306=DateTime, 36867=DateTimeOriginal, 36868=DateTimeDigitized
EXIF_TAG_DATETIME = 306
EXIF_TAG_DATETIME_ORIGINAL = 36867
EXIF_TAG_DATETIME_DIGITIZED = 36868
EXIF_IFD_POINTER_TAG = 34665  # 0x8769, points to EXIF sub-IFD
TIFF_TYPE_ASCII = 2
TIFF_TYPE_LONG = 4

# File extensions that use TIFF-based structure (EXIF in IFD/Exif IFD)
TIFF_BASED_EXIF_EXTENSIONS = ('.cr2', '.nef', '.tif', '.tiff')


def GetTiffBasedExifPhotoTakenTime(file_path):
    """Read EXIF from a TIFF-based image file and return the time the photo was taken.
    
    Handles CR2 (Canon RAW), NEF (Nikon RAW), TIF, and TIFF. Parses the TIFF structure
    to find the EXIF IFD and extract date/time tags. Returns the earliest valid timestamp
    found among DateTimeOriginal, DateTimeDigitized, DateTime.
    
    Args:
        file_path: Path to the file (.cr2, .nef, .tif, .tiff)
        
    Returns:
        Unix timestamp as float, or None if not found or on error
    """
    date_tag_ids = [EXIF_TAG_DATETIME_ORIGINAL, EXIF_TAG_DATETIME_DIGITIZED, EXIF_TAG_DATETIME]
    
    try:
        with open(file_path, 'rb') as f:
            data = f.read(1024 * 1024)  # Read first 1MB; EXIF is near start
        
        if len(data) < 8:
            return None
        
        # TIFF header: byte order (2), magic 42 (2), offset to first IFD (4)
        if data[0:2] == b'II':
            little_endian = True
        elif data[0:2] == b'MM':
            little_endian = False
        else:
            return None
        
        if little_endian:
            def read16(offset):
                return data[offset] | (data[offset + 1] << 8)
            def read32(offset):
                return (data[offset] | (data[offset + 1] << 8) |
                        (data[offset + 2] << 16) | (data[offset + 3] << 24))
        else:
            def read16(offset):
                return (data[offset] << 8) | data[offset + 1]
            def read32(offset):
                return ((data[offset] << 24) | (data[offset + 1] << 16) |
                        (data[offset + 2] << 8) | data[offset + 3])
        
        if read16(2) != 42:
            return None
        
        ifd0_offset = read32(4)
        if ifd0_offset >= len(data):
            return None
        
        # Get EXIF IFD offset from IFD0 (tag 34665)
        exif_ifd_offset = _ReadIfdForTag(data, ifd0_offset, EXIF_IFD_POINTER_TAG, read16, read32, little_endian)
        if exif_ifd_offset is None:
            return None
        
        # Read date/time tags from EXIF IFD (values may be inline or at offset)
        valid_timestamps = []
        for tag_id in date_tag_ids:
            value = _ReadAsciiTagFromIfd(data, exif_ifd_offset, tag_id, read16, read32, little_endian)
            if value:
                ts = ParseExifDateString(value)
                if ts is not None:
                    valid_timestamps.append(ts)
        
        if valid_timestamps:
            return min(valid_timestamps)
        return None
        
    except Exception as e:
        LOG('DEBUG', f"Error reading TIFF-based EXIF from {file_path}: {str(e)}")
        return None


def _ReadIfdForTag(data, ifd_offset, tag_id, read16, read32, little_endian):
    """Read an IFD and return the value/offset for the given tag (for LONG type, e.g. EXIF IFD pointer)."""
    if ifd_offset + 2 > len(data):
        return None
    num_entries = read16(ifd_offset)
    for i in range(num_entries):
        entry_offset = ifd_offset + 2 + i * 12
        if entry_offset + 12 > len(data):
            return None
        entry_tag = read16(entry_offset)
        if entry_tag == tag_id:
            # Type 4 LONG, count 1 -> value in bytes 8-11
            return read32(entry_offset + 8)
    return None


def _ReadAsciiTagFromIfd(data, ifd_offset, tag_id, read16, read32, little_endian):
    """Read an ASCII tag from an IFD. Returns the string value or None."""
    if ifd_offset + 2 > len(data):
        return None
    num_entries = read16(ifd_offset)
    for i in range(num_entries):
        entry_offset = ifd_offset + 2 + i * 12
        if entry_offset + 12 > len(data):
            return None
        entry_tag = read16(entry_offset)
        entry_type = read16(entry_offset + 2)
        entry_count = read32(entry_offset + 4)
        entry_value_or_offset = read32(entry_offset + 8)
        
        if entry_tag != tag_id or entry_type != TIFF_TYPE_ASCII or entry_count == 0:
            continue
        
        # ASCII: count includes null terminator; value inline if count <= 4 else at offset
        if entry_count <= 4:
            # Value stored in the 4-byte value field
            start = entry_offset + 8
            end = min(start + entry_count, len(data))
            raw = data[start:end]
        else:
            # Value at offset
            start = entry_value_or_offset
            end = min(start + entry_count, len(data))
            if start >= len(data):
                return None
            raw = data[start:end]
        
        try:
            s = raw.decode('ascii', errors='ignore').strip('\x00').strip()
            if s and len(s) >= 19:  # "YYYY:MM:DD HH:MM:SS"
                return s
        except Exception:
            pass
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
    try:
        shutil.copy2(filename, destname)
    except Exception as e:
        LOG('ERROR', f"Error copying {filename} to {destname}: {str(e)}", exc_info=True)
        return False
    return True

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


def AddPhoto(in_fullpath, in_filename, in_timestamp_float):
    """Add a photo to the library.
    
    Args:
        in_fullpath: Full path to the source image file
        infilename: Filename to use when copying (may be original filename from database)
        in_timestamp_float: Timestamp to use for organization
        
    Performance optimization: This function orders operations from cheapest to most expensive:
    1. Regex check for face crops (no I/O)
    2. Quick database lookup by source path (fast indexed query)
    3. File hash computation (only if needed - reads entire file)
    4. EXIF reading (only if file will be processed)
    """
    # LOG('DEBUG', f"AddPhoto: {fullpath} (new filename: {new_filename})")

    # === CHEAP CHECK 1: Skip face crop images (regex only, no I/O) ===
    if re.search(r'_face\d+', in_filename, re.IGNORECASE):
        LOG('DEBUG', f"Skipping face crop image: {in_filename}")
        return

    # === CHEAP CHECK 2: Quick lookup by source path (indexed DB query) ===
    # This avoids computing the expensive file hash for files already processed
    # from the same source location (common when re-running crawler)
    existing_by_path = settings.gDatabase.FindPhotoBySourcePath(in_fullpath)
    if existing_by_path is not None:
        # File was already imported from this exact source path
        # Check if the destination file still exists
        if os.path.exists(existing_by_path['filename']):
            settings.gSkippedDatabaseCount += 1
            LOG('DEBUG', f"Skipping {in_fullpath} (already imported from same source)")
            return

    # === FAST OPERATION: Compute quick file hash for duplicate detection ===
    # Uses partial hashing (first+last 64KB + size) instead of reading entire file
    # This reduces I/O by ~400x for large RAW files while maintaining excellent accuracy
    file_hash = ComputeQuickFileHash(in_fullpath)
    if file_hash is None:
        LOG('ERROR', f"Skipping {in_fullpath} (failed to compute hash)")
        return

    # === Check if photo with same content exists (different source path, same file) ===
    photo_attributes = settings.gDatabase.GetPhotoAttributesByHash(file_hash)

    if photo_attributes is not None:
        # Photo with same hash exists - check if destination file exists
        if os.path.exists(photo_attributes['filename']):
            settings.gSkippedDatabaseCount += 1
            LOG('WARNING', f"Skipping {in_fullpath} (duplicate content already in database)")
            return

    # === EXPENSIVE OPERATION: Read EXIF for organization timestamp ===
    # Only performed after confirming file needs to be processed
    organization_timestamp = in_timestamp_float  # Default to file mtime

    file_ext = os.path.splitext(in_filename)[1].lstrip('.').lower()
    if file_ext in settings.gExifImageExtensions:
        exif_timestamp = GetEarliestDateCreatedFromExif(in_fullpath)
        if exif_timestamp:
            organization_timestamp = exif_timestamp
            # LOG('DEBUG', f"Using EXIF date for organization: {exif_timestamp}")

    # organize pictures into nicer paths based on date
    structured_path = OrganizePath(in_fullpath, organization_timestamp)

    MakeSurePathExists(structured_path)

    # Check for filename conflict and compare files
    dest_path = os.path.join(structured_path, in_filename)
    should_copy = True
    
    if photo_attributes is not None: # this case it should be copied for sure
        if os.path.exists(dest_path): #if there's a file already there, check if the new file is better
            try:
            
                # Get file stats for comparison
                source_stat = os.stat(in_fullpath)
                dest_stat = os.stat(dest_path)
                
                source_mtime = source_stat.st_mtime
                dest_mtime = dest_stat.st_mtime
                source_size = source_stat.st_size
                dest_size = dest_stat.st_size
                
                # Compare: newer file wins, if same time then larger file wins
                if dest_mtime > source_mtime:
                    should_copy = False
                    settings.gSkippedBetterCount += 1
                    LOG('WARNING', f"Skipping {in_fullpath} - existing file {dest_path} is newer")
                if dest_size >= source_size:
                    should_copy = False
                    settings.gSkippedBetterCount += 1
                    LOG('WARNING', f"Skipping {in_fullpath} - existing file {dest_path} is larger or equal size")
            except OSError as e:
                LOG('ERROR', f"Error comparing files {in_fullpath} and {dest_path}: {str(e)}", exc_info=True)
                # On error, proceed with copy to be safe
                should_copy = True
    
    # copy image in a structured location (only if should_copy is True)
    if should_copy:
        if CopyImage(in_fullpath, structured_path, in_filename):
            # add to database with hash
            if settings.gDatabase.AddPhoto(in_filename, in_fullpath, in_timestamp_float, file_hash):
                LOG('DEBUG', f"Added {in_fullpath} to {structured_path}")
    else:
        LOG('DEBUG', f"Not copying {in_fullpath} - existing file is better")