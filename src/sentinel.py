from dataclasses import dataclass
from redis import asyncio as aioredis

import asyncio
import io
import json
import logging
from typing import (
    Any,
    Coroutine,
    Generator,
    Generic,
    Iterator,
    Mapping,
    Optional,
    ParamSpec,
    Type,
    TypeGuard,
    TypeVar,
    Union,
    overload,
)
import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime, timedelta
import asyncpg
import openai

import os
import env
from glob import glob
import importlib
import aiohttp
from selenium.webdriver import Firefox as SeleniumFirefox
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

from . import error_types as SentinelErrors
from .db_managers import UserDataManager, GuildDataManager, TagDataManager, GuildConfigManager, UserConfigManager

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")

__version__ = ("1", "0", "0")

P = ParamSpec("P")
T = TypeVar("T")

NumT = TypeVar("NumT", int, float)


class Sentinel(commands.Bot):
    def __init__(self):
        self.session: SentinelAIOSession
        self.apg: asyncpg.Pool
        self.driver: SentinelDriver

        self.udm: UserDataManager
        self.gdm: GuildDataManager
        self.tdm: TagDataManager

        self.deleted_message_cache = SentinelMessageCache()

        # get_pipe: Callable[[], StableDiffusionPipeline] = lambda: StableDiffusionPipeline.from_pretrained(
        #     "runwayml/stable-diffusion-v1-5",
        #     safety_checker=None
        # ) # type: ignore
        # self.pipe = get_pipe()
        # self.pipe.config
        # self.pipe = self.pipe.to(torch.device("cpu"))
        # one of cpu, cuda, ipu, xpu, mkldnn, opengl, opencl, ideep, hip, ve, fpga, ort, xla, lazy, vulkan, mps, meta, hpu, mtia, privateuseone

        openai.api_key = env.OPENAI_API_KEY


        super().__init__(
            command_prefix=_get_prefix,
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

        self.udm = UserDataManager(self.apg)
        self.gdm = GuildDataManager(self.apg)
        self.tdm = TagDataManager(self.apg)
        self.gcm = GuildConfigManager(self.apg)
        self.ucm = UserConfigManager(self.apg)

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
        await self.session._build_cache()

    async def on_message(self, message: discord.Message, /) -> None:
        if message.author.id in await self.apg.fetch("SELECT user_id FROM blacklist"):
            return

        return await super().on_message(message)

    async def prepare_databases(self):
        await self.apg.execute(open("schema.sql", "r").read())

    async def connect_driver(self):
        self.driver = SentinelDriver()

    @property
    def commands(self) -> set["TypedHybrid"]:
        return super().commands  # type: ignore

    @property
    def cogs(self) -> Mapping[str, "SentinelCog"]:
        return super().cogs  # type: ignore

    def get_cog(self, name: str, /) -> Optional["SentinelCog"]:
        return super().get_cog(name)  # type: ignore

    def get_command(self, name: str, /) -> Optional["TypedHybrid"]:
        return super().get_command(name)  # type: ignore

    def walk_commands(self) -> Generator["TypedHybrid", None, None]:
        return super().walk_commands()  # type: ignore

    def add_command(self, command: "TypedHybrid", /) -> None:
        super().add_command(command)

    def remove_command(self, name: str, /) -> Optional["TypedHybrid"]:
        return super().remove_command(name)  # type: ignore


_SentinelBotT = TypeVar("_SentinelBotT", bound=Sentinel, covariant=True)


class SentinelContext(commands.Context):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot: Sentinel = self.bot
        self.guild: discord.Guild = self.guild

    def embed(
        self,
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: Optional[discord.Color] = discord.Color.dark_teal(),
        files: Optional[list[discord.File]] = None,
    ) -> discord.Embed:

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
    def __init__(self, bot: Sentinel, **kwargs):
        self.bot = bot
        super().__init__(client=bot, **kwargs)

    async def interaction_check(self, itx: discord.Interaction, /) -> bool:
        await self.bot.udm.ensure_user(itx.user.id)
        if itx.type == discord.InteractionType.application_command:
            # TODO: automatically defer?
            pass
        return itx.user.id not in await self.bot.apg.fetch(
            "SELECT user_id FROM blacklist"
        )


class SentinelView(discord.ui.View):
    def __init__(
        self,
        ctx: SentinelContext,
        *,
        timeout: float | None = 600.0,
        disable_on_timeout: bool = True,
        any_responder: bool = False,
        any_channel: bool = False,
        any_guild: bool = False,
    ):
        self.message: Optional[discord.Message] = None
        self.ctx = ctx
        self.any_responder = any_responder
        self.any_channel = any_channel
        self.any_guild = any_guild

        super().__init__(timeout=timeout)

        if disable_on_timeout:
            self.on_timeout = self._disable_on_timeout

    async def prefab_close_button(
        self, itx: discord.Interaction, button: discord.ui.Button
    ):
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True
        await itx.response.edit_message(view=self)

    async def interaction_check(self, itx: discord.Interaction) -> bool:
        if not all(
            {
                await super().interaction_check(itx),
                self.ctx.author == itx.user or self.any_responder,
                self.ctx.channel == itx.channel or self.any_channel,
                self.ctx.guild == itx.guild or self.any_guild,
                not itx.user.bot,
            }
        ):
            await itx.response.send_message(
                "You do not have permission to use this screen.",
                ephemeral=True,
            )
            return False
        return True

    async def _disable_on_timeout(self) -> None:
        for child in self.children:
            if isinstance(child, (discord.ui.Button, discord.ui.Select)):
                child.disabled = True
        if self.message is not None:
            await self.message.edit(view=self)


class SentinelCog(commands.Cog):
    emoji: str
    hidden: bool

    def __init__(
        self,
        bot: Sentinel,
        emoji: Union[discord.Emoji, str] | None = None,
        *,
        hidden: bool | None = None,
    ):
        self.bot = bot
        self.emoji = str(emoji or self.emoji)
        self.hidden = hidden or self.hidden
        super().__init__()

    def __init_subclass__(
        cls,
        emoji: Union[discord.Emoji, str] = "\N{Black Question Mark Ornament}",
        hidden: bool = False,
    ) -> None:
        cls.emoji = str(emoji)
        cls.hidden = hidden

        super().__init_subclass__()

    async def cog_load(self) -> None:
        logging.debug(f"Cog Loaded: {self.__class__.__name__}")

    async def cog_unload(self) -> None:
        logging.debug(f"Cog Unloaded: {self.__class__.__name__}")

    def get_commands(self) -> list["TypedHybridCommand"]:
        new = []
        for command in super().get_commands():
            if not isinstance(command, commands.GroupMixin):
                new.append(command)
        return new

    def walk_commands(self) -> Generator["TypedHybridCommand", None, None]:
        return super().walk_commands()  # type: ignore


class SentinelAIOSession(aiohttp.ClientSession):
    def __init__(self):
        super().__init__(
            raise_for_status=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:101.0) Gecko/20100101 Firefox/101.0"
            },
        )
        self.cache: aioredis.Redis
    
    async def _build_cache(self):
        self.cache = await aioredis.from_url("redis://localhost", decode_responses=True)
    
    async def get(self, url: str, /, **kwargs) -> str:
        get_cache = kwargs.pop("get_cache", True)
        set_cache = kwargs.pop("set_cache", True)

        if get_cache:
            cached = await self.cache.get(url)
            if cached is not None and set_cache:
                return await self.get(url, get_cache=False, set_cache=True, **kwargs)
            
        response = await (await super().get(url, **kwargs)).read()

        if set_cache:
            await self.cache.set(url, response)
            self.cache.expire(url, int(datetime.now().timestamp() + 60*60))
        
        return response.decode()
    
    async def getjson(self, url: str, /, **kwargs) -> dict[str, Any]:
            
        response = await self.get(url, **kwargs)
        js:dict[str, Any] = json.loads(response)

        for key in kwargs.pop("route", []):
            js = js[key]

        return js


