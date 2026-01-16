
import os
import shutil

gImageExtensions = ('jpg', 'jpeg', 'png', 'tif', 'tiff')
gIgnoreFolders = ('__MACOSX', 'Data.noindex', '.Trash', 'Caches', 'Thumbnails', 'com.apple.AddressBook.', 'Library/Containers', 'Application Support')



def make_sure_path_exists(path):
    import errno
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

def makedir(path):
    make_sure_path_exists(path)



#copy image to new folder. retain timestamps and basename
def copyImage(filename, destinationpath):
    basename = os.path.basename(filename)
    destname = os.path.join(destinationpath, basename)
    shutil.copy2(filename, destname)

def isImageFile(filename):
    lowered_filename = filename.lower()
    for image_ext in gImageExtensions:
        if lowered_filename.endswith(image_ext):
            return True
    return False

#is this a zipfile    
def isZipFile(filename):
    return filename.lower().endswith('zip')

#see if we actually want to parse this folder, iphoto libraries have all kind of junk
def isValidSubDirectory(filename):
    for ignorefolder in gIgnoreFolders:
        if ignorefolder in filename:
            return False
    return True
