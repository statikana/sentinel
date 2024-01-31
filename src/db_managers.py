import datetime
from enum import Enum
import time
from typing import Optional, overload, Literal
import asyncpg

from .command_types import TagEntry, MetaTagEntry, GuildEntry, GuildConfigEntry

class SentinelDatabase:
    def __init__(self, apg: asyncpg.Pool):
        self.apg = apg


class UserDataManager(SentinelDatabase):
    """Should be used for getting and setting user data (currently only balance)"""

    async def ensure_user(self, user_id: int) -> None:
        await self.apg.execute(
            "INSERT INTO user_data (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
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
            "SELECT balance FROM user_data WHERE user_id = $1", user_id
        )
        if result is None:
            if create_if_unfound:
                await self.apg.execute(
                    "INSERT INTO user_data (user_id, balance) VALUES ($1, $2)", user_id, 0
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
                "INSERT INTO user_data (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = $2",
                user_id,
                balance,
            )
        else:
            await self.apg.execute(
                "UPDATE user_data SET balance = $2 WHERE user_id = $1", user_id, balance
            )

    async def modify_balance(
        self, user_id: int, amount: int, create_if_unfound: bool = True
    ) -> None:
        if create_if_unfound:
            await self.apg.execute(
                "INSERT INTO user_data (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = user_data.balance + $2",
                user_id,
                amount,
            )
        else:
            await self.apg.execute(
                "UPDATE user_data SET balance = user_data.balance + $2 WHERE user_id = $1",
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
    ) -> tuple[bool, int | None, int | None]:
        giver_bal = await self.get_balance(giver_id, create_if_unfound=True)
        rec_bal = await self.get_balance(receiver_id, create_if_unfound=True)

        # here, we assume that the balances have already
        # been checked for validity (ie, this person has enough to give 5 away)

        await self.apg.execute(
            "UPDATE user_data SET balance = user_data.balance - $2 WHERE user_id = $1",
            giver_id,
            amount,
        )
        await self.apg.execute(
            "UPDATE user_data SET balance = user_data.balance + $2 WHERE user_id = $1",
            receiver_id,
            amount,
        )
        return True, giver_bal - amount, rec_bal + amount

    async def add_tokens(self, user_id: int, amount: int) -> int:
        tokens: int = int(await self.apg.execute(
            "INSERT INTO user_data (user_id, tokens) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET tokens = user_data.tokens + $2 RETURNING tokens",
            user_id,
            amount,
        ))
        return tokens

    async def get_tokens(self, user_id: int) -> int:
        tokens: int = await self.apg.fetchval(
            "SELECT tokens FROM user_data WHERE user_id = $1",
            user_id,
        )
        return tokens

    async def set_tokens(self, user_id: int, amount: int) -> int:
        await self.apg.execute(
            """
            INSERT INTO user_data (user_id, tokens) VALUES ($1, $2)
            ON CONFLICT (user_id) DO UPDATE SET tokens = $2
            """
        )
        return amount
    
    async def try_hourly(self, user_id: int, success_amount: int) -> bool:
        await self.ensure_user(user_id)
        result = await self.apg.fetchval(
            """
            SELECT next_hourly FROM user_data WHERE user_id = $1
            """,
            user_id,
        )
        if result is not None and datetime.datetime.utcnow() > result:
            await self.apg.execute(
                """
                UPDATE user_data SET next_hourly = $2, balance = balance + $3 WHERE user_id = $1
                """,
                user_id,
                datetime.datetime.utcnow() + datetime.timedelta(hours=1),
                success_amount,
            )
            return True
        return False
    
    async def get_next_hourly(self, user_id: int) -> datetime.datetime:
        await self.ensure_user(user_id)
        return await self.apg.fetchval(
            """
            SELECT next_hourly FROM user_data WHERE user_id = $1
            """,
            user_id,
        ) # type: ignore
    
    async def try_daily(self, user_id: int, success_amount: int) -> bool:
        await self.ensure_user(user_id)
        result = await self.apg.fetchval(
            """
            SELECT next_daily FROM user_data WHERE user_id = $1
            """,
            user_id,
        )
        if result is not None and datetime.datetime.utcnow() > result:
            await self.apg.execute(
                """
                UPDATE user_data SET next_daily = $2, balance = balance + $3 WHERE user_id = $1
                """,
                user_id,
                datetime.datetime.utcnow() + datetime.timedelta(days=1),
                success_amount,
            )
            return True
        return False
    
    async def get_next_daily(self, user_id: int) -> datetime.datetime:
        await self.ensure_user(user_id)
        return await self.apg.fetchval(
            """
            SELECT next_daily FROM user_data WHERE user_id = $1
            """,
            user_id,
        ) # type: ignore
    
    async def try_weekly(self, user_id: int, success_amount: int) -> bool:
        await self.ensure_user(user_id)
        result = await self.apg.fetchval(
            """
            SELECT next_weekly FROM user_data WHERE user_id = $1
            """,
            user_id,
        )
        if result is not None and datetime.datetime.utcnow() > result:
            await self.apg.execute(
                """
                UPDATE user_data SET next_weekly = $2, balance = balance + $3 WHERE user_id = $1
                """,
                user_id,
                datetime.datetime.utcnow() + datetime.timedelta(days=7),
                success_amount,
            )
            return True
        return False
    
    async def get_next_weekly(self, user_id: int) -> datetime.datetime:
        await self.ensure_user(user_id)
        return await self.apg.fetchval(
            """
            SELECT next_weekly FROM user_data WHERE user_id = $1
            """,
            user_id,
        ) # type: ignore

    async def try_monthly(self, user_id: int, success_amount: int) -> bool:
        await self.ensure_user(user_id)
        result = await self.apg.fetchval(
            """
            SELECT next_monthly FROM user_data WHERE user_id = $1
            """,
            user_id,
        )
        if result is not None and datetime.datetime.utcnow() > result:
            await self.apg.execute(
                """
                UPDATE user_data SET next_monthly = $2, balance = balance + $3 WHERE user_id = $1
                """,
                user_id,
                datetime.datetime.utcnow() + datetime.timedelta(days=30),
                success_amount,
            )
            return True
        return False
    
    async def get_next_monthly(self, user_id: int) -> datetime.datetime:
        await self.ensure_user(user_id)
        return await self.apg.fetchval(
            """
            SELECT next_monthly FROM user_data WHERE user_id = $1
            """,
            user_id,
        ) # type: ignore
    






