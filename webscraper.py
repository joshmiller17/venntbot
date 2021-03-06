# --- Josh Aaron Miller 2021
# --- Web scraping helper file via beautiful soup

import time, requests, datetime, re
from bs4 import BeautifulSoup


import importlib
db = importlib.import_module("db")
logClass = importlib.import_module("logger")
logger = logClass.Logger("webscraper")


# Returns list of matches and URL string (if found)
def find_ability(*args):
	ability = " ".join(args[:])
	ability = ability.replace("'", "’") # I hate smart quotes
	logger.log("find_ability", "Looking for " + ability)
	approximations = []
	URL = ""
	for a in db.abilities:
		if ability.lower() in a["ability"].lower(): # approximate
			if a["ability"].lower() == ability.lower():
				URL = a["url"]
				return [a["ability"]], URL
			else:
				approximations.append(a["ability"])
				URL = a["url"]
	return approximations, URL

# Returns contents of ability as list of lines
def get_ability_contents(ability, URL):
	page = requests.get(URL)
	soup = BeautifulSoup(page.content, 'html.parser')
	found = False
	contents = []
	last_had_newline = False
	best_match = 999
	for hit in soup.find_all('p'):
		text = hit.get_text()
		text = text.replace("’", "'") # I hate smart quotes
		if ability in text and len(text) < best_match: # Goes through the whole page, takes the *shortest* valid line which matches the given description
			found = True
			best_match = len(text)
			contents = []
		if found and (text.isspace() or (text.startswith('\n') and last_had_newline)):
			found = False
		if found:
			contents.append(text)
			if text.endswith('\n'):
				last_had_newline = True
			else:
				last_had_newline = False
	return contents