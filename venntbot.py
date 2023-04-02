# --- Josh Aaron Miller 2021
# --- main run for Discord Vennt Bot
import discord, os, sys, traceback, json, time, re, requests, urllib, asyncio
from pretty_help import PrettyHelp

from discord.ext import commands
from dotenv import load_dotenv

# Other files
import importlib
logClass = importlib.import_module("logger")
logger = logClass.Logger("venntbot")
communication = importlib.import_module("communication")

# Discord setup
load_dotenv()
intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.reactions = True
TOKEN = os.getenv('DISCORD_TOKEN')
client = commands.Bot(command_prefix=("$","/", "!"), help_command=PrettyHelp(), intents=intents)

# Authenticate with Vennt Server API
#SERVER_URL = "https://topazgryphon.org:3004/"
SERVER_URL = "http://localhost:3004/"

GUILD_ID = 383650516225228801
VOTING_CHANNEL = 'secret'

BALLOT = []
BALLOT_INDEX = 0

with open("api_credentials.json") as f:
    vennt_creds = json.load(f)

# register if need be
username = vennt_creds["username"]
password = vennt_creds["password"]
data = '{"register": "%s", "password": "%s"}' % (username, password)
response = requests.post(SERVER_URL, data=data.encode('utf-8'), verify=False)

# login
data = '{"login": "%s", "password": "%s"}' % (username, password)
response = requests.post(SERVER_URL, data=data.encode('utf-8'), verify=False)

response = json.loads(response.text)
auth_token = response["auth_token"] # assume success
client.auth_token = auth_token

# load ability voting
with open('ballot.txt', 'r') as file:
    file_contents = file.read()
    BALLOT = file_contents.split("\r\n\r\n")
    print('Loaded %d abilities' % len(BALLOT))
    

async def do_quit(message):
    await message.author.send("Goodbye.")
    logger.log("on_message", "Goodbye")
    await client.close()
    
async def ability_vote_loop():
    # TODO post question to voting channel
    # TODO post initial reactions; use communication.make_choice_list
    # TODO on reaction, count it for the right message and right person
    # TODO command to show players' stats on voting
    # TODO command to order abilities by positive - negative votes (name and vote counts only)
    await asyncio.sleep(60) #test
    await ability_vote_loop()
    
async def renew_auth(message=None):
    logger.log("renew_auth", "renewing")
    data = '{"login": "%s", "password": "%s"}' % (username, password)
    response = requests.post(SERVER_URL, data=data.encode('utf-8'), verify=False)
    logger.log("renew_auth", response.text)
    response = json.loads(response.text)
    auth_token = response["auth_token"] # assume success
    client.auth_token = auth_token
    if message:
        ctx = await client.get_context(message)
        await communication.send(ctx, "Authentication renewed.")
    #while True:
    await asyncio.sleep(3600)
    await renew_auth()
        
# Setup and Run
@client.event
async def on_ready():
    global GUILD_ID, VOTING_CHANNEL
    
    print(f'{client.user} has connected to Discord!')
    await renew_auth()
    
    # Search for the voting channel by name
    channel = discord.utils.get(client.get_all_channels(), guild__id=GUILD_ID, name=VOTING_CHANNEL)
    if channel is not None:
        # Post the message to the channel
        VOTING_CHANNEL = channel
        await VOTING_CHANNEL.send('Hello, world!')
    else:
        print(f'Channel {VOTING_CHANNEL} not found on server {GUILD_ID}')
    return
    
@client.event
async def on_command_error(ctx, error):
    if isinstance(error, discord.ext.commands.errors.CommandNotFound):
        await communication.send(ctx,"No command found: " + ctx.message.content)
    elif isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        await communication.send(ctx,"That's not how that command works. Try $help <command>")
    else:
        await communication.send(ctx,"Oh, yikes! That's a new kind of error.\n" + str(error))
        traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
    
@client.event
async def on_message(message):
    if message.author == client.user:
        if message.content == "Authentication invalid":
            await renew_auth(message)
        return # don't respond to ourselves
    if message.content.startswith('>'):
        return # TODO
        await parse(message)
    if isinstance(message.channel, discord.channel.DMChannel):
        if (message.content == "quit"):
            await do_quit(message)
        if (message.content == "renew" or message.content == "reset"):
            await renew_auth(message)
    if message.content.startswith("/"):
        await client.process_commands(message)


@commands.command(pass_context=True)
async def version(self, ctx, *query):        
    await communication.send(ctx, "Bot version: 0.14.0\nAbility cache: v. 0.13.7")

@commands.command(pass_context=True, aliases=['whatis'])
async def lookup(self, ctx, *query):
    """Get the info of an ability."""
    renew_auth() # make sure we're logged in
    response = requests.get("https://topazgryphon.org:3004/" + 'lookup_ability?auth_token=%s&name=%s' % (self.bot.auth_token," ".join(query[:])), verify=False)
    response = json.loads(response.text)
    print(response)
    if not response["success"]:
        await communication.send(ctx, response["info"])
    else:
        msg = "".join(response["value"])
        if msg:
            await communication.send(ctx, "```" + msg + "```")
        else:
            await communication.send(ctx, "No ability found.")


client.description = "A bot to assist with running the Vennt RPG."
client.add_cog(communication.Communication(client))

client.run(TOKEN)