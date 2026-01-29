import os
import settings
import time
from enum import Enum
from Utils import *
import osxphotos

class IPhotoLibraryVersion(Enum):
    NONE = 0
    OLD = 1
    MODERN = 2

def IsPhotosLibraryPackage(path):
    """Check if a path is an Apple Photos library package.
    
    Args:
        path: Path to check
        
    Returns:
        IPhotoLibraryVersion: NONE, OLD, or MODERN
    """
    if os.path.isdir(path):
        if path.lower().endswith('.photoslibrary'):
            LOG('DEBUG', f"Found modern Photos library: {path}")
            return IPhotoLibraryVersion.MODERN
        try:
            LOG('DEBUG', f"Checking if path contains iPhoto files: {path}")
            for entry in os.scandir(path):
                if entry.name.lower().endswith('.iphoto'):
                    LOG('DEBUG', f"Found old iPhoto library: {entry.path}")
                    return IPhotoLibraryVersion.OLD
        except Exception as e:
            LOG('ERROR', f"Error scanning {path}: {str(e)}", exc_info=True)
    return IPhotoLibraryVersion.NONE


def ProcessPhotosLibrary(library_path):
    """Process Photos library using osxphotos.
    
    Args:
        library_path: Path to the Photos library package
    """
    version = IsPhotosLibraryPackage(library_path)
    
    if version == IPhotoLibraryVersion.NONE:
        LOG('DEBUG', f"Path is not a Photos library: {library_path}")
        return
    
    if version == IPhotoLibraryVersion.OLD:
        LOG('WARNING', f"Old iPhoto libraries are not fully supported by osxphotos: {library_path}")
        # Could fallback to old implementation if needed
        #return
    
    # Process modern Photos library using osxphotos
    try:
        LOG('INFO', f"Processing Photos library with osxphotos: {library_path}")
        db = osxphotos.PhotosDB(library_path)
        
        photo_count = 0
        skipped_count = 0
        
        for photo in db.photos():
            try:
                # Get the file path - prefer original, fallback to edited if original doesn't exist
                photo_path = photo.path
                if not photo_path or not os.path.exists(photo_path):
                    # Try edited version
                    if hasattr(photo, 'path_edited') and photo.path_edited:
                        photo_path = photo.path_edited
                    else:
                        LOG('DEBUG', f"Skipping photo (file not found, may be in iCloud): {photo.original_filename} [{photo.uuid}]")
                        skipped_count += 1
                        settings.gSkippedPhotosLibraryCount += 1
                        continue
                
                # Get original filename
                original_filename = photo.original_filename
                if not original_filename:
                    # Fallback to current filename if original not available
                    original_filename = os.path.basename(photo_path)
                
                # Get creation date and convert to Unix timestamp
                photo_date = photo.date
                if photo_date:
                    # photo.date is a datetime object, convert to Unix timestamp
                    timestamp = time.mktime(photo_date.timetuple())
                else:
                    # Fallback to file modification time
                    timestamp = os.path.getmtime(photo_path)
                
                # Increment folder image count (photos from Photos libraries)
                settings.gFolderImageCount += 1
                
                # Process the photo
                AddPhoto(photo_path, original_filename, timestamp)
                photo_count += 1
                
            except Exception as e:
                LOG('ERROR', f"Error processing photo {photo.uuid if hasattr(photo, 'uuid') else 'unknown'}: {str(e)}", exc_info=True)
                skipped_count += 1
                continue
        
        LOG('INFO', f"Processed {photo_count} photos from Photos library, skipped {skipped_count}")
        
    except Exception as e:
        error_msg = str(e).lower()
        if "locked" in error_msg or "database is locked" in error_msg:
            LOG('WARNING', f"Photos library database is locked (Photos app may be open): {library_path}")
        elif "no such file" in error_msg or "not found" in error_msg:
            LOG('WARNING', f"Photos library not found or invalid: {library_path}")
        else:
            LOG('ERROR', f"Error processing Photos library {library_path}: {str(e)}", exc_info=True)
