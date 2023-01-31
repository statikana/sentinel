import discord
from discord.ext import commands
from .sentinel import (
    SentinelContext,
    TypedHybridCommand,
    TypedHybridGroup,
    SentinelCog,
    SentinelErrors,
    NumT,
)


import re
from typing import TypeVar, Coroutine, Callable, Annotated
from difflib import SequenceMatcher

from .command_util import fuzz


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

    def __repr__(self) -> str:
        return f"Command | Group | Cog"


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

    def __repr__(self) -> str:
        return f"Command"


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

    def __repr__(self) -> str:
        return f"Group"


class CogConverter(commands.Converter):
    async def convert(self, ctx: SentinelContext, arg: str) -> commands.Cog | None:
        for cog in ctx.bot.cogs.values():
            if fuzz(arg, cog.qualified_name) > 0.95:
                return cog

    def __repr__(self) -> str:
        return f"Cog"


class RangeConverter(commands.Converter):
    def __init__(
        self,
        type: type[int] | type[float] = int,
        min: int | float | None = None,
        max: int | float | None = None,
    ):
        self.type = type
        self.min = min
        self.max = max

    async def convert(self, ctx: SentinelContext, argument: str) -> int | float:
        try:
            value = self.type(argument)
        except ValueError:
            raise commands.BadArgument(f"{argument} is not a valid number.") from None
        if self.min is not None and value < self.min:
            raise commands.BadArgument(
                f"{argument} is below the minimum value of {self.min}"
            )
        if self.max is not None and value > self.max:
            raise commands.BadArgument(
                f"{argument} is above the maximum value of {self.max}"
            )
        return value

    def __repr__(self) -> str:
        return f"Range[{self.type.__name__}]({self.min}, {self.max})"


StringParam = Annotated[str, StringArgParse]
LowerString = commands.param(converter=StringParam.lower)


def Range(
    type: NumT = int,
    min: int | float | None = None,
    max: int | float | None = None,
    default: NumT | None = None,
) -> Annotated[NumT, RangeConverter]:
    return commands.param(
        converter=RangeConverter(type, min=min, max=max),
        default=default or commands.Parameter.empty,
    )
