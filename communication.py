# --- Josh Aaron Miller 2021
# --- Interaction helper with the Discord bot

import discord
from discord.ext import commands

import random, d20, operator, time, time, asyncio
from enum import Enum


import importlib
logClass = importlib.import_module("logger")
logger = logClass.Logger("communication")

# Emojis
OK = '👍'
NOT_OK = '🚫' #'👎'
ACCEPT = '✅'
DECLINE = '❌'
SHIELD = '🛡'
DASH = '💨'
SWORDS = '⚔️'
RUNNING = '🏃'
SKIP = '⏭️'
REPEAT = '🔁'
THINKING = '🤔'
NUMBERS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
MORE = '➡️'
SCROLL = '📜'
FAST = '⚡'
MAGIC = '🪄'
POWERFUL = '💪'
COOL = '😎' # '🆒'
CUT = '✂️'

ATTRS = ["AGI", "CHA", "DEX", "INT", "PER", "SPI", "STR", "TEK", "WIS"]

    
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
        #if reaction.message == QUICK_ACTION_MESSAGE:
        #    pass