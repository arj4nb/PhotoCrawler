# settings.py

gOutputPath = "/path/to/output"
gTempPath = "/path/to/temp"
gDatabasePath = None  # Database directory path (defaults to gOutputPath if not set)
gImageExtensions = ["jpg", "jpeg", "png", "tif", "tiff", "gif", "bmp", "heic", "heif", "mov", "mp4", "m4v", "m4a", "m4b", "m4p", "m4v", "m4a", "m4b", "m4p", "cr2", "nef"]
gExifImageExtensions = ["jpg", "jpeg", "tif", "tiff", "mp4", "m4v", "m4a", "m4b", "m4p", "m4v", "m4a", "m4b", "m4p", "cr2", "nef"]
gIgnoreFolders = ["__MACOSX", "Data.noindex", ".Trash", "Caches", "Thumbnails", "com.apple.AddressBook.", "Library/Containers", "Application Support"]
gDatabase = None

# Statistics counters
gFolderImageCount = 0  # Number of images scanned in folders
gZipImageCount = 0     # Number of images scanned in ZIP files
gSkippedBetterCount = 0  # Number of files skipped because better versions exist
gSkippedDatabaseCount = 0  # Number of files skipped because already in database
gNonImageFileCount = 0  # Number of non-image files encountered
gSkippedPhotosLibraryCount = 0  # Number of photos skipped in Photos library because file not available (e.g., iCloud not downloaded)
