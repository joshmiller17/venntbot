# --- Josh Aaron Miller 2020
# --- Google Sheets commands

import discord
from discord.ext import commands

import os, pickle, time
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import importlib
db = importlib.import_module("db")
stats = importlib.import_module("stats")
meta = importlib.import_module("meta")
logClass = importlib.import_module("logger")
logger = logClass.Logger("sheets")

# style: globals are in all caps


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

STATS = {
	"AGI": "B2", "CHA": "B3", "DEX": "B4",
	"INT": "B5", "PER": "B6", "SPI": "B7",
	"STR": "B8", "TEK": "B9", "WIS": "B10",
	"HP": "B14",  "MAX_HP": "C14", "MP": "B17", 
	"VIM": "B16", "ARMOR": "B21", "HERO": "B15",
}

READ_ONLY_STATS = {
	"INIT" : "B19",
	"SPEED" : "B20" 
}


# Google Sheets API Login
creds = None
if os.path.exists('token.pickle'):
	with open('token.pickle', 'rb') as token:
		creds = pickle.load(token)
if not creds or not creds.valid:
	if creds and creds.expired and creds.refresh_token:
		creds.refresh(Request())
	else:
		flow = InstalledAppFlow.from_client_secrets_file(
			'credentials.json', SCOPES)
		creds = flow.run_local_server(port=0)
	with open('token.pickle', 'wb') as token:
		pickle.dump(creds, token)
service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()


def get_sheet_id(char_name):
	for character in db.characters:
		if character["name"] == char_name:
			return character["ID"]
	logger.err("get_sheet_id", "no sheet found for " + char_name)
	return ""

def get_from_sheets(spreadsheet_id, sheet_range):
	result = sheet.values().get(spreadsheetId=spreadsheet_id,
								range=sheet_range).execute()
	values = result.get('values', [])
	return values
	
def update_to_sheets(spreadsheet_id, sheet_range, vs):
	body = {'values' : vs}
	result = service.spreadsheets().values().update(
	spreadsheetId=spreadsheet_id, range=sheet_range,
	valueInputOption='RAW', body=body).execute()
	
async def set_stat(ctx, who, amount, stat): # internal call of set command
	logger.log("set_stat", "Set stat " + who + " " + str(amount) + " " + stat)
	stat = stat.upper()
	if stat not in STATS.keys():
		await ctx.send("Unknown stat: " + stat)
		return
	cell = "Stats!" + STATS[stat]
	update_to_sheets(get_sheet_id(who), cell, amount)
	await ctx.message.add_reaction(db.OK)
	
async def do_get(ctx, who, stat):
	if stat not in STATS.keys() and stat not in READ_ONLY_STATS.keys():
		await ctx.send("Unknown stat: " + stat)
		return
	if stat in STATS.keys():
		cell = "Stats!" + STATS[stat]
	else:
		cell = "Stats!" + READ_ONLY_STATS[stat]
	return int(get_from_sheets(get_sheet_id(who), cell)[0][0])
	
async def do_get_abilities(ctx, who):
	skills = get_from_sheets(get_sheet_id(who), "Skills!A7:A1000")
	skills = [s[0] for s in skills if len(s) > 0] # de-listify
	return skills


class Sheets(commands.Cog):
	"""Commands to modify character sheets."""

	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True)
	async def set_sheet(self, ctx, who, amount, stat):
		"""Set a stat on a character sheet. Players can only use 'me' or their name."""
		char_name = meta.get_character_name(ctx.message.author)
		if char_name != "GM" and who != "me" and who != char_name:
			await ctx.message.add_reaction(db.NOT_OK)
			return
		stat = int(stat)
		await set_stat(ctx, who, amount, stat)
		
	@commands.command(pass_context=True)
	async def modify_sheet(self, ctx, who, amount, stat):
		"""Modify a stat on a character sheet."""
		char_name = meta.get_character_name(ctx.message.author)
		if char_name != "GM" and who != "me" and who != char_name:
			ctx.message.add_reaction(db.NOT_OK)
			return
		amount = stats.clean_modifier(amount)
		amount = amount + await get(self, ctx, who, stat)
		await set_stat(ctx, who, amount, stat)

	@commands.command(pass_context=True)
	async def read_sheet(self, ctx, who, stat):
		"""See a stat on a character sheet."""
		ctx.send( await do_get(ctx, who, stat) )

	# Save characters.json -> Google Sheet
	@commands.command(pass_context=True)
	async def save(self, ctx, player):
		"""Save changes to character sheet, or 'all' for everyone."""
		if player == 'all':
			for p in db.get_player_names():
				await self.save(ctx, p)
		else:
			e = db.find(player)
			for stat in STATS.keys():
				await set_stat(ctx, player, getattr(e, stat), stat)
			# TODO save primary weapon info somewhere?
			# TODO save newly acquired skills
	
	# Load Google Sheet -> db -> characters.json
	@commands.command(pass_context=True)
	async def load(self, ctx, who):
		"""Load a character sheet, or 'all' for everyone (takes several minutes)."""
		await ctx.message.add_reaction(db.THINKING)
		if who == 'all':
			for p in db.get_player_names():
				logger.log("load", "Loading " + p)
				await self.load(ctx, p)
				time.sleep(60) # need to be extra nice to the server, this makes a lot of calls
		else:
			e = db.find(who)
			for stat in STATS.keys():
				e.attrs[stat] = await do_get(ctx, who, stat)
				time.sleep(1)
			for stat in READ_ONLY_STATS.keys():
				e.attrs[stat] = await do_get(ctx, who, stat)
				time.sleep(1)
			e.skills = await do_get_abilities(ctx, who)
			e.write() # write db -> characters.json
		await ctx.message.add_reaction(db.OK)
		await ctx.message.remove_reaction(db.THINKING, ctx.me)
	