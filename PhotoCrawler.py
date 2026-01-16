#my first python program!
import os
import scandir
import sys
import logging
import sqlite3
import dataset
from Crawl import analyzefolder
from Utils import *
from DataBase import *


def main():
    Log = logging.getLogger('myLogger')
    level = logging.getLevelName('WARNING')
    Log.setLevel(level)

    #create default paths
    from os.path import expanduser
    userpath = expanduser("~")

    global gOutputPath
    global gTempPath 
    
    from sys import platform as _platform
    if _platform=="win32":
        userpath = userpath +"\\Pictures\\"
        gOutputPath = "F:\\Photos\\"
        gTempPath = "F:\\Photos\\Temp\\"
    else:
        userpath = os.path.join(userpath, "PhotoTest")
        gOutputPath = os.path.join(userpath, "PhotoExportTest/")
        gTempPath = os.path.join(userpath, "Temp/")
           
    #create directories
    makeSurePathExists(gOutputPath)
    makeSurePathExists(gTempPath)

    print ("Output path set to ", gOutputPath)
    print ("Temporary path set to ", gTempPath) 

    print ("Starting Photo Crawler")

    #initialize database
    gDb = DataBase(gOutputPath)

    print ("Analyzing folder",userpath)
    analyzefolder(userpath, gDb)

    gDb.ExportDatabase()

    

if __name__ == '__main__':
    main()
    