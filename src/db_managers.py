from .sentinel import SentinelPool
import asyncpg


class DukesManager:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def ensure_user_exists(self, user_id: int) -> None:
        await self.pool.execute("INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING", user_id, 0)

    async def get_balance(self, user_id: int, create_if_unfound: bool = True) -> int | None:
        result = await self.pool.fetchrow("SELECT balance FROM users WHERE user_id = $1", user_id)
        if result is None:
            if create_if_unfound:
                await self.pool.execute("INSERT INTO users (user_id, balance) VALUES ($1, $2)", user_id, 0)
                return 0
            else:
                return None
        else:
            return result["balance"]
    
    async def set_balance(self, user_id: int, balance: int, create_if_unfound: bool = True) -> None:
        if create_if_unfound:
            await self.pool.execute("INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = $2", user_id, balance)
        else:
            await self.pool.execute("UPDATE users SET balance = $2 WHERE user_id = $1", user_id, balance)
        
    async def modify_balance(self, user_id: int, amount: int, create_if_unfound: bool = True) -> None:
        if create_if_unfound:
            await self.pool.execute("INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = users.balance + $2", user_id, amount)
        else:
            await self.pool.execute("UPDATE users SET balance = users.balance + $2 WHERE user_id = $1", user_id, amount)

    async def give_balance(self, giver_id: int, receiver_id: int, amount: int, create_if_unfound: bool = True) -> bool:
        giver_bal = await self.get_balance(giver_id, create_if_unfound)

        # Either the giver doesn't have an account and we're not creating one, or they don't have enough money anyway
        if (giver_bal is None and not create_if_unfound) or (giver_bal is not None and giver_bal < amount):
            return False
        
        if create_if_unfound:
            await self.pool.execute("INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = users.balance + $2", giver_id, -amount)
            await self.pool.execute("INSERT INTO users (user_id, balance) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET balance = users.balance + $2", receiver_id, amount)
        else:
            await self.pool.execute("UPDATE users SET balance = users.balance - $2 WHERE user_id = $1", giver_id, amount)
            await self.pool.execute("UPDATE users SET balance = users.balance + $2 WHERE user_id = $1", receiver_id, amount)
        return True

