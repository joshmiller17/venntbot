# --- Josh Aaron Miller 2020
# --- Stat-based commands
import discord
from discord.ext import commands


ATTRS = ["AGI", "CHA", "DEX", "INT", "PER", "SPI", "STR", "TEK", "WIS"]


def d6():
	return random.randint(1,6)

def half(num):
	return int(math.floor (num/2) )

	
def check_no_print(who, attr):
	attr_val = get_attr_val(who, attr)
	d1 = d6()
	d2 = d6()
	d3 = d6()
	return d1+d2+d3+attr_val

	
def is_player(name):
	return name in players

def get_char_name(sender):
	for character in characters:
		if character["played_by"] == sender:
			return character["name"]
	print("ERROR: no name found for " + str(sender))
	return ""

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

class Stats(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

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
async def attr(ctx, who, which, help="Get someone's attributes. Usage: $who name attribute"):
	data = get_from_sheets(get_sheet_id(who), "Stats!B2:B10")
	attr = which.upper()
	result = data[ATTRS.index(attr)]
	await ctx.send(who + "'s " + attr + " is " + result[0])
	


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
	


@client.command(pass_context=True)
async def roll(ctx, *args, help = "Basic dice rolling parser. For flow, use 4d6kh3. Comments can go in brackets."):
	rollstr = "".join(args[:]) # remove spaces
	r = d20.roll(rollstr)
	await ctx.send(str(r))
	return r.total



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
