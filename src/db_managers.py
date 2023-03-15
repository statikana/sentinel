import datetime
from enum import Enum
import random
import time
from typing import Optional, overload, Literal
import asyncpg

from config import DEFAULT_PREFIX

from .command_types import TagEntry, MetaTagEntry, GuildEntry, UserEntry
import discord


class SentinelDatabase:
    def __init__(self, apg: asyncpg.Pool):
        self.apg = apg


class UserManager(SentinelDatabase):
    """Should be used for getting and setting user data (currently only balance)"""

    async def ensure_user(self, user_id: int) -> None:
        await self.apg.execute(
            "INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
            user_id,
            0,
        )

    @overload
    async def get_balance(self, user_id: int, create_if_unfound: bool = True) -> int:
        pass

    @overload
    async def get_balance(
        self, user_id: int, create_if_unfound: bool = False
    ) -> int | None:
        pass

    async def get_balance(
        self, user_id: int, create_if_unfound: bool = True
    ) -> int | None:
        result = await self.apg.fetchrow(
            "SELECT balance FROM users WHERE user_id = $1", user_id
        )
        if result is None:
            if create_if_unfound:
                await self.apg.execute(
                    "INSERT INTO users (user_id, balance) VALUES ($1, $2)", user_id, 0
                )
                return 0
            else:
                return None
        else:
            return result["balance"]

    async def set_balance(
        self, user_id: int, balance: int, create_if_unfound: bool = True
    ) -> None:
        if create_if_unfound:
            await self.apg.execute(
                "INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = $2",
                user_id,
                balance,
            )
        else:
            await self.apg.execute(
                "UPDATE users SET balance = $2 WHERE user_id = $1", user_id, balance
            )

    async def modify_balance(
        self, user_id: int, amount: int, create_if_unfound: bool = True
    ) -> None:
        if create_if_unfound:
            await self.apg.execute(
                "INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = users.balance + $2",
                user_id,
                amount,
            )
        else:
            await self.apg.execute(
                "UPDATE users SET balance = users.balance + $2 WHERE user_id = $1",
                user_id,
                amount,
            )

    @overload
    async def give_balance(
        self,
        giver_id: int,
        receiver_id: int,
        amount: int,
        create_if_unfound: bool = True,
    ) -> tuple[bool, int, int]:
        pass

    @overload
    async def give_balance(
        self,
        giver_id: int,
        receiver_id: int,
        amount: int,
        create_if_unfound: bool = False,
    ) -> tuple[bool, int | None, int | None]:
        pass

    async def give_balance(
        self,
        giver_id: int,
        receiver_id: int,
        amount: int,
        create_if_unfound: bool = True,
    ) -> tuple[bool, int | None, int | None]:
        giver_bal = await self.get_balance(giver_id, create_if_unfound)
        rec_bal = await self.get_balance(receiver_id, create_if_unfound)
        # Either the giver doesn't have an account and we're not creating one, or they don't have enough money anyway
        # The balances will only be `None` if `create_if_unfound` is `False`
        if (
            (giver_bal is None)
            or (rec_bal is None)
            or (giver_bal is not None and giver_bal < amount)
        ):
            return (False, giver_bal, rec_bal)

        if create_if_unfound:
            await self.apg.execute(
                "INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = users.balance - $2",
                giver_id,
                amount,
            )
            await self.apg.execute(
                "INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = users.balance + $2",
                receiver_id,
                amount,
            )
        else:
            await self.apg.execute(
                "UPDATE users SET balance = users.balance - $2 WHERE user_id = $1",
                giver_id,
                amount,
            )
            await self.apg.execute(
                "UPDATE users SET balance = users.balance + $2 WHERE user_id = $1",
                receiver_id,
                amount,
            )
        return (True, giver_bal - amount, rec_bal + amount)


