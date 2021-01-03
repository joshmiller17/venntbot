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
meta = importlib.import_module("meta")
abilityClass = importlib.import_module("ability")
act = importlib.import_module("action")


turn_order = {} # who : value + 0.01 * score + 0.001* rand float for tie breaking
init_index = 99

quick_action_message = None
quick_reaction_message = None
quick_ctx = None
whose_turn = None
last_action = None
enemy_list_offset = 0
	

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
								
async def apply_attack(ctx, target, dmg):
	t = db.find(target)
	armor = t.get_stat("ARMOR")
	true_dmg = max(dmg - armor, 0)
	if true_dmg > t.get_stat("HP"):
		true_dmg = t.get_stat("HP")
	new_val = t.get_stat("HP") - true_dmg
	t.set_stat("HP", new_val)
	last_action.add_effect(act.ActionRole.TARGET, t, {"HP":true_dmg})
	await ctx.send(target + " takes " + str(true_dmg) + " damage!")
	await stats.do_examine(ctx, target)

async def check_hit(ctx, acc, vim, dmg):
	if acc < vim:
		await ctx.send("*A glancing blow...* ({0} < {1})".format(acc,vim))
		dmg = stats.half(dmg)
	else:
		await ctx.send("*A direct hit!* ({0} > {1})".format(acc,vim))
	return dmg
	
async def suggest_quick_actions(ctx, entity):
	global quick_action_message, quick_ctx
	available_actions = {"Repeat": db.REPEAT, "Basic attack" : db.SWORDS, "Move" : db.RUNNING, "End turn" : db.SKIP}
	actions_left = entity.actions
	if entity.primary_weapon is None:
		available_actions.pop('Basic attack', None)
	if True: # TODO
		available_actions.pop('Repeat', None)
	if actions_left < 2:
		available_actions.pop('Basic attack', None)
		if actions_left < 1:
			available_actions.pop('Move', None)
	ret = []
	for action, emoji in available_actions.items():
		ret.append("{0} {1}".format(emoji, action))
	m = await ctx.send("*(Quick actions: {0}.)*".format(", ".join(ret)))
	for action, emoji in available_actions.items():
		await m.add_reaction(emoji)
	quick_action_message = m
	quick_ctx = ctx

async def suggest_quick_reactions(ctx, entity):
	global quick_reaction_message
	if entity.reactions < 1:
		return
	m = await ctx.send("*(Quick reactions: {0} Dodge, {1} Block.)*".format(db.DASH, db.SHIELD))
	await m.add_reaction(db.DASH)
	await m.add_reaction(db.SHIELD)
	quick_reaction_message = m

