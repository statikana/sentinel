import discord
from discord.ext import commands

from ..sentinel import (
    Sentinel,
    SentinelCog,
    SentinelContext,
    SentinelView,
    TypedHybridCommand,
    TypedHybridGroup,
    TypedHybrid,
)
from ..converters import UniversalComponentConverter


class Help(SentinelCog, emoji="\N{White Question Mark Ornament}", hidden=True):
    """Contains help commands"""

    @commands.hybrid_command()
    async def help(
        self,
        ctx: SentinelContext,
        *,
        query: TypedHybrid
        | SentinelCog = commands.param(
            default=None,
            converter=UniversalComponentConverter,
        ),
    ):
        """Shows this message"""
        if query is None:
            await self.send_all_help(ctx)

        elif isinstance(query, commands.HybridCommand):
            await self.send_command_help(ctx, query)

        elif isinstance(query, commands.HybridGroup):
            await self.send_group_help(ctx, query)

        elif isinstance(query, SentinelCog):
            await self.send_cog_help(ctx, query)

    async def send_all_help(self, ctx: SentinelContext):
        embed = ctx.embed(title="Help", description="*Please select a cog*")
        view = SentinelView(ctx)
        view.add_item(self.select_cog_item(ctx))
        await ctx.send(embed=embed, view=view)

    async def send_command_help(
        self, ctx: SentinelContext, command: TypedHybridCommand
    ) -> None:
        """Shows all info on one command"""
        title = f"Help: `{command.name}` [`{command.qualified_name}`]"

        embed = ctx.embed(
            title=title,
            description=get_command_description(command, False),
        )
        embed.add_field(
            name="Usage",
            value=get_command_usage(ctx, command),
            inline=False,
        )
        add_command_params(embed, command)
        view = SentinelView(ctx)
        if command.parent is not None:
            view.add_item(self.select_command_item_from_group(ctx, command.parent))  # type: ignore
        view.add_item(self.select_cog_item(ctx))
        await ctx.send(embed=embed, view=None)

    async def send_group_help(self, ctx: SentinelContext, group: TypedHybridGroup):
        embed = ctx.embed(
            title=f"Help: `{group.name}` [`{group.qualified_name}`]",
            description=f"{get_group_description(group)}]\n**Please use the dropdown to select a command**",
        )
        embed.add_field(
            name="Usage",
            value=get_group_usage(ctx, group),
        )
        view = SentinelView(ctx)
        view.add_item(self.select_command_item_from_group(ctx, group))
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    async def send_cog_help(self, ctx: SentinelContext, cog: SentinelCog):
        embed = ctx.embed(
            title=f"Help: `{cog.qualified_name}`",
            description=f"*{cog.description}*\n**Please use the dropdown to select a command**",
        )
        view = SentinelView(ctx)
        view.add_item(self.select_command_item_from_cog(ctx, cog))
        view.add_item(self.select_cog_item(ctx))
        await ctx.send(embed=embed, view=view)

    def select_cog_item(self, ctx: SentinelContext) -> discord.ui.Select:
        options: list[discord.SelectOption] = []
        for name, cog in self.bot.cogs.items():
            if cog.hidden:
                continue
            options.append(
                discord.SelectOption(
                    label=name,
                    description=cog.description
                    if len(cog.description) < 100
                    else cog.description[:96] + "...",
                    emoji=cog.emoji,
                    default=False,
                )
            )
        sel = discord.ui.Select(
            placeholder="Select a Cog",
            options=options,
            min_values=1,
            max_values=1,
        )

        async def callback(interaction: discord.Interaction):
            itx = interaction  # goofy ahh python
            cog = ctx.bot.get_cog(sel.values[0])
            if cog is None:
                return
            embed = ctx.embed(
                title=f"Help: `{cog.qualified_name}`",
                description=f"*{cog.description}*",
            )
            view = SentinelView(ctx)
            view.add_item(self.select_command_item_from_cog(ctx, cog))
            view.add_item(self.select_cog_item(ctx))
            await itx.response.edit_message(embed=embed, view=view)

        sel.callback = callback
        return sel

    def select_command_item_from_group(
        self, ctx: SentinelContext, group: TypedHybridGroup | None
    ) -> discord.ui.Select:
        iter_commands: set[TypedHybridCommand] = set()
        if group is None:
            for cog in self.bot.cogs.values():
                iter_commands.update(cog.get_commands())
        else:
            iter_commands.update(group.commands)

        options: list[discord.SelectOption] = []
        for command in iter_commands:
            if isinstance(command, commands.GroupMixin) or command.hidden:
                continue
            options.append(
                discord.SelectOption(
                    label=command.qualified_name,
                    description=get_command_description(command),
                    default=False,
                    emoji=command.cog.emoji if command.cog is not None else None,
                )
            )
        sel = discord.ui.Select(
            placeholder="Select a Command from this Group",
            options=options,
            min_values=1,
            max_values=1,
        )

        async def callback(interaction: discord.Interaction):
            itx = interaction
            if command is None or isinstance(command, commands.GroupMixin):
                return

            embed = ctx.embed(
                title=f"Help: `{command.name}` [`{command.qualified_name}`]",
                description=get_command_description(command, False),
            )
            embed.add_field(
                name="Usage",
                value=get_command_usage(ctx, command),
                inline=False,
            )
            view = SentinelView(ctx)
            if command.parent is not None:
                view.add_item(self.select_command_item_from_group(ctx, command.parent))  # type: ignore
            view.add_item((self.select_cog_item(ctx)))
            await itx.response.edit_message(embed=embed, view=view)

        sel.callback = callback
        return sel

    def select_command_item_from_cog(
        self, ctx: SentinelContext, cog: SentinelCog
    ) -> discord.ui.Select:
        options: list[discord.SelectOption] = []
        for command in ctx.bot.walk_commands():
            if (
                isinstance(command, commands.GroupMixin)
                or command.hidden
                or not isinstance(command, commands.HybridCommand)
            ):
                continue
            if command.cog is None or command.cog.qualified_name != cog.qualified_name:
                continue
            options.append(
                discord.SelectOption(
                    label=command.qualified_name,
                    description=get_command_description(command),
                    default=False,
                    emoji=command.cog.emoji if command.cog is not None else None,
                )
            )
        sel = discord.ui.Select(
            placeholder="Select a Command from this Cog",
            options=options,
            min_values=1,
            max_values=1,
        )

        async def callback(interaction: discord.Interaction):
            itx = interaction
            command = ctx.bot.get_command(sel.values[0])
            if command is None or isinstance(command, commands.GroupMixin):
                return

            embed = ctx.embed(
                title=f"Help: `{command.name}` [`{command.qualified_name}`]",
                description=get_command_description(command, False),
            )
            embed.add_field(
                name="Usage",
                value=get_command_usage(ctx, command),
                inline=False,
            )
            view = SentinelView(ctx)
            # if command.parent is not None:
            #     view.add_item(self.select_command_item_from_group(ctx, command.parent))  # type: ignore
            # This was accessed via the cog, so we don't need to go back to the group
            view.add_item(self.select_command_item_from_cog(ctx, command.cog))
            view.add_item(self.select_cog_item(ctx))
            await itx.response.edit_message(embed=embed, view=view)

        sel.callback = callback
        return sel


