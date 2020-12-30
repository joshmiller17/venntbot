from __future__ import print_function
import discord, os, time, pickle, requests, json
import re, operator, random, d20
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


# -Vennt

OK = '👍'
NOT_OK = '👎'

ATTRS = ["AGI", "CHA", "DEX", "INT", "PER", "SPI", "STR", "TEK", "WIS"]
players = ["Bang", "January", "CC", "Shen", "Kyle", "Quinn"]

with open("characters.json") as f:
	file = json.load(f)
	characters = file["characters"]
with open("abilities.json",encoding="utf8") as f:
	abilities = json.load(f)
with open("weapons.json") as f:
	weapons = json.load(f)
with open("enemies.json") as f:
	enemies = json.load(f)		


turn_order = {} # who : value + 0.1 * score + 0.01* rand float for tie breaking
init_index = 99

combatants = [] # set of all active entities; players are just names, enemies are Enemy type

class Enemy:
	def __init__(self, name, hp, vim, armor, dmg):
		self.name = name
		self.hp = hp
		self.max_hp = hp
		self.vim = vim
		self.armor = armor
		self.dmg = dmg
	

# ------HELPER FUNCS -----------------

def make_enemies(number, name):
	ret = []
	for enemy in enemies:
		if enemy["name"] == name:
			if number == 1:
				return [Enemy(enemy["name"], enemy["hp"], enemy["vim"], enemy["armor"], enemy["dmg"])]
			else:
				for i in range(1, number+1): #1-index
					ret.append(Enemy(enemy["name"] + str(i), enemy["hp"], enemy["vim"], enemy["armor"], enemy["dmg"]))
				return ret
				
def get_enemy(e):
	for c in combatants:
		if not isinstance(c, str):
			if c.name == e:
				return c

def is_player(entity):
	return entity in players

def get_char_name(sender):
	for character in characters:
		if character["played_by"] == sender:
			return character["name"]
	print("ERROR: no name found for " + str(sender))
	return ""

def get_sheet_id(char_name):
	for character in characters:
		if character["name"] == char_name:
			return character["ID"]
	print("ERROR: no sheet found for " + char_name)
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

def d6():
	return random.randint(1,6)
	
def check_no_print(who, attr):
	attr_val = get_attr_val(who, attr)
	d1 = d6()
	d2 = d6()
	d3 = d6()
	return d1+d2+d3+attr_val
	
def compare_hp(current, max):
	percent = (1.0 * current) / (1.0 * max)
	if percent > 0.9:
		return "healthy."
	if percent >  0.7:
		return "scratched."
	if percent > 0.5:
		return "hurt."
	if percent > 0.3:
		return "bloodied!"
	if percent > 0.1:
		return "severely wounded!"
	if percent > 0:
		return "near death!"
	return "dead!"
	
	
async def apply_attack(ctx, target, dmg):
	if is_player(target):
		armor = get_attr_val(target, "armor")
		true_dmg = max(dmg - armor, 0)
		new_val = get_attr_val(target, "HP") - true_dmg
		await gm_set(ctx, target, new_val, "HP")
		await ctx.send(target + " takes " + str(true_dmg) + " damage!")
		await examine(ctx, target)
	else:
		# assume target is the Enemy type
		true_dmg = max(dmg - target.armor, 0)
		target.hp -= true_dmg
		await ctx.send(target.name + " takes " + str(true_dmg) + " damage!")
		await examine(ctx, target.name)

	
def get_attr_val(who, which):
	if who not in players:
		return 0
	if which.upper() in ATTRS:
		data = get_from_sheets(get_sheet_id(who), "Stats!B2:B10")
		attr = which.upper()
		attr_val = int(data[ATTRS.index(attr)][0])
	else:
		cell = "Stats!"
		if which.upper() == "INIT" or which.upper() == "INITIATIVE":
			cell += "B19"
		elif which.upper() == "HP":
			cell += "B14"
		elif which.upper() == "MAX_HP":
			cell += "C14"
		elif which.upper() == "VIM":
			cell += "B16"
		elif which.upper() == "MP":
			cell += "B17"
		elif which.upper() == "ARMOR":
			cell += "B21"
		data = get_from_sheets(get_sheet_id(who), cell)
		attr_val = int(data[0][0])
	return attr_val

# -------COMMANDS --------------------

@client.command(pass_context=True)
async def examine(ctx, target, help = "Check how healthy a combatant is, or 'all' to check all players."):
	if target == 'all':
		for player in players:
			await examine(player)
		return
	if is_player(target):
		status = compare_hp(get_attr_val(target, "HP"), get_attr_val(target, "MAX_HP"))
	else:
		e = get_enemy(target)
		status = compare_hp(e.hp, e.max_hp)
	await ctx.send(target + " is looking " + status)

@client.command(pass_context=True)
async def roll(ctx, *args, help = "Basic dice rolling parser. For flow, use 4d6kh3. Comments can go in brackets."):
	rollstr = "".join(args[:]) # remove spaces
	r = d20.roll(rollstr)
	await ctx.send(str(r))
	return r.total

@client.command(pass_context=True)
async def next_turn(ctx, help = "Advance the turn order"):
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
async def gm_set(ctx, who, val, stat, help="Set HP MP or Vim. Usage: $set character amount stat"):
	if isinstance(val, str):
		val = val.replace("+", "")
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
	await ctx.message.add_reaction(OK)

