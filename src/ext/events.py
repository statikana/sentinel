from typing import Callable, no_type_check
import discord
from discord.ext import commands

from ..sentinel import SentinelContext, SentinelCog, Sentinel


class Events(SentinelCog, emoji="\N{ELECTRIC LIGHT BULB}", hidden=True):
    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        await self.bot.tree.sync(guild=discord.Object(guild.id))
        await self.bot.gdm.ensure_guild(guild.id)
        await self.bot.gcm.ensure_guild_config(guild.id)

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        # await self.bot.gdm.remove_guild(guild.id)
        # await self.bot.gcm.remove_guild_config(guild.id)
        pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        await self.process_autoresponse_functions(message)
    
    async def process_autoresponse_functions(self, message: discord.Message):
        if message.guild is None:
            return
        functions: list[str] = await self.bot.apg.fetchval("SELECT autoresponse_functions FROM guild_configs WHERE guild_id = $1", message.guild.id)
        if functions is None:
            await self.on_guild_join(message.guild)
            return
        for function in functions:
            name = function[:function.index(";")]
            code = str(function[function.index(";") + 1:]).strip().splitlines()
            await self.process_code(code, message)
            

    async def process_code(self, code: list[str], message: discord.Message):
        for line in code:
            args = line.split(" ")
            if args[0] == "send":
                await self.process_send(args, message)
            elif args[0] == "reply":
                await self.process_reply(args, message)
            elif args[0] == "if":
                await self.process_if(args, message)
    
    def replace_keywords(self, text: str, message: discord.Message) -> str:
        return text.format(
            message_content=message.content,
            message_id=message.id,
            message_link=message.jump_url,
            author_mention=message.author.mention,
            author_name=message.author.name,
            author_id=message.author.id,
            author_full=f"{message.author}",
            channel_mention=message.channel.mention, # type: ignore
            channel_name=message.channel.name, # type: ignore
            channel_id=message.channel.id,
            guild_name=message.guild.name, # type: ignore
            guild_id=message.guild.id, # type: ignore
        )
    
    async def process_send(self, args: list[str], message: discord.Message):
        channel_id = int(args[1])
        text = " ".join(args[2:])
        text = self.replace_keywords(text, message)
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return
        if isinstance(channel, discord.TextChannel) and message.guild and channel.permissions_for(message.guild.me).send_messages:
            await channel.send(text)
        
    async def process_reply(self, args: list[str], message: discord.Message):
        # unlike send, reply just replies to the message
        text = " ".join(args[1:])
        text = self.replace_keywords(text, message)
        if isinstance(message.channel, discord.TextChannel) and message.guild and message.channel.permissions_for(message.guild.me).send_messages:
            await message.reply(text)

    async def process_if(self, args: list[str], message: discord.Message):
        # if(message_content == hello there) send 123456789 hello world
        #                    ^^ the operator divides the statement into two parts
        line = " ".join(args)
        statement = line[line.index("(")+1:line.index(")")]
        post = line[line.index(")")+1:].strip()
        # message_content == hello there
        # VALID_STATEMENT_KEYWORDS = {
        #     "message_content",
        #     "message_id",
        #     "message_link",
        #     "author_mention",
        #     "author_name",
        #     "author_id",
        #     "author_full",
        #     "channel_mention",
        #     "channel_name",
        #     "channel_id",
        #     "guild_name",
        #     "guild_id"
        # }
        VALID_OPERATORS: dict[str, Callable[[str | int, str | int], bool]] = {
            "==": Operators.equals, # equal to
            "!=": Operators.not_equals, # not equal to
            ">>": Operators.greater_than, # greater than
            "<<": Operators.less_than, # less than
            ">=": Operators.greater_than_or_equal_to, # greater than or equal to
            "<=": Operators.less_than_or_equal_to, # less than or equal to
            "<>": Operators.in_, # in
            "!<>": Operators.not_in, # not in
        }
        for operator in VALID_OPERATORS.keys():
            if operator in statement:
                left, right = statement.split(operator)
                left = left.strip()
                right = right.strip()
                l = self.replace_keywords(left, message)
                r = self.replace_keywords(right, message)
                if VALID_OPERATORS[operator](l, r):
                    await self.process_code([post], message)
                    # if the statement is true, then process the post code
                    # by stacking the code onto the stack and processing it, we can stack if statements
                    # if(bad flag !<> message_conent) if(secret key <> message_content) send 123456789 hello world
                    #
                    #                               -> post code from first if
                    #                                                                 -> post code from second if
                    
    

class Operators:
    @staticmethod
    def equals(a: str | int, b : str | int):
        a, b = Operators._try_typecast(a, b)
        return str(a) == str(b)
    
    @staticmethod
    def not_equals(a: str | int, b : str | int):
        return not Operators.equals(a, b)
    
    @staticmethod
    def greater_than(a: str | int, b : str | int):
        a, b = Operators._try_typecast(a, b)
        if isinstance(a, str) and isinstance(b, str):
            return a > b
        elif isinstance(a, int) and isinstance(b, int):
            return a > b
        else:
            return False
    
    @staticmethod
    def less_than(a: str | int, b : str | int):
        return not Operators.greater_than(a, b)
    
    @staticmethod
    def greater_than_or_equal_to(a: str | int, b : str | int):
        return Operators.greater_than(a, b) or Operators.equals(a, b)
    
    @staticmethod
    def less_than_or_equal_to(a: str | int, b : str | int):
        return Operators.less_than(a, b) or Operators.equals(a, b)
    
    @staticmethod
    def in_(a: str | int, b : str | int):
        a, b = Operators._try_typecast(a, b)
        return str(a) in str(b)
    
    @staticmethod
    def not_in(a: str | int, b : str | int):
        return not Operators.in_(a, b)
    
    @staticmethod
    def _try_typecast(a: str | int, b: str | int) -> tuple[str | int, str | int]:
        try:
            a_ = int(a)
        except ValueError:
            a_ = str(a)
        try:
            b_ = int(b)
        except ValueError:
            b_ = str(b)
        return a_, b_
    

async def setup(bot):
    await bot.add_cog(Events(bot))
