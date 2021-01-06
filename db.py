# --- Josh Aaron Miller 2021
# --- Data needed by all Vennt Discord Bot modules

import json

import importlib
logClass = importlib.import_module("logger")
logger = logClass.Logger("db")

# Emojis
OK = '👍'
NOT_OK = '🚫' #'👎'
ACCEPT = '✅'
DECLINE = '❌'
SHIELD = '🛡'
DASH = '💨'
SWORDS = '⚔️'
RUNNING = '🏃'
SKIP = '⏭️'
REPEAT = '🔁'
THINKING = '🤔'
NUMBERS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
MORE = '➡️'

ATTRS = ["AGI", "CHA", "DEX", "INT", "PER", "SPI", "STR", "TEK", "WIS"]

# Entities
ENEMIES = []
PLAYERS = []

QUICK_ACTION_MESSAGE = None
QUICK_REACTION_MESSAGE = None
QUICK_CTX = None
LAST_ACTION = None

# JSON files
with open("characters.json") as f:
	characters = json.load(f)
with open("abilities.json",encoding="utf8") as f:
	abilities = json.load(f)
with open("weapons.json") as f:
	weapons = json.load(f)
with open("enemies.json") as f:
	enemies = json.load(f)
	
def is_number_emoji(emoji):
	for n in NUMBERS:
		if str(emoji) == str(n):
			return True
	return False
	
def find(name):
	if name is None:
		raise ValueError("Null passed to db.find")
		
	logger.log("find", name)
	for e in ENEMIES:
		if e.display_name() == name:
			return e
	for p in PLAYERS:
		if p.name == name:
			return p		
	logger.warn("find", "none found")
	return None
	
def get_weapon(name):
	for weapon in weapons:
		if weapon["name"] == name:
			return weapon
	return None

def get_entity_file(name):
	for entity in entities:
		if entity.name == name:
			return entity
	return None
	
def get_enemy_file(name):
	for entity in enemies:
		if entity["name"] == name:
			return entity
	return None
	
def get_player_file(name):
	for entity in characters:
		if entity["name"] == name:
			return entity
	return None
	
def get_player_names():
	return [character["name"] for character in characters if character["name"] != "GM"]
	
def save_characters():
	with open("characters.json", 'w') as f:
		json.dump(characters, f, indent=4)
		
def save_weapons():
	with open("weapons.json", 'w') as f:
		json.dump(weapons, f, indent=4)