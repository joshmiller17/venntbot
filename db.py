# --- Josh Aaron Miller 2020
# --- Data needed by all Vennt Discord Bot modules

import json

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

ENEMIES = []
PLAYERS = []

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
	for e in ENEMIES:
		if e.display_name() == name:
			return e
	for p in PLAYERS:
		if p.name == name:
			return p		
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