import datetime
from dataclasses import dataclass


@dataclass(kw_only=True)
class RTFMMeta:
    name: str
    href: str
    source_description: str


@dataclass(kw_only=True)
class MetaTagEntry:
    tag_id: int
    tag_name: str
    uses: int
    guild_id: int
    alias_to: int | None = None


@dataclass(kw_only=True)
class TagEntry(MetaTagEntry):
    owner_id: int
    tag_content: str
    created_at: datetime.datetime


@dataclass(kw_only=True)
class GuildEntry:
    guild_id: int
    prime_status: bool
    joined_at: datetime.datetime


@dataclass(kw_only=True)
class UserEntry:
    user_id: int
    balance: int
