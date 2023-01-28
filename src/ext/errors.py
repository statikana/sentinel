from typing import Any
import discord
from discord.ext import commands

from ..sentinel import Sentinel, SentinelCog, SentinelContext, SentinelView


class Errors(SentinelCog):
    def __init__(self, bot: Sentinel):
        self.bot.tree.on_error = self.on_tree_error
        super().__init__(bot, emoji="\N{No Entry Sign}", hidden=True)

    @commands.Cog.listener()
    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any):
        pass

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: SentinelContext, error: commands.CommandError
    ):
        pass

    async def on_tree_error(
        self, itx: discord.Interaction, error: discord.app_commands.AppCommandError, /
    ) -> None:
        pass
