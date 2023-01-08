import logging
from .bot_typing import BotT, _Bot

import importlib
import discord
from discord.ext import commands
import os
import glob


def setup_logging() -> None:
    logger = logging.getLogger("matplotlib")
    logger.setLevel(logging.INFO)
    logger = logging.getLogger("selenium")
    logger.setLevel(logging.INFO)
    logger = logging.getLogger("PIL.PngImagePlugin")
    logger.setLevel(logging.WARNING)


async def load_extensions(bot: _Bot) -> tuple[list[str], list[str]]:
    reloaded_extensions = []
    reloaded_utils = []
    files = glob.glob("src\\ext\\**\\*.py", recursive=True)
    for file in files:
        file = file.replace("\\", ".")
        file = file.replace("/", ".")
        if file.startswith("_") or file.endswith("_.py"):
            continue
        ext = file[:-3]
        try:
            await bot.load_extension(ext)
            reloaded_extensions.append(ext)
        except commands.ExtensionAlreadyLoaded:
            await bot.reload_extension(ext)
            reloaded_extensions.append(ext)
    
    files = glob.glob("src\\**\\*.py", recursive=True)
    for file in files:
        file = file.replace("\\", ".")
        file = file.replace("/", ".")
        if file.startswith("_") or file.endswith("_.py"):
            continue
        if file.startswith("src.ext"):
            continue
        ext = file[:-3]
        try:
            importlib.import_module(ext)
            reloaded_utils.append(ext)
        except ModuleNotFoundError:
            continue
        
        
    return reloaded_extensions, reloaded_utils
