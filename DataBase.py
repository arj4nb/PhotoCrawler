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


"""
class Event:
	def __init__(self):
        pass

class Album:
	def __init__(self):
        pass
"""



class DataBase:
	def __init__(self,in_path):
		self.db = dataset.connect('sqlite:///'+in_path+'myphotos.db')

	def AddPhoto(self, in_name, in_filename, in_timestamp):
		try:
			print(in_name, in_timestamp)
			#newphoto = Photo(in_name, in_filename, in_timestamp)
			table = self.db['photos']
			table.insert(dict(name=in_name, filename=in_filename, timestamp=in_timestamp))
		except Exception as e:
			print("- database operation error ", str(e))

	def FindPhoto(self, in_filename):
		table = self.db['photos']
		print (table.columns)
		result = table.find(filename=in_filename)
		print (result)
		return result


	def ExportDatabase(self):
		# export all photos into a single JSON
		result = self.db['photos'].all()
		dataset.freeze(result, format='json', filename='photos.json')


