"""
File which includes the major types used in Sentinel:
    - Sentinel
    - SentinelContext
    - SentinelTree
    - SentinelSession
    - SentinelConnectionPool
"""


import asyncio
from functools import partial
import logging
from pathlib import Path
import sys
import threading
import time
from typing import (
    Any,
    Callable,
    Coroutine,
    Generator,
    Generic,
    Optional,
    ParamSpec,
    Type,
    TypeVar,
    Union,
)
import discord
from discord.ext import commands
from datetime import datetime
import asyncpg

import os
import env
from glob import glob
import importlib
import aiohttp
from selenium.webdriver import Firefox as SeleniumFirefox
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from . import error_types as SentinelErrors

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")

__version__ = ("1", "0", "0")


P = ParamSpec("P")
T = TypeVar("T")


class Sentinel(commands.Bot):
    def __init__(self):
        self.session: SentinelAIOSession
        self.apg: asyncpg.Pool
        self.guild_cache = SentinelCache(timeout=300)
        self.driver: SentinelDriver
        super().__init__(
            command_prefix=">>",
            help_command=None,
            tree_cls=SentinelTree,
            intents=discord.Intents.all(),
        )

    async def get_context(
        self,
        origin: Union[discord.Message, discord.Interaction],
        *,
        cls: Optional[Type[commands.Context["_SentinelBotT"]]] = None,
    ) -> Union[commands.Context, "SentinelContext"]:
        return await super().get_context(origin, cls=cls or SentinelContext)

    async def setup_hook(self) -> None:
        logging.info("Sentinel v" + ".".join(__version__) + " Online")
        await self.connect_db()
        await self.connect_session()
        await self.prepare_databases()
        await self.connect_driver()
        await self.reload_extensions()

    async def reload_extensions(
        self, ext_dir: str = ".\\src\\ext"
    ) -> tuple[list[str], list[str]]:
        loaded_extensions = []
        loaded_utilities = []
        for extension in os.listdir(ext_dir):
            if extension.endswith(".py"):
                path = (
                    os.path.join(ext_dir, extension).replace("\\", ".")[:-3].strip(".")
                )
                try:
                    await self.unload_extension(path)
                except commands.ExtensionNotLoaded:
                    pass
                await self.load_extension(path)
                loaded_extensions.append(path)

        for file in glob("./**/*.py"):
            try:
                module = importlib.import_module(
                    file.replace("\\", ".").strip(".")[:-3]
                )
            except ImportError:
                continue
            importlib.reload(module)
            loaded_utilities.append(file)

        return loaded_extensions, loaded_utilities

    async def connect_db(self):
        pool = await asyncpg.create_pool(
            f"postgres://{env.POSTGRES_USER}:{env.POSTGRES_PASSWORD}@{env.POSTGRES_HOST}:{env.POSTGRES_PORT}"
        )
        if pool is None:
            raise RuntimeError("Failed to connect to database")
        self.apg = pool

    async def connect_session(self):
        self.session = SentinelAIOSession()

    async def on_message(self, message: discord.Message, /) -> None:
        if message.author.id in await self.apg.fetch("SELECT user_id FROM blacklist"):
            return

        return await super().on_message(message)

    async def prepare_databases(self):
        await self.apg.execute(open("schema.sql", "r").read())

    async def connect_driver(self):
        self.driver = SentinelDriver()

    @property
    def commands(self) -> set["AnyTypedCommand"]:
        return super().commands

    def get_command(self, name: str, /) -> Optional["AnyTypedCommand"]:
        return super().get_command(name)

    def walk_commands(self) -> Generator["AnyTypedCommand", None, None]:
        return super().walk_commands()

    def add_command(self, command: "AnyTypedCommand", /) -> None:
        super().add_command(command)

    def remove_command(self, name: str, /) -> Optional["AnyTypedCommand"]:
        return super().remove_command(name)


_SentinelBotT = TypeVar("_SentinelBotT", bound=Sentinel, covariant=True)


class SentinelContext(commands.Context):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot: Sentinel = self.bot

    def embed(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[discord.Color] = discord.Color.dark_teal(),
    ) -> discord.Embed:
        if not title and not description:
            title = "undefined"

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.utcnow(),
        )

        embed.set_footer(
            text=f"Sentinel {'.'.join(__version__)} | {self.author}",
            icon_url=self.author.display_avatar.url,
        )

        return embed


