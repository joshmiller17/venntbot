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
		
	def new_turn(self):
		self.actions = ACTIONS_PER_TURN
		self.reactions = REACTIONS_PER_TURN
		
	# do we have these resources
	def can_afford(self, cost):
		for key, val in cost.items():
			try:
				val = int(val)
			except ValueError:
				pass
			if not isinstance(val, int):
				print("entity.can_afford ignoring " + key + ": " + str(val))
				continue # ignore X, *, Attack, Passive, etc
			if key == 'A':
				if self.actions < val:
					print("A " + str(self.actions) + " < " + str(val))
					return False
			if key == 'R':
				if self.reactions < val:
					print("A " + str(self.reactions) + " < " + str(val))
					return False
			if key == 'M':
				if self.attrs["MP"] < val:
					print("A " + str(self.attrs["MP"]) + " < " + str(val))
					return False
			if key == 'V':
				if self.attrs["VIM"] < val:
					print("A " + str(self.attrs["VIM"]) + " < " + str(val))
					return False
			# TODO Health and Hero Points
		return True
		
	
	async def change_resource_verbose(self, ctx, key, delta):
		if key == 'A':
			self.actions += delta
			await ctx.send(str(self.actions) + " Action(s) left")
		if key == 'R':
			self.reactions += delta
			await ctx.send(str(self.reactions) + " Reaction(s) left")
		if key == 'M':
			self.attrs["MP"] += delta
			await ctx.send(str(self.attrs["MP"]) + " MP left")
		if key == 'V':
			self.attrs["VIM"] += delta
			await ctx.send(str(self.attrs["VIM"]) + " Vim left")
		# TODO Health and Hero Points
			
	def change_resource(self, key, delta):
		if key == 'A':
			self.actions += delta
		if key == 'R':
			self.reactions += delta
		if key == 'M':
			self.attrs["MP"] += delta
		if key == 'V':
			self.attrs["VIM"] += delta
		# TODO Health and Hero Points
		
		
	def use_resources(self, cost):
		able_to_calculate = True
		for key, val in cost.items():
			try:
				val = int(val)
			except ValueError:
				pass
			if not isinstance(val, int):
				print("entity.use_resources ignoring " + key + ": " + str(val))
				if key == 'A' or key == 'R' or key == 'M' or key == 'V': # should be able to parse
					able_to_calculate = False
				continue # ignore X, *, Attack, Passive, etc
			self.change_resource(key, -1 * val)
		return able_to_calculate
		
	def add_resources(self, resources):
		for key, val in resources.items():
			self.change_resource(key, val)
			
	async def add_resources_verbose(self, ctx, resources):
		for key, val in resources.items():
			await self.change_resource_verbose(ctx, key, val)
		
	async def use_resources_verbose(self, ctx, cost):
		able_to_calculate = True
		for key, val in cost.items():
			try:
				val = int(val)
			except ValueError:
				pass
			if not isinstance(val, int):
				print("entity.use_resources ignoring " + key + ": " + str(val))
				if key == 'A' or key == 'R' or key == 'M' or key == 'V': # should be able to parse
					able_to_calculate = False
				continue # ignore X, *, Attack, Passive, etc
			await self.change_resource_verbose(ctx, key, -1 * val)
		return able_to_calculate
		
	
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