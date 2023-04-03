import platform, random, requests, aiohttp, asyncio
import constants
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks

# Here we name the cog and create a new class for the cog.
class General(commands.Cog, name="general"):
    def __init__(self, bot):
        self.bot = bot
        self.voting_channel = self.bot.get_channel(1069106533767598152)
        self.ballot_messages = {} # message : {up: [people], down: [people]}
        self.ballot = []
        self.ballot_index = 0
        # load ability voting
        with open('ballot.txt', 'r') as file:
            file_contents = file.read()
            self.ballot = file_contents.split("\n\n")
            print('Loaded %d abilities' % len(self.ballot))


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
        
    
    @checks.is_owner()
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    async def vote(self, context: Context) -> None:
        if self.ballot_index == 0:
            await self.voting_channel.send(f'Welcome to Cool or Cut! The channel for voting on new abilities. For each ability, you decide whether we keep it {constants.COOL} or cut it {constants.CUT}! Everyone will get special rewards at the end based on how many times they used their less-frequent vote. So if you vote 7 {constants.COOL} and 4 {constants.CUT}, you will get 4 points toward the special rewards! Have fun!')
            await asyncio.sleep(5) #test
        
        self.bot.logger.info("Ability vote loop")
        if self.ballot_index >= len(self.ballot):
            await self.voting_channel.send("That's it for Cool or Cut! Time to tally the votes!")
            return
            
        message = await self.voting_channel.send(f'**Cool or Cut #{self.ballot_index + 1}**\n What do you think of this ability?\n' + self.ballot[self.ballot_index])
        self.ballot_index += 1
        await asyncio.sleep(0.5)
        await message.add_reaction(constants.COOL)
        await asyncio.sleep(0.5)
        await message.add_reaction(constants.CUT)
        self.ballot_messages[message] = {constants.COOL: [], constants.CUT: []}
        
        
    @checks.not_blacklisted()
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    async def version(self, context: Context) -> None:
        """
        Get the bot's version and ability cache version.

        :param context: The hybrid command context.
        """
        await ctx.send("Bot version: 0.14.0\nAbility cache: v. 0.13.7")
        
    @checks.not_blacklisted()
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    async def leaderboard(self, context: Context) -> None:
        """
        Show Cool or Cut leaderboards.

        :param context: The hybrid command context.
        """
        await ctx.send(get_leaderboard())
        
        
    @checks.not_blacklisted()
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    async def voteresults(self, context: Context) -> None:
        """
        Show Cool or Cut vote results.

        :param context: The hybrid command context.
        """
        await ctx.send(get_vote_results())


    @commands.hybrid_command(
        name="lookup",
        description="Query the Vennt wiki for an ability.",
    )
    @checks.not_blacklisted()
    @app_commands.describe(query="The ability name to query.")
    @app_commands.guilds(discord.Object(id=constants.GUILD_ID))
    async def lookup(self, context: Context, *, query: str) -> None:
        """
        Get the info of an ability.

        :param context: The hybrid command context.
        :param query: The ability name to look up.
        """
        
        renew_auth_once() # make sure we're logged in
        response = requests.get(constants.SERVER_URL + 'lookup_ability?auth_token=%s&name=%s' % (self.bot.auth_token, query), verify=False)
        response = json.loads(response.text)
        print(response)
        if not response["success"]:
            await ctx.send(response["info"])
        else:
            msg = "".join(response["value"])
            if msg:
                await ctx.send("```" + msg + "```")
            else:
                await ctx.send("No ability found.")
                
                
    def get_vote_results():
        results_points = {}
        results_str = {}
        for msg in self.ballot_messages:
            content = msg.content
            ability_name = content.split('\n')[2]
            cool = len(self.ballot_messages[msg][constants.COOL])
            cut = len(self.ballot_messages[msg][constants.CUT])
            results_points[ability_name] = cool - cut
            results_str[ability_name] = f'{ability_name}: {cool - cut} (+{cool}, -{cut})'
        
        response = ""
        sorted_results = dict(sorted(results_points.items(), key=lambda x: x[1], reverse=True))
        for key, val in sorted_results.items():
            response += results_str[key] + "\n"
        return response

    def get_leaderboard():
        cools = defaultdict(int)
        cuts = defaultdict(int)
        for msg in self.ballot_messages:
            for user in self.ballot_messages[msg][constants.COOL]:
                cools[user] += 1
            for user in self.ballot_messages[msg][constants.CUT]:
                cuts[user] += 1
        
        response = ""
        all_users = list(cools.keys()) + list(cuts.keys())
        for user in all_users:
            cool = cools[user]
            cut = cuts[user]
            response += f'{user} has {abs(cool - cut)} points! ({cool} {constants.COOL}, {cut} {constants.CUT})'
        
        return response


# And then we finally add the cog to the bot so that it can load, unload, reload and use it's content.
async def setup(bot):
    general = General(bot)
    await bot.add_cog(general)
