import logging
from typing import Any, Generic, Optional, TypeVar, Union
import discord
from discord.ext import commands
from .bot_abc import Sentinel, SentinelContext


T = TypeVar("T")


class SentinelCog(commands.Cog):
    def __init__(
        self,
        bot: Sentinel,
        emoji: Union[str, discord.Emoji] = "\N{Black Question Mark Ornament}",
        *,
        hidden: bool = False,
        guild_ids: set[int] = set(),
    ):
        self.bot: Sentinel = bot
        self.emoji = str(emoji)
        self.hidden: bool = hidden
        self.guild_ids: set[int] = guild_ids
        super().__init__()

    async def cog_load(self) -> None:
        logging.debug(f"Cog Load: {self.qualified_name}")
        return await super().cog_load()

    async def cog_unload(self) -> None:
        logging.debug(f"Cog Unload: {self.qualified_name}")
        return await super().cog_unload()


class SentinelView(discord.ui.View):
    def __init__(self, ctx: SentinelContext, *, timeout: float = 600.0):
        self.message: Optional[discord.Message] = None
        self.ctx = ctx
        super().__init__(timeout=timeout)

    async def interaction_check(self, itx: discord.Interaction) -> bool:
        return all(
            {
                self.ctx.author == itx.user,
                self.ctx.channel == itx.channel,
                self.ctx.guild == itx.guild,
                not itx.user.bot,
            }
        )


class Paginator(SentinelView, Generic[T]):
    def __init__(
        self,
        ctx: SentinelContext,
        content_title: str,
        values: list[T],
        page_size: int,
        *,
        timeout: float = 600.0,
    ):
        self.ctx = ctx
        self.content_title = content_title
        self.values = values
        self.page_size = page_size
        self.current_page = 0
        if len(values) % page_size == 0:
            self.max_page = len(values) // page_size - 1
        else:
            self.max_page = len(values) // page_size

        super().__init__(ctx, timeout=timeout)

    @discord.ui.button(
        emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
        style=discord.ButtonStyle.grey,
        custom_id="first_page",
    )
    async def first_page(self, itx: discord.Interaction, button: discord.ui.Button):
        self.current_page = 0
        await self.update(itx)

    @discord.ui.button(
        emoji="\N{BLACK LEFT-POINTING TRIANGLE}",
        style=discord.ButtonStyle.grey,
        custom_id="previous_page",
    )
    async def previous_page(self, itx: discord.Interaction, button: discord.ui.Button):
        self.current_page -= 1
        await self.update(
            itx
        )  # .update() takes care of disabling buttons if necessary, so there is no need to check for that here or next_page

    @discord.ui.button(
        emoji="\N{CROSS MARK}", style=discord.ButtonStyle.danger, custom_id="close"
    )
    async def close(self, itx: discord.Interaction, button: discord.ui.Button):
        for component in self.children:
            if isinstance(component, (discord.ui.Button, discord.ui.Select)):
                component.disabled = True
        await self.update(itx)

    @discord.ui.button(
        emoji="\N{BLACK RIGHT-POINTING TRIANGLE}",
        style=discord.ButtonStyle.grey,
        custom_id="next_page",
    )
    async def next_page(self, itx: discord.Interaction, button: discord.ui.Button):
        self.current_page += 1
        await self.update(itx)

    @discord.ui.button(
        emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}",
        style=discord.ButtonStyle.grey,
        custom_id="last_page",
    )
    async def last_page(self, itx: discord.Interaction, button: discord.ui.Button):
        self.current_page = self.max_page
        await self.update(itx)

    async def update(self, itx: discord.Interaction):
        if itx.message is None:
            return

        if self.current_page == 0:
            self.last_page.disabled = True
            self.previous_page.disabled = True
        elif self.current_page == self.max_page:
            self.first_page.disabled = True
            self.next_page.disabled = True
        else:
            self.first_page.disabled = False
            self.last_page.disabled = False
            self.previous_page.disabled = False
            self.next_page.disabled = False

        start = self.current_page * self.page_size
        end = min(start + self.page_size, len(self.values))
        included_content = self.values[start:end]

        content: str | tuple[str, str] = await self.display_page(included_content)
        if isinstance(content, tuple):
            title, description = content
        else:
            title = f"`{self.content_title}:` Page `{self.current_page + 1}`/`{self.max_page + 1}` [{start + 1}-{end + 1}]"
            description = content

        embed = self.ctx.embed(title=title, description=description)
        await itx.message.edit(view=self, embed=embed)

    async def display_page(self, included_content: list[T]) -> str | tuple[str, str]:
        """
        A method that should be overloaded by subclasses to display the content of the page, given the current content that should be displayed.
        Should either return a string (taken as the embed's description) or a tuple of strings (taken as the embed's title and description).
        If no title is given, the paginator's content_title is formatted to look nice.
        """
        raise NotImplementedError