class SentinelDriver:
    def __init__(self):
        options = FirefoxOptions()
        options.headless = True
        options.binary_location = "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
        self.driver = SeleniumFirefox(
            options=options,
            executable_path="C:\\Program Files\\Mozilla Firefox\\geckodriver.exe",
            firefox_profile=FirefoxProfile(),
        )
        profile: FirefoxProfile = self.driver.firefox_profile  # type: ignore
        profile.add_extension("services/modify_headers_extension.xpi")

    async def get(self, url: str, /, wait: float = 0) -> str:
        thread_get = asyncio.to_thread(self.driver.get, url)
        await thread_get
        thread_get.close()
        await asyncio.sleep(wait)
        thread_return: Coroutine[Any, Any, str] = asyncio.to_thread(
            self.driver.execute_script, "return document.documentElement.outerHTML"
        )
        return await thread_return

    async def screenshot(self, url: str, /, wait: float = 0) -> io.BytesIO:
        thread_get = asyncio.to_thread(self.driver.get, url)
        await thread_get
        thread_get.close()
        await asyncio.sleep(wait)
        thread_return: Coroutine[Any, Any, bytes] = asyncio.to_thread(
            self.driver.get_screenshot_as_png
        )
        b = await thread_return
        buf = io.BytesIO(b)
        buf.seek(0)
        return buf

