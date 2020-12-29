from __future__ import print_function
import os, discord
import time, pickle, requests, json, operator, random
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

turn_order = {} # who : value + 0.1 * score + 0.01* rand float for tie breaking
init_index = 99
ATTRS = ["AGI", "CHA", "DEX", "INT", "PER", "SPI", "STR", "TEK", "WIS"]
with open("characters.json") as f:
	file = json.load(f)
	characters = file["characters"]
with open("abilities.json",encoding="utf8") as f:
	abilities = json.load(f)
	
players = ["Bang", "January", "CC", "Shen", "Kyle"]
	

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
	
def update_to_sheets(spreadsheet_id, sheet_range, vs):
	body = {'values' : vs}
	result = service.spreadsheets().values().update(
    spreadsheetId=spreadsheet_id, range=sheet_range,
	valueInputOption='RAW', body=body).execute()

def d6():
	return random.randint(1,6)

# parse a roll
def roll(roll_str):
	pass # TODO
	
def check_no_print(who, attr):
	attr_val = get_attr_val(who, attr)
	d1 = d6()
	d2 = d6()
	d3 = d6()
	return d1+d2+d3+attr_val

	
def get_attr_val(who, which):
	if who not in players:
		return 0
	if which.upper() in ATTRS:
		data = get_from_sheets(get_sheet_id(who), "Stats!B2:B10")
		attr = which.upper()
		attr_val = int(data[ATTRS.index(attr)][0])
	elif which.upper() == "INIT" or which.upper() == "INITIATIVE":
		data = get_from_sheets(get_sheet_id(who), "Stats!B19:B19")
		attr = which.upper()
		attr_val = int(data[0][0])
	return attr_val

# --------- COMMANDS --------------------


@client.command(pass_context=True)
async def set(ctx, who, val, stat, help="Set HP MP or Vim. Usage: $set character amount stat"):
	stat = stat.upper()
	if stat not in ["HP", "MP", "VIM"]:
		await ctx.send("Unknown stat")
		return
	cell = "Stats!"
	if stat == "HP":
		cell += "B14"
	if stat == "VIM":
		cell += "B16"
	if stat == "MP":
		cell += "B17"
	update_to_sheets(get_sheet_id(who), cell, [[int(val)]])
	

@client.command(pass_context=True)
async def next_turn(ctx, help="Advance the turn order"):
	global turn_order, init_index
	sorted_turns = sorted(turn_order.items(), key=operator.itemgetter(1),reverse=True)
	print(sorted_turns)
	for who, val in sorted_turns:
		if val < init_index:
			init_index = val
			await ctx.send("Now " + who + "'s turn.")
			return
	# reached the bottom, wrap around
	init_index = 99
	await ctx.send("New round!")
	await next_turn(ctx)

@client.command(pass_context=True)
async def check(ctx, who, which, help = "-- Roll a check. Usage: $check name attribute"):
	attr_val = get_attr_val(who, which)
	d1 = d6()
	d2 = d6()
	d3 = d6()
	res = d1+d2+d3+attr_val
	await ctx.send(who + "'s " + which.upper() + " check: **" + str(res) +
	"** ({0},{1},{2} + {3})".format(d1,d2,d3,attr_val))
	

@client.command(pass_context=True)
async def new_init(ctx, help = "-- Rolls a new initiative for everyone."):
	turn_order = {} # clear turn order
	for player in players:
		await add_turn(ctx, player, check_no_print(player, "init"))

@client.command(pass_context=True)
async def add_turn(ctx, who, init_val, help= "-- Usage: $add_turn character roll_result"):
	turn_order[who] = int(init_val) + 0.1 * get_attr_val(who, "init") + 0.01 * random.random()
	print("Turn order is now:")
	print(turn_order)


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


@client.command(pass_context=True)
async def whatis(ctx, *args, help="Get an ability's info. Usage: $whatis ABILITY. Example: $whatis Basic Cooking"):
	ability = " ".join(args[:])
	found = False
	approximations = []
	for a in abilities:
		if ability.lower() in a["ability"].lower(): # approximate
			if a["ability"].lower() == ability.lower():
				URL = a["url"]
				found = True
				break
			else:
				approximations.append(a["ability"])
				URL = a["url"]
	if len(approximations) == 1:
		found = True
	if not found:
		if approximations != []:
			await ctx.send("Did you mean: " + " or ".join(approximations))
		else:
			await ctx.send("No ability found named " + ability)
		return
	else:
		page = requests.get(URL)
		soup = BeautifulSoup(page.content, 'html.parser')
		# FIXME? sends every line as a separate message to avoid 2000 char limit, but could be smarter about this
		printing = False
		for hit in soup.find_all('p'):
			text = hit.get_text()
			if ability in text:
				printing = True
			if text.isspace() or "<br>" in text:
				printing = False
			if printing:
				await ctx.send(text)
		await ctx.send("From: <" + URL + ">")
	
	
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
			await message.author.send("Goodbye.")
			print("Goodbye")
			await client.close()

client.run(TOKEN)