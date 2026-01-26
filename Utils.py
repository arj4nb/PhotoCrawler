
import os
import shutil
import settings
import time
import hashlib
from datetime import datetime, timezone
from DataBase import *
from PIL import Image
from PIL.ExifTags import TAGS


def makeSurePathExists(path):
    import errno
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def makeDirectorySafe(path):
    makeSurePathExists(path)

def computeFileHash(filepath):
    """Compute MD5 hash of a file for duplicate detection."""
    try:
        hash_md5 = hashlib.md5()
        with open(filepath, "rb") as f:
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        print("- error computing hash for ", filepath, ": error", str(e))
        return None

#from Pillow: https://pillow.readthedocs.io/en/stable/handbook/overview.html#image-archives
def get_date_created(image_path):
    try:
        image = Image.open(image_path)
        exifdata = image._getexif()
        
        if exifdata:
            for tag_id, value in exifdata.items():
                tag = TAGS.get(tag_id, tag_id)
                if tag == 'DateTimeOriginal':
                    return value
    except Exception as e:
        print("- error reading EXIF data from ", image_path, ": error", str(e))
    return None     



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

    # compute file hash for duplicate detection
    file_hash = computeFileHash(fullpath)
    if file_hash is None:
        print("- skipping ", fullpath, " (failed to compute hash)")
        return

    # check if photo already exists in database
    if settings.gDatabase.PhotoExists(file_hash):
        print("- skipping ", fullpath, " (already in database)")
        return

    # organize pictures into nicer paths based on date
    structured_path = organizePath(fullpath, timestamp_float)

    makeSurePathExists(structured_path)

    # copy image in a structured location
    copyImage(fullpath, structured_path)
    # add to database with hash
    settings.gDatabase.AddPhoto(filename, fullpath, timestamp_float, file_hash)