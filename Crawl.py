
import os
import sys
from ZipCrawl import analyzeZip
from Utils import *
from DataBase import *
from datetime import datetime, timezone


#organize path
def organizePath(path, timestamp):
    base = os.path.basename(path)
    dirn = os.path.dirname(path)

    year = timestamp.strftime("%Y")
    month = timestamp.strftime("%m")
    day = timestamp.strftime("%d")

    newpath = os.path.join(gOutputPath, base)
    return newpath


def AddPhoto(path, filename, filestat, db):
    fullpath = os.path.join(path, filename)
    print("AddPhoto", fullpath)

    # extract time
    modified_time_stamp = datetime.fromtimestamp(filestat.st_mtime)

    # organize pictures into nicer paths based on date
    structured_path = organizePath(fullpath, modified_time_stamp)

    makeSurePathExists(structured_path)

    # copy image in a structured location
    copyImage(fullpath, structured_path)
    # add to database
    db.AddPhoto(filename, fullpath, filestat.st_mtime)


def analyzefolder(path, db):
    try:
        for entry in os.scandir(path):
            # print("Found entry ", entry.path)
            if entry.is_dir() and isValidSubDirectory(entry.path):
                # print("Recurse into folder ", entry.path)
                analyzefolder(entry.path, db)
            elif isImageFile(entry.name):
                AddPhoto(path, entry.name, entry.stat(), db)
            elif isZipFile(entry.name):
                analyzeZip(entry.path)
    except Exception as e:
        print("- error scanning ", path, str(e))


