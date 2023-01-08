from src.dev.bot_abc import Sentinel
from env import OAUTH_TOKEN
import asyncio
import logging

logging.getLogger().setLevel(logging.INFO)


async def main():
    bot = Sentinel()
    await bot.start(OAUTH_TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
