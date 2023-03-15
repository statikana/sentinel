import datetime
from dataclasses import dataclass
from typing import Union
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
