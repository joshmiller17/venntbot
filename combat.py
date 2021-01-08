# --- Josh Aaron Miller 2021
# --- Combat commands

import discord
from discord.ext import commands

import random, d20, operator, time, re

import importlib
db = importlib.import_module("db")
stats = importlib.import_module("stats")
enemy = importlib.import_module("enemy")
playerClass = importlib.import_module("player")
meta = importlib.import_module("meta")
abilityClass = importlib.import_module("ability")
act = importlib.import_module("action")
logClass = importlib.import_module("logger")
logger = logClass.Logger("combat")

async def apply_attack(ctx, target_ent, dmg):
	armor = target_ent.get_stat("ARMOR")
	true_dmg = max(dmg - armor, 0)
	if true_dmg > target_ent.get_stat("HP"):
		true_dmg = target_ent.get_stat("HP")
	new_val = target_ent.get_stat("HP") - true_dmg
	target_ent.set_stat("HP", new_val)
	db.LAST_ACTION.add_effect(act.ActionRole.TARGET, target_ent, {"HP":true_dmg})
	await ctx.send(target_ent.display_name() + " takes " + str(true_dmg) + " damage!")
	await stats.do_examine(ctx, target_ent)

async def check_hit(ctx, acc, vim, dmg):
	if acc < vim:
		await ctx.send("*A glancing blow...* ({0} < {1})".format(acc,vim))
		dmg = stats.half(dmg)
	else:
		await ctx.send("*A direct hit!* ({0} > {1})".format(acc,vim))
	return dmg
	
async def handle_round_effects(ctx):
	logger.log("handle_round_effects", "called")
	await ctx.message.add_reaction(db.THINKING)

	entities = []
	for player in db.PLAYERS:
		entities.append(player)
	for enemy in db.ENEMIES:
		entities.append(enemy)
		
	for e in entities:
		burning = e.mods.get_modifier_by_stat("BURNING")
		bleeding = e.mods.get_modifier_by_stat("BLEEDING")
		if burning is not None:
			await ctx.send(e.display_name() + " burns for " + str(burning.total()) + " damage!")
			await e.change_resource_verbose(ctx, "HP", -1 * burning.total())
			e.mods.remove_modifier_by_stat("BURNING")
			e.mods.add_modifier("BURNING", "burning", max(burning.total()-3, 0), False)
			if burning.total() - 3 <= 0:
				e.mods.remove_modifier_by_stat("BURNING")
				await ctx.send(e.display_name() + " stops burning!")
		if bleeding is not None:
			await ctx.send(e.display_name() + " bleeds for " + str(bleeding.total()) + " damage!")
			await e.change_resource_verbose(ctx, "HP", -1 * bleeding.total())
		time.sleep(0.25)
		
	await ctx.message.remove_reaction(db.THINKING, ctx.me)


