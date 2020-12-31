# --- Josh Aaron Miller 2020
# --- Entity class

from collections import defaultdict

import importlib
db = importlib.import_module("db")
sheets = importlib.import_module("sheets")


class Entity:
	def __init__(self, name):
		self.name = name
		self.mods = []
		
		self.attrs = defaultdict(int)
		self.read_from_file()
		
	def read_from_file(self):
		raise NotImplementedError
		
	def set_stat(self, stat, val):
		self.attrs[stat] = val
		
	def mod_stat(self, stat, val):
		self.attrs[stat] += val
		
	def get_stat(self, stat):
		return self.attrs[stat]
		
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