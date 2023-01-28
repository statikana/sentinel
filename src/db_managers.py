from typing import overload
from .sentinel import SentinelPool
import asyncpg


class CoinsManager:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def ensure_user_exists(self, user_id: int) -> None:
        await self.pool.execute(
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
        result = await self.pool.fetchrow(
            "SELECT balance FROM users WHERE user_id = $1", user_id
        )
        if result is None:
            if create_if_unfound:
                await self.pool.execute(
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
            await self.pool.execute(
                "INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = $2",
                user_id,
                balance,
            )
        else:
            await self.pool.execute(
                "UPDATE users SET balance = $2 WHERE user_id = $1", user_id, balance
            )

    async def modify_balance(
        self, user_id: int, amount: int, create_if_unfound: bool = True
    ) -> None:
        if create_if_unfound:
            await self.pool.execute(
                "INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = users.balance + $2",
                user_id,
                amount,
            )
        else:
            await self.pool.execute(
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
            await self.pool.execute(
                "INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = users.balance + $2 RETURNING *",
                giver_id,
                -amount,
            )
            await self.pool.execute(
                "INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = users.balance + $2 RETURNING *",
                receiver_id,
                amount,
            )
        else:
            await self.pool.execute(
                "UPDATE users SET balance = users.balance - $2 WHERE user_id = $1",
                giver_id,
                amount,
            )
            await self.pool.execute(
                "UPDATE users SET balance = users.balance + $2 WHERE user_id = $1",
                receiver_id,
                amount,
            )
        return (True, giver_bal - amount, rec_bal + amount)
