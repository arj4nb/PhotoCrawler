
import os
import shutil
import settings
import time
from datetime import datetime, timezone
from DataBase import *



def makeSurePathExists(path):
    import errno
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def makeDirectorySafe(path):
    makeSurePathExists(path)





#copy image to new folder. retain timestamps and basename
def copyImage(filename, destinationpath):
    basename = os.path.basename(filename)
    destname = os.path.join(destinationpath, basename)
    shutil.copy2(filename, destname)

def isImageFile(filename):
    lowered_filename = filename.lower()
    for image_ext in settings.gImageExtensions:
        if lowered_filename.endswith(image_ext):
            return True
    return False

#is this a zipfile    
def isZipFile(filename):
    return filename.lower().endswith('zip')

#see if we actually want to parse this folder, iphoto libraries have all kind of junk
def isValidSubDirectory(filename):
    for ignorefolder in settings.gIgnoreFolders:
        if ignorefolder in filename:
            return False
    return True



#organize path
def organizePath(path, timestamp_float):
    base = os.path.basename(path)
    dirn = os.path.dirname(path)

    timestr = time.localtime(timestamp_float)
    year = time.strftime("%Y", timestr)
    month = time.strftime("%m", timestr)
    day = time.strftime("%d", timestr)

    newpath = os.path.join(settings.gOutputPath, year, month, day)
    return newpath


def AddPhoto(path, filename, timestamp_float):
    fullpath = os.path.join(path, filename)
    print("AddPhoto", fullpath)

    # organize pictures into nicer paths based on date
    structured_path = organizePath(fullpath, timestamp_float)

    makeSurePathExists(structured_path)

    # copy image in a structured location
    copyImage(fullpath, structured_path)
    # add to database
    settings.gDatabase.AddPhoto(filename, fullpath, timestamp_float)