class TagDataManager(SentinelDatabase):
    def __init__(self, apg: asyncpg.Pool):
        super().__init__(apg)
        self.gdm = GuildDataManager(apg)
        self.usm = UserDataManager(apg)

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
            "SELECT * FROM tag_data WHERE tag_id = $1", resolved_id
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
            "SELECT * FROM tag_data WHERE tag_id = $1", tag_id
        )
        return self._form_tag(meta_result, full_result)

    async def get_tags_by_owner(self, owner_id: int) -> list[TagEntry]:
        tag_data = await self.apg.fetch(
            "SELECT * FROM tag_meta INNER JOIN tag_data ON tag_meta.tag_id = tag_data.tag_id WHERE owner_id = $1",
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
            "INSERT INTO tag_data (tag_id, tag_content) VALUES ($1, $2) ON CONFLICT DO NOTHING",
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
            "UPDATE tag_data SET tag_content = $1 WHERE tag_id = $2",
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
            "UPDATE tag_data SET tag_content = $1 WHERE tag_id = $2",
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
            "UPDATE tag_data SET tag_uses = tag_uses + $2 WHERE tag_id = $1",
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


class GuildDataManager(SentinelDatabase):
    async def ensure_guild(
        self, guild_id: int, prime_status: bool = False, *, safe_insert: bool = True
    ) -> GuildEntry:
        query = "INSERT INTO guild_data(guild_id, prime_status) VALUES ($1, $2)"
        if safe_insert:
            query += " ON CONFLICT DO NOTHING"
        query += " RETURNING *"
        result = await self.apg.execute(query, guild_id, prime_status)
        if isinstance(result, str):
            result = await self.apg.fetchrow(
                "SELECT * FROM guild_data WHERE guild_id = $1", guild_id
            )  # DO NOTHING clause messes with RETURNING
        return self._form_guild(result)

    async def get_guild(self, guild_id: int) -> GuildEntry | None:
        result = await self.apg.fetchrow(
            "SELECT * FROM guild_data WHERE guild_id = $1", guild_id
        )
        if result is None:
            return None
        return self._form_guild(result)

    async def get_all_guilds(self) -> list[GuildEntry]:
        results = await self.apg.fetch("SELECT * FROM guild_data")
        return [self._form_guild(result) for result in results]

    async def get_guild_exists(self, guild_id: int) -> bool:
        return (
            await self.apg.fetchrow(
                "SELECT * FROM guild_data WHERE guild_id = $1", guild_id
            )
            is not None
        )

    async def get_guilds_by_prime_status(self, prime_status: bool) -> list[GuildEntry]:
        results = await self.apg.fetch(
            "SELECT * FROM guild_data WHERE prime_status = $1", prime_status
        )
        return [self._form_guild(result) for result in results]

    async def leave_guild(self, guild_id: int) -> bool:
        result = await self.apg.execute(
            "DELETE FROM guild_data WHERE guild_id = $1 RETURNING *", guild_id
        )
        return result is not None

    async def set_guild_prime_status(self, guild_id: int, prime_status: bool) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_data SET prime_status = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            prime_status,
        )
        return result is not None

    async def set_guild_joined_at(
        self, guild_id: int, joined_at: datetime.datetime
    ) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_data SET joined_at = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            joined_at,
        )
        return result is not None

    async def get_prefix(self, guild_id: int) -> str:
        result = await self.apg.fetchrow(
            "SELECT prefix FROM guild_data WHERE guild_id = $1", guild_id
        )
        return result["prefix"]

    def _form_guild(self, result) -> GuildEntry:
        return GuildEntry(
            guild_id=result["guild_id"],
            prime_status=result["prime_status"],
            joined_at=result["joined_at"],
        )


