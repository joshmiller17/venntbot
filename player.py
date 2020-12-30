# --- Josh Aaron Miller 2020
# --- Player class
class Player:
	def __init__(self, name):
		self.name = name
		self.mods = []
		
	def add_modifier(self, name, stat, val, stacks=False):
		new_mod = {"name" : name, "stat" : stat, "val" : val}
		stacked = False
		if stacks:
			for m in mods:
				if m["name"] == name:
					m["val"] += val
					stacked = True
		if not stacked:
			mods.append(m)
			
	def get_modifier(self, name):
		for m in mods:
			if m["name"] == name:
				return m["val"]
		
	def remove_modifier(self, name):
		for m in mods:
			if m["name"] == name:
				mods.remove(m)