class Combat(commands.Cog):
	"""Commands to use in battle."""


	def __init__(self, bot):
		self.bot = bot
		self.gm = self.bot.get_cog('GM')

	@commands.command(pass_context=True, aliases=['oops'])
	async def undo(self, ctx):
		"""Undo an attack or ability."""
		logger.log("undo", "called")
		for role, entity in LAST_ACTION.entities.items():
			await ctx.send("Undoing effects for " + entity.name)
			await entity.add_resources_verbose(ctx, LAST_ACTION.effects[role])
			
	@commands.command(pass_context=True)
	async def howis(self, ctx, who):
		"""Get someone's full status. Can use 'party', 'enemies', or 'everyone'."""
		list = []
		if who == 'party' or who == 'everyone':
			list += db.get_player_names()
		if who == 'enemies' or who == 'everyone':
			list += [e.display_name() for e in db.ENEMIES]
		if list != []:
			await ctx.message.add_reaction(db.THINKING)
			for e in list:
				await self.howis(ctx, e)
			await ctx.message.remove_reaction(db.THINKING, ctx.me)
		else:
			entity = db.find(who)
			await ctx.send(entity.more())


	@commands.command(pass_context=True)
	async def add_effect(self, ctx, who, description, stat, val, stacks=""):
		"""Add a status or modifier. Can use 'party' for all players or 'enemies' for all enemies. Description is one word, e.g. burning or shield."""
		logger.log("add_effect", who)
		if who == 'party':
			await ctx.message.add_reaction(db.THINKING)
			for p in db.get_player_names():
				await self.add_effect(ctx, p, description, stat, val, stacks)
			await ctx.message.remove_reaction(db.THINKING, ctx.me)
		elif who == 'enemies':
			await ctx.message.remove_reaction(db.THINKING, ctx.me)
			for e in db.ENEMIES:
				await self.add_effect(ctx, e.display_name(), description, stat, val, stacks)
			await ctx.message.remove_reaction(db.THINKING, ctx.me)
		else:
			entity = db.find(who)
			stacks = stacks != ""
			entity.mods.add_modifier(description, stat, stats.clean_modifier(val), stacks)
			await ctx.message.add_reaction(db.OK)
			
	@commands.command(pass_context=True)
	async def modify_effect(self, ctx, who, description, stat, val):
		"""Modify an existing status. Can use 'all' for all players or 'enemies' for all enemies. Description is one word, e.g. burning or shield."""
		if who == 'party':
			await ctx.message.add_reaction(db.THINKING)
			for p in db.get_player_names():
				await self.modify_effect(ctx, p, description, stat, val)
		elif who == 'enemies':
			await ctx.message.remove_reaction(db.THINKING, ctx.me)
			for e in db.ENEMIES:
				await self.modify_effect(ctx, e.display_name(), description, stat, val)
			await ctx.message.remove_reaction(db.THINKING, ctx.me)
		else:
			entity = db.find(who)
			entity.mods.add_modifier(description, stat, stats.clean_modifier(val) + entity.mods.get_modifier_by_name(description), "true")
			await ctx.message.add_reaction(db.OK)
	
	@commands.command(pass_context=True)
	async def remove_effect(self, ctx, who, description):
		"""Remove a status or modifier. Can use 'all' for all players or 'enemies' for all enemies. Description is one word, e.g. burning or shield."""
		if who == 'party':
			await ctx.message.add_reaction(db.THINKING)
			for p in db.get_player_names():
				await self.remove_effect(ctx, p, description)
		elif who == 'enemies':
			await ctx.message.remove_reaction(db.THINKING, ctx.me)
			for e in db.ENEMIES:
				await self.remove_effect(ctx, e.display_name(), description)
			await ctx.message.remove_reaction(db.THINKING, ctx.me)
		else:
			entity = db.find(who)
			stacks = stacks != ""
			entity.mods.remove_modifier_by_name(description)
			await ctx.message.add_reaction(db.OK)
	
	@commands.command(pass_context=True)
	async def define_weapon(self, ctx, name, attr, dmg, *special):		
		"""Define a new weapon. For special damage, add at the end, e.g. '1d6 burning'"""
		new_weapon = {}
		new_weapon["name"] = name.lower()
		new_weapon["attr"] = attr.upper()
		new_weapon["dmg"] = dmg
		mods = list(special)
		if len(mods) > 0:
			if len(mods) % 2 != 0:
				await ctx.message.add_reaction(db.NOT_OK)
				await ctx.send("Bad args: Modifiers come in pairs, e.g. 1d6 burning")
				return
			new_weapon["mods"] = {}
			amt = None
			for i in range(len(mods)):
				if amt is None:
					amt = mods[i]
				else:
					new_weapon["mods"][mods[i]] = amt
					amt = None
			
		await ctx.message.add_reaction(db.OK)
		overwrite = False
		for weapon in db.weapons:
			if weapon["name"] == name:
				await ctx.send("Overwriting old weapon: " + str(weapon))
				weapon = new_weapon
				overwrite = True
				break
		if not overwrite:
			db.weapons.append(new_weapon)
		db.save_weapons()
		
	@commands.command(pass_context=True)
	async def set_primary_weapon(self, ctx, weapon):
		"""Set your primary weapon type for the weapon you use most often. If your weapon is special, see $define_weapon."""
		who = meta.get_character_name(ctx.message.author)
		await self.gm.gm_set_primary_weapon(ctx, who, weapon)
		
	@commands.command(pass_context=True)
	async def attack(self, ctx, target, weapon, acc_mod="+0", dmg_mod="+0"):
		"""Roll an attack with a weapon, optionally add Acc and Dmg modifiers."""
		who = meta.get_character_name(ctx.message.author)
		await self.gm.gm_attack(ctx, who, target, weapon, acc_mod, dmg_mod)	
	
	@commands.command(pass_context=True)
	async def use(self, ctx, *ability): # TODO allow the use of items
		"""Use an ability."""
		who = meta.get_character_name(ctx.message.author)
		await self.gm.gm_use(ctx, who, " ".join(ability[:]))
		
	@commands.command(pass_context=True, aliases=['ncast', 'normalcast', 'normal_cast'])
	async def cast(self, ctx, *spell):
		"""Cast a spell."""
		who = meta.get_character_name(ctx.message.author)
		spell = " ".join(spell[:])
		await self.gm.gm_cast(ctx, who, 1, spell)
		
	@commands.command(pass_context=True, aliases=['hcast', 'halfcast'])
	async def half_cast(self, ctx, *spell):
		"""Half-cast a spell."""
		who = meta.get_character_name(ctx.message.author)
		spell = " ".join(spell[:])
		await self.gm.gm_cast(ctx, who, 0, spell)
		
	@commands.command(pass_context=True, aliases=['dcast', 'doublecast'])
	async def double_cast(self, ctx, *spell):
		"""Double-cast a spell."""
		who = meta.get_character_name(ctx.message.author)
		spell = " ".join(spell[:])
		await self.gm.gm_cast(ctx, who, 2, spell)
		
	@commands.command(pass_context=True, aliases=['abilities'])
	async def skills(self, ctx):
		"""List your skills."""
		who = meta.get_character_name(ctx.message.author)
		await self.gm.gm_skills(ctx, who)
		