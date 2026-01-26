import dataset
import sqlite3
import datetime



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
		self.db = dataset.connect('sqlite:///'+in_path+'myphotos.db')

	def AddPhoto(self, in_name, in_filename, in_timestamp, in_hash):
		try:
			#print(in_name, in_timestamp)
			#newphoto = Photo(in_name, in_filename, in_timestamp)
			table = self.db['photos']
			table.insert(dict(name=in_name, filename=in_filename, timestamp=in_timestamp, hash=in_hash))
		except Exception as e:
			print("- database operation error ", str(e))

	def FindPhoto(self, in_filename):
		table = self.db['photos']
		result = table.find(filename=in_filename)
		return result

	def PhotoExists(self, file_hash):
		"""Check if a photo with the given hash already exists in the database."""
		try:
			table = self.db['photos']
			result = table.find_one(hash=file_hash)
			return result is not None
		except Exception as e:
			print("- database lookup error ", str(e))
			return False


	def GetPhotoCount(self):
		"""Get the total number of photos in the database."""
		try:
			table = self.db['photos']
			return len(list(table.all()))
		except Exception as e:
			print("- database count error ", str(e))
			return 0

	def ExportDatabase(self):
		# export all photos into a single JSON
		result = self.db['photos'].all()
		return result
		#dataset.freeze(result, format='json', filename='photos.json')

