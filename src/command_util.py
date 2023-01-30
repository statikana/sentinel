from difflib import SequenceMatcher
from typing import Annotated, Callable, Coroutine, Generic
import typing

from .sentinel import (
    Sentinel,
    SentinelCog,
    SentinelContext,
    SentinelView,
    T,
    TypedHybridCommand,
    TypedHybridGroup,
    SentinelErrors,
)
import discord
from discord.ext import commands
from discord.app_commands.transformers import RangeTransformer

import re


class Paginator(SentinelView, Generic[T]):
    def __init__(
        self,
        ctx: SentinelContext,
        values: tuple[T],
        page_size: int,
        *,
        timeout: float = 600.0,
    ):

        super().__init__(ctx, timeout=timeout)
        self.values = values
        self.page_size = page_size

        self.current_page = 0
        self.min_page = 0
        self.max_page = len(self.values) // self.page_size
        # if len(self.values) % self.page_size != 0:
        #     self.max_page += 1

        self.display_values_index_start = 0
        self.display_values_index_end = min(len(self.values), self.page_size)
        self.displayed_values = self.values[
            self.display_values_index_start : self.display_values_index_end
        ]

    @discord.ui.button(
        emoji="\N{Black Left-Pointing Double Triangle with Vertical Bar}",
        style=discord.ButtonStyle.grey,
    )
    async def first_page(
        self, itx: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.current_page = self.min_page
        await self.update(itx, button)

    @discord.ui.button(
        emoji="\N{Leftwards Black Arrow}", style=discord.ButtonStyle.grey
    )
    async def previous_page(
        self, itx: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.current_page -= 1
        await self.update(itx, button)

    @discord.ui.button(  # cross
        emoji="\N{Cross Mark}", style=discord.ButtonStyle.danger
    )
    async def close(self, itx: discord.Interaction, button: discord.ui.Button) -> None:
        await super().prefab_close_button(itx, button)

    @discord.ui.button(
        emoji="\N{Black Rightwards Arrow}", style=discord.ButtonStyle.grey
    )
    async def next_page(
        self, itx: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.current_page += 1
        await self.update(itx, button)

    @discord.ui.button(
        emoji="\N{Black Right-Pointing Double Triangle with Vertical Bar}",
        style=discord.ButtonStyle.grey,
    )
    async def last_page(
        self, itx: discord.Interaction, button: discord.ui.Button
    ) -> None:
        self.current_page = self.max_page
        await self.update(itx, button)

    async def update(
        self,
        itx: discord.Interaction | None = None,
        pressed: discord.ui.Button | None = None,
    ) -> None:
        if itx is not None:
            await itx.response.defer()
        self.current_page = min(self.max_page, max(self.min_page, self.current_page))

        self.display_values_index_start = self.current_page * self.page_size
        self.display_values_index_end = min(
            len(self.values), (self.current_page + 1) * self.page_size
        )
        self.displayed_values = self.values[
            self.display_values_index_start : self.display_values_index_end
        ]

        if self.current_page == self.min_page:
            self.first_page.disabled = True
            self.previous_page.disabled = True
        if self.current_page == self.max_page:
            self.last_page.disabled = True
            self.next_page.disabled = True
        if self.current_page > self.min_page:
            self.first_page.disabled = False
            self.previous_page.disabled = False
        if self.current_page < self.max_page:
            self.last_page.disabled = False
            self.next_page.disabled = False

        if pressed is not None:
            for button in self.children:
                if (
                    isinstance(button, discord.ui.Button)
                    and button is not pressed
                    and button.style != discord.ButtonStyle.danger
                ):
                    button.style = discord.ButtonStyle.grey
            pressed.style = discord.ButtonStyle.green

        embed = await self.embed(self.displayed_values)
        if self.message is not None:
            await self.message.edit(embed=embed, view=self)

    async def embed(self, value_range: tuple[T]) -> discord.Embed:
        raise NotImplementedError


class ParamDefaults:
    member = commands.param(
        converter=discord.Member,
        default=lambda ctx: ctx.author,
        displayed_default="<author>",
    )
    user = commands.param(
        converter=discord.User,
        default=lambda ctx: ctx.author,
        displayed_default="<author>",
    )
    channel = commands.param(
        converter=discord.TextChannel,
        default=lambda ctx: ctx.channel,
        displayed_default="<channel>",
    )
    guild = commands.param(
        converter=discord.Guild,
        default=lambda ctx: ctx.guild,
        displayed_default="<guild>",
    )


class StringArgParse(commands.Converter):
    def __init__(
        self,
        lower: bool = False,
        upper: bool = False,
        stripped: list[str] | None = None,
        regex: str | None = None,
    ):
        self._lower = lower
        self._upper = upper
        self._stripped = stripped
        self.regex = regex

    async def convert(self, ctx: commands.Context, arg: str) -> str:
        if self._lower:
            arg = arg.lower()
        if self.upper:
            arg = arg.upper()
        if self._stripped is not None:
            for chars in self._stripped:
                arg = arg.strip(chars)
        if self.regex is not None:
            if not re.match(self.regex, arg):
                raise commands.BadArgument(f"Invalid argument: {arg}")
        return arg

    @property
    def lower(self) -> "StringArgParse":
        return StringArgParse(
            lower=True, upper=self._upper, stripped=self._stripped, regex=self.regex
        )

    @property
    def upper(self) -> "StringArgParse":
        return StringArgParse(
            lower=self._lower, upper=True, stripped=self._stripped, regex=self.regex
        )


class UniversalComponentConverter(commands.Converter):
    def __init__(
        self,
        *,
        command: bool = True,
        group: bool = True,
        cog: bool = True,
        raise_on_missing: bool = True,
        return_check: Coroutine[
            None,
            None,
            Callable[
                [
                    SentinelContext,
                    commands.HybridCommand | commands.HybridGroup | commands.Cog,
                ],
                bool,
            ],
        ]
        | None = None,
        fuzzy_search_threshold: float = 0.9,
    ):
        self.command = command
        self.group = group
        self.cog = cog
        self.raise_on_missing = raise_on_missing
        self.return_check = return_check

    @staticmethod
    async def _default_return_check(
        ctx: SentinelContext,
        component: TypedHybridCommand | TypedHybridGroup | SentinelCog,
    ) -> bool:
        if isinstance(component, commands.HybridCommand):
            return (
                await component.can_run(ctx)
                and not component.hidden
                and not component.cog.hidden
            )
        elif isinstance(component, commands.HybridGroup):
            return (
                await component.can_run(ctx)
                and not component.hidden
                and not component.cog.hidden
            )
        elif isinstance(component, commands.Cog):
            return not component.hidden
        return False

    def _fuzzy_search(
        self, arg: str, component: TypedHybridCommand | TypedHybridGroup | SentinelCog
    ) -> float:
        if isinstance(component, commands.HybridCommand):
            return fuzz.ratio(arg, component.name)
        elif isinstance(component, commands.HybridGroup):
            return fuzz.ratio(arg, component.name)
        elif isinstance(component, commands.Cog):
            return fuzz.ratio(arg, component.qualified_name)
        return 0.0

    async def convert(self, ctx: SentinelContext, arg: str) -> commands.HybridCommand | commands.HybridGroup | commands.Cog | None:  # type: ignore
        self.return_check = self.return_check or self._default_return_check
        if self.command:
            if await CommandConverter().convert(ctx, arg) is not None:
                return await CommandConverter().convert(ctx, arg)
        if self.group:
            if await GroupConverter().convert(ctx, arg) is not None:
                return await GroupConverter().convert(ctx, arg)
        if self.cog:
            if await CogConverter().convert(ctx, arg) is not None:
                return await CogConverter().convert(ctx, arg)
        if self.raise_on_missing:
            raise SentinelErrors.ComponentNotFound(f"Component {arg} not found")


class CommandConverter(commands.Converter):
    async def convert(
        self, ctx: SentinelContext, arg: str
    ) -> commands.HybridCommand | None:
        for command in ctx.bot.walk_commands():
            if not isinstance(command, commands.GroupMixin) and (
                fuzz(arg, command.qualified_name) > 0.95
                or fuzz(arg, command.name) > 0.95
            ):
                return command


class GroupConverter(commands.Converter):
    async def convert(
        self, ctx: SentinelContext, arg: str
    ) -> commands.HybridGroup | None:
        for command in ctx.bot.walk_commands():
            if isinstance(command, commands.HybridGroup) and (
                fuzz(arg, command.qualified_name) > 0.95
                or fuzz(arg, command.name) > 0.95
            ):
                return command


class CogConverter(commands.Converter):
    async def convert(self, ctx: SentinelContext, arg: str) -> commands.Cog | None:
        for cog in ctx.bot.cogs.values():
            if fuzz(arg, cog.qualified_name) > 0.95:
                return cog


def fuzz(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


StringParam = Annotated[str, StringArgParse]
LowerString = commands.param(converter=StringParam.lower)