class TagsManager(SentinelDatabase):
    def __init__(self, apg: asyncpg.Pool):
        super().__init__(apg)
        self.gdm = GuildManager(apg)
        self.usm = UserManager(apg)

    @overload
    async def get_tag_by_name(
        self, guild_id: int, tag_name: str, *, allow_redirect: Literal[False]
    ) -> TagEntry | MetaTagEntry | None:
        pass

    @overload
    async def get_tag_by_name(
        self, guild_id: int, tag_name: str, *, allow_redirect: Literal[True]
    ) -> TagEntry | None:
        pass

    async def get_tag_by_name(
        self, guild_id: int, tag_name: str, *, allow_redirect: bool
    ) -> TagEntry | MetaTagEntry | None:
        meta_result = await self.apg.fetchrow(
            "SELECT * FROM tag_meta WHERE guild_id = $1 AND tag_name = $2",
            guild_id,
            tag_name,
        )
        updated_meta_result: asyncpg.Record | None = None
        if meta_result is None:
            return None
        redirected: bool
        resolved_id: int
        if meta_result["alias_to"] is not None:
            if allow_redirect:
                updated_meta_result = await self.apg.fetchrow(
                    "SELECT * FROM tag_meta WHERE tag_id = $1",
                    meta_result["alias_to"],
                )
                resolved_id = meta_result["alias_to"]
                redirected = True
            else:
                return self._form_meta_tag(meta_result)
        else:
            resolved_id = meta_result["tag_id"]
            redirected = False

        full_result = await self.apg.fetchrow(
            "SELECT * FROM tags WHERE tag_id = $1", resolved_id
        )
        return self._form_tag(
            updated_meta_result if redirected else meta_result,
            full_result,
            self._form_meta_tag(meta_result) if redirected else None,
        )
        # if we were redirected, give the origianl name that was queried

    async def get_tag_by_id(self, tag_id: int) -> TagEntry | None:
        meta_result = await self.apg.fetchrow(
            "SELECT * FROM tag_meta WHERE tag_id = $1", tag_id
        )
        if meta_result is None:
            return None
        full_result = await self.apg.fetchrow(
            "SELECT * FROM tags WHERE tag_id = $1", tag_id
        )
        return self._form_tag(meta_result, full_result)

    async def get_tags_by_owner(self, owner_id: int) -> list[TagEntry]:
        tag_data = await self.apg.fetch(
            "SELECT * FROM tag_meta INNER JOIN tags ON tag_meta.tag_id = tags.tag_id WHERE owner_id = $1",
            owner_id,
        )
        tags = []
        for tag_node in tag_data:
            tags.append(
                self._form_tag(tag_node, tag_node)
            )  # does this count as duck typing?
        return tags

    async def get_tags_in_guild(self, guild_id: int) -> list[TagEntry]:
        tag_data = await self.apg.fetch(
            "SELECT tag_id, alias_to FROM tag_meta WHERE guild_id = $1", guild_id
        )
        tags = []
        for tag_node in tag_data:
            if tag_node["alias_to"] is not None:
                continue
            tags.append(await self.get_tag_by_id(tag_node["tag_id"]))
        return tags

    async def create_tag(
        self, tag_name: str, tag_content: str, owner_id: int, guild_id: int
    ) -> "ReturnCode":

        tag_id = self._generate_tag_id(owner_id, guild_id)

        meta_result = await self.apg.execute(
            "INSERT INTO tag_meta (tag_id, owner_id, guild_id, tag_name) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING RETURNING *",
            tag_id,
            owner_id,
            guild_id,
            tag_name,
        )
        if meta_result is None:
            return ReturnCode.ALREADY_EXISTS
        full_result = await self.apg.execute(
            "INSERT INTO tags (tag_id, tag_content) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            tag_id,
            tag_content,
        )
        if full_result is None:
            await self.apg.execute("DELETE FROM tag_meta WHERE tag_id = $1", tag_id)
            return ReturnCode.ALREADY_EXISTS
        return ReturnCode.SUCCESS

    async def edit_tag_by_name(
        self,
        tag_name: str,
        new_content: str,
        guild_id: int,
        *,
        owner_id: int | None = None
    ) -> "ReturnCode":
        tag = await self.get_tag_by_name(guild_id, tag_name, allow_redirect=True)
        if tag is None:
            return ReturnCode.NOT_FOUND
        if owner_id is not None and tag.owner_id != owner_id:
            return ReturnCode.MISSING_PERMISSIONS
        await self.apg.execute(
            "UPDATE tags SET tag_content = $1 WHERE tag_id = $2",
            new_content,
            tag.tag_id,
        )
        return ReturnCode.SUCCESS

    async def edit_tag_by_id(
        self, tag_id: int, new_content: str, owner_id: int | None = None
    ) -> "ReturnCode":
        tag = await self.get_tag_by_id(tag_id)
        if tag is None:
            return ReturnCode.NOT_FOUND
        if owner_id is not None and tag.owner_id != owner_id:
            return ReturnCode.MISSING_PERMISSIONS
        await self.apg.execute(
            "UPDATE tags SET tag_content = $1 WHERE tag_id = $2",
            new_content,
            tag.tag_id,
        )
        return ReturnCode.SUCCESS

    async def delete_tag_by_name(
        self, tag_name: str, guild_id: int, owner_id: int | None = None
    ) -> "ReturnCode":
        tag = await self.get_tag_by_name(guild_id, tag_name, allow_redirect=False)
        if tag is None:
            return ReturnCode.NOT_FOUND
        if isinstance(tag, MetaTagEntry):
            return ReturnCode.NOT_ALIAS
        if owner_id is not None and tag.owner_id != owner_id:
            return ReturnCode.MISSING_PERMISSIONS
        await self.apg.execute("DELETE FROM tag_meta WHERE tag_id = $1", tag.tag_id)
        return ReturnCode.SUCCESS

    async def delete_tag_by_id(
        self, tag_id: int, owner_id: int | None = None
    ) -> "ReturnCode":
        tag = await self.get_tag_by_id(tag_id)
        if tag is None:
            return ReturnCode.NOT_FOUND
        if owner_id is not None and tag.owner_id != owner_id:
            return ReturnCode.MISSING_PERMISSIONS
        await self.apg.execute("DELETE FROM tag_meta WHERE tag_id = $1", tag.tag_id)
        return ReturnCode.SUCCESS

    async def create_alias(
        self,
        tag_name: str,
        alias_to: int,
        owner_id: int,
        guild_id: int,
    ) -> "ReturnCode":
        result = await self.apg.execute(
            "INSERT INTO tag_meta (tag_id, tag_name, owner_id, guild_id, alias_to) VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING RETURNING *",
            self._generate_tag_id(owner_id, guild_id),
            tag_name,
            owner_id,
            guild_id,
            alias_to,
        )
        if result is None or result == "INSERT 0 0":
            return ReturnCode.ALREADY_EXISTS
        return ReturnCode.SUCCESS

    async def delete_alias(
        self, tag_name: str, guild_id: int, owner_id: int | None = None
    ) -> "ReturnCode":
        tag = await self.get_tag_by_name(guild_id, tag_name, allow_redirect=False)
        if tag is None:
            return ReturnCode.NOT_FOUND
        if not isinstance(tag, MetaTagEntry):
            return ReturnCode.NOT_ALIAS
        if owner_id is not None and tag.owner_id != owner_id:
            return ReturnCode.MISSING_PERMISSIONS
        await self.apg.execute("DELETE FROM tag_meta WHERE tag_id = $1", tag.tag_id)
        return ReturnCode.SUCCESS

    async def increment_tag_uses(self, tag_id: int, amount: int = 1) -> None:
        await self.apg.execute(
            "UPDATE tags SET tag_uses = tag_uses + $2 WHERE tag_id = $1",
            tag_id,
            amount,
        )

    async def transfer_tag_ownership(
        self, tag_id: int, new_owner_id: int, owner_id: int | None = None
    ) -> "ReturnCode":
        tag = await self.get_tag_by_id(tag_id)
        if tag is None:
            return ReturnCode.NOT_FOUND
        if owner_id is not None and tag.owner_id != owner_id:
            return ReturnCode.MISSING_PERMISSIONS
        await self.apg.execute(
            "UPDATE tag_meta SET owner_id = $2 WHERE tag_id = $1",
            tag_id,
            new_owner_id,
        )
        return ReturnCode.SUCCESS

    def _generate_tag_id(self, owner_id: int, guild_id: int) -> int:
        return int((int(time.time()) | owner_id | guild_id))

    def _form_tag(
        self, meta_result, full_result, redirected_from: Optional[MetaTagEntry] = None
    ) -> TagEntry:
        return TagEntry(
            tag_id=full_result["tag_id"],
            tag_name=meta_result["tag_name"],
            uses=full_result["tag_uses"],
            owner_id=meta_result["owner_id"],
            guild_id=meta_result["guild_id"],
            tag_content=full_result["tag_content"],
            created_at=full_result["created_at"],
            redirected_from=redirected_from,
        )

    def _form_meta_tag(self, result) -> MetaTagEntry:
        return MetaTagEntry(
            tag_id=result["tag_id"],
            tag_name=result["tag_name"],
            owner_id=result["owner_id"],
            guild_id=result["guild_id"],
            alias_to=result["alias_to"],
        )