class GuildConfigManager(SentinelDatabase):
    def _form_guild_config(self, result) -> GuildConfigEntry:
        return GuildConfigEntry(
            guild_id=result["guild_id"],
            prefix=result["prefix"],
            autoresponse_functions=result["autoresponse_functions"],
            autoresponse_enabled=result["autoresponse_enabled"],
            allow_autoresponse_immunity=result["allow_autoresponse_immunity"],
            welcome_channel_id=result["welcome_channel_id"],
            welcome_message_title=result["welcome_message_title"],
            welcome_message_body=result["welcome_message_body"],
            welcome_message_enabled=result["welcome_message_enabled"],
            leave_channel_id=result["leave_channel_id"],
            leave_message_title=result["leave_message_title"],
            leave_message_body=result["leave_message_body"],
            leave_message_enabled=result["leave_message_enabled"],
            modlog_channel_id=result["modlog_channel_id"],
            modlog_enabled=result["modlog_enabled"],
        )

    async def get_guild_config(self, guild_id: int) -> GuildConfigEntry | None:
        result = await self.apg.fetchrow(
            "SELECT * FROM guild_configs WHERE guild_id = $1", guild_id
        )
        if result is None:
            return None
        return self._form_guild_config(result)
    
    async def ensure_guild_config(self, guild_id: int) -> GuildConfigEntry:
        result = await self.apg.fetchrow(
            "INSERT INTO guild_configs(guild_id) VALUES ($1) ON CONFLICT DO NOTHING RETURNING *",
            guild_id,
        )
        if result is None:
            result = await self.apg.fetchrow(
                "SELECT * FROM guild_configs WHERE guild_id = $1", guild_id
            )
        return self._form_guild_config(result)
    
    async def get_prefix(self, guild_id: int) -> str:
        result = await self.apg.fetchrow(
            "SELECT prefix FROM guild_configs WHERE guild_id = $1", guild_id
        )
        return result["prefix"]
    
    async def set_prefix(self, guild_id: int, prefix: str) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_configs SET prefix = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            prefix,
        )
        return result is not None
    
    async def get_autoresponse_functions(self, guild_id: int) -> list[str]:
        result = await self.apg.fetchrow(
            "SELECT autoresponse_functions FROM guild_configs WHERE guild_id = $1", guild_id
        )
        return result["autoresponse_functions"]
    
    async def set_autoresponse_functions(self, guild_id: int, functions: list[str]) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_configs SET autoresponse_functions = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            functions,
        )
        return result is not None
    
    async def get_autoresponse_enabled(self, guild_id: int) -> bool:
        result = await self.apg.fetchrow(
            "SELECT autoresponse_enabled FROM guild_configs WHERE guild_id = $1", guild_id
        )
        return result["autoresponse_enabled"]
    
    async def set_autoresponse_enabled(self, guild_id: int, enabled: bool) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_configs SET autoresponse_enabled = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            enabled,
        )
        return result is not None
    
    async def get_allow_autoresponse_immunity(self, guild_id: int) -> bool:
        result = await self.apg.fetchrow(
            "SELECT allow_autoresponse_immunity FROM guild_configs WHERE guild_id = $1", guild_id
        )
        return result["allow_autoresponse_immunity"]
    
    async def set_allow_autoresponse_immunity(self, guild_id: int, enabled: bool) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_configs SET allow_autoresponse_immunity = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            enabled,
        )
        return result is not None
    
    async def get_welcome_channel_id(self, guild_id: int) -> int:
        result = await self.apg.fetchrow(
            "SELECT welcome_channel_id FROM guild_configs WHERE guild_id = $1", guild_id
        )
        return result["welcome_channel_id"]
    
    async def set_welcome_channel_id(self, guild_id: int, channel_id: int) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_configs SET welcome_channel_id = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            channel_id,
        )
        return result is not None
    
    async def get_welcome_message_title(self, guild_id: int) -> str:
        result = await self.apg.fetchrow(
            "SELECT welcome_message_title FROM guild_configs WHERE guild_id = $1", guild_id
        )
        return result["welcome_message_title"]
    
    async def set_welcome_message_title(self, guild_id: int, title: str) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_configs SET welcome_message_title = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            title,
        )
        return result is not None
    
    async def get_welcome_message_body(self, guild_id: int) -> str:
        result = await self.apg.fetchrow(
            "SELECT welcome_message_body FROM guild_configs WHERE guild_id = $1", guild_id
        )
        return result["welcome_message_body"]
    
    async def set_welcome_message_body(self, guild_id: int, body: str) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_configs SET welcome_message_body = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            body,
        )
        return result is not None
    
    async def get_welcome_message_enabled(self, guild_id: int) -> bool:
        result = await self.apg.fetchrow(
            "SELECT welcome_message_enabled FROM guild_configs WHERE guild_id = $1", guild_id
        )
        return result["welcome_message_enabled"]
    
    async def set_welcome_message_enabled(self, guild_id: int, enabled: bool) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_configs SET welcome_message_enabled = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            enabled,
        )
        return result is not None
    
    async def get_leave_channel_id(self, guild_id: int) -> int:
        result = await self.apg.fetchrow(
            "SELECT leave_channel_id FROM guild_configs WHERE guild_id = $1", guild_id
        )
        return result["leave_channel_id"]
    
    async def set_leave_channel_id(self, guild_id: int, channel_id: int) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_configs SET leave_channel_id = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            channel_id,
        )
        return result is not None
    
    async def get_leave_message_title(self, guild_id: int) -> str:
        result = await self.apg.fetchrow(
            "SELECT leave_message_title FROM guild_configs WHERE guild_id = $1", guild_id
        )
        return result["leave_message_title"]
    
    async def set_leave_message_title(self, guild_id: int, title: str) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_configs SET leave_message_title = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            title,
        )
        return result is not None
    
    async def get_leave_message_body(self, guild_id: int) -> str:
        result = await self.apg.fetchrow(
            "SELECT leave_message_body FROM guild_configs WHERE guild_id = $1", guild_id
        )
        return result["leave_message_body"]
    
    async def set_leave_message_body(self, guild_id: int, body: str) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_configs SET leave_message_body = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            body,
        )
        return result is not None
    
    async def get_leave_message_enabled(self, guild_id: int) -> bool:
        result = await self.apg.fetchrow(
            "SELECT leave_message_enabled FROM guild_configs WHERE guild_id = $1", guild_id
        )
        return result["leave_message_enabled"]
    
    async def set_leave_message_enabled(self, guild_id: int, enabled: bool) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_configs SET leave_message_enabled = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            enabled,
        )
        return result is not None
    
    async def get_modlog_channel_id(self, guild_id: int) -> int:
        result = await self.apg.fetchrow(
            "SELECT modlog_channel_id FROM guild_configs WHERE guild_id = $1", guild_id
        )
        return result["modlog_channel_id"]
    
    async def set_modlog_channel_id(self, guild_id: int, channel_id: int) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_configs SET modlog_channel_id = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            channel_id,
        )
        return result is not None
    
    async def get_modlog_enabled(self, guild_id: int) -> bool:
        result = await self.apg.fetchrow(
            "SELECT modlog_enabled FROM guild_configs WHERE guild_id = $1", guild_id
        )
        return result["modlog_enabled"]
    
    async def set_modlog_enabled(self, guild_id: int, enabled: bool) -> bool:
        result = await self.apg.execute(
            "UPDATE guild_configs SET modlog_enabled = $2 WHERE guild_id = $1 RETURNING *",
            guild_id,
            enabled,
        )
        return result is not None
    

