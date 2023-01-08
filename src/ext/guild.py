from typing import Optional
import discord
from discord.ext import commands
from discord.app_commands import describe, Range

from ..dev.bot_typing import MISSING

from ..dev.bot_abc import Sentinel, SentinelContext
from ..dev.ext_abc import SentinelCog, SentinelView, Paginator


class Guild(SentinelCog):
    def __init__(self, bot: Sentinel):
        super().__init__(bot, emoji="\N{Hut}")

    @commands.hybrid_group()
    async def channel(self, ctx: SentinelContext):
        pass

    @channel.command()
    async def create(
        self,
        ctx: SentinelContext,
        name: str,
        description: str = MISSING,
        slowmode: Range[int, 0, 21600] = MISSING,
        nsfw: bool = MISSING,
        required_role_1: Optional[discord.Role] = None,
        required_role_2: Optional[discord.Role] = None,
        required_role_3: Optional[discord.Role] = None,
    ):
        """Create a channel."""
        overwrites = {}
        if required_role_1:
            overwrites[required_role_1] = discord.PermissionOverwrite(view_channel=True)
        if required_role_2:
            overwrites[required_role_2] = discord.PermissionOverwrite(view_channel=True)
        if required_role_3:
            overwrites[required_role_3] = discord.PermissionOverwrite(view_channel=True)
        if overwrites:
            overwrites[ctx.guild.default_role] = discord.PermissionOverwrite(view_channel=False)

        await ctx.guild.create_text_channel(
            name=name,
            topic=description,
            slowmode_delay=slowmode,
            nsfw=nsfw,
            reason=f"Requested by {ctx.author} ({ctx.author.id})",
            overwrites=overwrites,
        )
        embed = ctx.embed(
            title="Channel Created \N{White Heavy Check Mark}",
            description=
                f"**Name:** {name}\n**Description:** {description}\n"
                f"**Slowmode:** {slowmode//3600}h{slowmode/3600//60}m{slowmode/3600/60//60}s\n"
                f"**NSFW:** {nsfw}\n"
                f"**Required Roles:** {', '.join([role.mention for role in [required_role_1, required_role_2, required_role_3] if role])}",
        ) 
        await ctx.send(embed=embed)


async def setup(bot: Sentinel):
    await bot.add_cog(Guild(bot))
