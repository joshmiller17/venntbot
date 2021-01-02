# --- Josh Aaron Miller 2020
# --- Player class

import importlib
db = importlib.import_module("db")
entity = importlib.import_module("entity")

class Player(entity.Entity):
	def __init__(self, name):
		super().__init__(name)
	
	# Write player stats to file
	def write(self):
		for c in db.characters:
			if c["name"] == self.name:
				me = c
		if not me:
			raise ValueError("No such character")
		for key, val in self.attrs.items():
			me[key] = val
		db.save_characters()
		
	def read_from_file(self):
		e = db.get_player_file(self.name)
		for key, val in e.items():
			if isinstance(val, int):
				self.attrs[key] = val
				
				
	def __str__(self):
		ret = "[Player: " + self.name + "]"
		return ret
				
# init players
for character in db.characters:
	if character["name"] != "GM":
		p = Player(character["name"])
		p.read_from_file()
		db.PLAYERS.append(p)