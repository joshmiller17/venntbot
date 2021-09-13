# --- Josh Aaron Miller 2021
# --- main run for Discord Vennt Bot
import discord, os, sys, traceback, json, time, re, requests, urllib
from pretty_help import PrettyHelp

from discord.ext import commands
from dotenv import load_dotenv

# Other files
import importlib
db = importlib.import_module("db")
meta = importlib.import_module("meta")
sheets = importlib.import_module("sheets")
stats = importlib.import_module("stats")
communication = importlib.import_module("communication")
logClass = importlib.import_module("logger")
logger = logClass.Logger("venntbot")

# Discord setup
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = commands.Bot(command_prefix=("$","/", "!"), help_command=PrettyHelp())

# Authenticate with Vennt Server API
SERVER_URL = "https://topazgryphon.org:3004/"
#SERVER_URL = "http://localhost:3004/"

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

async def do_quit(message):
    await message.author.send("Goodbye.")
    logger.log("on_message", "Goodbye")
    await client.close()
    
async def do_tests(message):
    await message.author.send("Running all tests:")
    altered = message
    with open("tests.json") as f:
        tests = json.load(f)
    for module in tests:
        await message.author.send("**{0}**".format(module["name"]))
        for cmd in module["cmds"]:
            altered.content = cmd
            await message.author.send("`> " + cmd + "`")
            await client.on_message(altered)
            time.sleep(1)
    await message.author.send("Done.")
    
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
    await wait_and_renew_auth()
    
async def wait_and_renew_auth():
    asyncio.sleep(3600)
    renew_auth()

# Setup and Run
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
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
        return # don't respond to ourselves
    if message.content.startswith('>'):
        return # TODO
        await parse(message)
    if isinstance(message.channel, discord.channel.DMChannel):
        if (message.content == "quit"):
            await do_quit(message)
        if (message.content == "test"):
            return # TODO
            await do_tests(message)
        if (message.content == "renew" or message.content == "reset"):
            await renew_auth(message)
    if message.content.startswith("/"):
        await client.process_commands(message)
        

client.description = "A bot to assist with running the Vennt RPG."
client.add_cog(meta.Meta(client))
client.add_cog(sheets.Sheets(client))
client.add_cog(stats.Stats(client))
client.add_cog(communication.Communication(client))

client.run(TOKEN)
