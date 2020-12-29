from __future__ import print_function
import os, discord
import time, pickle, requests, json
from bs4 import BeautifulSoup
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from discord.ext import commands
from dotenv import load_dotenv

# Discord setup
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = commands.Bot(command_prefix="$")

# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']

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

turn_order = []
turn_index = 0
ATTRS = ["AGI", "CHA", "DEX", "INT", "PER", "SPI", "STR", "TEK", "WIS"]
with open("characters.json") as f:
	file = json.load(f)
	characters = file["characters"]


# -------- HELPER FUNCS -----------------

def get_sheet_id(char_name):
	for character in characters:
		if character["name"] == char_name:
			return character["ID"]
	print("ERROR: no sheet found for " + char_name)

def get_from_sheets(spreadsheet_id, sheet_range):
	result = sheet.values().get(spreadsheetId=spreadsheet_id,
								range=sheet_range).execute()
	values = result.get('values', [])
	return values


# needs async for await?
def next_turn():
	turn_index += 1
	if turn_index > len(turn_order):
		turn_index = 0
	# await ... send (it's X's turn)


# --------- COMMANDS --------------------


@client.command(pass_context=True)
async def attr(ctx, who, which, help="-- Get someone's attributes. Usage: $who name attribute"):
	data = get_from_sheets(get_sheet_id(who), "Stats!B2:B10")
	attr = which.upper()
	result = data[ATTRS.index(attr)]
	await ctx.send(who + "'s " + attr + " is " + result[0])
	

@client.command(pass_context=True)
async def ping(ctx, help='-- Pong!'):
	await ctx.send("pong!")



# Warning: breaks if not given ints, don't use this format	
# @client.command(name='roll', help='-- Simulates rolling X dice of Y sides. Usage: $roll X Y')
# async def roll(ctx, number_of_dice: int, number_of_sides: int):
    # dice = [
        # str(random.choice(range(1, number_of_sides + 1)))
        # for _ in range(number_of_dice)
    # ]
    # await ctx.send(', '.join(dice))


# FIXME only works on abilities and paths that don't have spaces
@client.command(pass_context=True)
async def whatis(ctx, ability, path, help="Get an ability's info. Usage: $whatis ABILITY PATH. Example: $whatis Aim Recruit"):
	URL = "https://vennt.fandom.com/wiki/Path_of_the_" + path.replace(" ", "_")
	print(URL)
	page = requests.get(URL)
	soup = BeautifulSoup(page.content, 'html.parser')
	printing = False
	for hit in soup.find_all('p'):
		text = hit.get_text()
		if ability in text:
			printing = True
		if text.isspace() or "<br>" in text:
			printing = False
		if printing:
			await ctx.send(text)
	
	
# ---------------------------------------


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
			print("Goodbye")
			await client.close()

client.run(TOKEN)