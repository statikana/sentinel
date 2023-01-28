import logging
from typing import Any
import discord
from discord.ext import commands
from discord.app_commands import errors as app_errors
from ..sentinel import Sentinel, SentinelCog, SentinelContext, SentinelView, SentinelErrors


class Errors(SentinelCog):
    def __init__(self, bot: Sentinel):
        super().__init__(bot, emoji="\N{No Entry Sign}", hidden=True)
        self.bot.tree.on_error = self.on_tree_error
        self.command_error_dict = {
            # CommandError
            commands.CommandError: "An error occurred while executing the command.",
            commands.CommandNotFound: "I could not find that command.",
            commands.DisabledCommand: "That command is disabled.",
            commands.CommandOnCooldown: "This command is on cooldown.",

            # CheckFailure
            commands.CheckFailure: "You do not have the required permissions to run this command.",
            commands.NoPrivateMessage: "That command cannot be used in private messages.",
            commands.NotOwner: "You are not the owner of this bot.",
            commands.MissingPermissions: "You are missing the required permissions to run this command.",
            commands.BotMissingPermissions: "I am missing the required permissions to execute this command.",
            commands.PrivateMessageOnly: "This command can only be used in private messages.",

            # UserInputError
            commands.UserInputError: "An error occurred while parsing your input.",
            commands.MissingRequiredArgument: "You are missing a required argument.",
            commands.BadArgument: "You provided an invalid argument.",
            commands.TooManyArguments: "You provided too many arguments.",
            commands.ArgumentParsingError: "An error occurred while parsing your arguments.",
            commands.UnexpectedQuoteError: "An unexpected quote was found while parsing your arguments.",
            commands.InvalidEndOfQuotedStringError: "An invalid end of quoted string was found while parsing your arguments.",
            commands.ExpectedClosingQuoteError: "An expected closing quote was found while parsing your arguments.",
            commands.BadUnionArgument: "You provided an invalid argument for a Union type.",
            commands.BadBoolArgument: "You provided an invalid boolean argument.",
            commands.BadColourArgument: "You provided an invalid color argument.",
            commands.BadInviteArgument: "You provided an invalid invite argument.",
            commands.BadFlagArgument: "You provided an invalid flag argument.",
            commands.BadLiteralArgument: "You provided an invalid literal argument.",
            commands.ObjectNotFound: "I could not find that object.",
        }
    
    @commands.Cog.listener()
    async def on_error(self, event_method: str, /, *args: Any, **kwargs: Any):
        logging.error(f"An error occurred in {event_method}: {args} {kwargs}")
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx: SentinelContext, error: commands.CommandError):
        if isinstance(error, commands.CommandInvokeError):
            description = f"An error occurred while executing the command:\n```py\n{error.original}```"
            embed = ctx.embed(title="Command Error", description=description, color=discord.Color.red())
            embed.set_footer(text=f"Is this a bug? Report it to the developers with /bug")
            await ctx.send(embed=embed, ephemeral=True)
        elif self.command_error_dict.get(type(error), None):
            embed = ctx.embed(title=f"**{type(error).__name__}**", description=self.command_error_dict[type(error)], color=discord.Color.red())
            embed.set_footer(text=f"Is this a bug? Report it to the developers with /bug")
            await ctx.send(embed=embed, ephemeral=True)
        else:
            embed = ctx.embed(title=f"**{type(error).__name__}**", description=f"An error occurred while executing the command:\n```py\n{error}```", color=discord.Color.red())
            embed.set_footer(text=f"Is this a bug? Report it to the developers with /bug")
            await ctx.send(embed=embed, ephemeral=True)
        if ctx.command is not None:
            ... # Send help command for the command that errored


    async def on_tree_error(self, itx: discord.Interaction, error: discord.app_commands.AppCommandError, /) -> None:
        logging.error(f"An error occurred in {itx.command}: {error}")

async def setup(bot: Sentinel):
    await bot.add_cog(Errors(bot))
    