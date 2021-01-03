# --- Josh Aaron Miller 2020
# --- meta/misc commands for Discord Vennt Bot

import discord
from discord.ext import commands

import time, datetime, json

import importlib
db = importlib.import_module("db")
webscraper = importlib.import_module("webscraper")
abilityClass = importlib.import_module("ability")


START_TIME = time.time()

def get_character_name(username):
	for character in db.characters:
		if character["played_by"] == str(username):
			return character["name"]
	print("meta.get_character_name: ERROR: no name found for " + str(username))
	return ""
	
def save_aliases(aliases):
	with open("aliases.json", 'w') as f:
		json.dump(aliases, f, indent=4)
	
	
class Meta(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		with open("aliases.json") as f:
			self.aliases = json.load(f)

	@commands.command(pass_context=True)
	async def ping(self, ctx, help='Pong!'):
		await ctx.send("Pong!")
		
		
	@commands.command(pass_context=True, aliases=['set_alias', 'newalias', 'new_alias', 'makealias', 'make_alias'])
	async def setalias(self, ctx, alias, *command, help='Make a shortcut for a commonly used command.'):
		who = str(ctx.message.author)
		found = False
		for user in self.aliases:
			if user["user"] == who:
				user[alias] = " ".join(command[:])
				found = True
				break
		if not found:
			new_entry = {"user": who, alias : " ".join(command[:])}
			self.aliases.append(new_entry)
		save_aliases(self.aliases)
		await ctx.send(alias + " saved as " + " ".join(command[:]))
		
	@commands.command(pass_context=True, aliases=['usealias', 'use_alias', 'a'])
	async def alias(self, ctx, alias, help='Use a shortcut you set with $setalias.'):
		who = str(ctx.message.author)
		for user in self.aliases:
			if user["user"] == who:
				if user[alias]:
					altered = ctx.message
					altered.content = user[alias]
					print("meta.alias: new content is " + altered.content)
					await self.bot.on_message(altered)
					await ctx.message.add_reaction(db.OK)
					return
		await ctx.message.add_reaction(db.NOT_OK)

	@commands.command(pass_context=True)
	async def uptime(self, ctx, help = "Get bot's lifespan"):
		await ctx.send("I've been up for " + str(datetime.timedelta(seconds = (time.time() - START_TIME))))
		
	@commands.command(pass_context=True)
	async def cost(self, ctx, *args, help = "Get an ability's cost."):
		name = " ".join(args[:])
		ability = abilityClass.get_ability(name)
		await ctx.send(str(ability.cost))

	@commands.command(pass_context=True)
	async def whatis(self, ctx, *args, help="Get an ability's info. Usage: $whatis ABILITY. Example: $whatis Basic Cooking"):
		matches, URL = webscraper.find_ability(*args)
		if len(matches) == 1:
			contents = webscraper.get_ability_contents(matches[0], URL)
			contents.append("From: <" + URL + ">")
			# ----- split contents into msgs < 2000 char
			msg_length = 0
			msg = ""
			if contents == []:
				await ctx.send("I found that ability but I didn't see any description for it.")
			for line in contents:
				line_len = len(line)
				if msg_length + line_len > 1800:
					await ctx.send(msg)
					msg_length = 0
					msg = ""
				msg += line
				msg_length += line_len
			if msg_length > 0:
				await ctx.send(msg)
			# ----- end sending msg
		elif len(matches) > 1:
			await ctx.send("Did you mean: " + " or ".join(matches))
		else:
			ability = " ".join(args[:])
			await ctx.send("No ability found: " + ability)
	
