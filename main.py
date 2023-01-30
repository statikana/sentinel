import env
from src.sentinel import Sentinel

import asyncio
import _logging_setup

if __name__ == "__main__":
    bot = Sentinel()
    asyncio.run(bot.start(env.DISCORD_OAUTH_TOKEN))
