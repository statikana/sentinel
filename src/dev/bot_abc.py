# File to handle all base classes used for cogs, views, commands, etc.

from typing import Generic, Optional, Union
import discord
from discord.ext import commands

from .bot_typing import BotT
from .settings import DEFAULT_EMBED_ACCENT, VERSION
import datetime


class SentinelContext(commands.Context, Generic[BotT]):
    """
    Custom context class for Sentinel. Used primarily to add special methods
    to the context, and also override some types for ease of development.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bot: Sentinel = self.bot  # type: ignore # Force linter to recognize bot as Sentinel type

    async def embed(
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


class Sentinel(commands.AutoShardedBot):
    def __init__(self):
        command_prefix = ">>"
        intents = discord.Intents.all()
        super().__init__(
            command_prefix=command_prefix,
            intents=intents,
            help_command=None,
            case_insensitive=True,
        )
        
    async def get_context(
        self, origin: Union[discord.Message, discord.Interaction], *, cls=SentinelContext
    ) -> Union[commands.Context, SentinelContext]:
        return await super().get_context(origin, cls=cls)