@client.command(pass_context=True)
async def set(ctx, who, val, stat, help="Set HP MP or Vim. Usage: $set amount stat"):
	char_name = get_char_name(ctx.message.author)
	if char_name != "GM" and who != "me" and who != char_name:
		ctx.message.add_reaction(NOT_OK)
		return
	await gm_set(ctx, char_name, val, stat)
	
	
@client.command(pass_context=True)
async def add_combatant(ctx, who, help="Add player (or 'all') to active combat."):
	if who == 'all':
		for player in players:
			combatants.append(player)
	else:
		combatants.append(who)
	await ctx.message.add_reaction(OK)
	
@client.command(pass_context=True)
async def add_enemies(ctx, num, name, help="Add X enemies to active combat. Usage: $add_enemies number name"):
	num = int(num)
	new_enemies = make_enemies(num, name)
	for e in new_enemies:
		combatants.append(e)
	await ctx.message.add_reaction(OK)
	

@client.command(pass_context=True)
async def clear_combatants(ctx, who, help="End combat."):
	combatants = []
	await ctx.message.add_reaction(OK)
	
@client.command(pass_context=True)
async def modify(ctx, who, val, stat, help="Modify HP MP or Vim. Usage: $modify character amount stat. Can use 'me' as character."):
	char_name = get_char_name(ctx.message.author)
	if char_name != "GM" and who != "me" and who != char_name:
		ctx.message.add_reaction(NOT_OK)
		return
	val = int(val.replace("+", ""))
	val = val + get_attr_val(who, stat)
	await gm_set(ctx, who, val, stat)
	await ctx.message.add_reaction(OK)


@client.command(pass_context=True)
async def check(ctx, which, help = "Roll a check for your character. Usage: $check attribute"):
	who = get_char_name(ctx.message.author)
	attr_val = get_attr_val(who, which)
	d1 = d6()
	d2 = d6()
	d3 = d6()
	res = d1+d2+d3+attr_val
	await ctx.send(who + "'s " + which.upper() + " check: **" + str(res) +
	"** ({0},{1},{2} + {3})".format(d1,d2,d3,attr_val))
	
@client.command(pass_context=True)
async def turn_order(ctx, help = "Get the turn order."):
	ret = "Turn order: "
	turns = []
	sorted_turns = sorted(turn_order.items(), key=operator.itemgetter(1),reverse=True)
	for who, val in sorted_turns:
		turns.append(who)
	ret += ', '.join(turns)
	await ctx.send(ret)

@client.command(pass_context=True)
async def new_init(ctx, help = "Rolls a new initiative for everyone."):
	turn_order = {} # clear turn order
	for player in players:
		await add_turn(ctx, player, check_no_print(player, "init"))
	await ctx.message.add_reaction(OK)

@client.command(pass_context=True)
async def add_turn(ctx, who, init_val, help= "Usage: $add_turn character roll_result"):
	turn_order[who] = int(init_val) + 0.1 * get_attr_val(who, "init") + 0.01 * random.random()
	await ctx.message.add_reaction(OK)


@client.command(pass_context=True)
async def attr(ctx, who, which, help="Get someone's attributes. Usage: $who name attribute"):
	data = get_from_sheets(get_sheet_id(who), "Stats!B2:B10")
	attr = which.upper()
	result = data[ATTRS.index(attr)]
	await ctx.send(who + "'s " + attr + " is " + result[0])
	
@client.command(pass_context=True)
async def enemy_attack(ctx, attacker, target, help='Usage: $enemy_attack attacker target'):
	await ctx.send(attacker + " attacks " + target + "!")
	total = await roll(ctx, get_enemy(attacker).dmg)
	await apply_attack(ctx, target, total)
	
@client.command(pass_context=True)
async def gm_attack(ctx, who, target, weapon, help='Roll an attack with a weapon. Usage: $attack who target weapon-type'):
	found = False
	for w in weapons:
		if w["name"] == weapon:
			w_attr = w["attr"]
			w_dmg = w["dmg"]
			found = True
			break
	
	if not found:
		ctx.send("Unrecognized weapon: " + weapon + ".")
	else:
		val = get_attr_val(who, w_attr)
		await ctx.send(who + " attacks " + target + " with a " + weapon + "!")
		total = await roll(ctx, w_dmg + "+" + str(val))
		await apply_attack(ctx, get_enemy(target), total)
	
@client.command(pass_context=True)
async def attack(ctx, target, weapon, help='Roll an attack with a weapon. Usage: $attack target weapon-type'):
	who = get_char_name(ctx.message.author)
	found = False
	for w in weapons:
		if w["name"] == weapon:
			w_attr = w["attr"]
			w_dmg = w["dmg"]
			found = True
			break
	
	if not found:
		ctx.send("Unrecognized weapon: " + weapon + ".")
	else:
		val = get_attr_val(who, w_attr)
		await ctx.send(who + " attacks " + target + " with a " + weapon + "!")
		total = await roll(ctx, w_dmg + "+" + str(val))
		await apply_attack(ctx, target, total)
	

@client.command(pass_context=True)
async def ping(ctx, help='Pong!'):
	await ctx.send("pong!")


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

client.run(TOKEN)