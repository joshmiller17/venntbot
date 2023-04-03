# --- Josh Aaron Miller 2021
# --- main run for Discord Vennt Bot
import discord, os, sys, traceback, json, time, traceback, re, requests, urllib, asyncio, d20, random, interactions
import constants
from collections import defaultdict
from enum import Enum
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands
from discord.ext.commands import Context


# Discord setup
load_dotenv()
#intents = discord.Intents.default()
#intents.members = True
#intents.messages = True
#intents.reactions = True
#intents.guilds = True
#intents.dm_typing = True
TOKEN = os.getenv('DISCORD_TOKEN')
# Authenticate with Vennt Server API
SERVER_URL = "https://topazgryphon.org:3004/"
#SERVER_URL = "http://localhost:3004/"

GUILD_ID = 383650516225228801
VOTING_CHANNEL = None
intents = discord.Intents.all()
client = commands.Bot(command_prefix="!",intents=intents)


# Emojis
OK = '👍'
NOT_OK = '🚫' #'👎'
ACCEPT = '✅'
DECLINE = '❌'
#SHIELD = '🛡' DASH = '💨' SWORDS = '⚔️' RUNNING = '🏃'
SKIP = '⏭️'
REPEAT = '🔁'
THINKING = '🤔'
NUMBERS = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
MORE = '➡️'
#SCROLL = '📜' FAST = '⚡' MAGIC = '🪄' POWERFUL = '💪'
COOL = '😎' # '🆒'
CUT = '✂️'
#ATTRS = ["AGI", "CHA", "DEX", "INT", "PER", "SPI", "STR", "TEK", "WIS"]

    
BALLOT_MESSAGES = {} # message : {up: [people], down: [people]}
SECONDS_PER_MSG_BATCH = 1
CTX_TO_MSG = {} # ctx : message obj
MSGS_SENT = False

message_queue = {} # ctx : msgs

BALLOT = []
BALLOT_INDEX = 0

with open("api_credentials.json") as f:
    vennt_creds = json.load(f)

# register if need be
username = vennt_creds["username"]
password = vennt_creds["password"]
#data = '{"register": "%s", "password": "%s"}' % (username, password)
#response = requests.post(SERVER_URL, data=data.encode('utf-8'), verify=False)

# login
data = '{"login": "%s", "password": "%s"}' % (username, password)
response = requests.post(SERVER_URL, data=data.encode('utf-8'), verify=False)

response = json.loads(response.text)
auth_token = response["auth_token"] # assume success
client.auth_token = auth_token
#client.auth_token = auth_token

# load ability voting
with open('ballot.txt', 'r') as file:
    file_contents = file.read()
    BALLOT = file_contents.split("\n\n")
    print('Loaded %d abilities' % len(BALLOT))
    
    
def log(function, message):
    t = time.strftime("%m/%d/%Y, %H:%M:%S", time.localtime())
    print("[" + t + "] " + function + ": " + message)
    
def warn(function, message):
    t = time.strftime("%m/%d/%Y, %H:%M:%S", time.localtime())
    print("[" + t + "] WARNING: " + function + ": " + message)

def err(function, message):
    t = time.strftime("%m/%d/%Y, %H:%M:%S", time.localtime())
    print("[" + t + "] ERROR: " + function + ": " + message)
    for line in traceback.format_stack():
        print(line.strip())

async def do_quit(message):
    await message.author.send("Goodbye.")
    log("on_message", "Goodbye")
    await client.close()
    
async def ability_vote_loop():
    global BALLOT_MESSAGES, BALLOT_INDEX   

    if BALLOT_INDEX == 0:
        await VOTING_CHANNEL.send(f'Welcome to Cool or Cut! The channel for voting on new abilities. For each ability, you decide whether we keep it {COOL} or cut it {CUT}! Everyone will get special rewards at the end based on how many times they used their less-frequent vote. So if you vote 7 {COOL} and 4 {CUT}, you will get 4 points toward the special rewards! Have fun!')
        await asyncio.sleep(5) #test
    
    log("ability_vote_loop", "looping")
    if BALLOT_INDEX >= len(BALLOT):
        await VOTING_CHANNEL.send("That's it for Cool or Cut! Time to tally the votes!")
        return
        
    message = await VOTING_CHANNEL.send(f'**Cool or Cut #{BALLOT_INDEX + 1}**\n What do you think of this ability?\n' + BALLOT[BALLOT_INDEX])
    BALLOT_INDEX += 1
    await asyncio.sleep(0.5)
    await message.add_reaction(COOL)
    await asyncio.sleep(0.5)
    await message.add_reaction(CUT)
    BALLOT_MESSAGES[message] = {COOL: [], CUT: []}
    
    await asyncio.sleep(60) #test
    await ability_vote_loop()
    
async def renew_auth(message=None):
    log("renew_auth", "renewing")
    data = '{"login": "%s", "password": "%s"}' % (username, password)
    response = requests.post(SERVER_URL, data=data.encode('utf-8'), verify=False)
    log("renew_auth", response.text)
    response = json.loads(response.text)
    auth_token = response["auth_token"] # assume success
    client.auth_token = auth_token
    if message:
        ctx = await client.get_context(message)
        await send(ctx, "Authentication renewed.")
    #while True:
    await asyncio.sleep(3600)
    await renew_auth()
        
