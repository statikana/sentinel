from typing import Generic, Optional, Union
import aiohttp
import asyncpg
import discord
from discord.ext import commands

from env import POSTGRES_HOST, POSTGRES_PASSWORD, POSTGRES_PORT, POSTGRES_USER
from .bot_util import load_extensions

from .bot_typing import BotT
from .settings import DEFAULT_EMBED_ACCENT, VERSION
import datetime
import logging


class SentinelContext(commands.Context, Generic[BotT]):
    """
    Custom context class for Sentinel. Used primarily to add special methods
    to the context, and also override some types for ease of development.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bot: Sentinel = self.bot  # type: ignore # Force linter to recognize bot as Sentinel type
        self.guild: discord.Guild = self.guild  # type: ignore # Force linter to recognize guild as discord.Guild type, and not Optional[discord.Guild]

    def embed(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[discord.Color] = DEFAULT_EMBED_ACCENT,
        url: Optional[str] = None,
        timestamp: Optional[datetime.datetime] = None,
    ) -> discord.Embed:

        if not title and not description:
            title = "undefined"

        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            url=url,
            timestamp=timestamp or datetime.datetime.utcnow(),
        )
        version = ".".join(VERSION)
        embed.set_footer(
            text=f"Sentinel v{version} | {self.author}",
            icon_url=self.author.display_avatar.url,
        )
        return embed


class Sentinel(commands.AutoShardedBot, Generic[BotT]):
    def __init__(self):
        command_prefix = ">>"
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=command_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
        )

        self.apg: SentinelConnectionPool
        self.session: SentinelAIOSession

    async def get_context(
        self,
        origin: Union[discord.Message, discord.Interaction],
        *,
        cls=SentinelContext,
    ) -> Union[commands.Context, SentinelContext]:
        return await super().get_context(origin, cls=cls)

    async def setup_hook(self) -> None:
        logging.info("Sentinel " + ".".join(VERSION) + " Online")
        await load_extensions(self)
        self.apg = await asyncpg.create_pool(
            f"postgres://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}",
            pool_class=SentinelConnectionPool,
        )  # type: ignore # asyncpg is kinda fucky, best to ignore it
        self.session = SentinelAIOSession()


class SentinelConnectionPool(asyncpg.Pool):
    """
    Custom connection pool class for Sentinel. Will most likely need specialized methods later on, so that's why it's here.
    """


class SentinelAIOSession(aiohttp.ClientSession):
    def __init__(self):
        super().__init__(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0"
            }
        )
