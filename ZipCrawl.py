import zipfile
from Utils import *
import os
import pathlib
import settings

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

        zip_crc = zipentry_info.CRC
        zip_str = str(zip_crc)
        zip_ext = pathlib.Path(zipentry).suffix
        crc_path = os.path.join(settings.gTempPath, zip_str) + zip_ext
        extracted_file_path = os.path.join(settings.gTempPath, zipentry)

        #TODO: basically testing if file already was extracted. not happy: files with same name but different crc could overwrite eachother
        if not os.path.isfile(extracted_file_path):
            #extract the actual file to Temporary Path
            zfile.extract(zipentry, settings.gTempPath)
            #set the original time back on the file
            os.utime(extracted_file_path, (orgtime, orgtime))

        #now copy the image to the final location (AddPhoto will check for duplicates)
        AddPhoto(settings.gTempPath, zipentry, time.mktime(orgdatetime.timetuple()))

    except Exception as e:
        log_error(f"Zip extract fail {zipentry}: {str(e)}", exc_info=True)


def AnalyzeZip(zipname):
    try:
        print ("Extracting Zip file ", zipname)
        zfile = zipfile.ZipFile(zipname)   

        for zipentry in zfile.namelist():
            if not zipentry.endswith('//') and isValidSubDirectory(zipentry) and isImageFile(zipentry):     #not a folder
                extractFileFromZip(zfile, zipentry)

        zfile.close()
    except Exception as e:
        log_error(f"Zip analyze - error handling zipfile {zipname}: {str(e)}", exc_info=True)

