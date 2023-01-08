import asyncpg
import discord
from discord.ext import commands
from typing import Union, TypeVar, Any

_Bot = Union[commands.Bot, commands.AutoShardedBot]
BotT = TypeVar("BotT", bound=_Bot)
MISSING: Any = discord.utils.MISSING
