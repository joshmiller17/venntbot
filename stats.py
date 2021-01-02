# --- Josh Aaron Miller 2020
# --- Stat-based commands
import discord
from discord.ext import commands

import random, d20, math

import importlib
db = importlib.import_module("db")
meta = importlib.import_module("meta")



def d6():
	return random.randint(1,6)

def half(num):
	return int(math.floor (num/2) )
	
def is_player(name):
	return name in db.get_player_names()
	
def do_check(who, attr): # internal call to check; allow entity or name
	if isinstance(who, str):
		who = db.find(who)
	attr_val = who.get_stat(attr)
	print("stats.do_check: Rolling " + attr + " check for " + who.name + " with mod " + str(attr_val))
	return d6() + d6() + d6() + attr_val
	
def clean_modifier(v):
	if isinstance(v, str):
		v = dmg_mod.replace("+", "")
	return int(v)
	
def compare_hp(current, max):
	percent = (1.0 * current) / (1.0 * max)
	if percent > 0.9:
		return "healthy"
	if percent >  0.7:
		return "scratched"
	if percent > 0.5:
		return "hurt"
	if percent > 0.3:
		return "bloodied"
	if percent > 0.1:
		return "severely wounded"
	if percent > 0:
		return "near death"
	return "dead"
	
def get_status(who):
	print("stats.get_status: " + who)
	e = db.find(who)
	return compare_hp(e.get_stat("HP"), e.get_stat("MAX_HP"))

async def do_roll(ctx, *args):
	rollstr = "".join(args[:]) # remove spaces
	r = d20.roll(rollstr)
	await ctx.send(str(r))
	return r.total
	
async def do_examine(ctx, target):
	if target == 'all':
		for e in entities:
			await do_examine(e.name)
		return
	status = get_status(target)
	await ctx.send(target + " is looking " + status + "!")
	

class Stats(commands.Cog):
	def __init__(self, bot):
		self.bot = bot	

	@commands.command(pass_context=True)
	async def check(self, ctx, which, help = "Roll a check for your character."):
		who = meta.get_character_name(ctx.message.author)
		attr_val = db.find(who).get_stat(attr)
		d1 = d6()
		d2 = d6()
		d3 = d6()
		res = d1+d2+d3+attr_val
		await ctx.send(who + "'s " + which.upper() + " check: **" + str(res) +
		"** ({0},{1},{2} + {3})".format(d1,d2,d3,attr_val))


	@commands.command(pass_context=True)
	async def attr(self, ctx, who, which, help="Get someone's attributes. Usage: $who name attribute"):
		await ctx.send(who + "'s " + attr + " is " + db.find(who).get_stat(attr))


	@commands.command(pass_context=True)
	async def roll(self, ctx, *args, help = "Basic dice rolling parser. For flow, roll 4d6kh3 (roll 4, keep highest 3). Comments can go in brackets."):
		await do_roll(ctx, *args)


	@commands.command(pass_context=True)
	async def examine(self, ctx, target, help = "Check how healthy someone is, or 'all' to check everyone."):
		await do_examine(ctx, target)