# Setup and Run
@client.event
async def on_ready():
    global GUILD_ID, VOTING_CHANNEL
    print(f'Connected to Discord!')
    VOTING_CHANNEL = client.get_channel(1069106533767598152)
    asyncio.create_task(renew_auth())
    #asyncio.create_task(ability_vote_loop())
    asyncio.create_task(schedule_messages(1))
    return
    
    
@client.event
async def on_message(message):
    if message.author == client.user:
        if message.content == "Authentication invalid":
            await renew_auth(message)
        return # don't respond to ourselves
    if isinstance(message.channel, discord.channel.DMChannel):
        if (message.content == "quit"):
            await do_quit(message)
        if (message.content == "renew" or message.content == "reset"):
            await renew_auth(message)
    if message.content.startswith("/"):
        await client.process_commands(message)


@commands.hybrid_command(name="version", description="Get the bot's version and ability cache version.")
async def version(context: Context) -> None:      
    print("version")
    await send(ctx, "Bot version: 0.14.0\nAbility cache: v. 0.13.7")
    
@commands.hybrid_command(name="leaderboard", description="Show Cool or Cut leaderboards.")
async def leaderboard(context: Context) -> None: 
    await send(ctx, get_leaderboard())

@commands.hybrid_command(name="voteresults", description="Show Cool or Cut vote results")
async def voteresults(context: Context) -> None: 
    await send(ctx, get_vote_results())

@commands.hybrid_command(name="lookup", description="Query the Vennt wiki for an ability")
@app_commands.describe(query="Ability to look up")
async def lookup(ctx: Context, *, query: str) -> None:
    """Get the info of an ability."""
    renew_auth() # make sure we're logged in
    response = requests.get("https://topazgryphon.org:3004/" + 'lookup_ability?auth_token=%s&name=%s' % (client.auth_token, query), verify=False)
    response = json.loads(response.text)
    print(response)
    if not response["success"]:
        await send(ctx, response["info"])
    else:
        msg = "".join(response["value"])
        if msg:
            await send(ctx, "```" + msg + "```")
        else:
            await send(ctx, "No ability found.")


                
def get_vote_results():
    results_points = {}
    results_str = {}
    for msg in BALLOT_MESSAGES:
        content = msg.content
        ability_name = content.split('\n')[2]
        cool = len(BALLOT_MESSAGES[msg][COOL])
        cut = len(BALLOT_MESSAGES[msg][CUT])
        results_points[ability_name] = cool - cut
        results_str[ability_name] = f'{ability_name}: {cool - cut} (+{cool}, -{cut})'
    
    response = ""
    sorted_results = dict(sorted(results_points.items(), key=lambda x: x[1], reverse=True))
    for key, val in sorted_results.items():
        response += results_str[key] + "\n"
    return response

def get_leaderboard():
    cools = defaultdict(int)
    cuts = defaultdict(int)
    for msg in BALLOT_MESSAGES:
        for user in BALLOT_MESSAGES[msg][COOL]:
            cools[user] += 1
        for user in BALLOT_MESSAGES[msg][CUT]:
            cuts[user] += 1
    
    response = ""
    all_users = list(cools.keys()) + list(cuts.keys())
    for user in all_users:
        cool = cools[user]
        cut = cuts[user]
        response += f'{user} has {abs(cool - cut)} points! ({cool} {COOL}, {cut} {CUT})'
    
    return response

async def send(ctx, message):
    print("send")
    global message_queue
    if ctx not in message_queue:
        message_queue[ctx] = []
    message_queue[ctx].append(message)

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

   
async def schedule_messages(timeout):
    global CTX_TO_MSG, MSGS_SENT, message_queue
    while True:
        await asyncio.sleep(timeout)
        MSGS_SENT = False
        CTX_TO_MSG = {}
        for ctx, msgs in message_queue.items():
            print("sending item")
            await send_in_batches(ctx, msgs)
        MSGS_SENT = True
        message_queue = {}   
                
                
@client.event
async def on_reaction_add(reaction, user):
    if user == client.user:
        return
    if reaction.message in BALLOT_MESSAGES:
        if reaction.emoji == COOL:
            BALLOT_MESSAGES[reaction.message][COOL].append(user)
            if user in BALLOT_MESSAGES[reaction.message][CUT]:
                BALLOT_MESSAGES[reaction.message][CUT].remove(user)
                await reaction.message.remove_reaction(CUT, user)
        if reaction.emoji == CUT:
            BALLOT_MESSAGES[reaction.message][CUT].append(user)
            if user in BALLOT_MESSAGES[reaction.message][COOL]:
                BALLOT_MESSAGES[reaction.message][COOL].remove(user)
                await reaction.message.remove_reaction(COOL, user)
        with open("vote_results.txt", "w") as file:
            file.write(get_vote_results())


client.description = "Just your friendly neighborhood Vennt RPG client."
client.run(TOKEN)