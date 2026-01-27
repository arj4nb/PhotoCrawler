# settings.py

gOutputPath = "/path/to/output"
gTempPath = "/path/to/temp"
gDatabasePath = None  # Database directory path (defaults to gOutputPath if not set)
gImageExtensions = ["jpg", "jpeg", "png", "tif", "tiff", "gif", "bmp", "heic", "heif"]
gIgnoreFolders = ["__MACOSX", "Data.noindex", ".Trash", "Caches", "Thumbnails", "com.apple.AddressBook.", "Library/Containers", "Application Support"]
gDatabase = None

# Statistics counters
gFolderImageCount = 0  # Number of images scanned in folders
gZipImageCount = 0     # Number of images scanned in ZIP files
gSkippedBetterCount = 0  # Number of files skipped because better versions exist
