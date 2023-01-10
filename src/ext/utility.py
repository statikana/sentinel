import discord
from discord.ext import commands
import time

from ..sentinel import Sentinel, SentinelCog, SentinelContext
from config import WOLFRAM_API_URL
from env import WOLFRAM_APPID
from urllib import parse
import aiohttp

class Utility(SentinelCog):
    def __init__(self, bot: Sentinel):
        super().__init__(bot, "\N{Input Symbol for Numbers}")

    @commands.hybrid_command()
    async def ping(self, ctx: SentinelContext):
        """Get the latency of the bot."""
        description = (
            f"\N{Shinto Shrine} **Gateway:** {round(self.bot.latency * 1000, 3)}ms\n"
        )

        start = time.perf_counter()
        await self.bot.apg.fetch("SELECT 1")
        description += f"<:postgreSQL:1061456211897225309> **Database:** {round((time.perf_counter() - start) * 1000, 3)}ms\n"

        await self.bot.session.get("https://google.com")
        description += f"\N{Globe with Meridians} **API:** {round((time.perf_counter() - start) * 1000, 3)}ms\n"

        embed = ctx.embed(
            title="Pong! \N{Table Tennis Paddle and Ball}", description=description
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @commands.cooldown(1, 90, commands.BucketType.user)
    async def wolfram(self, ctx: SentinelContext, *, question: str):
        question = parse.quote_plus(question)
        url = f"{WOLFRAM_API_URL}"
        url += f"?appid={WOLFRAM_APPID}&i={question}"

        try:
            response = await self.bot.session.get(url)
            title = (await response.read()).decode("utf-8")
        except:
            title = "Something happened... try asking a better question?"

        embed = ctx.embed(title=title)
        await ctx.send(embed=embed)


async def setup(bot: Sentinel):
    await bot.add_cog(Utility(bot))
