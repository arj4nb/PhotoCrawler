import zipfile
from Utils import *
import os
import pathlib
import settings
import IPhotoLibrary

def ZipTimeConvert(z):
    import datetime
    return datetime.datetime(z.date_time[0],z.date_time[1],z.date_time[2],z.date_time[3],z.date_time[4],z.date_time[5])


def RemoveEmptyDirs(dir_path, stop_at_path):
    """Remove empty directories recursively, stopping at stop_at_path.
    
    Args:
        dir_path: Directory path to start removing from
        stop_at_path: Stop removing when we reach this path (don't remove this one)
    """
    try:
        # Normalize paths for comparison
        dir_path = os.path.normpath(dir_path)
        stop_at_path = os.path.normpath(stop_at_path)
        
        # Don't remove if we've reached the stop path
        if dir_path == stop_at_path:
            return
        
        # Don't remove if directory doesn't exist
        if not os.path.exists(dir_path):
            return
        
        # Don't remove if it's not a directory
        if not os.path.isdir(dir_path):
            return
        
        # Try to remove the directory if it's empty
        try:
            os.rmdir(dir_path)
            LOG('DEBUG', f"Removed empty directory: {dir_path}")
            
            # Recursively try to remove parent directory
            parent_dir = os.path.dirname(dir_path)
            if parent_dir and parent_dir != dir_path:
                RemoveEmptyDirs(parent_dir, stop_at_path)
        except OSError:
            # Directory not empty or other error - that's fine, just stop
            pass
    except Exception as e:
        LOG('WARNING', f"Error removing directory {dir_path}: {str(e)}")



def ExtractFileFromZip(zfile, zipentry):
    import time
    extracted_file_path = None
    try:
        LOG('DEBUG', f"zip extracting : {zipentry}")

        #get the file attributes in the zipfile
        zipentry_info = zfile.getinfo(zipentry)
        orgdatetime = ZipTimeConvert(zipentry_info)
        orgtime = time.mktime(orgdatetime.timetuple())

        zip_crc = zipentry_info.CRC
        zip_str = str(zip_crc)
        zip_ext = pathlib.Path(zipentry).suffix
        crc_path = os.path.join(settings.gTempPath, zip_str) + zip_ext
        extracted_file_path = os.path.join(settings.gTempPath, zipentry)

        if not os.path.isfile(extracted_file_path):
            #extract the actual file to Temporary Path
            zfile.extract(zipentry, settings.gTempPath)
            #set the original time back on the file
            os.utime(extracted_file_path, (orgtime, orgtime))

        #now copy the image to the final location (AddPhoto will check for duplicates)
        AddPhoto(settings.gTempPath, zipentry, time.mktime(orgdatetime.timetuple()))

        # Clean up extracted file (only files, directories will be cleaned up after ZIP is fully processed)
        if extracted_file_path and os.path.exists(extracted_file_path):
            try:
                os.remove(extracted_file_path)
                LOG('DEBUG', f"Removed temp file: {extracted_file_path}")
            except OSError as e:
                LOG('WARNING', f"Failed to remove temp file {extracted_file_path}: {str(e)}")

    except Exception as e:
        LOG('ERROR', f"Zip extract fail {zipentry}: {str(e)}", exc_info=True)


def AnalyzeZip(zipname):
    zfile = None
    created_dirs = set()
    extracted_photos_libraries = []
    processed_photos_library_entries = set()
    
    try:
        LOG('INFO', f"Extracting Zip file {zipname}")
        zfile = zipfile.ZipFile(zipname)
        
        # First pass: identify and extract Photos library packages
        photos_library_prefixes = []
        for zipentry in zfile.namelist():
            entry_lower = zipentry.lower()
            # Check if this entry is or belongs to a Photos library
            if entry_lower.endswith('.photoslibrary/') or entry_lower.endswith('.photoslibrary'):
                # Extract the library name (base name without path)
                library_name = os.path.basename(zipentry.rstrip('/'))
                if not library_name.endswith('.photoslibrary'):
                    library_name = library_name + '.photoslibrary'
                library_prefix = zipentry.rstrip('/').rstrip('.photoslibrary') + '.photoslibrary'
                if library_prefix not in photos_library_prefixes:
                    photos_library_prefixes.append(library_prefix)
        
        # Extract and process each Photos library
        for library_prefix in photos_library_prefixes:
            extracted_library_path = os.path.join(settings.gTempPath, os.path.basename(library_prefix))
            if not os.path.exists(extracted_library_path):
                LOG('INFO', f"Extracting Photos library from ZIP: {library_prefix}")
                # Extract all entries belonging to this library
                for zipentry in zfile.namelist():
                    if zipentry.startswith(library_prefix) or zipentry == library_prefix.rstrip('/'):
                        if not zipentry.endswith('/'):
                            zfile.extract(zipentry, settings.gTempPath)
                            processed_photos_library_entries.add(zipentry)
                            # Track directory paths
                            zipentry_dir = os.path.dirname(zipentry)
                            if zipentry_dir:
                                extracted_dir = os.path.join(settings.gTempPath, zipentry_dir)
                                created_dirs.add(extracted_dir)
                
                # Process the extracted Photos library
                if os.path.exists(extracted_library_path) and os.path.isdir(extracted_library_path):
                    extracted_photos_libraries.append(extracted_library_path)
                    IPhotoLibrary.AnalyzeIphotoFolder(extracted_library_path)

        # Second pass: process regular files (skip entries already processed as part of Photos libraries)
        for zipentry in zfile.namelist():
            if zipentry in processed_photos_library_entries:
                continue  # Skip entries that were part of Photos libraries
                
            if not zipentry.endswith('//') and IsValidSubDirectory(zipentry):
                if IsImageFile(zipentry):     #not a folder
                    settings.gZipImageCount += 1
                    ExtractFileFromZip(zfile, zipentry)
                    
                    # Track directory paths created during extraction
                    zipentry_dir = os.path.dirname(zipentry)
                    if zipentry_dir:
                        # Build the full directory path in temp and track it
                        extracted_dir = os.path.join(settings.gTempPath, zipentry_dir)
                        created_dirs.add(extracted_dir)
                else:
                    settings.gNonImageFileCount += 1
                    LOG('DEBUG', f"Skipping non-image file in ZIP {zipname}: {zipentry}")

    except Exception as e:
        LOG('ERROR', f"Zip analyze - error handling zipfile {zipname}: {str(e)}", exc_info=True)
    finally:
        # Ensure ZIP file is closed
        if zfile is not None:
            try:
                zfile.close()
            except Exception as e:
                LOG('WARNING', f"Error closing ZIP file {zipname}: {str(e)}")
        
        # Clean up extracted Photos libraries
        for library_path in extracted_photos_libraries:
            try:
                import shutil
                if os.path.exists(library_path):
                    shutil.rmtree(library_path)
                    LOG('DEBUG', f"Removed extracted Photos library: {library_path}")
            except Exception as e:
                LOG('WARNING', f"Failed to remove extracted Photos library {library_path}: {str(e)}")
        
        # Clean up all directories created during extraction (even if processing failed)
        # Process directories from deepest to shallowest to avoid removing parent before child
        if created_dirs:
            sorted_dirs = sorted(created_dirs, key=lambda x: x.count(os.sep), reverse=True)
            for dir_path in sorted_dirs:
                RemoveEmptyDirs(dir_path, settings.gTempPath)

