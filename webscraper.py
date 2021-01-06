# --- Josh Aaron Miller 2021
# --- Web scraping helper file via beautiful soup

import time, requests, datetime, re
from bs4 import BeautifulSoup


import importlib
db = importlib.import_module("db")

# Returns list of matches and URL string (if found)
def find_ability(*args):
	ability = " ".join(args[:])
	print("webscraper.find_ability: Looking for " + ability)
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
	for hit in soup.find_all('p'):
		text = hit.get_text()
		if ability in text: # FIXME not good at getting substrings, e.g. "Grow" vs "Growth" vs "Growth II"
			found = True
		if found and (text.isspace() or (text.startswith('\n') and last_had_newline)):
			return contents
		if found:
			contents.append(text)
			if text.endswith('\n'):
				last_had_newline = True
			else:
				last_had_newline = False
	return contents