class UserConfigManager:
    def __init__(self, apg):
        self.apg = apg
    
    async def get_user_config(self, user_id: int) -> dict:
        result = await self.apg.fetchrow(
            "SELECT * FROM user_configs WHERE user_id = $1", user_id
        )
        return result
    
    async def ensure_user_config(self, user_id: int) -> bool:
        await UserDataManager(self.apg).ensure_user(user_id)

        result = await self.apg.execute(
            "INSERT INTO user_configs (user_id) VALUES ($1) ON CONFLICT DO NOTHING",
            user_id,
        )
        return result is not None
    
    async def get_autoresponse_immune(self, user_id: int) -> bool:
        result = await self.apg.fetchval(
            "SELECT autoresponse_immune FROM user_configs WHERE user_id = $1", user_id
        )
        return result
    
    async def set_autoresponse_immune(self, user_id: int, immune: bool) -> bool:
        result = await self.apg.execute(
            "UPDATE user_configs SET autoresponse_immune = $2 WHERE user_id = $1 RETURNING *",
            user_id,
            immune,
        )
        return result is not None

    



class ReturnCode(Enum):
    SUCCESS = 0
    ALREADY_EXISTS = 1
    NOT_FOUND = 2
    MISSING_PERMISSIONS = 3
    IS_ALIAS = 4
    NOT_ALIAS = 5
    UNKNOWN_ERROR = 6
