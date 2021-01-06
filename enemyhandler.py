# --- Josh Aaron Miller 2020
# --- Enemy commands

import discord
from discord.ext import commands

import random, d20, operator, time, re

import importlib
db = importlib.import_module("db")
stats = importlib.import_module("stats")
enemy = importlib.import_module("enemy")


# style: globals are in all caps


def make_enemies(number, name):
	ret = []
	for en in db.enemies:
		if en["name"] == name:
			for i in range(1, number+1): #1-index
				e = enemy.Enemy(en["name"])
				e.id = i
				e.read_from_file()
				ret.append(e)
	return ret
				
def get_enemy(e):
	for c in ENEMIES:
		if isinstance(c, enemy.Enemy):
			if c.display_name() == e:
				print("combat.get_enemy: Found enemy: ")
				print(c.more())
				return c

class EnemyHandler(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		
	@commands.command(pass_context=True)
	async def enemy_attack(self, ctx, attacker, target):
		await ctx.send(attacker + " attacks " + target + "!")
		total = await stats.do_roll(ctx, db.find(attacker).dmg)
		
		atkr = db.find(attacker)
		acc = atkr.get_stat("ACC")
		vim = db.find(target).get_stat("VIM")
		total = await check_hit(ctx, acc, vim, total)
		
		db.LAST_ACTION = act.Action(act.ActionType.ATTACK, "enemy attack")
		db.LAST_ACTION.add_effect(act.ActionRole.USER, atkr, {})
		
		await apply_attack(ctx, target, total)
		await suggest_quick_reactions(ctx, db.find(target))
		