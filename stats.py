# --- Josh Aaron Miller 2021
# --- Stat-based commands
import discord
from discord.ext import commands

import random, d20, math

import importlib
db = importlib.import_module("db")
meta = importlib.import_module("meta")
communication = importlib.import_module("communication")
logClass = importlib.import_module("logger")
logger = logClass.Logger("stats")


def d6():
	return random.randint(1,6)

def half(num):
	return int(math.floor (int(num)/2) )
	
def is_player(name):
	return name in db.get_player_names()
	
def do_check(entity, attr):
	attr_val = entity.get_stat(attr)
	logger.log("do_check", " Rolling " + attr + " check for " + entity.display_name() + " with mod " + str(attr_val))
	return d6() + d6() + d6() + attr_val
	
def clean_modifier(v):
	if isinstance(v, str):
		v = v.replace("+", "")
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
	
def get_status(entity):
	logger.log("get_status", entity.display_name())
	return compare_hp(entity.get_stat("HP"), entity.get_stat("MAX_HP"))

async def do_roll(ctx, *args):
	rollstr = "".join(args[:]) # remove spaces
	logger.log("do_roll", rollstr)
	r = d20.roll(rollstr, allow_comments=True)
	await communication.send(ctx,str(r))
	return r.total
	
async def do_examine(ctx, target_ent):
	status = get_status(target_ent)
	await communication.send(ctx,target_ent.display_name() + " is looking " + status + "!")
	

class Stats(commands.Cog):
	"""Basic rolls, checks, and using resources."""

	def __init__(self, bot):
		self.bot = bot	
		
	@commands.command(pass_context=True)
	async def half(self, ctx, num):
		"""Get half of a number."""
		await communication.send(ctx,"```{0} / 2 = **{1}**```".format(num, half(num)))
		
	@commands.command(pass_context=True)
	async def gm_check(self, ctx, who, stat):
		"""Roll a check for someone."""
		stat = stat.upper()
		attr_val = db.find(who).get_stat(stat)
		d1 = d6()
		d2 = d6()
		d3 = d6()
		res = d1+d2+d3+attr_val
		await communication.send(ctx,who + "'s " + stat.upper() + " check: **" + str(res) +
		"** ({0},{1},{2} + {3})".format(d1,d2,d3,attr_val))

	@commands.command(pass_context=True)
	async def check(self, ctx, stat):
		"""Roll a check for your character."""
		who = meta.get_character_name(ctx.message.author)
		await self.gm_check(ctx, who, stat)

	@commands.command(pass_context=True)
	async def gm_set(self, ctx, who, stat, value):
		"""Set a stat."""
		value = clean_modifier(value)
		entity = db.find(who)
		if stat.lower() == "action":
			stat = "actions"
		if stat.lower() == "reaction":
			stat = "reactions"
		if stat == "actions" or stat == "reactions":
			setattr(entity, stat, value)
		else:
			stat = stat.upper()
			entity.attrs[stat] = value
		
	@commands.command(pass_context=True)
	async def gm_modify(self, ctx, who, value, stat):
		"""Modify a stat."""
		value = clean_modifier(value)
		entity = db.find(who)
		if stat.lower() == "action":
			stat = "actions"
		if stat.lower() == "reaction":
			stat = "reactions"
		if stat == "actions" or stat == "reactions":
			setattr(entity, stat, value + getattr(entity, stat))
		else:
			stat = stat.upper()
			entity.attrs[stat] += value
		await ctx.message.add_reaction(db.OK)
	
	@commands.command(pass_context=True)
	async def set(self, ctx, stat, value):
		"""Set your stat."""
		who = meta.get_character_name(ctx.message.author)
		await self.gm_set(ctx, who, stat, value)
		
	@commands.command(pass_context=True)
	async def gm_spend(self, ctx, who, value, stat):
		"""Spend someone's stat. For GM use only."""
		value = clean_modifier(value)
		await self.gm_modify(ctx, who, -1 * value, stat)
	
	@commands.command(pass_context=True)
	async def spend(self, ctx, value, stat):
		"""Spend a stat (negative value assumed)."""
		who = meta.get_character_name(ctx.message.author)
		await self.gm_modify(ctx, who, -1 * value, stat)
		
	@commands.command(pass_context=True)
	async def modify(self, ctx, value, stat):
		"""Modify your stat (positive value assumed)."""
		who = meta.get_character_name(ctx.message.author)
		await self.gm_modify(ctx, who, value, stat)

	@commands.command(pass_context=True)
	async def attr(self, ctx, who, which):
		"""Get someone's attributes."""
		which = which.upper()
		await communication.send(ctx,who + "'s " + which + " is " + str(db.find(who).get_stat(which)))


	@commands.command(pass_context=True)
	async def roll(self, ctx, *roll):
		"""Basic dice rolling parser. For flow, roll 4d6kh3 (roll 4, keep highest 3). Comments can go in brackets."""
		await do_roll(ctx, *roll)


	@commands.command(pass_context=True)
	async def examine(self, ctx, target):
		"""Check how healthy someone is, or 'all' to check everyone."""
		if target == 'all':
			for e in entities:
				await do_examine(ctx, e)
			return
		await do_examine(ctx, db.find(target))
