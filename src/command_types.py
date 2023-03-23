import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Union
from bs4 import Tag
from discord import (
    VoiceChannel,
    StageChannel,
    TextChannel,
    CategoryChannel,
    ForumChannel,
    Thread,
)

VocalGuildChannel = Union[VoiceChannel, StageChannel]
GuildChannel = Union[VocalGuildChannel, ForumChannel, TextChannel, CategoryChannel]


@dataclass(kw_only=True)
class RTFMMeta:
    name: str
    href: str
    source_description: str


@dataclass(kw_only=True)
class MetaTagEntry:
    tag_id: int
    tag_name: str
    owner_id: int
    guild_id: int
    alias_to: int | None = None


@dataclass(kw_only=True)
class TagEntry(MetaTagEntry):
    tag_content: str
    created_at: datetime.datetime
    uses: int
    redirected_from: MetaTagEntry | None = None  # This is the tag name that was redirected to this tag. Is not stored in the database, as it depends on the alias used to get to this tag


@dataclass(kw_only=True)
class GuildEntry:
    guild_id: int
    prime_status: bool
    joined_at: datetime.datetime


@dataclass(kw_only=True)
class UserEntry:
    user_id: int
    balance: int


@dataclass(kw_only=True)
class GuildConfigEntry:
    guild_id: int
    prefix: str
    autoresponse_enabled: bool
    autoresponse_functions: list[str]
    allow_autoresponse_immunity: bool
    welcome_message_enabled: bool
    welcome_channel_id: int
    welcome_message_title: str
    welcome_message_body: str
    leave_message_enabled: bool
    leave_channel_id: int
    leave_message_title: str
    leave_message_body: str
    modlog_channel_id: int
    modlog_enabled: bool


@dataclass(kw_only=True)
class UserConfigEntry:
    user_id: int
    autoresponse_immune: bool


@dataclass(kw_only=True)
class SteamUser:
    avatar_url: str
    username: str
    persona_name: str
    custom_url: str
    time_created: datetime.datetime
    country_code: str
    state_code: str