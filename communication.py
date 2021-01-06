# --- Josh Aaron Miller 2021
# --- Interaction helper with the Discord bot

import discord
from discord.ext import commands

import random, d20, operator, time, re

import importlib
db = importlib.import_module("db")
stats = importlib.import_module("stats")
init = importlib.import_module("initiative")
abilityClass = importlib.import_module("ability")
act = importlib.import_module("action")
meta = importlib.import_module("meta")
logClass = importlib.import_module("logger")
logger = logClass.Logger("communication")

async def suggest_quick_actions(ctx, who):
	if who is None:
		return # No one's turn
		
	entity = db.find(who)

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
	db.QUICK_ACTION_MESSAGE = m
	db.QUICK_CTX = ctx

async def suggest_quick_reactions(ctx, who):
	if who is None:
		return # No one's turn
		
	entity = db.find(who)

	if entity.reactions < 1:
		return
	m = await ctx.send("*(Quick reactions: {0} Dodge, {1} Block.)*".format(db.DASH, db.SHIELD))
	await m.add_reaction(db.DASH)
	await m.add_reaction(db.SHIELD)
	db.QUICK_REACTION_MESSAGE = m
	
async def make_enemy_list(self, ctx, offset):
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
	db.QUICK_ACTION_MESSAGE = m
	self.enemy_list_offset += 9

class Communication(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.enemy_list_offset = 0
		self.initCog = self.bot.get_cog('Initiative')
		self.gm = self.bot.get_cog('GM')

	
	async def remove_bot_reactions(self, message):
		for reaction in message.reactions:
			if reaction.me:
				await reaction.remove(self.bot.user)
				await self.remove_bot_reactions(message) # refresh list and try again
	
	@commands.Cog.listener()
	async def on_reaction_add(self, reaction, user):
		if user == self.bot.user:
			return
		if reaction.message == db.QUICK_ACTION_MESSAGE:
			if meta.get_character_name(user) == self.initCog.whose_turn or meta.get_character_name(user) == "GM":
				await self.remove_bot_reactions(reaction.message)
				if reaction.emoji == db.MORE: # assume we're doing basic attack
					await make_enemy_list(self, db.QUICK_CTX, self.enemy_list_offset)
				if reaction.emoji == db.SWORDS:
					self.enemy_list_offset = 0
					await make_enemy_list(self, db.QUICK_CTX, self.enemy_list_offset)
				if db.is_number_emoji(reaction.emoji):
					self.enemy_list_offset -= 9
					enemy_index = db.NUMBERS.index(reaction.emoji) + self.enemy_list_offset
					target = db.ENEMIES[enemy_index]
					await self.gm.gm_attack(db.QUICK_CTX, self.initCog.whose_turn, target.display_name(), db.find(self.initCog.whose_turn).primary_weapon)
					await suggest_quick_actions(db.QUICK_CTX, self.initCog.whose_turn) 
				if reaction.emoji == db.RUNNING:
					entity = db.find(self.initCog.whose_turn)
					success = await entity.use_resources_verbose(db.QUICK_CTX, {'A':1})
					await db.QUICK_CTX.send(self.initCog.whose_turn + " moved.")
					await suggest_quick_actions(db.QUICK_CTX, self.initCog.whose_turn)
				if reaction.emoji == db.REPEAT:
					last_action = act.get_last_action(user=db.find(self.initCog.whose_turn))
					if last_action.type == act.ActionType.ABILITY:
						await self.gm.gm_use(db.QUICK_CTX, self.initCog.whose_turn, last_action.description)
					elif last_action.type == act.ActionType.SPELL:
						await self.gm.gm_cast(db.QUICK_CTX, self.initCog.whose_turn, last_action.description)
					else:
						raise ValueError("combat.on_reaction_add: only ABILITY and SPELL action types are supported")
				if reaction.emoji == db.SKIP:
					await self.initCog.next_turn(db.QUICK_CTX)
		if reaction.message == db.QUICK_REACTION_MESSAGE:
			if meta.get_character_name(user) == self.initCog.whose_turn or meta.get_character_name(user) == "GM":
				await self.remove_bot_reactions(reaction.message)
				if reaction.emoji == db.DASH:
					attacked = db.find(self.initCog.whose_turn)
					dodged_action = act.get_last_action(type=act.ActionType.ATTACK, target=attacked)
					attacked.add_resources_verbose(ctx, dodged_action.effects[act.ActionRole.TARGET])
					db.find(self.initCog.whose_turn).use_resources_verbose({'R':1})
				if reaction.emoji == db.SHIELD:
					attacked = db.find(self.initCog.whose_turn)
					blocked_action = act.get_last_action(type=act.ActionType.ATTACK, target=attacked)
					hp_lost = blocked_action.effects[act.ActionRole.TARGET]["HP"]
					attacked.add_resources_verbose(ctx, {"HP": hp_lost, "VIM" : -1 * hp_lost})
					db.find(self.initCog.whose_turn).use_resources_verbose({'R':1})