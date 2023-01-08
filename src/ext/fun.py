from ..dev.bot_abc import Sentinel
from ..dev.ext_abc import SentinelCog, SentinelContext, SentinelView, Paginator

import discord
from discord.ext import commands


class Fun(SentinelCog):
    def __init__(self, bot: Sentinel):
        super().__init__(bot, emoji="\N{Party Popper}")


async def setup(bot: Sentinel):
    await bot.add_cog(Fun(bot))
