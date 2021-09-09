# --- Josh Aaron Miller 2021
# --- meta/misc commands for Discord Vennt Bot

import discord
from discord.ext import commands

import time, datetime, json, random, requests

import importlib
db = importlib.import_module("db")
communication = importlib.import_module("communication")
logClass = importlib.import_module("logger")
logger = logClass.Logger("meta")

    
def save_macros(macros):
    with open("macros.json", 'w') as f:
        json.dump(macros, f, indent=4)
    
class Meta(commands.Cog):
    """Miscellaneous and meta commands."""

    def __init__(self, bot):
        self.bot = bot
           
        try:
            with open("macros.json") as f:
                self.macros = json.load(f)
        except:
            logger.warn("__init__", "Unable to open macros.json, starting from scratch.")
            self.macros = []

    @commands.command(pass_context=True)
    async def ping(self, ctx):
        """Pong!"""
        await communication.send(ctx,"Pong!")
    

    @commands.command(pass_context=True, aliases=['setalias'])
    async def setmacro(self, ctx, macro, *command):
        """Make a shortcut for a commonly used command. Split new commands using "/". Use "{}" to specify an ad lib to be filled in when the macro is used. Example: $setmacro pingandsay $ping / $say {}"""
        who = str(ctx.message.author)
        found = False
        new_cmd = " ".join(command[:])
        new_cmd = new_cmd.split(' / ')
        if len(new_cmd) > 10:
            await ctx.message.add_reaction(db.NOT_OK)
            await communication.send(ctx,"Macros are limited to 10 commands.")
            return
        for cmd in new_cmd:
            if cmd.startswith("$alias") or cmd.startswith("$macro"):
                await ctx.message.add_reaction(db.NOT_OK)
                await communication.send(ctx,"To avoid infinite loops, you cannot define a macro which calls another macro.")
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
        await communication.send(ctx,macro + " saved.")
        
    @commands.command(pass_context=True, aliases=['alias'])
    async def macro(self, ctx, macro, *adlibs):
        """Use a shortcut you set with $setmacro. If you gave your macro ad libs, put them after."""
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
    async def mymacros(self, ctx, macro=None):
        """See the macros you set, or try $mymacros macro-name to see the details of a particular macro."""
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
                            await communication.send(ctx,key + ": " + " / ".join(val))
                            return
                    else:
                        macros.append("{0} -- {1} command(s)".format(key, len(val)))
        if macros != []:
            await communication.send(ctx,ret.format("\n".join(macros)))
        else:
            if macro is not None:
                await communication.send(ctx,"No macro found named " + macro)
            else:
                await communication.send(ctx,"No macros saved.")
            
            
    @commands.command(pass_context=True)
    async def say(self, ctx, *msg):
        """Say something as your character. For use with macros."""
        who = str(ctx.message.author)
        character = get_character_name(who)
        await communication.send(ctx,"**{0}**: {1}".format(character, " ".join(msg)))
    
    @commands.command(pass_context=True, aliases=['me'])
    async def emote(self, ctx, *msg):
        """Do something as your character. For use with macros."""
        who = str(ctx.message.author)
        character = get_character_name(who)
        await communication.send(ctx,"*{0} {1}*".format(character, " ".join(msg)))

    @commands.command(pass_context=True)
    async def uptime(self, ctx):
        """Get bot's lifespan"""
        await communication.send(ctx,"I've been up for " + str(datetime.timedelta(seconds = (time.time() - START_TIME))))
        

    @commands.command(pass_context=True, aliases=['whatis'])
    async def lookup(self, ctx, *query):
        """Get the info of an ability."""
        response = requests.get("https://topazgryphon.org:3004/" + 'lookup_ability?auth_token=%s&name=%s' % (self.bot.auth_token," ".join(query[:])), verify=False)
        response = json.loads(response.text)
        print(response)
        if not response["success"]:
            if response["info"] == "Authentication invalid":
                await self.bot.renew_auth(None)
                print("Authentication renewed!")
                self.lookup(ctx, *query)
            else:
                await communication.send(ctx, response["info"])
        else:
            msg = "".join(response["value"])
            if msg:
                await communication.send(ctx, "```" + msg + "```")
            else:
                await communication.send(ctx, "No ability found.")