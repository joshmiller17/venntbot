# --- Josh Aaron Miller 2020
# --- Action class, used for modifying previous actions taken

from collections import defaultdict

from enum import Enum

import importlib
db = importlib.import_module("db")

class ActionRole(Enum):
	USER = 1
	TARGET = 2

class Action:
	
	def __init__(self, type):
		self.type = type
		self.effects = {}
		self.entities = {}
		
	def add_effect(self, role, entity, cost):
		self.effects[role] = cost
		self.entities[role] = entity
		print("Action.add_effect: recorded " + entity.name + " changed " + str(cost))