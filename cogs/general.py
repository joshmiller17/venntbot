import platform, random, requests, aiohttp, asyncio
import constants
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ext.commands import Context
from collections import defaultdict

from helpers import checks


# Here we name the cog and create a new class for the cog.
class General(commands.Cog, name="general"):
    def __init__(self, bot):
        self.bot = bot
        self.ballot_messages = {} # message : {up: [people], down: [people]}
        self.ballot = []
        self.ballot_index = 0
        # load ability voting
        with open('ballot.txt', 'r') as file:
            file_contents = file.read()
            self.ballot = file_contents.split("\n\n")
            bot.logger.info('Loaded %d abilities' % len(self.ballot))


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
        if reaction.message in self.ballot_messages:
            if reaction.emoji == constants.COOL:
                self.ballot_messages[reaction.message][constants.COOL].append(user)
                if user in self.ballot_messages[reaction.message][constants.CUT]:
                    self.ballot_messages[reaction.message][constants.CUT].remove(user)
                    await reaction.message.remove_reaction(constants.CUT, user)
            if reaction.emoji == constants.CUT:
                self.ballot_messages[reaction.message][constants.CUT].append(user)
                if user in self.ballot_messages[reaction.message][constants.COOL]:
                    self.ballot_messages[reaction.message][constants.COOL].remove(user)
                    await reaction.message.remove_reaction(constants.COOL, user)
            with open("vote_results.txt", "w") as file:
                file.write(self.get_vote_results())
    

    #@tasks.loop(minutes=1.0)
    @checks.not_blacklisted()
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    @commands.hybrid_command(
        name="vote",
        description="Start an ability vote.",
    )
    async def vote(self, context: Context) -> None:
        self.bot.logger.info("Ability vote")
        if self.ballot_index == 0:
            await context.send(f'Welcome to Cool or Cut! The channel for voting on new abilities. For each ability, you decide whether we keep it {constants.COOL} or cut it {constants.CUT}! Everyone will get special rewards at the end based on how many times they used their less-frequent vote. So if you vote 7 {constants.COOL} and 4 {constants.CUT}, you will get 4 points toward the special rewards! Have fun!')
            await asyncio.sleep(5) #test
        
        if self.ballot_index >= len(self.ballot):
            await context.send("That's it for Cool or Cut! Time to tally the votes!")
            return
            
        message = await context.send(f'**Cool or Cut #{self.ballot_index + 1}**\n What do you think of this ability?\n```' + self.ballot[self.ballot_index] + '```')
        self.ballot_index += 1
        await asyncio.sleep(0.5)
        await message.add_reaction(constants.COOL)
        await asyncio.sleep(0.5)
        await message.add_reaction(constants.CUT)
        self.ballot_messages[message] = {constants.COOL: [], constants.CUT: []}
        
        
        
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
        await context.send("Bot version: 0.14.0\nAbility cache: v. 0.13.7")
        
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
        await context.send(self.get_leaderboard())
        
        
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
        await context.send(self.get_vote_results())


    @commands.hybrid_command(
        name="lookup",
        description="Query the Vennt wiki for an ability.",
    )
    @app_commands.describe(
        query="The ability name or partial match to search for"
    )
    @checks.not_blacklisted()
    @app_commands.describe(query="The ability name to query.")
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    async def lookup(self, context: Context, query: str) -> None:
        """
        Get the info of an ability.

        :param context: The hybrid command context.
        :param query: The ability name to look up.
        """
        
        renew_auth_once() # make sure we're logged in
        # This will prevent your bot from stopping everything when doing a web request - see: https://discordpy.readthedocs.io/en/stable/faq.html#how-do-i-make-a-web-request
        async with aiohttp.ClientSession() as session:
            async with session.get(
                constants.SERVER_URL + 'lookup_ability?auth_token=%s&name=%s' % (self.bot.auth_token, query)
            ) as request:
                if request.status == 200:
                    data = await request.json(
                        content_type="application/javascript"
                    )  # For some reason the returned content is of type JavaScript
                    response = json.loads(data)
                    self.bot.logger.info(data)
                    self.bot.logger.info(response)
                    if not response["success"]:
                        await context.send(response["info"])
                    else:
                        msg = "".join(response["value"])
                        if msg:
                            await context.send("```" + msg + "```")
                        else:
                            await context.send("No ability found.")
                
                
    def get_vote_results(self):
        results_points = {}
        results_str = {}
        for msg in self.ballot_messages:
            content = msg.content
            ability_name = content.split('\n')[2]
            cool = len(self.ballot_messages[msg][constants.COOL])
            cut = len(self.ballot_messages[msg][constants.CUT])
            results_points[ability_name] = cool - cut
            results_str[ability_name] = f'{ability_name}: {cool - cut} (+{cool}, -{cut})'
        
        response = "The votes are in!:\n"
        sorted_results = dict(sorted(results_points.items(), key=lambda x: x[1], reverse=True))
        for key, val in sorted_results.items():
            response += results_str[key] + "\n"
        return response

    def get_leaderboard(self):
        cools = defaultdict(int)
        cuts = defaultdict(int)
        for msg in self.ballot_messages:
            for user in self.ballot_messages[msg][constants.COOL]:
                cools[user] += 1
            for user in self.ballot_messages[msg][constants.CUT]:
                cuts[user] += 1
        
        response = "Leaderboard:\n"
        all_users = list(cools.keys()) + list(cuts.keys())
        for user in all_users:
            cool = cools[user]
            cut = cuts[user]
            response += f'{user} has {abs(cool - cut)} point{"s" if abs(cool - cut) == 1 else ""}! ({cool} {constants.COOL}, {cut} {constants.CUT})'
        
        return response


# And then we finally add the cog to the bot so that it can load, unload, reload and use it's content.
async def setup(bot):
    general = General(bot)
    await bot.add_cog(general)
    #await general.vote.start()
