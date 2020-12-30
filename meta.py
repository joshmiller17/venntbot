# --- Josh Aaron Miller 2020
# --- meta/misc commands for Discord Vennt Bot

import discord
from discord.ext import commands


start_time = time.time()

class Meta(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command(pass_context=True)
	async def ping(ctx, help='Pong!'):
		await ctx.send("pong!")



@client.command(pass_context=True)
async def uptime(ctx, help = "Get bot's lifespan"):
	await ctx.send("I've been up for " + str(datetime.timedelta(seconds = (time.time() - start_time))))


	