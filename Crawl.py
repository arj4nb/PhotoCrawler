
import os
import sys
import scandir
from ZipCrawl import analyzeZip
from Utils import *
from DataBase import *



def AddPhoto(path, entry, db):
	fullpath = os.path.join(path,entry.name)
	print ("AddPhoto", fullpath)
	tstat = entry.stat()
	db.AddPhoto(entry.name, fullpath, tstat.st_mtime)





def analyzefolder(path, db):
    try:
        for entry in scandir.scandir(path):
            print("Found entry ", entry.path)
            if entry.is_dir() and isValidSubDirectory(entry.path):
                print("Entering folder ", entry.path)
                analyzefolder(entry.path, db)
            elif isImageFile(entry.name):
                AddPhoto(path, entry, db)
            elif isZipFile(entry.name):
                analyzeZip(entry.path)
    except Exception as e:
        print ("- error scanning ", path, str(e))


