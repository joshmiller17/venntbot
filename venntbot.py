import os, discord
import time
import requests
from bs4 import BeautifulSoup
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

client = commands.Bot(command_prefix="$")

# --------- COMMANDS --------------------

@client.command(pass_context=True)
async def ping(ctx, help='-- Pong!'):
	await ctx.send("pong!")



# Warning: breaks if not given ints, don't use this format	
# @client.command(name='roll', help='-- Simulates rolling X dice of Y sides. Usage: $roll X Y')
# async def roll(ctx, number_of_dice: int, number_of_sides: int):
    # dice = [
        # str(random.choice(range(1, number_of_sides + 1)))
        # for _ in range(number_of_dice)
    # ]
    # await ctx.send(', '.join(dice))


# FIXME only works on abilities and paths that don't have spaces
@client.command(pass_context=True)
async def whatis(ctx, ability, path, help="Get an ability's info. Usage: $whatis ABILITY PATH. Example: $whatis Aim Recruit"):
	URL = "https://vennt.fandom.com/wiki/Path_of_the_" + path.replace(" ", "_")
	print(URL)
	page = requests.get(URL)
	soup = BeautifulSoup(page.content, 'html.parser')
	printing = False
	for hit in soup.find_all('p'):
		text = hit.get_text()
		if ability in text:
			printing = True
		if text.isspace() or "<br>" in text:
			printing = False
		if printing:
			await ctx.send(text)
	
	
# ---------------------------------------


@client.event
async def on_ready():
	print(f'{client.user} has connected to Discord!')
	return
	
@client.event
async def on_message(message):
	await client.process_commands(message)
	if message.author == client.user:
		return # don't respond to ourselves
	if isinstance(message.channel, discord.channel.DMChannel):
		if (message.content == "quit"):
			print("Goodbye")
			await client.close()

client.run(TOKEN)