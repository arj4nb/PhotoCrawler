import dataset
import sqlite3
import datetime
import os
from Utils import log_debug, log_info, log_warning, log_error



class Base:
	def __init__(self):
		self.name=''
		self.timestamp=datetime.now



class Photo:
	def __init__(self,in_name,in_filename,in_timestamp):
		self.name=in_name
		self.filename=in_filename
		self.timestamp=in_timestamp



class Event:
	def __init__(self):
		self.name=''

class Album:
	def __init__(self):
		self.name=''



class DataBase:
	def __init__(self,in_path):
		# Ensure path ends with separator for directory paths
		if not in_path.endswith(os.sep) and not in_path.endswith('/'):
			in_path = in_path + os.sep
		# Construct full database path
		db_path = in_path + 'myphotos.db'
		
		log_debug(f"Opening database at: {db_path}")
		
		# Check if database file exists
		db_exists = os.path.exists(db_path)
		if db_exists:
			log_info(f"Database file exists: {db_path}")
			log_debug("Database file exists")
		else:
			log_info(f"Creating new database file: {db_path}")
			log_debug("Creating new database file")
		
		try:
			self.db = dataset.connect('sqlite:///' + db_path)
			log_info(f"Database opened successfully: {db_path}")
			log_debug("Database opened successfully")
		except sqlite3.OperationalError as e:
			error_msg = f"Database operational error: Cannot open database at {db_path}. Error: {str(e)}"
			log_error(error_msg)
			raise
		except sqlite3.DatabaseError as e:
			error_msg = f"Database error: Corrupted or invalid database at {db_path}. Error: {str(e)}"
			log_error(error_msg)
			raise
		except Exception as e:
			error_msg = f"Unexpected error opening database at {db_path}. Error: {str(e)}"
			log_error(error_msg, exc_info=True)
			raise

	def AddPhoto(self, in_name, in_filename, in_timestamp, in_hash):
		log_debug(f"Adding photo to database: {in_filename} (hash: {in_hash[:16]}...)")
		
		try:
			table = self.db['photos']
			table.insert(dict(name=in_name, filename=in_filename, timestamp=in_timestamp, hash=in_hash))
			log_debug(f"Photo added successfully: {in_filename}")
		except sqlite3.IntegrityError as e:
			error_msg = f"Database integrity error adding photo {in_filename}: {str(e)}"
			log_warning(error_msg)
			# Integrity errors (like duplicate hash) are expected in some cases, don't raise
		except sqlite3.OperationalError as e:
			error_msg = f"Database operational error adding photo {in_filename}: {str(e)}"
			log_error(error_msg)
			# Operational errors (table doesn't exist, locked, etc.) should be raised
			raise
		except sqlite3.DatabaseError as e:
			error_msg = f"Database error adding photo {in_filename}: {str(e)}"
			log_error(error_msg)
			raise
		except Exception as e:
			error_msg = f"Unexpected error adding photo {in_filename}: {str(e)}"
			log_error(error_msg, exc_info=True)
			raise

	def FindPhoto(self, in_filename):
		"""Find a photo by filename in the database."""
		log_debug(f"Finding photo in database: {in_filename}")
		
		try:
			table = self.db['photos']
			result = table.find(filename=in_filename)
			log_debug(f"Photo lookup completed for: {in_filename}")
			return result
		except sqlite3.OperationalError as e:
			error_msg = f"Database operational error finding photo {in_filename}: {str(e)}"
			log_error(error_msg)
			# Return empty result on error
			return iter([])
		except sqlite3.DatabaseError as e:
			error_msg = f"Database error finding photo {in_filename}: {str(e)}"
			log_error(error_msg)
			return iter([])
		except Exception as e:
			error_msg = f"Unexpected error finding photo {in_filename}: {str(e)}"
			log_error(error_msg, exc_info=True)
			return iter([])

	def PhotoExists(self, file_hash):
		"""Check if a photo with the given hash already exists in the database."""
		log_debug(f"Checking if photo exists (hash: {file_hash[:16]}...)")
		
		try:
			table = self.db['photos']
			result = table.find_one(hash=file_hash)
			exists = result is not None
			if exists:
				log_debug(f"Photo found in database (hash: {file_hash[:16]}...)")
			return exists
		except sqlite3.OperationalError as e:
			error_msg = f"Database operational error checking photo existence: {str(e)}"
			log_error(error_msg)
			# Return False on error but log it
			return False
		except sqlite3.DatabaseError as e:
			error_msg = f"Database error checking photo existence: {str(e)}"
			log_error(error_msg)
			return False
		except Exception as e:
			error_msg = f"Unexpected error checking photo existence: {str(e)}"
			log_error(error_msg, exc_info=True)
			return False


	def GetPhotoCount(self):
		"""Get the total number of photos in the database."""
		log_debug("Getting photo count from database")
		
		try:
			table = self.db['photos']
			count = len(list(table.all()))
			log_debug(f"Photo count: {count}")
			return count
		except sqlite3.OperationalError as e:
			error_msg = f"Database operational error getting photo count: {str(e)}"
			log_error(error_msg)
			# Return 0 on error but log it
			return 0
		except sqlite3.DatabaseError as e:
			error_msg = f"Database error getting photo count: {str(e)}"
			log_error(error_msg)
			return 0
		except Exception as e:
			error_msg = f"Unexpected error getting photo count: {str(e)}"
			log_error(error_msg, exc_info=True)
			return 0

	def ExportDatabase(self):
		# export all photos into a single JSON
		log_debug("Exporting database...")
		
		try:
			result = self.db['photos'].all()
			# Convert to list to get count and ensure we can iterate
			result_list = list(result)
			count = len(result_list)
			
			log_info(f"Database export complete: {count} photos exported")
			log_debug(f"Database export complete: {count} photos exported")
			
			# Return iterator for compatibility
			return iter(result_list)
		except sqlite3.OperationalError as e:
			error_msg = f"Database operational error during export: {str(e)}"
			log_error(error_msg)
			raise
		except sqlite3.DatabaseError as e:
			error_msg = f"Database error during export: {str(e)}"
			log_error(error_msg)
			raise
		except Exception as e:
			error_msg = f"Unexpected error during database export: {str(e)}"
			log_error(error_msg, exc_info=True)
			raise
		#dataset.freeze(result, format='json', filename='photos.json')