def add_arrow_on_selected(select: discord.ui.Select, chosen: discord.SelectOption):
    for option in select.options:
        if option == chosen:
            option.emoji = "\N{Rightwards Black Arrow}"
        else:
            option.emoji = discord.utils.MISSING


def get_command_usage(ctx: SentinelContext, command: TypedHybridCommand) -> str:
    formatted_params = ""
    for name, param in command.params.items():
        if command.app_command is None:
            continue
        param_type = get_param_repr(param)
        if not param.default in (param.empty, None):
            formatted_params += f"[{name}: {param_type}] "
        else:
            formatted_params += f"<{name}: {param_type}> "
    return f"```{ctx.prefix}{command.qualified_name} {formatted_params}```"


def get_group_usage(ctx: SentinelContext, group: TypedHybridGroup) -> str:
    return f"```{ctx.prefix}{group.qualified_name} <subcommand>```"


def add_command_params(embed: discord.Embed, command: TypedHybridCommand) -> None:
    if command.app_command is None:
        return
    for name, app_param in command.app_command._params.items():
        com_param = command.params[name]
        if com_param.default is commands.Parameter.empty:
            value = (
                f"*{app_param.description or 'No Description'}*\n**Required:** `True`"
            )
        else:
            value = f"*{app_param.description or 'No Description'}*\nRequired: `False`\nDefault: `{com_param.displayed_default}`"
        embed.add_field(
            name=f"**__Param `{app_param.display_name}` [Type `{get_param_repr(com_param)}`]__**",
            value=value,
            inline=False,
        )


def get_param_repr(param: commands.Parameter) -> str:
    if param.annotation is param.empty:
        return "Any"
    try:
        return param.annotation.__name__
    except AttributeError:
        return param.annotation.__str__()


def get_command_description(command: TypedHybridCommand, cutoff: bool = True) -> str:
    dec = command.short_doc or "No description provided."
    if len(dec) > 100 and cutoff:
        return dec[:94] + "..."
    return f"*{dec}*"


def get_group_description(group: TypedHybridGroup, cutoff: bool = True) -> str:
    dec = group.short_doc or "No description provided."
    if len(dec) > 100 and cutoff:
        return dec[:94] + "..."
    return f"*{dec}*"


async def setup(bot: Sentinel):
    await bot.add_cog(Help(bot))
