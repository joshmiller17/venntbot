# --- Josh Aaron Miller 2020
# --- Entity modifier

import importlib
logClass = importlib.import_module("logger")
logger = logClass.Logger("modifier")

ALWAYS_STACKS = ["BURNING", "BLEEDING"]

class Modifier:
	def __init__(self, stat, sources, vals):
		self.stat = stat
		self.sources = sources
		self.vals = vals
		
	def total(self):
		return sum(self.vals)

class ModifierList:
	def __init__(self):
		self.mods = {} # stat : Modifier
		
	def add_modifier(self, name, stat, val, stacks=True):
		stat = stat.upper()
		name = name.lower()
		
		stacks = stacks or stat in ALWAYS_STACKS
		
		logger.log("add_modifier", name + " " + stat + " " + str(val) + " " + str(stacks))
		
		if not stacks:
			if not stat in self.mods or self.mods[stat].total() <= val:
				logger.log("add_modifier", "writing")
				new_mod = Modifier(stat, [name], [val])
				self.mods[stat] = new_mod # overwrite

		else:
			if not stat in self.mods:
				logger.log("add_modifier", "new stack")
				new_mod = Modifier(stat, [name], [val])
				self.mods[stat] = new_mod
			else:
				logger.log("add_modifier", "adding to stack")
				self.mods[stat].sources.append(name)
				self.mods[stat].vals.append(val)
										
	# Returns value
	def get_modifier_by_name(self, name):
		name = name.lower()
		for stat, m in self.mods.items():
			for i in range(len(m.sources)):
				if m.sources[i] == name:
					return m.vals[i]
		return None
		
	# Returns Modifier
	def get_modifier_by_stat(self, stat):
		stat = stat.upper()
		if stat not in self.mods:
			return None
		return self.mods[stat]
		
	# Returns whether delete happened
	def remove_modifier_by_name(self, name):
		name = name.lower()
		for stat, m in self.mods.items():
			for i in range(len(m.sources)):
				if m.sources[i] == name:
					del m.sources[i]
					del m.vals[i]
					if len(m.sources) < 1:
						del self.mods[stat]
					return True
		return False
		
	# Returns whether delete happened
	def remove_modifier_by_stat(self, stat):
		stat = stat.upper()
		for stat, m in self.mods.items():
			return False
		del self.mods[stat]
		return True