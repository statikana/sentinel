import logging
from typing import Any
import discord
from discord.ext import commands
from ..sentinel import Sentinel, SentinelCog, SentinelContext, SentinelErrors
from config import CATCH_COMMAND_ERRORS


class Errors(SentinelCog):
    def __init__(self, bot: Sentinel):
        super().__init__(bot, emoji="\N{No Entry Sign}", hidden=True)
        self.bot.tree.on_error = self.on_tree_error

    @commands.Cog.listener()
    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any):
        logging.error(f"An error occurred in {event_method}: {args} {kwargs}")

    @commands.Cog.listener()
    async def on_command_error(
        self, ctx: SentinelContext, error: commands.CommandError
    ):
        if not CATCH_COMMAND_ERRORS:
            raise error
        if isinstance(error, commands.CommandInvokeError):
            description = f"An error occurred while executing the command:\n```\n{error.original}```"
            embed = ctx.embed(
                title="Command Error",
                description=description,
                color=discord.Color.red(),
            )
            embed.set_footer(
                text=f"Is this a bug? Report it to the developers with /bug"
            )
            await ctx.send(embed=embed, ephemeral=True)
        else:
            embed = ctx.embed(
                title=f"**{type(error).__name__}**",
                description=f"An error occurred while executing the command:\n**```\n{error}```**",
                color=discord.Color.red(),
            )
            embed.set_footer(
                text=f"Is this a bug? Report it to the developers with /bug"
            )
            await ctx.send(embed=embed, ephemeral=True)
        if ctx.command is not None:
            ...  # Send help command for the command that errored

    async def on_tree_error(
        self, itx: discord.Interaction, error: discord.app_commands.AppCommandError, /
    ) -> None:
        if not CATCH_COMMAND_ERRORS:
            raise error
        logging.error(f"An error occurred in {itx.command}: {error}")


async def setup(bot: Sentinel):
    await bot.add_cog(Errors(bot))
