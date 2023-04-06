import platform, random, requests, aiohttp, asyncio, json, os
import constants
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Context
from collections import defaultdict

from helpers import checks, db_manager

# Here we name the cog and create a new class for the cog.
class General(commands.Cog, name="general"):
    def __init__(self, bot):
        self.bot = bot
        self.ballot = []
        self.ballot_items = []
        self.count = 1 # see count.txt
        if os.path.exists('count.txt'):
            with open('count.txt', 'r') as file:
                self.count = int(file.read().strip())
        self.ballot_index = self.count - 1
        self.botversion = "0.14.0"
        self.abilityversion = "0.13.7"
        
        # load ability voting
        with open('ballot.txt', 'r') as file:
            file_contents = file.read()
            self.ballot = file_contents.split("\n\n")
            for item in self.ballot:
                self.ballot_items.append(item.split("\n")[0])
            bot.logger.info('Loaded %d abilities' % len(self.ballot))
        random.seed(42)
        random.shuffle(self.ballot) # random but ordered


    @commands.hybrid_command(
        name="help", description="List all commands the bot has loaded.",
    )
    @checks.not_blacklisted()
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    async def help(self, context: Context) -> None:
        prefix = self.bot.config["prefix"]
        embed = discord.Embed(
            title="Help", description="List of available commands:", color=0x9C84EF
        )
        for i in self.bot.cogs:
            cog = self.bot.get_cog(i.lower())
            commands = cog.get_commands()
            data = []
            for command in commands:
                description = command.description.partition("\n")[0]
                data.append(f"{prefix}{command.name} - {description}")
            help_text = "\n".join(data)
            embed.add_field(
                name=i.capitalize(), value=f"```{help_text}```", inline=False
            )
        await context.send(embed=embed)
        
    @checks.not_blacklisted()
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    async def ping(self, context: Context) -> None:
        """
        Check if the bot is alive.

        :param context: The hybrid command context.
        """
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"The bot latency is {round(self.bot.latency * 1000)}ms.",
            color=0x9C84EF,
        )
        await context.send(embed=embed)
        
        
    @commands.hybrid_command(
        name="sync",
        description="Synchonizes the slash commands.",
    )
    @app_commands.describe(scope="The scope of the sync. Can be `global` or `guild`")
    @checks.not_blacklisted()
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    async def sync(self, context: Context, scope: str) -> None:
        """
        Synchonizes the slash commands.

        :param context: The command context.
        :param scope: The scope of the sync. Can be `global` or `guild`.
        """

        if scope == "global":
            await context.bot.tree.sync()
            embed = discord.Embed(
                description="Slash commands have been globally synchronized.",
                color=0x9C84EF,
            )
            await context.send(embed=embed)
            return
        elif scope == "guild":
            context.bot.tree.copy_global_to(guild=context.guild)
            await context.bot.tree.sync(guild=context.guild)
            embed = discord.Embed(
                description="Slash commands have been synchronized in this guild.",
                color=0x9C84EF,
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description="The scope must be `global` or `guild`.", color=0xE02B2B
        )
        await context.send(embed=embed)

    @commands.hybrid_command(
        name="unsync",
        description="Unsynchonizes the slash commands.",
    )
    @app_commands.describe(
        scope="The scope of the sync. Can be `global`, `current_guild` or `guild`"
    )
    @checks.not_blacklisted()
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    async def unsync(self, context: Context, scope: str) -> None:
        """
        Unsynchonizes the slash commands.

        :param context: The command context.
        :param scope: The scope of the sync. Can be `global`, `current_guild` or `guild`.
        """

        if scope == "global":
            context.bot.tree.clear_commands(guild=None)
            await context.bot.tree.sync()
            embed = discord.Embed(
                description="Slash commands have been globally unsynchronized.",
                color=0x9C84EF,
            )
            await context.send(embed=embed)
            return
        elif scope == "guild":
            context.bot.tree.clear_commands(guild=context.guild)
            await context.bot.tree.sync(guild=context.guild)
            embed = discord.Embed(
                description="Slash commands have been unsynchronized in this guild.",
                color=0x9C84EF,
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description="The scope must be `global` or `guild`.", color=0xE02B2B
        )
        await context.send(embed=embed)


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user == self.bot.user:
            return
            
        votable_name = await db_manager.votable_name(reaction.message.id)
        vote = 0
        if reaction.emoji == constants.COOL or reaction.emoji == constants.CUT:
            if votable_name:
                original_vote = await db_manager.set_vote(user.name, votable_name, vote)
                self.bot.logger.info(f'{user.name} set vote {votable_name} from {original_vote} to {vote}')

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user == self.bot.user:
            return
            
        votable_name = await db_manager.votable_name(reaction.message.id)
        vote = 0
        if reaction.emoji == constants.COOL:
            vote = 1
        if reaction.emoji == constants.CUT:
            vote = -1
        if votable_name:
            original_vote = await db_manager.set_vote(user.name, votable_name, vote)
            self.bot.logger.info(f'{user.name} set vote {votable_name} from {original_vote} to {vote}')
            if original_vote == 1 and original_vote != vote:
                await reaction.message.remove_reaction(constants.COOL, user)
            if original_vote == -1  and original_vote != vote:
                await reaction.message.remove_reaction(constants.CUT, user)
    

    #@tasks.loop(minutes=1.0)
    @checks.not_blacklisted()
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    @commands.hybrid_command(
        name="vote",
        description="Start an ability vote.",
    )
    async def vote(self, context: Context) -> None:
        self.bot.logger.info("Ability vote")
        
        if self.ballot_index >= len(self.ballot):
            await context.send("That's it for Cool or Cut! Time to tally the votes!")
            return
            
        message = await context.send(f'**Cool or Cut #{self.count}**\n What do you think of this ability? Remember to vote on the concept rather than specific details, this ability may be re-balanced during implementation.\n```' + self.ballot[self.ballot_index] + '```')
        self.ballot_index += 1
        self.count += 1
        with open("count.txt", 'w') as f:
            f.write(str(self.count))
        await asyncio.sleep(0.5)
        await message.add_reaction(constants.COOL)
        await asyncio.sleep(0.5)
        await message.add_reaction(constants.CUT)
        
        query = self.ballot[self.ballot_index-1].split('\n')[0].strip()
        if await self.has_lookup(query):
            await context.send(f'**Warning!** Version {self.abilityversion} of Vennt has an ability of the same name:\n')
            await self.lookup(context, query)
        
        await db_manager.add_ability(message.id, query)
        
        
        
    @commands.hybrid_command(
        name="version",
        description="Get the version.",
    )
    @checks.not_blacklisted()
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    async def version(self, context: Context) -> None:
        """
        Get the bot's version and ability cache version.

        :param context: The hybrid command context.
        """
        await context.send(f'Bot version: {self.botversion}\nAbility cache: v. {self.abilityversion}')
        
    @commands.hybrid_command(
        name="leaderboard",
        description="Show the leaderboard.",
    )
    @checks.not_blacklisted()
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    async def leaderboard(self, context: Context) -> None:
        """
        Show Cool or Cut leaderboards.

        :param context: The hybrid command context.
        """
        await context.send(await self.get_leaderboard())
        
        
    @commands.hybrid_command(
        name="voteresults",
        description="Get the vote results.",
    )
    @checks.not_blacklisted()
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    async def voteresults(self, context: Context) -> None:
        """
        Show Cool or Cut vote results.

        :param context: The hybrid command context.
        """
        await context.send(await self.get_vote_results())

    async def get_vote_results(self) -> str:
        vote_dict = await db_manager.get_votes()
        
        key_vals = {}
        for key, val in vote_dict.items():
            key_vals[key] = val['cool'] - val['cut'] 
        ordered_ability_names = dict(sorted(key_vals.items(), key = lambda x: x[1], reverse = True)).keys()
        
        response = "The votes are in!:\n"
        for key in ordered_ability_names:
            response += f'{key}: **{vote_dict[key]["cool"] - vote_dict[key]["cut"]}**   (+{vote_dict[key]["cool"]}, -{vote_dict[key]["cut"]})' + "\n"
        return response

    async def get_leaderboard(self) -> str:
        vote_dict = await db_manager.get_leaderboard()
        
        key_vals = {}
        for key, val in vote_dict.items():
            key_vals[key] = min(val['cool'], val['cut'])
        ordered_players = dict(sorted(key_vals.items(), key = lambda x: x[1], reverse = True)).keys()
        response = "Leaderboard:\n"
        for key in ordered_players:
            points = min(vote_dict[key]["cool"], vote_dict[key]["cut"])
            response += f'{key}: {points} point{"" if points == 1 else "s"} ({vote_dict[key]["cool"]} {constants.COOL}, {vote_dict[key]["cut"]} {constants.CUT})' + "\n"
        return response


    async def has_lookup(self, query):
        # This will prevent your bot from stopping everything when doing a web request - see: https://discordpy.readthedocs.io/en/stable/faq.html#how-do-i-make-a-web-request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                constants.SERVER_URL + 'lookup_ability?auth_token=%s&name=%s' % (self.bot.auth_token, query)
            ) as request:
                if request.status == 200:
                    response = await request.json(content_type="text/html")
                    return response["success"] and response["value"] != ''
            return False


    @commands.hybrid_command(
            name="lookup",
            description="Query the Vennt wiki for an ability.",)
    @checks.not_blacklisted()
    @app_commands.describe(query="The ability name or partial match to search for")
    @app_commands.describe(query="The ability name to query.")
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    async def lookup(self, context: Context, query: str) -> None:
        """
        Get the info of an ability.

        :param context: The hybrid command context.
        :param query: The ability name to look up.
        """
        
        # This will prevent your bot from stopping everything when doing a web request - see: https://discordpy.readthedocs.io/en/stable/faq.html#how-do-i-make-a-web-request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                constants.SERVER_URL + 'lookup_ability?auth_token=%s&name=%s' % (self.bot.auth_token, query)
            ) as request:
                if request.status == 200:
                    response = await request.json(content_type="text/html")
                    self.bot.logger.info("Lookup:" + str(response))
                    if not response["success"]:
                        await context.send(f'`[{response["info"]}]` I couldn\'t find any ability matching `{query}` in version {self.abilityversion} of the ability cache.')
                    else:
                        msg = "".join(response["value"])
                        if msg:
                            await context.send("```\n" + msg + "```")
                        else:
                            await context.send(f'`No such ability` I couldn\'t find any ability matching `{query}` in version {self.abilityversion} of the ability cache.')


# And then we finally add the cog to the bot so that it can load, unload, reload and use it's content.
async def setup(bot):
    general = General(bot)
    await bot.add_cog(general)
    #await general.vote.start()
