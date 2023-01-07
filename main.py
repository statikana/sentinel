from src.dev.bot_abc import Sentinel
from env import TOKEN
import asyncio


async def main():
    bot = Sentinel()
    await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())