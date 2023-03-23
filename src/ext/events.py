from typing import Callable, no_type_check
import discord
from discord.ext import commands

from ..sentinel import SentinelContext, SentinelCog, Sentinel, SentinelMessageCacheValue


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
        if message.author.bot or not message.guild:
            return
        guild_opt = await self.bot.gcm.get_autoresponse_enabled(message.guild.id)
        if guild_opt:
            discord.Interaction.message
            await AutoresponseManager(self.bot).process_autoresponse_functions(message)
        

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        return self.bot.deleted_message_cache.add(
            (message.guild.id, message.channel.id),
            SentinelMessageCacheValue(
                message_id=message.id,
                author_id=message.author.id,
                content=message.content,
                attachment_urls={attachment.url for attachment in message.attachments},
                timestamp=int(message.created_at.timestamp())
            ).dismantle()
        )
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild:
            return
        if before.content == after.content:
            return
        await self.on_message_delete(before)


class AutoresponseManager:
    def __init__(self, bot: Sentinel):
        self.bot = bot
        self.on_guild_join = Events(self.bot).on_guild_join

    async def process_autoresponse_functions(self, message: discord.Message):
        if message.guild is None:
            return
        functions: list[str] = await self.bot.apg.fetchval("SELECT autoresponse_functions FROM guild_configs WHERE guild_id = $1", message.guild.id)
        if functions is None:
            await self.on_guild_join(message.guild)
            return
        for function in functions:
            code = str(function[function.index(";") + 1:]).strip().splitlines()
            await self.process_code(code, message)
            

    async def process_code(self, code: list[str], message: discord.Message):
        await self.bot.ucm.ensure_user_config(message.author.id)
        user_opt = await self.bot.ucm.get_autoresponse_immune(message.author.id)
        if user_opt:
            return
        for line in code:
            args = line.split(" ")
            if args[0] == "send":
                await self.process_send(args, message)
            elif args[0] == "reply":
                await self.process_reply(args, message)
            elif args[0] == "if":
                await self.process_if(args, message)
            elif args[0] == "delete":
                await self.process_delete(args, message)
    
    async def replace_keywords(self, text: str, message: discord.Message) -> str:
        return text.format(**await get_message_context(message))
    
    async def process_send(self, args: list[str], message: discord.Message):
        channel_id = int(args[1])
        text = " ".join(args[2:])
        text = await self.replace_keywords(text, message)
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            return
        if isinstance(channel, discord.TextChannel) and message.guild and channel.permissions_for(message.guild.me).send_messages:
            await channel.send(text)
        
    async def process_reply(self, args: list[str], message: discord.Message):
        # unlike send, reply just replies to the message
        text = " ".join(args[1:])
        text = await self.replace_keywords(text, message)
        
        if isinstance(message.channel, discord.TextChannel) and message.guild and message.channel.permissions_for(message.guild.me).send_messages:
            await message.reply(text)
        
    async def process_delete(self, args: list[str], message: discord.Message):
        try:
            await message.delete()
        except discord.Forbidden:
            pass

    async def process_if(self, args: list[str], message: discord.Message):
        # if(message_content == hello there) send 123456789 hello world
        #                    ^^ the operator divides the statement into two parts
        line = " ".join(args)
        statement = line[line.index("(")+1:line.index(")")]
        post = line[line.index(")")+1:].strip()
        

        for operator in VALID_OPERATORS.keys():
            if operator in statement:
                left, right = statement.split(operator)
                left = left.strip()
                right = right.strip()
                l = await self.replace_keywords(left, message)
                r = await self.replace_keywords(right, message)
                try:
                    result = eval(l)
                    if result is not None:
                        l = result
                        try:
                            l = int(l)
                        except ValueError:
                            pass
                except SyntaxError:
                    pass
                    
                try:
                    result = eval(r)
                    if result is not None:
                        r = result
                        try:
                            r = int(r)
                        except ValueError:
                            pass
                except SyntaxError:
                    pass
                if VALID_OPERATORS[operator](l, r):
                    await self.process_code([post], message)
                    
    

