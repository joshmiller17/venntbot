# --- Josh Aaron Miller 2020
# --- Entity class

from collections import defaultdict

import importlib
db = importlib.import_module("db")
sheets = importlib.import_module("sheets")
stats = importlib.import_module("stats")
mod = importlib.import_module("modifier")
logClass = importlib.import_module("logger")
logger = logClass.Logger("entity")

ACTIONS_PER_TURN = 3
REACTIONS_PER_TURN = 1


class Entity:
	def __init__(self, name):
		self.name = name
		self.mods = mod.ModifierList()
		
		self.actions = ACTIONS_PER_TURN
		self.reactions = REACTIONS_PER_TURN
		
		self.attrs = defaultdict(int)
		self.read_from_file()
		
	def display_name(self):
		return self.name
		
	def read_from_file(self):
		raise NotImplementedError
		
	def set_stat(self, stat, val):
		self.attrs[stat] = val
		
	def mod_stat(self, stat, val):
		self.attrs[stat] += val
		
	def get_stat(self, stat):
		ret = self.attrs[stat]
		mods = self.mods.get_modifier_by_stat(stat)
		if mods is not None:
			ret += mods.total()
		return ret
		
	def more(self):
		status = []
		for stat, m in self.mods.mods.items():
			if m is not None:
				status.append("   {0} {1} ({2})".format(m.total(), stat, ", ".join(m.sources)))
		if status != []:
			status = "\nEffects:\n{0}".format("\n".join(status))
		else:
			status = ""
		ret = "```\n{0}\nHP: {1}{2}```".format(self.display_name(), stats.get_status(self), status)
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
				logger.log("can_afford", " ignoring " + key + ": " + str(val))
				continue # ignore X, *, Attack, Passive, etc
			if key == 'A':
				if self.actions < val:
					logger.log("can_afford", "A " + str(self.actions) + " < " + str(val))
					return False
			if key == 'R':
				if self.reactions < val:
					logger.log("can_afford", "R " + str(self.reactions) + " < " + str(val))
					return False
			if key == 'M':
				if self.attrs["MP"] < val:
					logger.log("can_afford", "M " + str(self.attrs["MP"]) + " < " + str(val))
					return False
			if key == 'V':
				if self.attrs["VIM"] < val:
					logger.log("can_afford", "V " + str(self.attrs["VIM"]) + " < " + str(val))
					return False
			if key == 'HP':
				if self.attrs["HP"] < val:
					logger.log("can_afford", "HP " + str(self.attrs["HP"]) + " < " + str(val))
					return False
			if key == 'HERO':
				if self.attrs["HERO"] < val:
					logger.log("can_afford", "HERO " + str(self.attrs["HERO"]) + " < " + str(val))
					return False
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
		if key == 'HP':
			self.attrs["HP"] += delta
			await ctx.send(str(self.attrs["HP"]) + " HP left")
		if key == 'HERO':
			self.attrs["HERO"] += delta
			await ctx.send(str(self.attrs["HERO"]) + " Hero points left")
			
	def change_resource(self, key, delta):
		if key == 'A':
			self.actions += delta
		if key == 'R':
			self.reactions += delta
		if key == 'M':
			self.attrs["MP"] += delta
		if key == 'V':
			self.attrs["VIM"] += delta
		if key == 'HP':
			self.attrs["HP"] += delta
		if key == 'HERO':
			self.attrs["HERO"] += delta
		
		
	def use_resources(self, cost):
		able_to_calculate = True
		for key, val in cost.items():
			try:
				val = int(val)
			except ValueError:
				pass
			if not isinstance(val, int):
				logger.log("use_resources", "ignoring " + key + ": " + str(val))
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
				logger.log("use_resources_verbose", "ignoring " + key + ": " + str(val))
				if key == 'A' or key == 'R' or key == 'M' or key == 'V': # should be able to parse
					able_to_calculate = False
				continue # ignore X, *, Attack, Passive, etc
			await self.change_resource_verbose(ctx, key, -1 * val)
		return able_to_calculate