# --- Josh Aaron Miller 2020
# --- meta/misc commands for Discord Vennt Bot

import discord
from discord.ext import commands

import time, requests, datetime
from bs4 import BeautifulSoup

import importlib
db = importlib.import_module("db")

start_time = time.time()

def get_character_name(username):
	for character in db.characters:
		if character["played_by"] == username:
			return character["name"]
	print("ERROR: no name found for " + str(username))
	return ""

class Meta(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True)
	async def ping(self, ctx, help='Pong!'):
		await ctx.send("Pong!")


	@commands.command(pass_context=True)
	async def uptime(self, ctx, help = "Get bot's lifespan"):
		await ctx.send("I've been up for " + str(datetime.timedelta(seconds = (time.time() - start_time))))


	@commands.command(pass_context=True)
	async def whatis(self, ctx, *args, help="Get an ability's info. Usage: $whatis ABILITY. Example: $whatis Basic Cooking"):
		ability = " ".join(args[:])
		found = False
		approximations = []
		for a in abilities:
			if ability.lower() in a["ability"].lower(): # approximate
				if a["ability"].lower() == ability.lower():
					URL = a["url"]
					found = True
					break
				else:
					approximations.append(a["ability"])
					URL = a["url"]
		if len(approximations) == 1:
			found = True
		if not found:
			if approximations != []:
				await ctx.send("Did you mean: " + " or ".join(approximations))
			else:
				await ctx.send("No ability found named " + ability)
			return
		else:
			page = requests.get(URL)
			soup = BeautifulSoup(page.content, 'html.parser')
			# FIXME? sends every line as a separate message to avoid 2000 char limit, but could be smarter about this
			printing = False
			for hit in soup.find_all('p'):
				text = hit.get_text()
				if ability in text:
					printing = True
				if text.isspace() or "<br>" in text:
					printing = False
				if printing:
					await ctx.send(text)
			await ctx.send("From: <" + URL + ">")
	