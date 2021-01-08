# --- Josh Aaron Miller 2020
# --- Enemy commands

import discord
from discord.ext import commands

import random, d20, operator, time, re

import importlib
db = importlib.import_module("db")
stats = importlib.import_module("stats")
enemy = importlib.import_module("enemy")
logClass = importlib.import_module("logger")
logger = logClass.Logger("enemyhandler")


def make_enemies(number, name):
	ret = []
	for en_file in db.enemies:
		if en_file["name"] == name:
			for i in range(1, number+1): #1-index
				enemy_ent = enemy.Enemy(en_file["name"])
				enemy_ent.id = i
				enemy_ent.read_from_file()
				ret.append(enemy_ent)
	return ret
				
def get_enemy(name):
	for ent in db.ENEMIES:
		if ent.display_name() == name:
			logger.log("get_enemy", "Found enemy: " + ent.more())
			return ent

class EnemyHandler(commands.Cog):
	"""Commands to control enemies."""

	def __init__(self, bot):
		self.bot = bot
		
	@commands.command(pass_context=True)
	async def enemy_attack(self, ctx, attacker, target):
		await ctx.send(attacker + " attacks " + target + "!")
		attacker_ent = db.find(attacker)
		target_ent = db.find(target)
		total = await stats.do_roll(ctx, attacker_ent.dmg)
		
		acc = attacker_ent.get_stat("ACC")
		vim = target_ent.get_stat("VIM")
		total = await check_hit(ctx, acc, vim, total)
		
		db.LAST_ACTION = act.Action(act.ActionType.ATTACK, "enemy attack")
		db.LAST_ACTION.add_effect(act.ActionRole.USER, attacker_ent, {})
		
		await apply_attack(ctx, target_ent, total)
		await suggest_quick_reactions(ctx, target_ent)
		