import dataset
import sqlite3
import datetime
import os
from Utils import LOG
from Utils import ComputeQuickFileHash

# Database schema version - increment when making breaking changes (e.g., hash algorithm change)
# Version history:
#   1: Original MD5 hashing
#   2: Changed to xxHash (xxh64) for faster hashing
DB_SCHEMA_VERSION = 2


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
		
		LOG('DEBUG', f"Opening database at: {db_path}")
		
		# Check if database file exists
		db_exists = os.path.exists(db_path)
		if db_exists:
			LOG('INFO', f"Database file exists: {db_path}")
		else:
			LOG('INFO', f"Creating new database file: {db_path}")
		
		try:
			self.db = dataset.connect('sqlite:///' + db_path)
			LOG('INFO', f"Database opened successfully: {db_path}")
			
			# Check and handle database version migration
			self._check_and_migrate_version()
			
			# Create indexes for faster lookups (O(1) instead of O(n) table scan)
			self.db.query('CREATE INDEX IF NOT EXISTS idx_photos_hash ON photos(hash)')
			self.db.query('CREATE INDEX IF NOT EXISTS idx_photos_filename ON photos(filename)')
			LOG('DEBUG', "Database indexes on hash and filename columns ensured")
		except Exception as e:
			error_msg = f"Unexpected error opening database at {db_path}. Error: {str(e)}"
			LOG('ERROR', error_msg, exc_info=True)
			raise

	def _check_and_migrate_version(self):
		"""Check database schema version and migrate if necessary.
		
		If the stored version doesn't match DB_SCHEMA_VERSION, the photos table
		is cleared since hash values are incompatible between versions.
		"""
		metadata_table = self.db['metadata']
		
		# Get current stored version
		version_row = metadata_table.find_one(key='schema_version')
		stored_version = int(version_row['value']) if version_row else None
		
		if stored_version is None:
			# New database or pre-versioning database
			LOG('INFO', f"No schema version found, initializing to version {DB_SCHEMA_VERSION}")
			
			# Check if photos table has data (pre-versioning database)
			try:
				result = self.db.query('SELECT COUNT(*) as count FROM photos')
				count = list(result)[0]['count']
				if count > 0:
					LOG('WARNING', f"Found {count} photos from pre-versioning database, clearing due to hash algorithm change")

					self._clear_photos_table()
					#dont clear the table, just update the hashes
					# photos = self.db['photos'].all()
					#for photo in photos:
					#	photo['hash'] = ComputeQuickFileHash(photo['filename'])
					#	self.db['photos'].update(photo, ['id'])
			except Exception:
				# Table doesn't exist yet, that's fine
				pass
			
			# Set initial version
			metadata_table.upsert(dict(key='schema_version', value=str(DB_SCHEMA_VERSION)), ['key'])
			
		elif stored_version != DB_SCHEMA_VERSION:
			# Version mismatch - need to migrate
			LOG('WARNING', f"Database schema version mismatch: stored={stored_version}, current={DB_SCHEMA_VERSION}")
			LOG('WARNING', "Clearing photos table due to incompatible hash algorithm")
			
			self._clear_photos_table()
			
			# Update version
			metadata_table.upsert(dict(key='schema_version', value=str(DB_SCHEMA_VERSION)), ['key'])
			LOG('INFO', f"Database migrated to schema version {DB_SCHEMA_VERSION}")
		else:
			LOG('DEBUG', f"Database schema version {stored_version} is current")

	def _clear_photos_table(self):
		"""Clear all entries from the photos table."""
		try:
			photos_table = self.db['photos']
			photos_table.delete()
			LOG('INFO', "Photos table cleared successfully")
		except Exception as e:
			LOG('ERROR', f"Error clearing photos table: {str(e)}", exc_info=True)
			raise


	def AddPhoto(self, in_name, in_filename, in_timestamp, in_hash):
		# LOG('DEBUG', f"Adding photo to database: {in_filename} (hash: {in_hash[:16]}...)")
		try:
			table = self.db['photos']
			table.insert(dict(name=in_name, filename=in_filename, timestamp=in_timestamp, hash=in_hash))
			# LOG('DEBUG', f"Photo added successfully: {in_filename}")
			return True
		except Exception as e:
			error_msg = f"Unexpected error adding photo {in_filename}: {str(e)}"
			LOG('ERROR', error_msg, exc_info=True)
			raise
		return False


	def FindPhoto(self, in_filename):
		"""Find a photo by filename in the database."""
		# LOG('DEBUG', f"Finding photo in database: {in_filename}")
		
		try:
			table = self.db['photos']
			result = table.find(filename=in_filename)
			# LOG('DEBUG', f"Photo lookup completed for: {in_filename}")
			return result
		except Exception as e:
			error_msg = f"Unexpected error finding photo {in_filename}: {str(e)}"
			LOG('ERROR', error_msg, exc_info=True)
			return iter([])


	def GetPhotoAttributesByHash(self, in_file_hash):
		"""Get the attributes of a photo by file hash."""
		# LOG('DEBUG', f"Finding photo in database: {in_filename}")
		
		try:
			table = self.db['photos']
			result = table.find_one(hash=in_file_hash)
			# LOG('DEBUG', f"Photo lookup completed for: {in_filename}")
			return result
		except Exception as e:
			error_msg = f"Unexpected error finding photo by hash {in_file_hash}: {str(e)}"
			LOG('ERROR', error_msg, exc_info=True)
			return None


	def FindPhotoBySourcePath(self, source_path):
		"""Quick lookup to check if a source path was already processed.
		
		This is a cheap check that avoids computing file hash for files
		that have already been imported from the same source location.
		
		Args:
			source_path: The full source path of the file being imported
			
		Returns:
			Photo attributes dict if found, None otherwise
		"""
		try:
			table = self.db['photos']
			result = table.find_one(filename=source_path)
			return result
		except Exception as e:
			error_msg = f"Unexpected error finding photo by source path {source_path}: {str(e)}"
			LOG('ERROR', error_msg, exc_info=True)
			return None		


	def PhotoExists(self, filename, file_hash):
		"""Check if a photo with the given hash already exists in the database."""
		#LOG('DEBUG', f"Checking if photo exists (hash: {file_hash[:16]}...)")
		
		try:
			table = self.db['photos']
			result = table.find_one(hash=file_hash)
			exists = result is not None
			return exists
		except Exception as e:
			error_msg = f"Unexpected error checking photo existence: {str(e)}"
			LOG('ERROR', error_msg, exc_info=True)
			return False


	def GetPhotoCount(self):
		"""Get the total number of photos in the database."""
		LOG('DEBUG', "Getting photo count from database")
		
		try:
			# Use SQL COUNT(*) for efficiency instead of loading all rows into memory
			result = self.db.query('SELECT COUNT(*) as count FROM photos')
			count = list(result)[0]['count']
			LOG('DEBUG', f"Photo count: {count}")
			return count
		except Exception as e:
			error_msg = f"Unexpected error getting photo count: {str(e)}"
			LOG('ERROR', error_msg, exc_info=True)
			return 0


	def ExportDatabase(self, initial_count=0):
		# export all photos into a single JSON
		LOG('DEBUG', "Exporting database...")
		
		try:
			result = self.db['photos'].all()

			total_count = self.GetPhotoCount()
			new_photos = total_count - initial_count
			
			if initial_count > 0:
				LOG('INFO', f"Import complete: {new_photos} new photos imported, {total_count} total photos in database")
			else:
				LOG('INFO', f"Import complete: {total_count} photos imported (fresh scan)")
			
		except Exception as e:
			error_msg = f"Unexpected error during database export: {str(e)}"
			LOG('ERROR', error_msg, exc_info=True)
			raise
		#dataset.freeze(result, format='json', filename='photos.json')

