# --- Josh Aaron Miller 2020
# --- main run for Discord Vennt Bot
from __future__ import print_function
import discord, os, time, pickle, requests, json
import re, operator, random, d20, datetime
import importlib
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from discord.ext import commands
from dotenv import load_dotenv

# Other files
meta = importlib.import_module("meta")
combat = importlib.import_module("combat")
sheets = importlib.import_module("sheets")
stats = importlib.import_module("stats")
playerClass = importlib.import_module("player")
enemyClass = importlib.import_module("enemy")

# Discord setup
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = commands.Bot(command_prefix="$")

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

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


# --- Vennt

OK = '👍'
NOT_OK = '👎'
SHIELD = '🛡'
DASH = '💨'
SWORDS = '⚔️'
RUNNING = '🏃'
SKIP = '⏭️'
REPEAT = '🔁'

with open("characters.json") as f:
	file = json.load(f)
	characters = file["characters"]
with open("abilities.json",encoding="utf8") as f:
	abilities = json.load(f)
with open("weapons.json") as f:
	weapons = json.load(f)
with open("enemies.json") as f:
	enemies = json.load(f)		



# Setup and Run
@client.event
async def on_ready():
	print(f'{client.user} has connected to Discord!')
	return
	
@client.event
async def on_message(message):
	await client.process_commands(message)
	if message.author == client.user:
		return # don't respond to ourselves
	if isinstance(message.channel, discord.channel.DMChannel):
		if (message.content == "quit"):
			await message.author.send("Goodbye.")
			print("Goodbye")
			await client.close()
			
client.add_cog(meta.Meta(client))
client.add_cog(sheets.Sheets(client))
client.add_cog(stats.Stats(client))
client.add_cog(combat.Combat(client))

client.run(TOKEN)