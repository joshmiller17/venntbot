# --- Josh Aaron Miller 2020
# --- Player class

import importlib
db = importlib.import_module("db")
entity = importlib.import_module("entity")

class Player(entity.Entity):
	def __init__(self, name):
		super().__init__(name)
		
		# unique to player:
		if "mp" not in self.attrs:
			self.attrs["mp"] = 0
		if "hero" not in self.attrs:
			self.attrs["hero"] = 0
		
	# Write player stats to file
	def write(self):
		for key, val in self.attrs.items():
			db.characters[name].key = val
		save_characters()
		
	def read_from_file(self):
		e = db.get_player_file(self.name)
		for key, val in e.items():
			if isinstance(val, int):
				self.attrs[key] = val
				
				
				
				
# init players
for character in db.characters:
	if character["name"] != "GM":
		p = Player(character["name"])
		db.PLAYERS.append(p)