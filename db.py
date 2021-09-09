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
SCROLL = '📜'
FAST = '⚡'
MAGIC = '🪄'
POWERFUL = '💪'

ATTRS = ["AGI", "CHA", "DEX", "INT", "PER", "SPI", "STR", "TEK", "WIS"]

QUICK_ACTION_MESSAGE = None
QUICK_REACTION_MESSAGE = None
QUICK_CTX = None
LAST_ACTION = None


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