from env import DISCORD_OAUTH_TOKEN
from src.sentinel import Sentinel

import asyncio
import _logging_setup

if __name__ == "__main__":
    bot = Sentinel()
    asyncio.run(bot.start(DISCORD_OAUTH_TOKEN))
