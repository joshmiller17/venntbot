# --- Josh Aaron Miller 2020
# --- Entity class

from collections import defaultdict

import importlib
db = importlib.import_module("db")
sheets = importlib.import_module("sheets")

ACTIONS_PER_TURN = 3
REACTIONS_PER_TURN = 1


class Entity:
	def __init__(self, name):
		self.name = name
		self.mods = []
		
		self.actions = ACTIONS_PER_TURN
		self.reactions = REACTIONS_PER_TURN
		
		self.attrs = defaultdict(int)
		self.read_from_file()
		
	def read_from_file(self):
		raise NotImplementedError
		
	def set_stat(self, stat, val):
		stat = stat.upper()
		self.attrs[stat] = val
		
	def mod_stat(self, stat, val):
		stat = stat.upper()
		self.attrs[stat] += val
		
	def get_stat(self, stat):
		stat = stat.upper()
		return self.attrs[stat]
		
	def more(self):
		ret = self.name + "\n"
		ret += str(self.attrs["HP"]) + " HP"
		return ret
		
	#def can_afford(self, ...) # TODO
		# do we have resources to buy this action etc?
	
	def add_modifier(self, name, stat, val, stacks=False):
		stat = stat.upper()
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