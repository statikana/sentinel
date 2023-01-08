import time
from ..dev.ext_abc import SentinelCog, SentinelContext, SentinelView, Paginator
from ..dev.bot_abc import Sentinel

import discord
from discord.ext import commands
from discord.app_commands import describe


class Utility(SentinelCog):
    def __init__(self, bot: Sentinel):
        super().__init__(bot, emoji="\N{Input Symbol for Numbers}")

    @commands.hybrid_command()
    async def ping(self, ctx: SentinelContext):
        """Get the latency of the bot."""
        desc = f"\N{Shinto Shrine} **GateWay:** {round(self.bot.latency * 1000, 3)}ms\n"

        start = time.perf_counter()
        await self.bot.apg.fetch("SELECT 1")  # Dummy query
        desc += f"<:postgreSQL:1061456211897225309> **Database:** {round((time.perf_counter() - start) * 1000, 3)}ms\n"

        await self.bot.session.get("https://google.com")
        desc += f"\N{Globe with Meridians} **Web Client:** {round((time.perf_counter() - start) * 1000, 3)}ms\n"

        embed = ctx.embed(
            title="Pong! \N{Table Tennis Paddle and Ball}", description=desc
        )
        await ctx.send(embed=embed)


async def setup(bot: Sentinel):
    await bot.add_cog(Utility(bot))
