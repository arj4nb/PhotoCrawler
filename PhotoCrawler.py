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


gOutputPath = ""
gTempPath = ""


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
        userpath = "C:\\users\\arjan\\Pictures\\"
        gOutputPath = "F:\\Photos\\"
        gTempPath = "F:\\Photos\\Temp\\"
    else:
        gOutputPath = userpath + "/PhotoTest/"
        gTempPath = userpath + "/Temp/"
           
    #create directories
    makedir(gOutputPath)
    makedir(gTempPath)

    print ("Output path set to ", gOutputPath)
    print ("Temporary path set to ", gTempPath) 

    print ("Starting Photo Crawler")

    #initialize database
    gDb = DataBase(gOutputPath)

    print ("analyzing folder",userpath)
    analyzefolder(userpath, gDb)

    gDb.ExportDatabase()

    

if __name__ == '__main__':
    main()
    