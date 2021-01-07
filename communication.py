# --- Josh Aaron Miller 2021
# --- Interaction helper with the Discord bot

import discord
from discord.ext import commands

import random, d20, operator, time, re
from enum import Enum


import importlib
db = importlib.import_module("db")
stats = importlib.import_module("stats")
init = importlib.import_module("initiative")
abilityClass = importlib.import_module("ability")
act = importlib.import_module("action")
meta = importlib.import_module("meta")
logClass = importlib.import_module("logger")
logger = logClass.Logger("communication")


class CommState(Enum):
	ATTACK = 1
	ABILITIES = 2
	
	
COMM_STATE = None

async def suggest_quick_actions(ctx, entity):
	if entity is None:
		return # No one's turn
		
	available_actions = {"Basic attack" : db.SWORDS, "Move" : db.RUNNING, "End turn" : db.SKIP, "More" : db.MORE}
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
	db.QUICK_ACTION_MESSAGE = m
	db.QUICK_CTX = ctx

async def suggest_quick_reactions(ctx, entity):
	if entity is None:
		return # No one's turn
	
	if entity.reactions < 1:
		return
	m = await ctx.send("*(Quick reactions: {0} Dodge, {1} Block.)*".format(db.DASH, db.SHIELD))
	await m.add_reaction(db.DASH)
	await m.add_reaction(db.SHIELD)
	db.QUICK_REACTION_MESSAGE = m
	
async def make_choice_list(self, ctx, choices, offset):
	choice_map = {}
	count = 0
	has_more = False
	for c in choices:
		if offset > 0:
			offset -= 1
			continue
		if count > 8:
			choice_map["More..."] = db.MORE
			has_more = True
			break
		choice_map[e] = db.NUMBERS[count]
		count += 1
		
	ret = []
	for c, emoji in choice_map.items():
		ret.append("{0} {1}".format(emoji, c))
	
	m = await ctx.send("```{0}\n```".format("\n".join(ret)))
	for i in range(count):
		await m.add_reaction(db.NUMBERS[i])
	if has_more:
		await m.add_reaction(db.MORE)
	db.QUICK_ACTION_MESSAGE = m
	
async def make_ability_list(self, ctx, offset):
	ability_list = []
	entity = db.find(self.initCog.whose_turn)
	for a in entity.skills:
		# TODO check if that ability is affordable, if so, list its cost
		# TODO throw a warning if can't find / understand ability
		ability_list.append(a)
	await make_choice_list(self, ctx, ability_list, offset)
	await ctx.send("Use which ability?")
	COMM_STATE = CommState.ABILITIES
	self.ability_list_offset += 9
	
async def make_enemy_list(self, ctx, offset):
	enemy_list = []
	for e in db.ENEMIES:
		enemy_list.append(e.display_name() + " - " + stats.get_status(e))
	await make_choice_list(self, ctx, enemy_list, offset)
	await ctx.send("Attack who?")
	COMM_STATE = CommState.ATTACK
	self.enemy_list_offset += 9
	
async def ask_cast_strength(self, ctx):
	m = await ctx.send("Cast at what strength? {0} Half, {1} Normal, {2} Double".format(db.FAST, db.MAGIC, db.POWERFUL))
	await m.add_reaction(db.FAST)
	await m.add_reaction(db.MAGIC)
	await m.add_reaction(db.POWERFUL)
	db.QUICK_ACTION_MESSAGE = m

