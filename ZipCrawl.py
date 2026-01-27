import zipfile
from Utils import *
import os
import pathlib
import settings
import shutil
import time
import uuid

def ZipTimeConvert(z):
    import datetime
    return datetime.datetime(z.date_time[0],z.date_time[1],z.date_time[2],z.date_time[3],z.date_time[4],z.date_time[5])


def AnalyzeZip(zipname):
    zfile = None
    extracted_dir = None
    
    try:
        LOG('INFO', f"Extracting Zip file {zipname}")
        zfile = zipfile.ZipFile(zipname)
        
        # Create unique temporary directory for this ZIP
        zip_basename = os.path.splitext(os.path.basename(zipname))[0]
        extracted_dir = os.path.join(settings.gTempPath, f"zip_{zip_basename}_{uuid.uuid4().hex[:8]}")
        os.makedirs(extracted_dir, exist_ok=True)
        
        # Extract all entries and preserve timestamps
        for zipentry in zfile.namelist():
            if not zipentry.endswith('/'):  # Skip directory entries
                if IsValidSubDirectory(zipentry):
                    zfile.extract(zipentry, extracted_dir)
                    # Preserve original timestamp from ZIP
                    zipentry_info = zfile.getinfo(zipentry)
                    orgdatetime = ZipTimeConvert(zipentry_info)
                    orgtime = time.mktime(orgdatetime.timetuple())
                    extracted_path = os.path.join(extracted_dir, zipentry)
                    if os.path.exists(extracted_path):
                        os.utime(extracted_path, (orgtime, orgtime))
        
        # Track image count before processing
        initial_folder_count = settings.gFolderImageCount
        
        # Process extracted directory using standard folder analysis
        # Import here to avoid circular import with Crawl.py
        from Crawl import AnalyzeFolder
        AnalyzeFolder(extracted_dir)
        
        # Calculate images found in ZIP and update counters
        images_found = settings.gFolderImageCount - initial_folder_count
        settings.gZipImageCount += images_found
        settings.gFolderImageCount -= images_found
        
    except Exception as e:
        LOG('ERROR', f"Zip analyze - error handling zipfile {zipname}: {str(e)}", exc_info=True)
    finally:
        # Ensure ZIP file is closed
        if zfile is not None:
            try:
                zfile.close()
            except Exception as e:
                LOG('WARNING', f"Error closing ZIP file {zipname}: {str(e)}")
        
        # Clean up extracted directory
        if extracted_dir and os.path.exists(extracted_dir):
            try:
                shutil.rmtree(extracted_dir)
                LOG('DEBUG', f"Removed extracted ZIP directory: {extracted_dir}")
            except Exception as e:
                LOG('WARNING', f"Failed to remove extracted ZIP directory {extracted_dir}: {str(e)}")

