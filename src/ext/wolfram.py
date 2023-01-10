import discord
from discord.ext import commands

from ..sentinel import Sentinel, SentinelCog, SentinelContext
from config import WOLFRAM_API_URL
from env import WOLFRAM_APPID
from urllib import parse

class Wolfram(SentinelCog):
    def __init__(self, bot: Sentinel):
        super().__init__(bot)
    

    @commands.hybrid_group()
    async def wf(self, ctx: SentinelContext):
        pass

    @wf.command()
    @commands.cooldown(1, 90, commands.BucketType.user)
    async def ask(self, ctx: SentinelContext, *, question: str):
        question = parse.quote_plus(question)
        url = f"{WOLFRAM_API_URL}"
        url += f"?appid={WOLFRAM_APPID}&i={question}"
        response = await self.bot.session.get(url)
        response.raise_for_status()

        embed = ctx.embed(
            title=(await response.read()).decode("utf-8")
        )
        await ctx.send(embed=embed)


async def setup(bot: Sentinel):
    await bot.add_cog(Wolfram(bot))
        
    