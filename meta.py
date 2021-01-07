# --- Josh Aaron Miller 2021
# --- meta/misc commands for Discord Vennt Bot

import discord
from discord.ext import commands

import time, datetime, json, random

import importlib
db = importlib.import_module("db")
webscraper = importlib.import_module("webscraper")
abilityClass = importlib.import_module("ability")
logClass = importlib.import_module("logger")
logger = logClass.Logger("meta")

TEST_SCRIPT_EASY = [
		"$add_turn Bang 20", 
		"$add_enemies 2 rat",
		"$add_enemies 1 skeleton", 
		"$next_turn",
		"$gm_attack Bang skeleton heat_death     ",
		"$undo                                   ",
		"$gm_attack Bang skeleton heat_death     ",
		"$gm_attack Bang rat heat_death +0 /2    ",
		"$gm_spend Bang 1 Reaction               ",
		"$end                                    ",
		"$enemy_attack rat2 Bang				 ",
		"$end                                    ",
		"$end                                    ",
		"$gm_attack Bang skeleton ratchet        ",
		"$gm_spend Bang 2 hero                   ",
		"$gm_modify Bang 2 Action                ",
		"$gm_attack Bang rat2 ratchet            ",
		"$end                                    "
		]

TEST_SCRIPT_HARD = [
		">[aim]                                                                           ",
		">shoot [rat A] with [rifle]                                                      ",
		">I'll [move] away from the enemies                                               ",
		">then attack the [skeleton] with [crippling shot]                                ",
		">I end my turn                                                                   ",
		">I'll use [Instant Focus]                                                        ",
		">then attack [rat B] with the [rifle]                                            ",
		">I end my turn                                                                   ",
		">I'm going to [Aim]                                                              ",
		">then shoot the [skeleton] in the head with [disabling shot]                     ",
		">[TIL this song is more than the opening fanfare]                                "
]


START_TIME = time.time()

def get_character_name(username):
	for character in db.characters:
		if character["played_by"] == str(username):
			return character["name"]
	logger.err("get_character_name", "no name found for " + str(username))
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
		
	@commands.command(pass_context=True)
	async def test_script(self, ctx, which, help="For debug only."):
		altered = ctx.message
		await ctx.send("Now running test fight.")
		if which == "easy":
			script = TEST_SCRIPT_EASY
		else:
			script = TEST_SCRIPT_HARD
		for line in script:
			altered.content = line
			await ctx.send("`> " + line + "`")
			await self.bot.on_message(altered)
			time.sleep(2)
		await ctx.send("Done.")
	

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
					logger.log("alias","new content is " + altered.content)
					await self.bot.on_message(altered)
					await ctx.message.add_reaction(db.OK)
					return
		await ctx.message.add_reaction(db.NOT_OK)
		
	@commands.command(pass_context=True, aliases=['aliases'])
	async def myaliases(self, ctx, help='See the aliases you set.'):
		who = str(ctx.message.author)
		ret = "```\n{0}\n```"
		aliases = []
		for user in self.aliases:
			if user["user"] == who:
				for key, val in user.items():
					if key == "user":
						continue
					aliases.append(key + " -- " + val)
		if aliases != []:
			await ctx.send(ret.format("\n".join(aliases)))
		else:
			await ctx.send("No aliases saved.")

	@commands.command(pass_context=True)
	async def uptime(self, ctx, help = "Get bot's lifespan"):
		await ctx.send("I've been up for " + str(datetime.timedelta(seconds = (time.time() - START_TIME))))
		
	@commands.command(pass_context=True)
	async def cost(self, ctx, *ability, help = "Get an ability's cost."):
		name = " ".join(ability[:])
		ability = abilityClass.get_ability(name)
		await ctx.send(str(ability.cost))

	@commands.command(pass_context=True)
	async def whatis(self, ctx, *ability, help="Get an ability's info."):
		matches, URL = webscraper.find_ability(*ability)
		if len(matches) == 1:
			contents = webscraper.get_ability_contents(matches[0], URL)
			logger.log("whatis",str(contents))
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
			if len(matches) < 10:
				await ctx.send("Did you mean: " + " or ".join(matches))
			else:
				await ctx.send("Your query matches too many abilities. Please try being more specific.")
				logger.log("whatis","found too many matches")
				logger.log("whatis",matches)
		else:
			ability = " ".join(ability[:])
			await ctx.send("No ability found: " + ability)
	