SENTINEL_MESSAGE_CACHE_KEY = tuple[int, int]
SENTINEL_MESSAGE_CACHE_VALUE = tuple[int, int, str, frozenset[str], int]
SENTINEL_MESSAGE_CACHE = dict[SENTINEL_MESSAGE_CACHE_KEY, set[SENTINEL_MESSAGE_CACHE_VALUE]]

class SentinelMessageCache(SENTINEL_MESSAGE_CACHE):
    def __init__(self, data: SENTINEL_MESSAGE_CACHE = dict(), *, limit: int = 100):
        self.limit = limit
        super().__init__(data)

    def __iter__(self) -> Iterator[SENTINEL_MESSAGE_CACHE_KEY]:
        return super().__iter__()

    def add(self, __key: SENTINEL_MESSAGE_CACHE_KEY, __value: SENTINEL_MESSAGE_CACHE_VALUE) -> None:
        if len(self[__key]) >= self.limit:
            self[__key].remove(self._get_min(self[__key]))
        self[__key].add(__value)


    def __getitem__(self, __key: Union[SENTINEL_MESSAGE_CACHE_KEY, "SentinelMessageCacheKey"]) -> set[SENTINEL_MESSAGE_CACHE_VALUE]:
        if isinstance(__key, SentinelMessageCacheKey):
            __key = __key.dismantle()
        try:
            return super().__getitem__(__key)
        except KeyError:
            default = set()
            self[__key] = default
            return default

    def _dismantle_set(self, __value: set["SentinelMessageCacheValue"]) -> set[SENTINEL_MESSAGE_CACHE_VALUE]:
        return set(map(lambda x: x.dismantle(), __value))
    
    def _get_min(self, __value: set[SENTINEL_MESSAGE_CACHE_VALUE]) -> SENTINEL_MESSAGE_CACHE_VALUE:
        return min(__value, key=lambda x: x[4])
    

@dataclass
class SentinelMessageCacheKey:
    guild_id: int
    channel_id: int

    def dismantle(self) -> SENTINEL_MESSAGE_CACHE_KEY:
        return self.guild_id, self.channel_id


@dataclass
class SentinelMessageCacheValue:
    message_id: int
    author_id: int
    content: str
    attachment_urls: frozenset[str]
    timestamp: int

    def dismantle(self) -> SENTINEL_MESSAGE_CACHE_VALUE:
        return self.message_id, self.author_id, self.content, self.attachment_urls, self.timestamp
    
    def __init__(
        self,
        message_id: int,
        author_id: int,
        content: str,
        attachment_urls: set[str] | frozenset[str],
        timestamp: int,
    ):
        self.message_id = message_id
        self.author_id = author_id
        self.content = content
        if isinstance(attachment_urls, set):
            self.attachment_urls = frozenset(attachment_urls)
        else:
            self.attachment_urls = attachment_urls
        self.timestamp = timestamp

async def _get_prefix(bot: Sentinel, message: discord.Message) -> str:
    if message.guild is None:
        return ">>"
    await bot.gdm.ensure_guild(message.guild.id)
    return await bot.gdm.get_prefix(message.guild.id)


SentinelCogT = TypeVar("SentinelCogT", bound=SentinelCog, covariant=True)


class TypedHybridCommandType(commands.HybridCommand, Generic[SentinelCogT, P, T]):
    pass


class TypedHybridGroupType(commands.HybridGroup, Generic[SentinelCogT, P, T]):
    @property
    def commands(self) -> list["TypedHybridCommand"]:
        return super().commands  # type: ignore


TypedHybridCommand = TypedHybridCommandType[SentinelCog, P, T]
TypedHybridGroup = TypedHybridGroupType[SentinelCog, P, T]
TypedHybrid = Union[TypedHybridCommand, TypedHybridGroup]
