# --- Josh Aaron Miller 2020
# --- Enemy class

import importlib
db = importlib.import_module("db")
entity = importlib.import_module("entity")

class Enemy(entity.Entity):
	def __init__(self, name):
		#unique to enemy:
		self.dmg = "0"
		self.id = 0
	
		super().__init__(name)
				
	def display_name(self):
		return self.name + str(self.id)
		
	def read_from_file(self):
		e = db.get_enemy_file(self.name)
		self.dmg = e["dmg"]
		for key, val in e.items():
			if isinstance(val, int):
				self.attrs[key] = val