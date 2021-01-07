# --- Josh Aaron Miller 2020
# --- Player class

import importlib
db = importlib.import_module("db")
entity = importlib.import_module("entity")
logClass = importlib.import_module("logger")
logger = logClass.Logger("player")

class Player(entity.Entity):
	def __init__(self, name):
		super().__init__(name)
		self.primary_weapon = None
		self.skills = []
	
	# Write player stats from db.characters to file (characters.json)
	def write(self):
		for c in db.characters:
			if c["name"] == self.name:
				me = c
		if not me:
			raise ValueError("No such character")
		for key, val in self.attrs.items():
			me[key] = val
		me["primary_weapon"] = self.primary_weapon
		me["skills"] = self.skills
		db.save_characters()
		
	def read_from_file(self):
		e = db.load_player(self.name)
		for key, val in e.items():
			if isinstance(val, int):
				self.attrs[key] = val
			if key == "primary_weapon":
				self.primary_weapon = val
			if key == "skills":
				self.skills = val
				
	def __str__(self):
		ret = "[Player: " + self.name + "]"
		return ret
				

def init():			
	# init players
	for character in db.characters:
		if character["name"] != "GM":
			p = Player(character["name"])
			p.read_from_file()
			db.PLAYERS.append(p)
			logger.log("init", "Loaded player: {0}".format(p.display_name()))
			
init()