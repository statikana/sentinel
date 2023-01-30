import datetime
import random
import time
from typing import overload
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

    async def get_tag_by_name(self, guild_id: int, tag_name: str) -> TagEntry | None:
        meta_result = await self.apg.fetchrow(
            "SELECT * FROM tag_meta WHERE guild_id = $1 AND tag_name = $2",
            guild_id,
            tag_name,
        )
        if meta_result is None:
            return None

        search_id: int
        if meta_result["alias_to"] is not None:
            search_id = meta_result["alias_to"]
        else:
            search_id = meta_result["tag_id"]

        full_result = await self.apg.fetchrow(
            "SELECT * FROM tags WHERE tag_id = $1", search_id
        )
        if full_result is None:  # Should never happen
            await self.apg.execute(
                "DELETE FROM tag_meta WHERE tag_id = $1", search_id
            )  # At some point in time this tag was deleted, but the meta wasn't. Delete the meta, cascades to main table
            return None
        return self._form_tag(meta_result, full_result)

    async def get_tag_by_id(self, tag_id: int) -> TagEntry | None:
        meta_result = await self.apg.fetchrow(
            "SELECT * FROM tag_meta WHERE tag_id = $1", tag_id
        )
        if meta_result is None:
            return None

        search_id: int
        if meta_result["alias_to"] is not None:
            search_id = meta_result["alias_to"]
        else:
            search_id = meta_result["tag_id"]

        full_result = await self.apg.fetchrow(
            "SELECT * FROM tags WHERE tag_id = $1", search_id
        )
        if full_result is None:
            await self.apg.execute("DELETE FROM tag_meta WHERE tag_id = $1", search_id)
            return None

        return self._form_tag(meta_result, full_result)

    async def get_tags_by_owner(self, owner_id: int) -> list[TagEntry]:
        tag_ids = await self.apg.fetch(
            "SELECT tag_id FROM tags WHERE owner_id = $1", owner_id
        )
        tags = []
        for tag_id in tag_ids:
            tags.append(await self.get_tag_by_id(tag_id["tag_id"]))
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

    @overload
    async def create_tag(
        self,
        tag_name: str,
        tag_content: str,
        owner_id: int,
        guild_id: int,
        *,
        safe_insert: bool = False
    ) -> TagEntry:
        pass

    @overload
    async def create_tag(
        self,
        tag_name: str,
        tag_content: str,
        owner_id: int,
        guild_id: int,
        *,
        safe_insert: bool = True
    ) -> TagEntry | None:
        pass

    async def create_tag(
        self,
        tag_name: str,
        tag_content: str,
        owner_id: int,
        guild_id: int,
        *,
        safe_insert: bool = True
    ) -> TagEntry | None:

        tag_id = self._generate_tag_id(owner_id, guild_id)
        if safe_insert:
            if await self.get_tag_by_name(guild_id, tag_name) is not None:
                return None

        full_tag = await self.apg.execute(
            # "INSERT INTO tags (tag_id, owner_id, tag_content) VALUES ($1, $2, $3) ON CONFLICT DO UPDATE SET tag_id = $1, owner_id = $2, tag_content = $3 RETURNING *",
            "INSERT INTO tags (tag_id, owner_id, tag_content) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING RETURNING *",
            tag_id,
            owner_id,
            tag_content,
        )
        if isinstance(full_tag, str):
            full_tag = await self.apg.fetchrow(
                "SELECT * FROM tags WHERE tag_id = $1", tag_id
            )
        tag_meta = await self.apg.execute(
            # "INSERT INTO tag_meta (tag_id, tag_name, guild_id) VALUES ($1, $2, $3) ON CONFLICT DO UPDATE SET tag_id = $1, tag_name = $2, guild_id = $3 RETURING *",
            "INSERT INTO tag_meta (tag_id, tag_name, guild_id) VALUES ($1, $2, $3) ON CONFLICT DO NOTHING RETURNING *",
            tag_id,
            tag_name,
            guild_id,
        )
        if isinstance(tag_meta, str):
            tag_meta = await self.apg.fetchrow(
                "SELECT * FROM tag_meta WHERE tag_id = $1", tag_id
            )
        return self._form_tag(tag_meta, full_tag)

    async def get_tag_exists_by_name(self, guild_id: int, tag_name: str) -> bool:
        return (
            await self.apg.fetchrow(
                "SELECT * FROM tag_meta WHERE guild_id = $1 AND tag_name = $2",
                guild_id,
                tag_name,
            )
            is not None
        )

    async def get_tag_exists_by_id(self, tag_id: int) -> bool:
        return (
            await self.apg.fetchrow("SELECT * FROM tags WHERE tag_id = $1", tag_id)
            is not None
        )

    async def edit_tag_by_name(
        self,
        tag_name: str,
        guild_id: int,
        new_content: str,
        check_tag_owner: bool = True,
        check_tag_exists: bool = True,
        owner_id: int | None = None,
    ) -> bool:
        if check_tag_owner or check_tag_exists:
            tag = await self.get_tag_by_name(guild_id, tag_name)
            if check_tag_exists and (tag is None or tag.alias_to is not None):
                return False
            if check_tag_owner and tag is not None and tag.owner_id != owner_id:
                return False
        tag_id = await self.apg.fetchrow(
            "SELECT tag_id FROM tag_meta WHERE tag_name = $1 AND guild_id = $2",
            tag_name,
            guild_id,
        )
        if tag_id is None:
            return False
        await self.apg.execute(
            "UPDATE tags SET tag_content = $1 WHERE tag_id = $2",
            new_content,
            tag_id["tag_id"],
        )
        return True

    async def delete_tag_by_name(
        self,
        tag_name: str,
        guild_id: int,
        check_tag_owner: bool = True,
        check_tag_exists: bool = True,
        owner_id: int | None = None,
    ) -> bool:
        if check_tag_owner or check_tag_exists:
            tag = await self.get_tag_by_name(guild_id, tag_name)
            if check_tag_exists and (tag is None or tag.alias_to is not None):
                return False
            if check_tag_owner and tag is not None and tag.owner_id != owner_id:
                return False

        await self.apg.execute(
            "DELETE FROM tags WHERE tag_name = $1 AND guild_id = $2", tag_name, guild_id
        )  # Should cascade to tag_meta
        return True

    async def delete_tag_by_id(self, tag_id: int) -> bool:
        tag = await self.get_tag_by_id(tag_id)
        if tag is None:
            return False
        await self.apg.execute(
            "DELETE FROM tags WHERE tag_id = $1", tag_id
        )  # Should cascade to tag_meta
        return True

    async def create_alias(
        self, tag_name: str, owner_id: int, guild_id: int, alias_to: int
    ):
        # Tag aliases exist only within tag_meta
        tag_id = self._generate_tag_id(owner_id, guild_id)
        await self.apg.execute(
            "INSERT INTO tag_meta (tag_id, tag_name, guild_id, alias_to) VALUES ($1, $2, $3, $4) ON CONFLICT DO NOTHING",
            tag_id,
            tag_name,
            guild_id,
            alias_to,
        )

    async def delete_alias(self, tag_name: str, guild_id: int) -> bool:
        result = await self.apg.execute(
            "DELETE FROM tag_meta WHERE tag_name = $1 AND guild_id = $2 RETURING *",
            tag_name,
            guild_id,
        )
        return result is not None

    async def increment_tag_uses(self, tag_id: int, amount: int = 1):
        await self.apg.execute(
            "UPDATE tag_meta SET tag_uses = tag_uses + $2 WHERE tag_id = $1",
            tag_id,
            amount,
        )

    async def transfer_tag_ownership(self, tag_id: int, new_owner_id: int) -> None:
        await self.apg.execute(
            "UPDATE tags SET owner_id = $1 WHERE tag_id = $2", new_owner_id, tag_id
        )

    def _generate_tag_id(self, owner_id: int, guild_id: int) -> int:
        return (int(time.time()) | owner_id << 32 | guild_id << 48) ** 0.25

    def _form_tag(self, meta_result, full_result) -> TagEntry:
        return TagEntry(
            tag_id=full_result["tag_id"],
            tag_name=meta_result["tag_name"],
            uses=meta_result["tag_uses"],
            guild_id=meta_result["guild_id"],
            owner_id=full_result["owner_id"],
            tag_content=full_result["tag_content"],
            created_at=full_result["created_at"],
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
