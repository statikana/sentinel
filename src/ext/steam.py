import datetime
from bs4 import BeautifulSoup, Tag
import discord
from discord.ext import commands

from ..command_util import Paginator
from ..sentinel import Sentinel, SentinelCog, SentinelContext, SentinelView

from ..converters import Range, URLCleanParam, URLCleanAnnotation
from ..command_types import SteamUser

from env import STEAM_API_KEY

class Steam(SentinelCog, emoji="\N{Video Game}"):
    @commands.hybrid_group()
    async def steam(self, ctx: SentinelContext):
        """Steam commands"""
        pass

    @steam.command()
    async def user(self, ctx: SentinelContext, id: int = commands.param(converter=lambda x: int(x))):
        url = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
        params = {
            "key": STEAM_API_KEY,
            "steamids": id,
        }
        data = await self.bot.session.getjson(url, params=params, route=["response", "players", 0], cache=True)
        user = SteamUser(
            avatar_url=data["avatarfull"],
            username=data["realname"],
            persona_name=data["personaname"],
            custom_url=data["profileurl"],
            time_created=datetime.datetime.fromtimestamp(data["timecreated"]),
            country_code=data.get("loccountrycode", "N/A"),
            state_code=data.get("locstatecode", "N/A"),
        )

        embed = ctx.embed(
            title=f"Steam User - {user.persona_name}",
        )
        embed.add_field(
            name="Username",
            value=user.username,
        )
        embed.add_field(
            name="Time Created",
            value=f"<t:{int(user.time_created.timestamp())}:F>",
        )
        embed.add_field(
            name="Location",
            value=f"`{user.state_code}`, `{user.country_code}`",
        )

        embed.url = user.custom_url
        embed.set_image(url=user.avatar_url)
        await ctx.send(embed=embed)


async def setup(bot: Sentinel):
    await bot.add_cog(Steam(bot))