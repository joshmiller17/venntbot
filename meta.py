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
	
def save_macros(macros):
	with open("macros.json", 'w') as f:
		json.dump(macros, f, indent=4)
	
class Meta(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		try:
			with open("macros.json") as f:
				self.macros = json.load(f)
		except:
			logger.warn("__init__", "Unable to open macros.json, starting from scratch.")
			self.macros = []

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
	

	@commands.command(pass_context=True, aliases=['setalias'])
	async def setmacro(self, ctx, macro, *command, help='Make a shortcut for a commonly used command. Split new commands using "/". Use "{}" to specify an ad lib to be filled in when the macro is used. Example: $setmacro pingandsay $ping / $say {}'):
		who = str(ctx.message.author)
		found = False
		new_cmd = " ".join(command[:])
		new_cmd = new_cmd.split(' / ')
		if len(new_cmd) > 10:
			await ctx.message.add_reaction(db.NOT_OK)
			await ctx.send("Macros are limited to 10 commands.")
			return
		for cmd in new_cmd:
			if cmd.startswith("$alias") or cmd.startswith("$macro"):
				await ctx.message.add_reaction(db.NOT_OK)
				await ctx.send("To avoid infinite loops, you cannot define a macro which calls another macro.")
				return
		for user in self.macros:
			if user["user"] == who:
				user[macro] = new_cmd
				found = True
				break
		if not found:
			new_entry = {"user": who, macro : new_cmd}
			self.macros.append(new_entry)
		save_macros(self.macros)
		await ctx.send(macro + " saved.")
		
	@commands.command(pass_context=True, aliases=['alias'])
	async def macro(self, ctx, macro, *adlibs, help='Use a shortcut you set with $setmacro. If you gave your macro ad libs, put them after.'):
		who = str(ctx.message.author)
		args = list(adlibs)
		for user in self.macros:
			if user["user"] == who:
				if user[macro]:
					for line in user[macro]:
						altered = ctx.message
						args_needed = line.count("{}")
						current_args = []
						while args_needed > 0:
							if len(args) < 1:
								args.append("{}") # add blanks as needed to make the macro valid and show the user what they missed
							current_args.append(args.pop(0))
							args_needed -= 1
						line = line.format(*current_args)
						altered.content = line
						logger.log("macro","new content is " + altered.content)
						await self.bot.on_message(altered)
						time.sleep(1)
					return
		await ctx.message.add_reaction(db.NOT_OK)
		
	@commands.command(pass_context=True, aliases=['aliases', 'macros', 'myaliases'])
	async def mymacros(self, ctx, macro=None, help='See the macros you set, or try $mymacros macro-name to see the details of a particular macro.'):
		who = str(ctx.message.author)
		ret = "```\n{0}\n```"
		macros = []
		for user in self.macros:
			if user["user"] == who:
				for key, val in user.items():
					if key == "user":
						continue
					if macro is not None:
						if key == macro:
							await ctx.send(key + ": " + " / ".join(val))
							return
					else:
						macros.append("{0} -- {1} command(s)".format(key, len(val)))
		if macros != []:
			await ctx.send(ret.format("\n".join(macros)))
		else:
			if macro is not None:
				await ctx.send("No macro found named " + macro)
			else:
				await ctx.send("No macros saved.")
			
			
	@commands.command(pass_context=True)
	async def say(self, ctx, *msg, help='Say something as your character. For use with macros.'):
		who = str(ctx.message.author)
		character = get_character_name(who)
		await ctx.send("**{0}**: {1}".format(character, " ".join(msg)))
	
	@commands.command(pass_context=True, aliases=['me'])
	async def emote(self, ctx, *msg, help='Do something as your character. For use with macros.'):
		who = str(ctx.message.author)
		character = get_character_name(who)
		await ctx.send("*{0} {1}*".format(character, " ".join(msg)))

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
	