class GuildManager(SentinelDatabase):
    async def ensure_guild(
        self, guild_id: int, prime_status: bool = False, *, safe_insert: bool = True
    ) -> GuildEntry:
        query = "INSERT INTO guilds(guild_id, prime_status) VALUES ($1, $2)"
        if safe_insert:
            query += " ON CONFLICT DO NOTHING"
        query += " RETURNING *"
        result = await self.apg.execute(query, guild_id, prime_status)
        if isinstance(result, str):
            result = await self.apg.fetchrow(
                "SELECT * FROM guilds WHERE guild_id = $1", guild_id
            )  # DO NOTHING clause messes with RETURNING
        return self._form_guild(result)

    async def get_guild(self, guild_id: int) -> GuildEntry | None:
        result = await self.apg.fetchrow(
            "SELECT * FROM guilds WHERE guild_id = $1", guild_id
        )
        if result is None:
            return None
        return self._form_guild(result)

    async def get_all_guilds(self) -> list[GuildEntry]:
        results = await self.apg.fetch("SELECT * FROM guilds")
        return [self._form_guild(result) for result in results]

    async def get_guild_exists(self, guild_id: int) -> bool:
        return (
            await self.apg.fetchrow(
                "SELECT * FROM guilds WHERE guild_id = $1", guild_id
            )
            is not None
        )

    async def get_guilds_by_prime_status(self, prime_status: bool) -> list[GuildEntry]:
        results = await self.apg.fetch(
            "SELECT * FROM guilds WHERE prime_status = $1", prime_status
        )
        return [self._form_guild(result) for result in results]

    async def leave_guild(self, guild_id: int) -> bool:
        result = await self.apg.execute(
            "DELETE FROM guilds WHERE guild_id = $1 RETURNING *", guild_id
        )
        return result is not None

    async def set_guild_prime_status(self, guild_id: int, prime_status: bool) -> bool:
        result = await self.apg.execute(
            "UPDATE guilds SET prime_status = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            prime_status,
        )
        return result is not None

    async def set_guild_joined_at(
        self, guild_id: int, joined_at: datetime.datetime
    ) -> bool:
        result = await self.apg.execute(
            "UPDATE guilds SET joined_at = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            joined_at,
        )
        return result is not None

    async def get_prefix(self, guild_id: int) -> str:
        result = await self.apg.fetchrow(
            "SELECT prefix FROM guilds WHERE guild_id = $1", guild_id
        )
        return result["prefix"]

    def _form_guild(self, result) -> GuildEntry:
        return GuildEntry(
            guild_id=result["guild_id"],
            prime_status=result["prime_status"],
            joined_at=result["joined_at"],
        )


class ReturnCode(Enum):
    SUCCESS = 0
    ALREADY_EXISTS = 1
    NOT_FOUND = 2
    MISSING_PERMISSIONS = 3
    IS_ALIAS = 4
    NOT_ALIAS = 5
    UNKNOWN_ERROR = 6