class SentinelTree(discord.app_commands.CommandTree):
    def __init__(self, bot: commands.Bot, **kwargs):
        self.bot = bot
        super().__init__(client=bot, **kwargs)

    async def interaction_check(self, itx: discord.Interaction, /) -> bool:
        if itx.type == discord.InteractionType.application_command:
            # TODO: automatically defer?
            pass
        return (
            itx.user.id
            not in await self.bot.apg.fetch(  # type: ignore # mmmm, circlar references
                "SELECT user_id FROM blacklist"
            )
        )


class SentinelCog(commands.Cog):
    def __init__(
        self,
        bot: Sentinel,
        emoji: Union[discord.Emoji, str] = "\N{Black Question Mark Ornament}",
        *,
        hidden: bool = False,
    ):
        self.bot = bot
        self.emoji = str(emoji)
        self.hidden = hidden
        super().__init__()

    async def cog_load(self) -> None:
        logging.debug(f"Cog Loaded: {self.__class__.__name__}")

    async def cog_unload(self) -> None:
        logging.debug(f"Cog Unloaded: {self.__class__.__name__}")


class SentinelAIOSession(aiohttp.ClientSession):
    def __init__(self):
        super().__init__(
            raise_for_status=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0"
            },
        )


class SentinelDriver:
    def __init__(self):
        options = FirefoxOptions()
        options.headless = True
        options.binary_location = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
        self.driver = SeleniumFirefox(
            options=options,
            executable_path="C:\\Program Files\\Mozilla Firefox\\geckodriver.exe",
        )

    async def get(self, url: str, /, wait: float = 0.5) -> str:
        thread_get = asyncio.to_thread(self.driver.get, url)
        await thread_get
        thread_get.close()
        await asyncio.sleep(wait)
        thread_return: Coroutine[Any, Any, str] = asyncio.to_thread(
            self.driver.execute_script, "return document.documentElement.outerHTML"
        )
        return await thread_return


class SentinelView(discord.ui.View):
    def __init__(
        self,
        ctx: SentinelContext,
        *,
        timeout: float | None = 600.0,
        row: int | None = None,
    ):
        self.message: Optional[discord.Message] = None
        self.ctx = ctx
        super().__init__(timeout=timeout)

        if row is not None:
            self.add_item(
                discord.ui.Button(
                    style=discord.ButtonStyle.danger,
                    label="Close",
                    custom_id="close",
                    row=row,
                )
            )

    async def close_button(self, itx: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True
        await itx.response.edit_message(view=self)

    async def interaction_check(self, itx: discord.Interaction) -> bool:
        return all(
            {
                self.ctx.author == itx.user,
                self.ctx.channel == itx.channel,
                self.ctx.guild == itx.guild,
                not itx.user.bot,
            }
        )


class SentinelPool(asyncpg.Pool):
    def __init__(self, bot: Sentinel, *connect_args, **kwargs):
        self.bot = bot
        super().__init__(*connect_args, **kwargs)

    async def fetch(self, query, *args, timeout=None, use_cache: bool = False):
        if use_cache:
            if (cached := self.bot.guild_cache[query]) is not None:
                return cached


class SentinelCache(dict[Any, "SentinelCacheEntry"], Generic[_KT, _VT]):
    def __init__(self, *, timeout: int):
        super().__init__()
        self.timeout = timeout

    def __setitem__(self, __key: _KT, __value: _VT) -> None:
        return super().__setitem__(__key, SentinelCacheEntry(__value, self.timeout))

    def __getitem__(self, __key: _KT) -> Optional[_VT]:
        cache_entry: Optional[SentinelCacheEntry] = super().get(__key, None)
        if cache_entry is None:
            return None

        if cache_entry.time + self.timeout <= time.time():
            super().__delitem__(__key)
            return None

        return cache_entry.value


class SentinelCacheEntry:
    def __init__(self, value: Any, timeout: int):
        self.value = value
        self.time = int(
            time.time()
        )  # Ints are much faster to work with and no need for decimals


SentinelCogT = TypeVar("SentinelCogT", bound=SentinelCog, covariant=True)

TypedCommand = commands.Command[SentinelCogT, P, T]
TypedHybridCommand = commands.HybridCommand[SentinelCogT, P, T]
TypedGroup = commands.Group[SentinelCogT, P, T]
TypedHybridGroup = commands.HybridGroup[SentinelCogT, P, T]
AnyTypedCommand = Union[TypedCommand, TypedHybridCommand, TypedGroup, TypedHybridGroup]
