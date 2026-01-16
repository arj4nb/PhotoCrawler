import zipfile
from Utils import *
import os

def zipTimeConvert(z):
    import datetime
    return datetime.datetime(z.date_time[0],z.date_time[1],z.date_time[2],z.date_time[3],z.date_time[4],z.date_time[5])



def extractFileFromZip(zfile, zipentry):
    import time
    try:
        print ("zip extracting :", zipentry)

        #get the file attributes in the zipfile
        zipentry_info = zfile.getinfo(zipentry)
        orgdatetime = zipTimeConvert(zipentry_info)
        orgtime = time.mktime(orgdatetime.timetuple())

        global gTempPath

        #extract the actual file to Temporary Path
        zfile.extract(zipentry, gTempPath)

        #fix the path
        zippathfixed = zipentry.replace('/','\\')
        #get the actual location of the temporary file
        tempfile = os.path.join(gTempPath, zippathfixed)
        #set the original time back on the file
        os.utime(tempfile, (orgtime, orgtime))

    except:
        print ("zip extract fail", zipentry)


def analyzeZip(zipname):
    try:
        print ("Extracting Zip file ", zipname)
        zfile = zipfile.ZipFile(zipname)   

        for zipentry in zfile.namelist():
            if not zipentry.endswith('//') and isValidSubDirectory(zipentry) and isImageFile(zipentry):     #not a folder
                extractFileFromZip(zfile, zipentry)

        zipfile.close()
    except:
        print ("zip analyze - error handling zipfile ",zipname)

