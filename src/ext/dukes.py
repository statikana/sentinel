import discord
from discord.ext import commands
from discord.app_commands import describe, Range

from ..sentinel import Sentinel, SentinelCog, SentinelContext, SentinelView, SentinelPool
from ..command_util import ParamDefaults
from ..db_managers import DukesManager


class Dukes(SentinelCog):
    """
    Sentinel's very own global currency system! You can earn by levelling up, logging in daily, gambling, and many more ways!"""
    def __init__(self, bot: Sentinel):
        self.dkm = DukesManager(bot.apg)
        super().__init__(bot, emoji="\N{Banknote with Dollar Sign}")
    
    @commands.hybrid_command()
    async def balance(self, ctx: SentinelContext, member: discord.Member = ParamDefaults.member):
        balance = await self.dkm.get_balance(member.id)
        embed = ctx.embed(
            title=f"`{member}`'s Balance",
            description=f"\N{Coin}{balance}"
        )
        await ctx.send(embed=embed)


async def setup(bot: Sentinel):
    await bot.add_cog(Dukes(bot))
