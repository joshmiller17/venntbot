# --- Josh Aaron Miller 2020
# --- Action class, used for modifying previous actions taken

from collections import defaultdict

from enum import Enum

import importlib
db = importlib.import_module("db")
ent = importlib.import_module("entity")

NEXT_ID = 0
ACTION_HISTORY = []

class ActionRole(Enum):
	USER = 1
	TARGET = 2

class ActionType(Enum):
	ATTACK = 1
	ABILITY = 2
	SPELL = 3
	
	
def get_last_action(type=None, user=None, target=None):
	for i in reversed(range(len(ACTION_HISTORY))):
		action = ACTION_HISTORY[i]
		if ((type is None or type == action.type)
		and (user is None or user == action.entities[ActionRole.USER])
		and (target is None or target == action.entities[ActionRole.TARGET])):
			return action
	return None

class Action:
	
	def __init__(self, type, description):
		global NEXT_ID, ACTION_HISTORY
		self.type = type
		self.description = description
		self.effects = {}
		self.entities = {}
		self.id = NEXT_ID
		NEXT_ID += 1
		ACTION_HISTORY.append(self)
		
	def add_effect(self, role, entity, cost):
		self.effects[role] = cost
		self.entities[role] = entity
		print("Action.add_effect: recorded " + entity.name + " changed " + str(cost))