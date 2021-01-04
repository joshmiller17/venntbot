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

TEST_SCRIPT_EASY =
		"$add_turn Bang 20", 
		"$add_enemies 2 rat",
		"$add_enemies 1 skeleton", 
		"$next_turn",
		"$gm_attack Bang skeleton heat_death     ",
		"$undo                                   ",
		"$gm_attack Bang skeleton heat_death     ",
		"$gm_attack Bang rat heat_death +0 /2    ",
		"$gm_spend Bang 1 Reaction               ",
		"$end                                    ",
		"$enemy_attack rat2 Bang				 ",
		"$end                                    ",
		"$end                                    ",
		"$gm_attack Bang skeleton ratchet        ",
		"$gm_spend Bang 2 hero                   ",
		"$gm_modify Bang 2 Action                ",
		"$gm_attack Bang rat2 ratchet            ",
		"$end                                    "
		]

TEST_SCRIPT_HARD = [
"I will spend one action to [Aim] then shoot one of the rats with my rifle       ",
"[aim]                                                                           ",
"shoot [rat A] with [rifle]                                                      ",
"I'll [move] away from the enemies                                               ",
"then attack the [skeleton] with [crippling shot]                                ",
"I end my turn                                                                   ",
"I'll use [Instant Focus]                                                        ",
"then attack [rat B] with the [rifle]                                            ",
"I end my turn                                                                   ",
"I'm going to [Aim]                                                              ",
"then shoot the [skeleton] in the head with [disabling shot]                     ",
"[TIL this song is more than the opening fanfare]                                "
]


# style: globals are in all caps
TURN_ORDER = {} # who : value + 0.01 * score + 0.001* rand float for tie breaking
INIT_INDEX = 99

QUICK_ACTION_MESSAGE = None
QUICK_REACTION_MESSAGE = None
QUICK_CTX = None
WHOSE_TURN = None
LAST_ACTION = None
ENEMY_LIST_OFFSET = 0
	

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
	global LAST_ACTION
	t = db.find(target)
	armor = t.get_stat("ARMOR")
	true_dmg = max(dmg - armor, 0)
	if true_dmg > t.get_stat("HP"):
		true_dmg = t.get_stat("HP")
	new_val = t.get_stat("HP") - true_dmg
	t.set_stat("HP", new_val)
	LAST_ACTION.add_effect(act.ActionRole.TARGET, t, {"HP":true_dmg})
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
	global QUICK_ACTION_MESSAGE, QUICK_CTX
	available_actions = {"Basic attack" : db.SWORDS, "Move" : db.RUNNING, "End turn" : db.SKIP}
	actions_left = entity.actions
	
	# Repeat
	their_last_action =  act.get_last_action(user=entity)
	if their_last_action is not None and their_last_action.type != act.ActionType.ATTACK:
		abiObj = abilityClass.get_ability(their_last_action.description)
		if entity.can_afford(abiObj.cost):
			available_actions[their_last_action.description] = db.REPEAT
	
	if entity.primary_weapon is None:
		available_actions.pop('Basic attack', None)
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
	QUICK_ACTION_MESSAGE = m
	QUICK_CTX = ctx

