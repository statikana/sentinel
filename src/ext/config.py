import re
from typing import Iterator, TypeVar
import discord
from discord.ext import commands

from ..command_util import fuzz, Paginator, dev

from ..sentinel import Sentinel, SentinelContext, SentinelCog, SentinelView
from .events import VALID_OPERATORS


T = TypeVar("T")


class Config(SentinelCog, emoji="\N{Gear}"):
    @commands.hybrid_group()
    async def config(self, ctx: SentinelContext):
        """Configuration commands"""
        pass

    @config.group()
    async def me(self, ctx: SentinelContext):
        """Commands for configuring your own settings"""
        pass
    
    # @me.group(name="get")
    # async def me_get(self, ctx: SentinelContext):
    #     """Commands for getting personal configuration settings"""
    #     pass

    @me.command()
    async def get_autoresponse_immune(self, ctx: SentinelContext):
        """Gets whether or not you are immune to autoresponses"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.ucm.ensure_user_config(ctx.author.id)
        status = await self.bot.ucm.get_autoresponse_immune(ctx.author.id)
        embed = ctx.embed(
            title=f"Autoresponse Immunity: `{status}`",
        )
        if await self.bot.gcm.get_allow_autoresponse_immunity(ctx.guild.id):
            embed.description = "You can toggle this with `/config me set_autoresponse_immune <true/false>`"
        else:
            embed.description = "However, this guild has disabled autoresponse immunity. Please contact a server administrator to enable it, if you wish to use it."
        await ctx.send(embed=embed)
        

    # @me.group(name="set")
    # async def me_set(self, ctx: SentinelContext):
    #     """Commands for setting personal configuration settings"""
    #     pass

    @me.command()
    async def set_autoresponse_immune(self, ctx: SentinelContext, status: bool):
        """Sets whether or not you are immune to autoresponses"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.ucm.ensure_user_config(ctx.author.id)
        # still allow the user to change the setting, though tell them it will have no effect if the guild has disabled it
        await self.bot.ucm.set_autoresponse_immune(ctx.author.id, status)
        embed = ctx.embed(
            title=f"Autoresponse Immunity: `{status}`",
        )
        if await self.bot.gcm.get_allow_autoresponse_immunity(ctx.guild.id):
            embed.description = "You can toggle this with `/config me set autoresponse_immune <true/false>`"
        else:
            embed.description = "However, this guild has disabled autoresponse immunity. Please contact a server administrator to enable it, if you wish to use it."
        await ctx.send(embed=embed)
    

    @config.group()
    async def guild(self, ctx: SentinelContext):
        """Commands for configuring guild settings"""
        pass

    @guild.command()
    @commands.guild_only()
    async def get_prefix(self, ctx: SentinelContext):
        """Gets the guild's prefix"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        prefix = await self.bot.gcm.get_prefix(ctx.guild.id)
        embed = ctx.embed(
            title=f"Prefix: `{prefix}`",
        )
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    async def get_autoresponse_enabled(self, ctx: SentinelContext):
        """Gets whether or not autoresponses are enabled"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        status = await self.bot.gcm.get_autoresponse_enabled(ctx.guild.id)
        embed = ctx.embed(
            title=f"Autoresponses: `{status}`",
        )
        embed.description = "Members can change autoresponse immunity using `/config me set_autoresponse_immune <true/false>`"
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    async def get_allow_autoresponse_immunity(self, ctx: SentinelContext):
        """Gets whether or not autoresponse immunity is enabled"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        status = await self.bot.gcm.get_allow_autoresponse_immunity(ctx.guild.id)
        embed = ctx.embed(
            title=f"Autoresponse Immunity: `{status}`",
        )
        if status:
            embed.description = "Users can toggle this with `/config guild set_allow_autoresponse_immunity <true/false>`"
        else:
            embed.description = "Users' autoresponse immunity can be changed, though it will have no effect."
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    async def get_welcome_channel(self, ctx: SentinelContext):
        """Gets the guild's welcome channel"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        channel_id = await self.bot.gcm.get_welcome_channel_id(ctx.guild.id)
        if channel_id is None:
            embed = ctx.embed(
                title="Welcome Channel: `None`",
            )
        else:
            channel = await ctx.guild.get_channel(channel_id) # type: ignore # Command is guild only
            embed = ctx.embed(
                title=f"Welcome Channel: `{channel or 'None'}`",
            )
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    async def get_welcome_message_title(self, ctx: SentinelContext):
        """Gets the guild's welcome message title"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        title = await self.bot.gcm.get_welcome_message_title(ctx.guild.id)
        embed = ctx.embed(
            title=f"Welcome Message Title: `{title}`",
        )
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    async def get_welcome_message_body(self, ctx: SentinelContext):
        """Gets the guild's welcome message body"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        body = await self.bot.gcm.get_welcome_message_body(ctx.guild.id)
        embed = ctx.embed(
            title=f"Welcome Message Body",
            description=body
        )
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    async def get_welcome_message_enabled(self, ctx: SentinelContext):
        """Gets whether or not welcome messages are enabled"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        status = await self.bot.gcm.get_welcome_message_enabled(ctx.guild.id)
        embed = ctx.embed(
            title=f"Welcome Messages: `{status}`",
        )
        await ctx.send(embed=embed)
    
    @guild.command()
    @commands.guild_only()
    async def get_leave_channel(self, ctx: SentinelContext):
        """Gets the guild's leave channel"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        channel_id = await self.bot.gcm.get_leave_channel_id(ctx.guild.id)
        if channel_id is None:
            embed = ctx.embed(
                title="Leave Channel: `None`",
            )
        else:
            channel = await ctx.guild.get_channel(channel_id) # type: ignore # Command is guild only
            embed = ctx.embed(
                title=f"Leave Channel: `{channel or 'None'}`",
            )
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    async def get_leave_message_title(self, ctx: SentinelContext):
        """Gets the guild's leave message title"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        title = await self.bot.gcm.get_leave_message_title(ctx.guild.id)
        embed = ctx.embed(
            title=f"Leave Message Title: `{title}`",
        )
        await ctx.send(embed=embed)
    
    @guild.command()
    @commands.guild_only()
    async def get_leave_message_body(self, ctx: SentinelContext):
        """Gets the guild's leave message body"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        body = await self.bot.gcm.get_leave_message_body(ctx.guild.id)
        embed = ctx.embed(
            title=f"Leave Message Body",
            description=body
        )
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    async def get_leave_message_enabled(self, ctx: SentinelContext):
        """Gets whether or not leave messages are enabled"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        status = await self.bot.gcm.get_leave_message_enabled(ctx.guild.id)
        embed = ctx.embed(
            title=f"Leave Messages: `{status}`",
        )
        await ctx.send(embed=embed)
    
    @guild.command()
    @commands.guild_only()
    async def get_modlog_channel(self, ctx: SentinelContext):
        """Gets the guild's modlog channel"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        channel_id = await self.bot.gcm.get_modlog_channel_id(ctx.guild.id)
        if channel_id is None:
            embed = ctx.embed(
                title="Modlog Channel: `None`",
            )
        else:
            channel = await ctx.guild.get_channel(channel_id) # type: ignore # Command is guild only
            embed = ctx.embed(
                title=f"Modlog Channel: `{channel or 'None'}`",
            )
        await ctx.send(embed=embed)
    
    @guild.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_channels=True))
    async def get_modlog_enabled(self, ctx: SentinelContext):
        """Gets whether or not modlog is enabled"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        status = await self.bot.gcm.get_modlog_enabled(ctx.guild.id)
        embed = ctx.embed(
            title=f"Modlog: `{status}`",
        )
        await ctx.send(embed=embed)


    # set


    @guild.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_guild=True))
    async def set_prefix(self, ctx: SentinelContext, prefix: str):
        """Sets the guild's prefix"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.gcm.set_prefix(ctx.guild.id, prefix)
        embed = ctx.embed(
            title=f"Prefix: `{prefix}`",
        )
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_channels=True))
    async def set_welcome_channel(self, ctx: SentinelContext, channel: discord.TextChannel):
        """Sets the guild's welcome channel"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.gcm.set_welcome_channel_id(ctx.guild.id, channel.id)
        embed = ctx.embed(
            title=f"Welcome Channel: `{channel}`",
        )
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_channels=True))
    async def set_welcome_message_title(self, ctx: SentinelContext, title: str):
        """Sets the guild's welcome message title"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.gcm.set_welcome_message_title(ctx.guild.id, title)
        embed = ctx.embed(
            title=f"Welcome Message Title: `{title}`",
        )
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_channels=True))
    async def set_welcome_message_body(self, ctx: SentinelContext, *, body: str):
        """Sets the guild's welcome message body"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.gcm.set_welcome_message_body(ctx.guild.id, body)
        embed = ctx.embed(
            title=f"Welcome Message Body",
            description=body
        )
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_channels=True))
    async def set_welcome_message_enabled(self, ctx: SentinelContext, status: bool):
        """Sets whether or not welcome messages are enabled"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.gcm.set_welcome_message_enabled(ctx.guild.id, status)
        embed = ctx.embed(
            title=f"Welcome Messages: `{status}`",
        )
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_channels=True))
    async def set_leave_channel(self, ctx: SentinelContext, channel: discord.TextChannel):
        """Sets the guild's leave channel"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.gcm.set_leave_channel_id(ctx.guild.id, channel.id)
        embed = ctx.embed(
            title=f"Leave Channel: `{channel}`",
        )
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_channels=True))
    async def set_leave_message_title(self, ctx: SentinelContext, title: str):
        """Sets the guild's leave message title"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.gcm.set_leave_message_title(ctx.guild.id, title)
        embed = ctx.embed(
            title=f"Leave Message Title: `{title}`",
        )
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_channels=True))
    async def set_leave_message_body(self, ctx: SentinelContext, *, body: str):
        """Sets the guild's leave message body"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.gcm.set_leave_message_body(ctx.guild.id, body)
        embed = ctx.embed(
            title=f"Leave Message Body",
            description=body
        )
        await ctx.send(embed=embed)

    @guild.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_channels=True))
    async def set_leave_message_enabled(self, ctx: SentinelContext, status: bool):
        """Sets whether or not leave messages are enabled"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.gcm.set_leave_message_enabled(ctx.guild.id, status)
        embed = ctx.embed(
            title=f"Leave Messages: `{status}`",
        )
        await ctx.send(embed=embed)
    
    @guild.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_channels=True))
    async def set_modlog_channel(self, ctx: SentinelContext, channel: discord.TextChannel):
        """Sets the guild's modlog channel"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.gcm.set_modlog_channel_id(ctx.guild.id, channel.id)
        embed = ctx.embed(
            title=f"Modlog Channel: `{channel}`",
        )
        await ctx.send(embed=embed)
    
    @guild.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_channels=True))
    async def set_modlog_enabled(self, ctx: SentinelContext, status: bool):
        """Sets whether or not modlogs are enabled"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.gcm.set_modlog_enabled(ctx.guild.id, status)
        embed = ctx.embed(
            title=f"Modlogs: `{status}`",
        )
        await ctx.send(embed=embed)


    @config.group()
    async def autoresponse(self, ctx: SentinelContext):
        """Autoresponse configuration"""
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @autoresponse.command()
    @commands.guild_only()
    async def get_autoresponse_functions(self, ctx: SentinelContext):
        """Gets the guild's autoresponse functions"""
        functions = await self.bot.gcm.get_autoresponse_functions(ctx.guild.id)
        if not functions:
            embed = ctx.embed(
                title="Autoresponse Functions",
                description="No functions found"
            )
            return await ctx.send(embed=embed)
        view = AutoresponseFunctionsPaginator(ctx, functions)
        await view.update()
        embed = await view.embed(view.displayed_values)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @autoresponse.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_channels=True))
    async def add_autoresponse_function(self, ctx: SentinelContext):
        """Adds an autoresponse function"""
        # modal
        modal = AddAutoresponseFunction(ctx)
        if ctx.interaction:
            await ctx.interaction.response.send_modal(modal)

    @autoresponse.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_channels=True))
    async def remove_autoresponse_function(self, ctx: SentinelContext, function: str):
        """Removes an autoresponse function"""
        # the autocomp choices are limited to a 100 char value, so I just truncate the function name and find it later  
        functions = await self.bot.gcm.get_autoresponse_functions(ctx.guild.id)
        for f in functions:
            if f.startswith(function):
                function = f
                break
        else:
            return await ctx.send("That function doesn't exist. Please use the autocomplete.")
        functions.remove(function)
        await self.bot.gcm.set_autoresponse_functions(ctx.guild.id, functions)
        embed = ctx.embed(
            title=f"Removed Autoresponse Function: `{function[:function.index(';')]}`",
        )
        await ctx.send(embed=embed)


    @remove_autoresponse_function.autocomplete(name="function")
    async def remove_autoresponse_function_autocomplete(self, itx: discord.Interaction, argument: str):
        return sorted([
            discord.app_commands.Choice(name=function[:function.index(";")], value=function[:100])
            for function in await self.bot.gcm.get_autoresponse_functions(itx.guild.id) # type: ignore
            if fuzz(function[:function.index(";")], argument) > 0.25 or not argument
        ][:25], key=lambda choice: fuzz(choice.name, argument), reverse=True)
    
    @autoresponse.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_guild=True))
    async def set_autoresponse_enabled(self, ctx: SentinelContext, status: bool):
        """Sets whether or not autoresponses are enabled"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.gcm.set_autoresponse_enabled(ctx.guild.id, status)
        embed = ctx.embed(
            title=f"Autoresponses: `{status}`",
        )
        await ctx.send(embed=embed)
    
    @autoresponse.command()
    @commands.guild_only()
    @dev(commands.has_guild_permissions(manage_guild=True))
    async def set_allow_autoresponse_immunity(self, ctx: SentinelContext, status: bool):
        """Sets whether or not autoresponses are enabled"""
        await self.bot.gcm.ensure_guild_config(ctx.guild.id)
        await self.bot.gcm.set_allow_autoresponse_immunity(ctx.guild.id, status)
        embed = ctx.embed(
            title=f"Allow Autoresponse Immunity: `{status}`",
        )
        await ctx.send(embed=embed)


class AutoresponseFunctionsPaginator(Paginator):
    def __init__(self, ctx: SentinelContext, functions: list[str]):
        super().__init__(ctx, tuple(functions), 1)

    async def embed(self, value_range: tuple[str]) -> discord.Embed:
        function = value_range[0]
        embed = self.ctx.embed(
            title=f"Autoresponse Functions - `{self.current_page+1}/{self.max_page+1}`",
            description=f"**Name:** `{function[:function.index(';')]}`\n**Function:**\n```py\n{function[function.index(';')+1:]}```",
        )
        return embed


class AddAutoresponseFunction(discord.ui.Modal):
    def __init__(self, ctx: SentinelContext):
        super().__init__(
            title="Add Autoresponse Function",
            timeout=60
        )
        self.ctx = ctx

    name = discord.ui.text_input.TextInput(label="Name", placeholder="Please enter title.", min_length=1, max_length=32)
    content = discord.ui.text_input.TextInput(label="Content", placeholder="Please enter code. See GitHub page in readme for syntax.", min_length=7, max_length=1000, style=discord.TextStyle.long)


    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.ctx.author.id
    
    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not self.validate_name_syntax(self.name.value):
            await interaction.response.send_message("Invalid name syntax.", ephemeral=True)
            return
        if not self.validate_code_syntax(self.content.value):
            await interaction.response.send_message("Invalid code syntax.", ephemeral=True)
            return
        functions = await self.ctx.bot.gcm.get_autoresponse_functions(self.ctx.guild.id)
        functions.append(f"{self.name.value};{self.content.value}")
        await self.ctx.bot.gcm.set_autoresponse_functions(self.ctx.guild.id, functions)
        await interaction.response.send_message("Added autoresponse function.", ephemeral=True)
        self.stop()
    
    def validate_name_syntax(self, name: str) -> bool:
        if not re.match(r"^[A-z0-9, \[\]\-_!@#$%^&*()]{1,32}$", name):
            return False
        return True
    
    def validate_code_syntax(self, code: str) -> bool:
        operators = VALID_OPERATORS.keys()
        escaped_operators = "|".join(map(lambda o: re.escape(o), operators))
        pattern = r"(^(if *\((.+(" + escaped_operators + r").+)\) +)*((send +[0-9]{18,19} +.{1,1000})|(reply +.{1,1000})|(delete *))\n?)+"
        print(pattern)
        code_syntax = re.compile(pattern)
        if not code_syntax.match(code):
            return False
        return True

    

async def setup(bot: Sentinel):
    await bot.add_cog(Config(bot))
