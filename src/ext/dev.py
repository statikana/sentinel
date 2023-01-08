from typing import Optional
import discord
from discord.ext import commands
from discord.app_commands import describe, Range

from ..dev.bot_util  import load_extensions

from ..dev.bot_typing import MISSING
from ..dev.bot_abc import Sentinel, SentinelContext
from ..dev.ext_abc import SentinelCog, SentinelView, Paginator


class Dev(SentinelCog):
    def __init__(self, bot: Sentinel):
        super().__init__(bot, guild_ids={871913539936329768})
    

    @commands.command()
    async def test(self, ctx: SentinelContext):
        await ctx.send("test")
    

    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx: SentinelContext, guild_id: Optional[int]):
        await self.bot.tree.sync(guild=discord.Object(id=guild_id) if guild_id else None)
        embed = ctx.embed(
            title="Synced \N{White Heavy Check Mark}",
            description=f"Synced {guild_id or 'all guild'}'s commands",
        )

    
    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx: SentinelContext):
        exts, utils = await load_extensions(self.bot)
        desc = "\n".join((f"**{ex}**" for ex in exts))
        desc += "\n" + "\n".join((f"*{ut}*" for ut in utils))
        embed = ctx.embed(
            title="Reloaded \N{White Heavy Check Mark}",
            description=desc,
        )
        await ctx.send(embed=embed)


async def setup(bot: Sentinel):
    await bot.add_cog(Dev(bot))