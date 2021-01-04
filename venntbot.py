# --- Josh Aaron Miller 2020
# --- main run for Discord Vennt Bot
import discord
import os, sys, traceback

from discord.ext import commands
from dotenv import load_dotenv

# Other files
import importlib
db = importlib.import_module("db")
meta = importlib.import_module("meta")
combat = importlib.import_module("combat")
sheets = importlib.import_module("sheets")
stats = importlib.import_module("stats")

# Discord setup
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
client = commands.Bot(command_prefix="$")


# Setup and Run
@client.event
async def on_ready():
	print(f'{client.user} has connected to Discord!')
	return
	
@client.event
async def on_command_error(ctx, error):
	if isinstance(error, discord.ext.commands.errors.CommandNotFound):
		await ctx.send("No command found: " + ctx.message.content)
	elif isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
		await ctx.send("That's not how that command works. Try $help <command>")
	else:
		await ctx.send("Oh, yikes! That's a new kind of error.\n" + str(error))
		traceback.print_exception(type(error), error, error.__traceback__, file=sys.stderr)
	
@client.event
async def on_message(message):
	await client.process_commands(message)
	if message.author == client.user:
		return # don't respond to ourselves
	if isinstance(message.channel, discord.channel.DMChannel):
		if (message.content == "quit"):
			await message.author.send("Goodbye.")
			print("Goodbye")
			await client.close()
			
client.add_cog(meta.Meta(client))
client.add_cog(sheets.Sheets(client))
client.add_cog(stats.Stats(client))
client.add_cog(combat.Combat(client))

client.run(TOKEN)