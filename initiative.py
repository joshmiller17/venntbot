# --- Josh Aaron Miller 2021
# --- Initiative commands

import discord
from discord.ext import commands

import random, d20, operator, time, re

import importlib
db = importlib.import_module("db")
stats = importlib.import_module("stats")
enemyhandler = importlib.import_module("enemyhandler")
playerClass = importlib.import_module("player")
communication = importlib.import_module("communication")
combat = importlib.import_module("combat")



async def add_turn_internal(self, ctx, display_name, who, result):
	multiturn = 2
	d_name = display_name
	while d_name in self.turns.keys():
		d_name = d_name + " (" + str(multiturn) + ")"
		multiturn += 1

	if not db.find(who):
		await ctx.send("No entity found named " + display_name)
		await ctx.message.add_reaction(db.NOT_OK)
		return
		
	self.turns[d_name] = int(result) + 0.01 * db.find(who).get_stat("INIT") + 0.001 * random.random()
	await ctx.message.add_reaction(db.OK)
	
async def list_enemies_internal(ctx):
	ret = []
	for e in db.ENEMIES:
		ret.append(e.display_name() + " - " + stats.get_status(e.display_name()))
	if ret != []:
		await ctx.send("```{0}```".format("\n".join(ret)))
	else:
		await ctx.send("No enemies")

class Initiative(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.turns = {} # who : value + 0.01 * score + 0.001* rand float for tie breaking
		self.init_index = 99
		self.whose_turn = None
		
	@commands.command(pass_context=True)
	async def test(self, ctx, help="For debug only."):
		await self.new_init(ctx)
		await self.add_enemies(ctx, "3", "rat")
		await self.next_turn(ctx)
		
	@commands.command(pass_context=True, aliases=['next', 'end'])
	async def next_turn(self, ctx, help = "Advance the turn order."):
		if self.turns == {}:
			await ctx.message.add_reaction(db.NOT_OK)
			await ctx.send("Not in combat.")
			return
		sorted_turns = sorted(self.turns.items(), key=operator.itemgetter(1),reverse=True)
		print("combat.next_turn: ")
		print(sorted_turns)
		for who, val in sorted_turns:
			if val < self.init_index:
				self.init_index = val
				await ctx.send("Now " + who + "'s turn.")
				if who.startswith("[ENEMY]"):
					who = who[who.index('x')+2:]
					print("combat.next_turn: who is " + who)
				else: # for now, don't process enemy turns, do later
					entity = db.find(who)
					entity.new_turn()
					if isinstance(entity, playerClass.Player):
						await communication.suggest_quick_actions(ctx, who)
				self.whose_turn = who				
				return
		# reached the bottom, wrap around
		self.init_index = 99
		await ctx.send("New round!")
		await combat.handle_round_effects(ctx)
		await self.next_turn(ctx)
		
	@commands.command(pass_context=True)
	async def list_enemies(self, ctx):
		await list_enemies_internal(ctx)
		
	@commands.command(pass_context=True)
	async def end_round(self, ctx, help="Skip all remaining turns and jump to the top of the next round. For debug only."):
		self.init_index = -99
		await self.next_turn(ctx)
		
	@commands.command(pass_context=True)
	async def add_enemies(self, ctx, num, name, help="Add X enemies to active combat."):
		num = int(num)
		new_enemies = enemyhandler.make_enemies(num, name)
		for e in new_enemies:
			db.ENEMIES.append(e)
			print("initiative.add_enemy: " + e.display_name())
		who = db.ENEMIES[-1].display_name()
		await add_turn_internal(self, ctx, "[ENEMY] " + str(num) + "x " + e.name, who, stats.do_check(who, "INIT"))
		await self.turn_order(ctx)

	@commands.command(pass_context=True)
	async def clear_fight(self, ctx, help="End combat."):
		db.ENEMIES = []
		self.turns = {}
		await ctx.message.add_reaction(db.OK)	
		
	@commands.command(pass_context=True)
	async def turn_order(self, ctx, help = "Get the turn order."):
		ret = "Turn order: "
		turns = []
		sorted_turns = sorted(self.turns.items(), key=operator.itemgetter(1),reverse=True)
		for who, val in sorted_turns:
			turns.append(who)
		ret += ', '.join(turns)
		await ctx.send(ret)

	@commands.command(pass_context=True)
	async def new_init(self, ctx, go="", help = "Rolls a new initiative for everyone."):
		await ctx.message.add_reaction(db.THINKING)
		await self.clear_fight(ctx)
		for player in db.get_player_names():
			await self.add_turn(ctx, player, stats.do_check(player, "INIT"))
		await ctx.message.remove_reaction(db.THINKING, ctx.me)
		await self.turn_order(ctx)
		if go:
			await self.next_turn(ctx)

	@commands.command(pass_context=True)
	async def add_turn(self, ctx, who, result, help= "Usage: $add_turn character roll_result"):
		await add_turn_internal(self, ctx, who, who, result)