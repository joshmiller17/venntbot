# --- Josh Aaron Miller 2021
# --- main run for Discord Vennt Bot
import discord
import os, sys, traceback, json, time, re

from discord.ext import commands
from dotenv import load_dotenv

# Other files
import importlib
db = importlib.import_module("db")
meta = importlib.import_module("meta")
combat = importlib.import_module("combat")
sheets = importlib.import_module("sheets")
stats = importlib.import_module("stats")
enemyhandler = importlib.import_module("enemyhandler")
initiative = importlib.import_module("initiative")
gm = importlib.import_module("gm")
communication = importlib.import_module("communication")
webscraper = importlib.import_module("webscraper")
logClass = importlib.import_module("logger")

logger = logClass.Logger()


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
	if message.content.startswith('>'):
		logger.log("on_message", "Experimental parser activated: " + message.content)
		matches = re.findall("\[[^\]]*\]|end my turn", message.content)
		target = None
		weapon = None
		acc_mod = "+0"
		dmg_mod = "+0"
		cast_strength = None
		initCog = client.get_cog('Initiative')
		gm = client.get_cog('GM')
		ctx = await client.get_context(message)
		who = meta.get_character_name(ctx.message.author)
		entity = db.find(who)
		for match in matches:
			match = match.replace('[', '')
			match = match.replace(']', '')
			logger.log("on_message", match)
			ability_matches, URL = webscraper.find_ability(match)
			if match.lower() == "end my turn":
				await initCog.next_turn(ctx)
			elif match in db.get_player_names():
				who = match
				entity = db.find(who)
			elif match.lower() == "move" or match.lower() == "moves":
				success = await entity.use_resources_verbose(ctx, {'A':1})
				await ctx.send(who + " moved.")
			elif match in [e.display_name() for e in db.ENEMIES]:
				target = match
			elif db.get_weapon(match) is not None:
				weapon = match
			elif "cast" in match.lower():
				if "half" in match.lower():
					cast_strength = 0
				elif "double" in match.lower():
					cast_strength = 2
				else:
					cast_strength = 1
			elif len(ability_matches) == 1:
				if cast_strength is not None:
					await gm.gm_cast(ctx, who, cast_strength, ability_matches[0])
					cast_strength = None
				else:
					await gm.gm_use(ctx, who, ability_matches[0])
			elif match.startswith('+') or match.startswith('-'):
				mod = match.split(' ')
				if mod[1].upper() == "ACC":
					acc_mod = mod[0]
				elif mod[1].upper() == "DMG":
					dmg_mod = mod[0]
			else:
				await ctx.send("Sorry, I don't understand [" + match + "]")
		if target is not None and weapon is not None:
			await gm.gm_attack(ctx, who, target, weapon, acc_mod, dmg_mod)
			target = None
			weapon = None
			acc_mod = "+0"
			dmg_mod = "+0"
				
		
	if isinstance(message.channel, discord.channel.DMChannel):
		if (message.content == "quit"):
			await message.author.send("Goodbye.")
			logger.log("on_message", "Goodbye")
			await client.close()
		if (message.content == "test"):
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
			
client.add_cog(meta.Meta(client))
client.add_cog(sheets.Sheets(client))
client.add_cog(stats.Stats(client))
client.add_cog(initiative.Initiative(client))
client.add_cog(gm.GM(client)) # requires initiative
client.add_cog(combat.Combat(client)) # requires GM
client.add_cog(enemyhandler.EnemyHandler(client))
client.add_cog(communication.Communication(client)) # requires initiative

client.run(TOKEN)