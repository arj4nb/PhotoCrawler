import os
import sys
import settings
from Utils import *
from ZipCrawl import AnalyzeZip
import IPhotoLibrary


def AnalyzeFolder(path):
    try:
        for entry in os.scandir(path):
            # print("Found entry ", entry.path)
            if IPhotoLibrary.IsPhotosLibraryPackage(entry.path) == IPhotoLibrary.IPhotoLibraryVersion.MODERN:
                # Process Modern iPhotos library using osxphotos
                try:
                    IPhotoLibrary.ProcessPhotosLibrary(entry.path)
                except Exception as e:
                    LOG('ERROR', f"Error processing Photos library {entry.path}: {str(e)}")
            elif entry.is_dir() and IsValidSubDirectory(entry.path):
                AnalyzeFolder(entry.path)
            elif IsImageFile(entry.name):
                settings.gFolderImageCount += 1
                fullpath = os.path.join(path, entry.name)
                AddPhoto(fullpath, entry.name, entry.stat().st_mtime)
            elif IsZipFile(entry.name):
                AnalyzeZip(entry.path)
            elif entry.is_file():
                settings.gNonImageFileCount += 1
                LOG('DEBUG', f"Skipping non-image file: {entry.path}")
    except Exception as e:
        LOG('ERROR', f"Error scanning {path}: {str(e)}", exc_info=True)


