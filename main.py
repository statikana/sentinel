from env import OAUTH_TOKEN
from src.sentinel import Sentinel

import asyncio
import _logging_setup


if __name__ == "__main__":
    bot = Sentinel()
    asyncio.run(bot.start(OAUTH_TOKEN))