async def suggest_quick_reactions(ctx, entity):
	global QUICK_REACTION_MESSAGE
	if entity.reactions < 1:
		return
	m = await ctx.send("*(Quick reactions: {0} Dodge, {1} Block.)*".format(db.DASH, db.SHIELD))
	await m.add_reaction(db.DASH)
	await m.add_reaction(db.SHIELD)
	QUICK_REACTION_MESSAGE = m
	
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
		
	@commands.command(pass_context=True)
	async def test(self, ctx, help="For debug only."):
		await self.new_init(ctx)
		await self.add_enemies(ctx, "3", "rat")
		await self.next_turn(ctx)
		
	@commands.command(pass_context=True)
	async def test_script_easy(self, ctx, which, help="For debug only."):
		altered = ctx.message
		await ctx.send("Now running test fight.")
		if which == "easy":
			script = TEST_SCRIPT_EASY
		else:
			script = TEST_SCRIPT_HARD
		for line in script:
			altered.content = line
			await ctx.send("`> " + line + "`")
			await self.bot.on_message(altered)
			time.sleep(3)
		await ctx.send("Done.")
	
	async def add_turn_internal(self, ctx, display_name, who, result):
		multiturn = 2
		d_name = display_name
		while d_name in TURN_ORDER:
			d_name = d_name + " (" + str(multiturn) + ")"
			multiturn += 1

		TURN_ORDER[d_name] = int(result) + 0.01 * db.find(who).get_stat("INIT") + 0.001 * random.random()
		await ctx.message.add_reaction(db.OK)
		
	async def make_enemy_list(self, ctx, offset):
		global ENEMY_LIST_OFFSET
		global QUICK_ACTION_MESSAGE
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
		QUICK_ACTION_MESSAGE = m
		ENEMY_LIST_OFFSET += 9
	
	async def remove_bot_reactions(self, message):
		for reaction in message.reactions:
			if reaction.me:
				await reaction.remove(self.bot.user)
	
	@commands.Cog.listener()
	async def on_reaction_add(self, reaction, user):
		global ENEMY_LIST_OFFSET
		if user == self.bot.user:
			return
		if reaction.message == QUICK_ACTION_MESSAGE:
			if meta.get_character_name(user) == WHOSE_TURN or meta.get_character_name(user) == "GM":
				await self.remove_bot_reactions(reaction.message)
				if reaction.emoji == db.MORE: # assume we're doing basic attack
					await self.make_enemy_list(QUICK_CTX, ENEMY_LIST_OFFSET)
				if reaction.emoji == db.SWORDS:
					ENEMY_LIST_OFFSET = 0
					await self.make_enemy_list(QUICK_CTX, ENEMY_LIST_OFFSET)
				if db.is_number_emoji(reaction.emoji):
					ENEMY_LIST_OFFSET -= 9
					enemy_index = db.NUMBERS.index(reaction.emoji) + ENEMY_LIST_OFFSET
					target = db.ENEMIES[enemy_index]
					await self.gm_attack(QUICK_CTX, WHOSE_TURN, target.display_name(), db.find(WHOSE_TURN).primary_weapon)
					await suggest_quick_actions(QUICK_CTX, db.find(WHOSE_TURN)) 
				if reaction.emoji == db.RUNNING:
					entity = db.find(WHOSE_TURN)
					success = await entity.use_resources_verbose(QUICK_CTX, {'A':1})
					await QUICK_CTX.send(WHOSE_TURN + " moved.")
					await suggest_quick_actions(QUICK_CTX, db.find(WHOSE_TURN))
				if reaction.emoji == db.REPEAT:
					last_action = act.get_last_action(user=db.find(WHOSE_TURN))
					if last_action.type == act.ActionType.ABILITY:
						await self.gm_use(QUICK_CTX, WHOSE_TURN, last_action.description)
					elif last_action.type == act.ActionType.SPELL:
						await self.gm_cast(QUICK_CTX, WHOSE_TURN, last_action.description)
					else:
						raise ValueError("combat.on_reaction_add: only ABILITY and SPELL action types are supported")
				if reaction.emoji == db.SKIP:
					await self.next_turn(QUICK_CTX)
		if reaction.message == QUICK_REACTION_MESSAGE:
			if meta.get_character_name(user) == WHOSE_TURN or meta.get_character_name(user) == "GM":
				await self.remove_bot_reactions(reaction.message)
				if reaction.emoji == db.DASH:
					attacked = db.find(WHOSE_TURN)
					dodged_action = act.get_last_action(type=act.ActionType.ATTACK, target=attacked)
					attacked.add_resources_verbose(ctx, dodged_action.effects[act.ActionRole.TARGET])
					db.find(WHOSE_TURN).use_resources_verbose({'R':1})
				if reaction.emoji == db.SHIELD:
					attacked = db.find(WHOSE_TURN)
					blocked_action = act.get_last_action(type=act.ActionType.ATTACK, target=attacked)
					hp_lost = blocked_action.effects[act.ActionRole.TARGET]["HP"]
					attacked.add_resources_verbose(ctx, {"HP": hp_lost, "VIM" : -1 * hp_lost})
					db.find(WHOSE_TURN).use_resources_verbose({'R':1})

	@commands.command(pass_context=True, aliases=['oops'])
	async def undo(self, ctx, help = "Undo an attack or ability."):
		print("combat.undo called")
		for role, entity in LAST_ACTION.entities.items():
			await ctx.send("Undoing effects for " + entity.name)
			await entity.add_resources_verbose(ctx, LAST_ACTION.effects[role])
		
	@commands.command(pass_context=True, aliases=['next', 'end'])
	async def next_turn(self, ctx, help = "Advance the turn order."):
		global TURN_ORDER, INIT_INDEX, WHOSE_TURN
		if TURN_ORDER == {}:
			await ctx.message.add_reaction(db.NOT_OK)
			await ctx.send("Not in combat.")
			return
		sorted_turns = sorted(TURN_ORDER.items(), key=operator.itemgetter(1),reverse=True)
		print("combat.next_turn: ")
		print(sorted_turns)
		for who, val in sorted_turns:
			if val < INIT_INDEX:
				INIT_INDEX = val
				await ctx.send("Now " + who + "'s turn.")
				if who.startswith("[ENEMY]"):
					who = who[who.index('x')+2:]
					print("combat.next_turn: who is " + who)
				else: # for now, don't process enemy turns, do later
					entity = db.find(who)
					entity.new_turn()
					if isinstance(entity, playerClass.Player):
						await suggest_quick_actions(ctx, entity)
				WHOSE_TURN = who				
				return
		# reached the bottom, wrap around
		INIT_INDEX = 99
		await ctx.send("New round!")
		await self.handle_round_effects(ctx)
		await self.next_turn(ctx)
		
	@commands.command(pass_context=True)
	async def list_enemies(self, ctx):
		ret = []
		for e in db.ENEMIES:
			ret.append(e.display_name() + " - " + stats.get_status(e.display_name()))
		await ctx.send("```{0}```".format("\n".join(ret)))
		
	@commands.command(pass_context=True)
	async def add_enemies(self, ctx, num, name, help="Add X enemies to active combat."):
		num = int(num)
		new_enemies = make_enemies(num, name)
		for e in new_enemies:
			db.ENEMIES.append(e)
		who = db.ENEMIES[-1].display_name()
		await self.add_turn_internal(ctx, "[ENEMY] " + str(num) + "x " + e.name, who, stats.do_check(who, "INIT"))
		await self.turn_order(ctx)

	@commands.command(pass_context=True)
	async def clear_fight(self, ctx, help="End combat."):
		global TURN_ORDER
		db.ENEMIES = []
		TURN_ORDER = {}
		await ctx.message.add_reaction(db.OK)
		
		
	@commands.command(pass_context=True)
	async def turn_order(self, ctx, help = "Get the turn order."):
		ret = "Turn order: "
		turns = []
		sorted_turns = sorted(TURN_ORDER.items(), key=operator.itemgetter(1),reverse=True)
		for who, val in sorted_turns:
			turns.append(who)
		ret += ', '.join(turns)
		await ctx.send(ret)

	@commands.command(pass_context=True)
	async def new_init(self, ctx, go="", help = "Rolls a new initiative for everyone."):
		await ctx.message.add_reaction(db.THINKING)
		global TURN_ORDER
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
	async def enemy_attack(self, ctx, attacker, target):
		global LAST_ACTION
		await ctx.send(attacker + " attacks " + target + "!")
		total = await stats.do_roll(ctx, db.find(attacker).dmg)
		
		atkr = db.find(attacker)
		acc = atkr.get_stat("ACC")
		vim = db.find(target).get_stat("VIM")
		total = await check_hit(ctx, acc, vim, total)
		
		LAST_ACTION = act.Action(act.ActionType.ATTACK, "enemy attack")
		LAST_ACTION.add_effect(act.ActionRole.USER, atkr, {})
		
		await apply_attack(ctx, target, total)
		await suggest_quick_reactions(ctx, db.find(target))
		
	@commands.command(pass_context=True)
	async def gm_attack(self, ctx, who, target, weapon, acc_mod="+0", dmg_mod="+0", help="Roll someone's attack with a weapon. For GM use only."):
		target_entity = db.find(target)
		if target_entity is None:
			await ctx.send("No target named " + target + ", try:")
			await self.list_enemies(ctx)
			return
		
		global LAST_ACTION
		print("combat.gm_attack: " + str(who) + " " + str(target) + " " + str(weapon))
		found = False
		for w in db.weapons:
			if w["name"] == weapon:
				w_attr = w["attr"]
				w_dmg = w["dmg"]
				found = True
				break
				
		if not found:
			await ctx.send("Unrecognized weapon: " + str(weapon) + ".")
			return
			
		atkr = db.find(who)
		val = atkr.get_stat(w_attr)
		acc = val * 10 + stats.clean_modifier(acc_mod)
		vim = db.find(target).get_stat("VIM")
		
		LAST_ACTION = act.Action(act.ActionType.ATTACK, weapon)
		LAST_ACTION.add_effect(act.ActionRole.USER, atkr, {"A":2})
		atkr.actions -= 2
		
		await ctx.send(who + " attacks " + target + " with a " + weapon + "!")
		rollstr = "(" + w_dmg + "[" + weapon + "] +" + str(val) + "[" + w_attr + "])" + (dmg_mod if dmg_mod != "+0" else "")
		print("combat.gm_attack: rolling " + rollstr)
		total = await stats.do_roll(ctx, rollstr)
		total = await check_hit(ctx, acc, vim, total)
		await apply_attack(ctx, target, total)
		
		await suggest_quick_actions(QUICK_CTX, db.find(WHOSE_TURN)) 
		
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
	async def gm_set_primary_weapon(self, ctx, who, weapon, help="Set someone's primary weapon type. For GM use only."):
		entity = db.get_player_file(who)
		entity["primary_weapon"] = weapon
		db.save_characters()
		await ctx.message.add_reaction(db.OK)
		
	@commands.command(pass_context=True)
	async def set_primary_weapon(self, ctx, weapon, help="Set your primary weapon type for the weapon you use most often. If your weapon is special, see $define_weapon."):
		who = meta.get_character_name(ctx.message.author)
		await self.gm_set_primary_weapon(ctx, who, weapon)
		
	@commands.command(pass_context=True)
	async def attack(self, ctx, target, weapon, acc_mod="+0", dmg_mod="+0", help='Roll an attack with a weapon, optionally add Acc and Dmg modifiers.'):
		who = meta.get_character_name(ctx.message.author)
		await self.gm_attack(ctx, who, target, weapon, acc_mod, dmg_mod)
		
	@commands.command(pass_context=True)
	async def gm_use(self, ctx, who, *ability, help="Use someone's ability. For GM use only."): 	# TODO allow the use of items
		global LAST_ACTION
		print("combat.gm_use:")
		abiObj = abilityClass.get_ability(" ".join(ability[:]))
		user = db.find(who)
		if not user.can_afford(abiObj.cost):
			await ctx.send(who + " can't afford " + abiObj.name) # TODO add more details of why
			return
		success = await user.use_resources_verbose(ctx, abiObj.cost)
		
		LAST_ACTION = act.Action(act.ActionType.ABILITY, abiObj.name)
		LAST_ACTION.add_effect(act.ActionRole.USER, user, abiObj.cost)
		await ctx.send(who + " spent " + str(abiObj.cost)) # TEST clean up
		
		await ctx.message.add_reaction(db.OK if success else db.NOT_OK) # TODO add more details of why
		# TODO more feedback
		await suggest_quick_actions(QUICK_CTX, db.find(WHOSE_TURN)) 
	
	@commands.command(pass_context=True)
	async def use(self, ctx, *ability, help='Use an ability.'): # TODO allow the use of items
		who = meta.get_character_name(ctx.message.author)
		await self.gm_use(ctx, who, " ".join(ability[:]))
		
	@commands.command(pass_context=True)
	async def gm_cast(self, ctx, who, strength="normal", *spell, help="Cast someone's spell. For GM use only."):
		global LAST_ACTION
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
		
		LAST_ACTION = act.Action(act.ActionType.SPELL, abiObj.name)
		LAST_ACTION.add_effect(act.ActionRole.USER, user, abiObj.cost)
		await ctx.send(who + " spent " + str(abiObj.cost)) # TEST clean up
		
		await ctx.message.add_reaction(db.OK if success else db.NOT_OK) # TODO add more details of why
		# TODO more feedback
		roll_res = stats.do_check(user, "SPI")
		dl = int(abiObj.casting_dl[cast_strength])
		if roll_res >= dl:
			await ctx.send("Success! ({0} > {1})".format(roll_res, dl))
		else:
			await ctx.send("Failure! ({0} < {1})".format(roll_res, dl))
		await suggest_quick_actions(QUICK_CTX, db.find(WHOSE_TURN)) 
		
		
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
		