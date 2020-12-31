# --- Josh Aaron Miller 2020
# --- Combat commands

import discord
from discord.ext import commands

import random, d20, operator

import importlib
db = importlib.import_module("db")
stats = importlib.import_module("stats")
enemy = importlib.import_module("enemy")
playerClass = importlib.import_module("player")


turn_order = {} # who : value + 0.01 * score + 0.001* rand float for tie breaking
init_index = 99
	

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
				return c
				
async def apply_attack(ctx, target, dmg):
	t = db.find(target)
	armor = t.get_stat("armor")
	true_dmg = max(dmg - armor, 0)
	if true_dmg > t.get_stat("hp"):
		true_dmg = t.get_stat("hp")
	new_val = t.get_stat("hp") - true_dmg
	t.set_stat("hp", new_val)
	await ctx.send(target + " takes " + str(true_dmg) + " damage!")
	await examine(ctx, target)

async def check_hit(ctx, acc, vim, dmg):
	if acc < vim:
		await ctx.send("*A glancing blow...*")
		dmg = half(total)
	else:
		await ctx.send("*A direct hit!*")
	return dmg

class Combat(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True)
	async def next_turn(self, ctx, help = "Advance the turn order"):
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
		
	async def add_turn_internal(self, ctx, display_name, who, result):
		multiturn = 2
		d_name = display_name
		while d_name in turn_order:
			d_name = d_name + " (" + str(multiturn) + ")"
			multiturn += 1

		turn_order[d_name] = int(result) + 0.01 * db.find(who).get_stat("init") + 0.001 * random.random()
		await ctx.message.add_reaction(db.OK)
		
	@commands.command(pass_context=True)
	async def add_enemies(self, ctx, num, name, help="Add X enemies to active combat."):
		num = int(num)
		new_enemies = make_enemies(num, name)
		for e in new_enemies:
			db.ENEMIES.append(e)
		who = db.ENEMIES[-1].display_name()
		await self.add_turn_internal(ctx, str(num) + "x " + e.name, who, stats.do_check(who, "init"))
		await self.turn_order(ctx)

	@commands.command(pass_context=True)
	async def clear_fight(self, ctx, who, help="End combat."):
		db.ENEMIES = []
		turn_order = {}
		await ctx.message.add_reaction(db.OK)
		
		
	@commands.command(pass_context=True)
	async def turn_order(self, ctx, help = "Get the turn order."):
		ret = "Turn order: "
		turns = []
		sorted_turns = sorted(turn_order.items(), key=operator.itemgetter(1),reverse=True)
		for who, val in sorted_turns:
			turns.append(who)
		ret += ', '.join(turns)
		await ctx.send(ret)

	@commands.command(pass_context=True)
	async def new_init(self, ctx, help = "Rolls a new initiative for everyone."):
		global turn_order
		turn_order = {} # clear turn order
		for player in db.get_player_names():
			await self.add_turn(ctx, player, stats.do_check(player, "init"))
		await self.turn_order(ctx)

	@commands.command(pass_context=True)
	async def add_turn(self, ctx, who, result, help= "Usage: $add_turn character roll_result"):
		await self.add_turn_internal(ctx, who, who, result)


	@commands.command(pass_context=True)
	async def enemy_attack(self, ctx, attacker, target, help='Usage: $enemy_attack attacker target'):
		await ctx.send(attacker + " attacks " + target + "!")
		total = await stats.roll(ctx, db.find(attacker).dmg)
		
		acc = db.find(attacker).get_stat("acc")
		vim = db.find(target).get_stat("vim")
		
		await check_hit()
		await apply_attack(ctx, target, total)
		
	@commands.command(pass_context=True)
	async def gm_attack(self, ctx, who, target, weapon, help="Roll someone's attack with a weapon. For GM use only."):
		found = False
		for w in db.weapons:
			if w["name"] == weapon:
				w_attr = w["attr"]
				w_dmg = w["dmg"]
				found = True
				break
				
		if not found:
			ctx.send("Unrecognized weapon: " + weapon + ".")
			return
		
		val = db.find(who).get_stat(w_attr)
		acc = val * 10
		vim = db.find(target).get_stat("vim")
		
		await ctx.send(who + " attacks " + target + " with a " + weapon + "!")
		total = await stats.roll(ctx, w_dmg + "+" + str(val))
		await check_hit()
		await apply_attack(ctx, db.find(target), total)
		
	@commands.command(pass_context=True)
	async def attack(self, ctx, target, weapon, help='Roll an attack with a weapon. Usage: $attack target weapon-type'):
		who = get_char_name(ctx.message.author)
		await gm_attack(self, ctx, who, target, weapon)
	