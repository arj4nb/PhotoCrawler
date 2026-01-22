#my first python program!
import os
import scandir
import sys
import logging
import sqlite3
import dataset
import settings
from Utils import *
from DataBase import *
import Crawl


def main():
    Log = logging.getLogger('myLogger')
    level = logging.getLevelName('WARNING')
    Log.setLevel(level)

    #create default paths
    from os.path import expanduser
    userpath = expanduser("~")

    scanpath = userpath

    from sys import platform as _platform
    if _platform=="win32":
        scanpath = userpath +"\\Pictures\\"
        settings.gOutputPath = "F:\\Photos\\"
        gTempPath = "F:\\Photos\\Temp\\"
    else:
        scanpath = os.path.join(userpath, "PhotoTest")
        settings.gOutputPath = os.path.join(userpath, "PhotoExportTest/")
        settings.gTempPath = os.path.join(settings.gOutputPath, "Temp/")
           
    #create directories
    makeSurePathExists(settings.gOutputPath)
    makeSurePathExists(settings.gTempPath)

    print ("Starting Photo Crawler")
    print ("Output path set to ", settings.gOutputPath)
    print ("Temporary path set to ", settings.gTempPath) 
    print ("Analyzing folder", scanpath)

    #initialize database
    settings.gDatabase = DataBase(settings.gOutputPath)
    
    #recurseiveley analyze folder
    Crawl.AnalyzeFolder(scanpath)

    #export database
    settings.gDatabase.ExportDatabase()

    

if __name__ == '__main__':
    main()
    