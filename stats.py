# --- Josh Aaron Miller 2021
# --- Stat-based commands
import discord
from discord.ext import commands

import random, d20, math

import importlib
db = importlib.import_module("db")
meta = importlib.import_module("meta")
communication = importlib.import_module("communication")
logClass = importlib.import_module("logger")
logger = logClass.Logger("stats")

class Stats(commands.Cog):
    """Basic rolls, checks, and using resources."""

    def __init__(self, bot):
        self.bot = bot  

    @commands.command(pass_context=True)
    async def roll(self, ctx, *roll):
        """Basic dice rolling parser. For flow, roll 4d6kh3 (roll 4, keep highest 3). Comments can go in brackets."""
        rollstr = "".join(args[:]) # remove spaces
        logger.log("roll", rollstr)
        r = d20.roll(rollstr, allow_comments=True)
        await communication.send(ctx,str(r))
        return r.total