import os
import sys
import settings
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
            LOG('DEBUG', f"Found modern iPhoto library: {entry.path}")
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


def AnalyzeIphotoFolder(path):
    try:
        LOG('DEBUG', f"Processing Apple Photos library path : {path}")
        for entry in os.scandir(path):
            if entry.is_dir() and IsValidSubDirectory(entry.path):
                AnalyzeIphotoFolder(entry.path)
            elif IsImageFile(entry.name):
                settings.gFolderImageCount += 1
                AddPhoto(path, entry.name, entry.stat().st_mtime)
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

