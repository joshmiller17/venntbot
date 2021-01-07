# --- Josh Aaron Miller 2020
# --- Ability class

import re

import importlib
webscraper = importlib.import_module("webscraper")
logClass = importlib.import_module("logger")
logger = logClass.Logger("ability")


# style: globals are in all caps
ABILITY_CACHE = {} # name : Ability

def get_ability(name):
	for key, value in ABILITY_CACHE.items():
		if key == name:
			return value
	# cache miss
	new_ability = make_ability(name)
	ABILITY_CACHE[name] = new_ability
	return new_ability
	
# Input: ability name
# Output: Ability object
def make_ability(name):
	approximations, URL = webscraper.find_ability(name)
	if len(approximations) != 1:
		raise ValueError("Bad call to ability.make_ability, incorrect number of approximations (" + str(len(approximations)) + "): " + ", ".join(approximations))
	contents = webscraper.get_ability_contents(name, URL)
	pur_cost = None
	act_cost = None
	eff = ""
	exp_for = None
	m_cost = None
	cast_dl = None
	unlock = None
	ability_range = None
	prereq = None
	parsed_name = False
	for line in contents:
		if line.startswith("Cost:"):
			pur_cost = parse_purchase_cost(line)
		elif line.startswith("Expedited for:"):
			exp_for = parse_expedited(line)
		elif line.startswith("Unlocks:"):
			unlock = parse_unlocks(line)
		elif line.startswith("Prereq"):
			prereq = parse_prereq(line)
		elif line.startswith("MP Cost:"):
			m_cost = parse_mp_costs(line)
		elif line.startswith("Casting DL:"):
			cast_dl = parse_casting_dl(line)
		elif line.startswith("Activation:"):
			act_cost = parse_activation_cost(line)
			parsed_activation = True
		elif line.startswith("Range:"):
			ability_range = parse_range(line)
		elif parsed_name:
			eff += line
			
		parsed_name = True
			
	ret =  Ability(name, contents, purchase_cost=pur_cost, activation_cost=act_cost, effect=eff, unlocks=unlock, prerequisites=prereq, expedited_for=exp_for, mp_costs=m_cost, casting_dl=cast_dl, range=ability_range)
	logger.log("make_ability", ret)
	return ret
	

def parse_purchase_cost(line):
	return line[6:-1] # just get string for now

def parse_expedited(line):
	return line[15:-1] # just get string for now
	
def parse_unlocks(line):
	return line[9:-1] # just get string for now
	
def parse_prereq(line):
	logger.log("parse_prereq", line[12:14])
	if line[12] == 's':
		return line[16:-1] # just get string for now
	else:
		return line[15:-1] # just get string for now

def parse_mp_costs(line):
	matches = re.findall("\[ ?(\d*) ?\/ ?(\d*) ?\/ ?(\d*) ?\]", line)
	for match_tuple in matches:
		return match_tuple[0:3]

def parse_casting_dl(line):
	matches = re.findall("\[ ?(\d*) ?\/ ?(\d*) ?\/ ?(\d*) ?\]", line)
	for match_tuple in matches:
		return match_tuple[0:3]

def parse_activation_cost(line):
	cost = {}
	matches = re.findall("Activation: ((?:Passive)|(\d Actions?)|(Attack)|(?:, )|(\d*\**X? Actions?)|(\d*\**X? Reactions?)|(\d*\**X? Vim)|(\d*\**X? MP))*", line)
	for match_tuple in matches:
		logger.log("parse_activation_cost", "tuple: " + str(match_tuple))
		for match in match_tuple:
			if match == "" or match == ", ":
				continue
			if match == "Attack":
				cost["Attack"] = True
				continue
			if match == "Passive":
				cost["Passive"] = True
				continue
			if "Activation" not in match: # skip "capture all" group
				cost_str = match.split(' ')
				type = cost_str[1][0] # first char of word
				amt = cost_str[0]
				cost[type] = amt
	return cost

def parse_range(line):
	return line[7:-1] # just get string for now


class Ability():
	def __init__(self, name, contents, purchase_cost, activation_cost, effect, unlocks=None, prerequisites=None, expedited_for = None, mp_costs = None, casting_dl = None, range = None):
		self.name = name
		self.contents = contents
		self.purchase_cost = purchase_cost
		self.unlocks = unlocks
		self.prerequisites = prerequisites
		self.cost = activation_cost
		self.expedited = expedited_for
		self.is_spell = (mp_costs != None) or (casting_dl != None)
		self.mp_costs = mp_costs
		self.casting_dl = casting_dl
		self.range = range
		self.effect = effect
	
	def is_valid(self):
		if not self.name or not self.contents or not self.cost:
			return False
		return True
		
	def is_spell(self):
		return self.mp_costs is not None or self.casting_dl is not None
	
	def __str__(self):
		ret = "[" + self.name + "]\n"
		ret += "-- Cost: " + str(self.purchase_cost) + "\n"
		ret += "-- Expedited for: " + str(self.expedited) + "\n"
		if self.is_spell:
			ret += "-- MP Cost: " + str(self.mp_costs) + "\n"
			ret += "-- Casting DL: " + str(self.casting_dl) + "\n"
		if self.range is not None:
			ret += "-- Range: " + str(self.range) + "\n"
		ret += "-- Effect: " + self.effect + "\n"
		return ret