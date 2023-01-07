import discord
from discord.ext import commands
from typing import Union, TypeVar, Any

_Bot = Union[commands.Bot, commands.AutoShardedBot]
BotT = TypeVar("BotT", bound=_Bot, covariant=True)
MISSING: Any = discord.utils.MISSING
