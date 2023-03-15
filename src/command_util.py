from difflib import SequenceMatcher
import inspect
from typing import Annotated, Callable, Coroutine, Generic, TypeVar
import typing

from .sentinel import SentinelContext, SentinelView, NumT
import discord
from discord.ext import commands


class Paginator(SentinelView, Generic[NumT]):
    def __init__(
        self,
        ctx: SentinelContext,
        values: tuple[NumT],
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
        if len(self.values) % self.page_size == 0:
            self.max_page -= 1

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

    async def embed(self, value_range: tuple[NumT]) -> discord.Embed:
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


def fuzz(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def lim(string: str, length: int, *, suffix: str = "...") -> str:
    if len(string) > length:
        return string[: length - len(suffix)] + suffix
    return string