class Operators:
    @staticmethod
    def equals(a: str | int, b : str | int):
        return str(a) == str(b)
    
    @staticmethod
    def not_equals(a: str | int, b : str | int):
        return not Operators.equals(a, b)
    
    @staticmethod
    def greater_than(a: str | int, b : str | int):
        a, b = Operators._try_typecast(a, b)
        if type(a) == type(b):
            return a > b # type: ignore
        return str(a) > str(b)
    
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
        return str(a) in str(b)
    
    @staticmethod
    def in_casefold(a: str | int, b : str | int):
        return str(a).casefold() in str(b).casefold()
    
    @staticmethod
    def not_in(a: str | int, b : str | int):
        return not Operators.in_(a, b)
    
    @staticmethod
    def not_in_casefold(a: str | int, b : str | int):
        return not Operators.in_casefold(a, b)
    
    @staticmethod
    def starts_with(a: str | int, b : str | int):
        return str(a).startswith(str(b))
    
    @staticmethod
    def starts_with_casefold(a: str | int, b : str | int):
        return str(a).casefold().startswith(str(b).casefold())
    
    @staticmethod
    def does_not_start_with(a: str | int, b : str | int):
        return not Operators.starts_with(a, b)
    
    @staticmethod
    def does_not_start_with_casefold(a: str | int, b : str | int):
        return not Operators.starts_with_casefold(a, b)
    
    @staticmethod
    def ends_with(a: str | int, b : str | int):
        return str(a).endswith(str(b))
    
    @staticmethod
    def ends_with_casefold(a: str | int, b : str | int):
        return str(a).casefold().endswith(str(b).casefold())

    @staticmethod
    def does_not_end_with(a: str | int, b : str | int):
        return not Operators.ends_with(a, b)
    
    @staticmethod
    def does_not_end_with_casefold(a: str | int, b : str | int):
        return not Operators.ends_with_casefold(a, b)
    
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


VALID_OPERATORS: dict[str, Callable[[str | int, str | int], bool]] = {
    "==": Operators.equals,
    "!=": Operators.not_equals,
    ">>": Operators.greater_than,
    "<<": Operators.less_than,
    ">=": Operators.greater_than_or_equal_to,
    "<=": Operators.less_than_or_equal_to,
    "<.>": Operators.in_,
    "<?>": Operators.in_casefold,
    "!<.>": Operators.not_in,
    "!<?>": Operators.not_in_casefold,
    ".>": Operators.starts_with,
    "?>": Operators.starts_with_casefold,
    "!.>": Operators.does_not_start_with,
    "!?>": Operators.does_not_start_with_casefold,
    ".<": Operators.ends_with,
    "?<": Operators.ends_with_casefold,
    "!.<": Operators.does_not_end_with,
    "!?<": Operators.does_not_end_with_casefold
}

async def get_message_context(message: discord.Message, get_last: bool = False) -> dict[str, int | str]:
    if get_last: 
        last_message = [m async for m in message.channel.history(limit=2)][1]
    else:
        last_message = message
    context: dict[str, int | str] = {
        "message_content": f"\"{message.content}\"",
        "message_id": message.id,
        "message_link": f"\"{message.jump_url}\"",
        "author_mention": f"\"{message.author.mention}\"",
        "author_name": f"\"{message.author.name}\"",
        "author_id": message.author.id,
        "author_full": f"\"{message.author}\"",
        "channel_mention": f"\"{message.channel.mention}\"", # type: ignore
        "channel_name": f"\"{message.channel.name}\"", # type: ignore
        "channel_id": message.channel.id,
        "guild_name": f"\"{message.guild.name}\"", # type: ignore
        "guild_id": message.guild.id, # type: ignore

        "last_message_content": f"\"{last_message.content}\"", # type: ignore
        "last_message_id": last_message.id, # type: ignore
        "last_message_link": f"\"{last_message.jump_url}\"", # type: ignore
        "last_author_mention": f"\"{last_message.author.mention}\"", # type: ignore
        "last_author_name": f"\"{last_message.author.name}\"", # type: ignore
        "last_author_id": last_message.author.id, # type: ignore
        "last_author_full": f"{last_message.author}", # type: ignore
    }
    return context


async def setup(bot):
    await bot.add_cog(Events(bot))
