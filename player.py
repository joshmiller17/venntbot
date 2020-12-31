# --- Josh Aaron Miller 2020
# --- Player class

import importlib
db = importlib.import_module("db")
entity = importlib.import_module("entity")

ACTIONS_PER_TURN = 3
REACTIONS_PER_TURN = 1

class Player(entity.Entity):
	def __init__(self, name):
		super().__init__(name)
		
		# unique to player:
		if "mp" not in self.attrs:
			self.attrs["mp"] = 0
		if "hero" not in self.attrs:
			self.attrs["hero"] = 0
		self.actions = ACTIONS_PER_TURN
		self.reactions = REACTIONS_PER_TURN
	
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
				
# init players
for character in db.characters:
	if character["name"] != "GM":
		p = Player(character["name"])
		p.read_from_file()
		db.PLAYERS.append(p)