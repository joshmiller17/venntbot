# --- Josh Aaron Miller 2021
# --- Interaction helper with the Discord bot

import discord
from discord.ext import commands

import random, d20, operator, time, time, asyncio
from enum import Enum


import importlib
db = importlib.import_module("db")
stats = importlib.import_module("stats")
meta = importlib.import_module("meta")
logClass = importlib.import_module("logger")
logger = logClass.Logger("communication")

    
COMM_STATE = None
ABILITY_LIST_CACHE = None
SECONDS_PER_MSG_BATCH = 1
COMM_BOT = None
CTX_TO_MSG = {} # ctx : message obj
MSGS_SENT = False

async def send(ctx, message):
    if not COMM_BOT:
        logger.err("send", "COMM_BOT not initialized")
    if ctx not in COMM_BOT.message_queue:
        COMM_BOT.message_queue[ctx] = []
    COMM_BOT.message_queue[ctx].append(message)

# call this send instead when you need the Message obj back
async def send_and_return(ctx, message):
    await send(ctx, message)
    return await asyncio.create_task(get_message(ctx))
    
async def get_message(ctx):
    global CTX_TO_MSG
    wait_time = 0
    while True:
        if MSGS_SENT and ctx in CTX_TO_MSG:
            ret = CTX_TO_MSG[ctx]
            del CTX_TO_MSG[ctx]
            return ret
        await asyncio.sleep(0.5)
        wait_time += 0.5
        if wait_time > SECONDS_PER_MSG_BATCH * 3:
            logger.err("get_message", "no message found")
            return None

# split contents into messages < 2000 characters (Discord limit)
async def send_in_batches(ctx, msg_list):
    global CTX_TO_MSG
    if msg_list == []:
        return
    #logger.log("send_in_batches",str(COMM_BOT.message_queue))
    msg_length = 0
    msg = ""
    for line in msg_list:
        line_len = len(line)
        if msg_length + line_len > 1999:
            message_obj = await ctx.send(msg)
            msg_length = 0
            msg = ""
        if msg != "":
            msg += "\n"
        msg += line
        msg_length += line_len + 2 # newline
    if msg_length > 0: # finally, send whatever is left
        message_obj = await ctx.send(msg)
    CTX_TO_MSG[ctx] = message_obj

    
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
        choice_map[c] = db.NUMBERS[count]
        count += 1
        
    ret = []
    for c, emoji in choice_map.items():
        ret.append("{0} {1}".format(emoji, c))
    
    m = await send_and_return(ctx,"```\n{0}\n```".format("\n".join(ret)))
    for i in range(count):
        await m.add_reaction(db.NUMBERS[i])
    if has_more:
        await m.add_reaction(db.MORE)
    db.QUICK_ACTION_MESSAGE = m


class Communication(commands.Cog):
    """Interface with the bot."""


    def __init__(self, bot):
        global COMM_BOT
        self.bot = bot
        COMM_BOT = self
        self.enemy_list_offset = 0
        self.ability_list_offset = 0
        self.chosen_ability = None # stored for convenience
        self.initCog = self.bot.get_cog('Initiative')
        self.gm = self.bot.get_cog('GM')
        self.message_queue = {} # ctx : msgs
        self.scheduler = None
        
    @commands.Cog.listener()
    async def on_message(self, message):
        if not self.scheduler:
            self.scheduler = asyncio.create_task(self.schedule_messages(SECONDS_PER_MSG_BATCH))


    async def schedule_messages(self, timeout):
        global CTX_TO_MSG, MSGS_SENT
        while True:
            await asyncio.sleep(timeout)
            MSGS_SENT = False
            CTX_TO_MSG = {}
            for ctx, msgs in self.message_queue.items():
                await send_in_batches(ctx, msgs)
            MSGS_SENT = True
            self.message_queue = {}
    
    async def remove_bot_reactions(self, message):
        for reaction in message.reactions:
            if reaction.me:
                await reaction.remove(self.bot.user)
                await self.remove_bot_reactions(message) # refresh list and try again
                
    @commands.command(pass_context=True)
    async def quick(self, ctx):
        """Show available quick actions."""
        await suggest_quick_actions(ctx, db.find(self.initCog.whose_turn))
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        global COMM_STATE, ABILITY_LIST_CACHE
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
                        ABILITY_LIST_CACHE = None
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
                        abiObj = ABILITY_LIST_CACHE[ability_index]
                        self.chosen_ability = abiObj
                        if abiObj.is_spell:
                            await ask_cast_strength(db.QUICK_CTX)
                        else:
                            await self.gm.gm_use(db.QUICK_CTX, who, abiObj.name)
                        await suggest_quick_actions(db.QUICK_CTX, who_ent) 
                    else:
                        raise ValueError("communication.on_reaction_add: CommState was None")
                        
                if reaction.emoji == db.FAST:
                    await self.gm.gm_cast(db.QUICK_CTX, who, 0, self.chosen_ability.name)
                    
                if reaction.emoji == db.MAGIC:
                    await self.gm.gm_cast(db.QUICK_CTX, who, 1, self.chosen_ability.name)
                    
                if reaction.emoji == db.POWERFUL:
                    await self.gm.gm_cast(db.QUICK_CTX, who, 2, self.chosen_ability.name)
                    
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