class Combat(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		
	async def add_turn_internal(self, ctx, display_name, who, result):
		multiturn = 2
		d_name = display_name
		while d_name in turn_order:
			d_name = d_name + " (" + str(multiturn) + ")"
			multiturn += 1

		turn_order[d_name] = int(result) + 0.01 * db.find(who).get_stat("INIT") + 0.001 * random.random()
		await ctx.message.add_reaction(db.OK)
		
	async def make_enemy_list(self, ctx, offset):
		global enemy_list_offset
		global quick_action_message
		enemy_list = []
		for e in db.ENEMIES:
			enemy_list.append(e.display_name() + " - " + stats.get_status(e.display_name()))
		enemy_reaction_map = {}
		count = 0
		has_more = False
		for e in enemy_list:
			if offset > 0:
				offset -= 1
				continue
			if count > 8:
				enemy_reaction_map["More..."] = db.MORE
				has_more = True
				break
			enemy_reaction_map[e] = db.NUMBERS[count]
			count += 1
			
		ret = []
		for enemy, emoji in enemy_reaction_map.items():
			ret.append("{0} {1}".format(emoji, enemy))
		
		m = await ctx.send("Attack who?\n```{0}\n```".format("\n".join(ret)))
		for i in range(count):
			await m.add_reaction(db.NUMBERS[i])
		if has_more:
			await m.add_reaction(db.MORE)
		quick_action_message = m
		enemy_list_offset += 9
	
	@commands.Cog.listener()
	async def on_reaction_add(self, reaction, user):
		global enemy_list_offset
		if user == self.bot.user:
			return
		if reaction.message == quick_action_message:
			if meta.get_character_name(user) == whose_turn or meta.get_character_name(user) == "GM":
				if reaction.emoji == db.MORE: # assume we're doing basic attack
					await self.make_enemy_list(quick_ctx, enemy_list_offset)
				if reaction.emoji == db.SWORDS:
					enemy_list_offset = 0
					await self.make_enemy_list(quick_ctx, enemy_list_offset)
				if db.is_number_emoji(reaction.emoji):
					enemy_list_offset -= 9
					enemy_index = db.NUMBERS.index(reaction.emoji) + enemy_list_offset
					target = db.ENEMIES[enemy_index]
					await self.gm_attack(quick_ctx, whose_turn, target.display_name(), db.find(whose_turn).primary_weapon)
					await suggest_quick_actions(quick_ctx, db.find(whose_turn)) 
				if reaction.emoji == db.RUNNING:
					entity = db.find(whose_turn)
					success = await entity.use_resources_verbose(quick_ctx, {'A':1})
					await quick_ctx.send(whose_turn + " moved.")
					await suggest_quick_actions(quick_ctx, db.find(whose_turn))
				if reaction.emoji == db.REPEAT:
					pass #TODO
				if reaction.emoji == db.SKIP:
					await self.next_turn(quick_ctx)
					print("Next turn")
		if reaction.message == quick_reaction_message:
			if meta.get_character_name(user) == whose_turn or meta.get_character_name(user) == "GM":
				if reaction.emoji == db.DASH:
					self.undo(quick_ctx)
					db.find(whose_turn).use_resources_verbose({'R':1})
				if reaction.emoji == db.SHIELD:
					pass #TODO

	@commands.command(pass_context=True)
	async def undo(self, ctx, help = "Undo an attack or ability."):
		for role, entity in last_action.entities:
			await ctx.send("Undoing effects for " + entity.name)
			entity.add_resources_verbose(last_action.effects[role])
		
	@commands.command(pass_context=True)
	async def next_turn(self, ctx, help = "Advance the turn order."):
		global turn_order, init_index, whose_turn
		sorted_turns = sorted(turn_order.items(), key=operator.itemgetter(1),reverse=True)
		print("combat.next_turn: ")
		print(sorted_turns)
		for who, val in sorted_turns:
			if val < init_index:
				init_index = val
				await ctx.send("Now " + who + "'s turn.")
				whose_turn = who
				entity = db.find(who)
				entity.new_turn()
				if isinstance(entity, playerClass.Player):
					await suggest_quick_actions(ctx, entity)
				return
		# reached the bottom, wrap around
		init_index = 99
		await ctx.send("New round!")
		await next_turn(ctx)
		
	@commands.command(pass_context=True)
	async def add_enemies(self, ctx, num, name, help="Add X enemies to active combat."):
		num = int(num)
		new_enemies = make_enemies(num, name)
		for e in new_enemies:
			db.ENEMIES.append(e)
		who = db.ENEMIES[-1].display_name()
		await self.add_turn_internal(ctx, str(num) + "x " + e.name, who, stats.do_check(who, "INIT"))
		await self.turn_order(ctx)

	@commands.command(pass_context=True)
	async def clear_fight(self, ctx, help="End combat."):
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
	async def new_init(self, ctx, go="", help = "Rolls a new initiative for everyone."):
		await ctx.message.add_reaction(db.THINKING)
		global turn_order
		await self.clear_fight(ctx)
		for player in db.get_player_names():
			await self.add_turn(ctx, player, stats.do_check(player, "INIT"))
		await ctx.message.remove_reaction(db.THINKING, ctx.me)
		await self.turn_order(ctx)
		if go:
			await self.next_turn(ctx)

	@commands.command(pass_context=True)
	async def add_turn(self, ctx, who, result, help= "Usage: $add_turn character roll_result"):
		await self.add_turn_internal(ctx, who, who, result)


	@commands.command(pass_context=True)
	async def enemy_attack(self, ctx, attacker, target, help='Usage: $enemy_attack attacker target'):
		global last_action
		await ctx.send(attacker + " attacks " + target + "!")
		total = await stats.do_roll(ctx, db.find(attacker).dmg)
		
		atkr = db.find(attacker)
		acc = atkr.get_stat("ACC")
		vim = db.find(target).get_stat("VIM")
		total = await check_hit(ctx, acc, vim, total)
		
		last_action = act.Action("attack")
		last_action.add_effect(act.ActionRole.USER, atkr, {})
		
		await apply_attack(ctx, target, total)
		await suggest_quick_reactions(ctx, db.find(target))
		
	@commands.command(pass_context=True)
	async def gm_attack(self, ctx, who, target, weapon, acc_mod="+0", dmg_mod="+0", help="Roll someone's attack with a weapon. For GM use only."):
		global last_action
		print("combat.gm_attack: " + str(who) + " " + str(target) + " " + str(weapon))
		found = False
		for w in db.weapons:
			if w["name"] == weapon:
				w_attr = w["attr"]
				w_dmg = w["dmg"] + dmg_mod
				found = True
				break
				
		if not found:
			await ctx.send("Unrecognized weapon: " + str(weapon) + ".")
			return
			
		atkr = db.find(who)
		val = atkr.get_stat(w_attr)
		acc = val * 10 + stats.clean_modifier(acc_mod)
		vim = db.find(target).get_stat("VIM")
		
		last_action = act.Action("attack")
		last_action.add_effect(act.ActionRole.USER, atkr, {"A":2})
		atkr.actions -= 2
		
		await ctx.send(who + " attacks " + target + " with a " + weapon + "!")
		total = await stats.do_roll(ctx, w_dmg + "+" + str(val))
		total = await check_hit(ctx, acc, vim, total)
		await apply_attack(ctx, target, total)
		
	@commands.command(pass_context=True)
	async def attack(self, ctx, target, weapon, acc_mod=0, dmg_mod=0, help='Roll an attack with a weapon, optionally add Acc and Dmg modifiers.'):
		who = meta.get_character_name(ctx.message.author)
		await self.gm_attack(ctx, who, target, weapon, acc_mod, dmg_mod)
		
	@commands.command(pass_context=True)
	async def gm_use(self, ctx, who, *ability, help="Use someone's ability. For GM use only."): # TODO allow the use of items
		global last_action
		abiObj = abilityClass.get_ability(" ".join(ability[:])
		user = db.find(who)
		if not user.can_afford(abiObj.cost):
			await ctx.send(who + " can't afford " + abiObj.name) # TODO add more details of why
			return
		success = await user.use_resources_verbose(ctx, abiObj.cost)
		
		last_action = act.Action("use")
		last_action.add_effect(act.ActionRole.USER, user, abiObj.cost)
		
		await ctx.message.add_reaction(db.OK if success else db.NOT_OK) # TODO add more details of why
		# TODO more feedback
	
	@commands.command(pass_context=True)
	async def use(self, ctx, *ability, help='Use an ability.'): # TODO allow the use of items
		who = meta.get_character_name(ctx.message.author)
		await self.gm_use(ctx, who, ability[:])
		
	@commands.command(pass_context=True)
	async def gm_cast(self, ctx, who, strength="normal", *spell, help="Cast someone's spell. For GM use only."):
		global last_action
		spell = " ".join(spell[:])
		abiObj = abilityClass.get_ability(spell)
		user = db.find(who)
		if not isinstance(strength, int):
			strength = strength.lower()
			cast_strength = 1
			if strength[0] == "h":
				cast_strength = 0
			if strength[0] == "d":
				cast_strength = 2
		else:
			cast_strength = strength
		abiObj.cost["M"] = abiObj.mp_costs[cast_strength]
		if not user.can_afford(abiObj.cost):
			await ctx.send(who + " can't afford " + abiObj.name) # TODO add more details of why
			return
		success = await user.use_resources_verbose(ctx, abiObj.cost)
		
		last_action = act.Action("cast")
		last_action.add_effect(act.ActionRole.USER, user, abiObj.cost)
		
		await ctx.message.add_reaction(db.OK if success else db.NOT_OK) # TODO add more details of why
		# TODO more feedback
		roll_res = stats.do_check(user, "SPI")
		dl = int(abiObj.casting_dl[cast_strength])
		if roll_res >= dl:
			await ctx.send("Success! ({0} > {1})".format(roll_res, dl))
		else:
			await ctx.send("Failure! ({0} < {1})".format(roll_res, dl))
		
		
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
		