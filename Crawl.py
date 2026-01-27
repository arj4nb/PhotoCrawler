import os
import sys
import settings
from Utils import *
from ZipCrawl import AnalyzeZip


def AnalyzeFolder(path):
    try:
        for entry in os.scandir(path):
            # print("Found entry ", entry.path)
            if entry.is_dir() and isValidSubDirectory(entry.path):
                AnalyzeFolder(entry.path)
            elif isImageFile(entry.name):
                settings.gFolderImageCount += 1
                AddPhoto(path, entry.name, entry.stat().st_mtime)
            elif isZipFile(entry.name):
                AnalyzeZip(entry.path)
    except Exception as e:
        LOG('ERROR', f"Error scanning {path}: {str(e)}", exc_info=True)