class Communication(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.enemy_list_offset = 0
		self.ability_list_offset = 0
		self.chosen_ability = None # stored for convenience
		self.initCog = self.bot.get_cog('Initiative')
		self.gm = self.bot.get_cog('GM')
	
	async def remove_bot_reactions(self, message):
		for reaction in message.reactions:
			if reaction.me:
				await reaction.remove(self.bot.user)
				await self.remove_bot_reactions(message) # refresh list and try again
				
	@commands.command(pass_context=True)
	async def quick(self, ctx, help="Show available quick actions."):
		await self.suggest_quick_actions(ctx, db.find(self.initCog.whose_turn))
	
	@commands.Cog.listener()
	async def on_reaction_add(self, reaction, user):
		if user == self.bot.user:
			return
		if reaction.message == db.QUICK_ACTION_MESSAGE:
		
			if self.initCog.whose_turn is None:
				db.QUICK_CTX.send("Cannot process reactions, I don't know whose turn it is.")
				return
				
			if meta.get_character_name(user) == self.initCog.whose_turn or meta.get_character_name(user) == "GM":
				await self.remove_bot_reactions(reaction.message)
				who = self.initCog.whose_turn
				who_ent = db.find(who)
				
				if reaction.emoji == db.MORE:
					if COMM_STATE == CommState.ATTACK:
						await make_enemy_list(self, db.QUICK_CTX, self.enemy_list_offset)
					elif COMM_STATE == CommState.ABILITIES:
						await make_ability_list(self, db.QUICK_CTX, self.ability_list_offset)
					else:
						self.ability_list_offset = 0
						self.chosen_ability = None
						await make_ability_list(self, db.QUICK_CTX, self.ability_list_offset)
						
				if reaction.emoji == db.SWORDS:
					self.enemy_list_offset = 0
					await make_enemy_list(self, db.QUICK_CTX, self.enemy_list_offset)
					
				if db.is_number_emoji(reaction.emoji):
					if COMM_STATE == CommState.ATTACK:
						self.enemy_list_offset -= 9
						enemy_index = db.NUMBERS.index(reaction.emoji) + self.enemy_list_offset
						target_ent = db.ENEMIES[enemy_index]
						await self.gm.gm_attack(db.QUICK_CTX, who, target_ent.display_name(), who_ent.primary_weapon)
						await suggest_quick_actions(db.QUICK_CTX, who_ent) 
					
					elif COMM_STATE == CommState.ABILITIES:
						self.ability_list_offset -= 9
						ability_index = db.NUMBERS.index(reaction.emoji) + self.ability_list_offset
						choice = who_ent.skills[ability_index]
						abiObj = abilityClass.get_ability(choice)
						if abiObj.is_spell():
							await ask_cast_strength(db.QUICK_CTX)
						else:
							await self.gm.gm_use(db.QUICK_CTX, who, choice)
						await suggest_quick_actions(db.QUICK_CTX, who_ent) 
					else:
						raise ValueError("communication.on_reaction_add: CommState was None")
						
				if reaction.emoji == db.FAST:
					await self.gm.gm_cast(db.QUICK_CTX, who, 0, self.chosen_ability)
					
				if reaction.emoji == db.MAGIC:
					await self.gm.gm_cast(db.QUICK_CTX, who, 1, self.chosen_ability)
					
				if reaction.emoji == db.POWERFUL:
					await self.gm.gm_cast(db.QUICK_CTX, who, 2, self.chosen_ability)
					
				if reaction.emoji == db.RUNNING:
					success = await who_ent.use_resources_verbose(db.QUICK_CTX, {'A':1})
					await db.QUICK_CTX.send(who_ent.display_name() + " moved.")
					await suggest_quick_actions(db.QUICK_CTX, who_ent)
					
				if reaction.emoji == db.REPEAT:
					last_action = act.get_last_action(user=who_ent)
					
					if last_action.type == act.ActionType.ABILITY:
						await self.gm.gm_use(db.QUICK_CTX, who_ent.display_name(), last_action.description)
					elif last_action.type == act.ActionType.SPELL:
						await self.gm.gm_cast(db.QUICK_CTX, who_ent.display_name(), last_action.description)
					else:
						raise ValueError("communication.on_reaction_add: only ABILITY and SPELL action types are supported")
						
				if reaction.emoji == db.SKIP:
					await self.initCog.next_turn(db.QUICK_CTX)
					
		if reaction.message == db.QUICK_REACTION_MESSAGE:
		
			if self.initCog.whose_turn is None:
				db.QUICK_CTX.send("Cannot process reactions, I don't know whose turn it is.")
				return
				
			if meta.get_character_name(user) == self.initCog.whose_turn or meta.get_character_name(user) == "GM":
			
				await self.remove_bot_reactions(reaction.message)
				who = self.initCog.whose_turn
				who_ent = db.find(who)
				
				if reaction.emoji == db.DASH:
					dodged_action = act.get_last_action(type=act.ActionType.ATTACK, target=who_ent)
					who_ent.add_resources_verbose(ctx, dodged_action.effects[act.ActionRole.TARGET])
					who_ent.use_resources_verbose({'R':1})
					
				if reaction.emoji == db.SHIELD:
					blocked_action = act.get_last_action(type=act.ActionType.ATTACK, target=who_ent)
					hp_lost = blocked_action.effects[act.ActionRole.TARGET]["HP"]
					who_ent.add_resources_verbose(ctx, {"HP": hp_lost, "VIM" : -1 * hp_lost})
					who_ent.use_resources_verbose({'R':1})