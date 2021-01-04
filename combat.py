# --- Josh Aaron Miller 2020
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


async def apply_attack(ctx, target, dmg):
	t = db.find(target)
	armor = t.get_stat("ARMOR")
	true_dmg = max(dmg - armor, 0)
	if true_dmg > t.get_stat("HP"):
		true_dmg = t.get_stat("HP")
	new_val = t.get_stat("HP") - true_dmg
	t.set_stat("HP", new_val)
	db.LAST_ACTION.add_effect(act.ActionRole.TARGET, t, {"HP":true_dmg})
	await ctx.send(target + " takes " + str(true_dmg) + " damage!")
	await stats.do_examine(ctx, target)

async def check_hit(ctx, acc, vim, dmg):
	if acc < vim:
		await ctx.send("*A glancing blow...* ({0} < {1})".format(acc,vim))
		dmg = stats.half(dmg)
	else:
		await ctx.send("*A direct hit!* ({0} > {1})".format(acc,vim))
	return dmg
	
async def handle_round_effects(ctx):
	entities = []
	for player in db.PLAYERS:
		entities.append(player)
	for enemy in db.PLAYERS:
		entities.append(enemy)
		
	for e in entities:
		burning = e.get_modifier("burning")
		bleeding = e.get_modifier("bleeding")
		if burning is not None:
			ctx.send(e.display_name() + " burns for " + str(burning) + " damage!")
			e.change_resource_verbose(ctx, "HP", burning)
			e.add_modifier("burning", "HP", max(burning-3, 0))
			if burning - 3 <= 0:
				e.remove_modifier("burning")
				ctx.send(e.display_name() + " stops burning!")
		if bleeding is not None:
			ctx.send(e.display_name() + " bleeds for " + str(bleeding) + " damage!")

class Combat(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True, aliases=['oops'])
	async def undo(self, ctx, help = "Undo an attack or ability."):
		print("combat.undo called")
		for role, entity in LAST_ACTION.entities.items():
			await ctx.send("Undoing effects for " + entity.name)
			await entity.add_resources_verbose(ctx, LAST_ACTION.effects[role])

	@commands.command(pass_context=True)
	async def add_effect(self, ctx, who, description, stat, val, stacks="", help="Add a status or modifier. Can use 'all' for all players or 'enemies' for all enemies. Description is one word, e.g. burning or shield."):
		if who == 'all':
			ctx.message.add_reaction(db.THINKING)
			for p in db.get_player_names():
				await self.add_effect(ctx, p, description, stat, val, stacks)
		elif who == 'enemies':
			ctx.message.remove_reaction(db.THINKING, ctx.me)
			for e in db.ENEMEIS:
				await self.add_effect(ctx, e.display_name(), description, stat, val, stacks)
			ctx.message.remove_reaction(db.THINKING, ctx.me)
		else:
			entity = db.find(who)
			stacks = stacks != ""
			entity.add_modifier(description, stat, val, stacks)
			ctx.message.add_reaction(db.OK)
	
	@commands.command(pass_context=True)
	async def define_weapon(self, ctx, name, attr, dmg, *special, help="Define a new weapon. For special damage, add at the end, e.g. '1d6 burning'"):
		new_weapon = {}
		new_weapon["name"] = name
		new_weapon["attr"] = attr
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
		db.weapons.append(new_weapon)
		db.save_weapons()
		
	@commands.command(pass_context=True)
	async def set_primary_weapon(self, ctx, weapon, help="Set your primary weapon type for the weapon you use most often. If your weapon is special, see $define_weapon."):
		who = meta.get_character_name(ctx.message.author)
		await self.gm_set_primary_weapon(ctx, who, weapon)
		
	@commands.command(pass_context=True)
	async def attack(self, ctx, target, weapon, acc_mod="+0", dmg_mod="+0", help='Roll an attack with a weapon, optionally add Acc and Dmg modifiers.'):
		who = meta.get_character_name(ctx.message.author)
		await self.gm_attack(ctx, who, target, weapon, acc_mod, dmg_mod)	
	
	@commands.command(pass_context=True)
	async def use(self, ctx, *ability, help='Use an ability.'): # TODO allow the use of items
		who = meta.get_character_name(ctx.message.author)
		await self.gm_use(ctx, who, " ".join(ability[:]))
		
	@commands.command(pass_context=True, aliases=['ncast', 'normalcast', 'normal_cast'])
	async def cast(self, ctx, *spell, help='Cast a spell.'):
		who = meta.get_character_name(ctx.message.author)
		spell = " ".join(spell[:])
		await self.gm_cast(ctx, who, 1, spell)
		
	@commands.command(pass_context=True, aliases=['hcast', 'halfcast'])
	async def half_cast(self, ctx, *spell, help='Half-cast a spell.'):
		who = meta.get_character_name(ctx.message.author)
		spell = " ".join(spell[:])
		await self.gm_cast(ctx, who, 0, spell)
		
	@commands.command(pass_context=True, aliases=['dcast', 'doublecast'])
	async def double_cast(self, ctx, *spell, help='Double-cast a spell.'):
		who = meta.get_character_name(ctx.message.author)
		spell = " ".join(spell[:])
		await self.gm_cast(ctx, who, 2, spell)
		