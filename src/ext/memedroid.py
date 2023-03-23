from dataclasses import dataclass
import datetime
from enum import Enum
import random
from typing import Optional
import bs4
from bs4.element import Tag
import discord
from discord.ext import commands
from discord.ext import tasks
from discord.app_commands import describe
import asyncio
from selenium.webdriver.common.by import By

from ..command_util import Paginator
from ..sentinel import Sentinel, SentinelCog, SentinelContext, SentinelView

from ..converters import Range, URLCleanParam, URLCleanAnnotation


class MemeDroid(SentinelCog):
    """Commands for interacting with MemeDroid"""
    def __init__(self, bot: Sentinel):
        self.bot = bot
        super().__init__(bot, emoji="\N{OK Hand Sign}")

    @commands.hybrid_group()
    async def memedroid(self, ctx: SentinelContext, *, username: Optional[str] = None):
        """MemeDroid commands"""
        if username is not None:
            return await self.user.callback(self, ctx, username=username)

    @memedroid.command()
    @describe(username="The username of the user you want to get the information of")
    async def user(self, ctx: SentinelContext, *, username=URLCleanParam):
        """Gets detailed information about a user"""
        url_base = f"https://www.memedroid.com/user/view/{username}"
        page_content = await self.bot.driver.get(url_base)

        profile_stats_selector = (
            "div#user-profile-main-container.user-profile-main-container"
        )

        pfp_selector = "div > div > img.user-profile-avatar"
        bio_selector = "div > div > p.user-profile-status"
        cased_username_selector = "div > p.user-profile-username"

        ranking_selector = "div > div > div.user-profile-score-info-rank > p > span"
        score_selector = "div > div > div.user-profile-score-info-score > p > span"

        follow_selector = "div#user-profile-followers-info-container"

        soup = bs4.BeautifulSoup(page_content, "html.parser")
        profile_stats = soup.select_one(profile_stats_selector)
        if profile_stats is None:
            return

        pfp_url: str = profile_stats.select_one(pfp_selector).get("src")  # type: ignore
        bio: str = profile_stats.select_one(bio_selector).text  # type: ignore
        cased_username: str = profile_stats.select_one(cased_username_selector).text  # type: ignore

        ranking: str = profile_stats.select_one(ranking_selector).text  # type: ignore
        score: str = profile_stats.select_one(score_selector).text  # type: ignore

        follow = soup.select_one(follow_selector)  # type: ignore # intentionally not sourced from profile_stats
        followers, following = follow.select("div > a > span")  # type: ignore
        followers = followers.text
        following = following.text

        embed = ctx.embed(
            title=cased_username,
            description=f"*{discord.utils.escape_markdown(bio)}*\n"
            f"**Ranking:** {ranking}\n"
            f"**Score:** {score}\n"
            f"**Followers:** {followers}\n"
            f"**Following:** {following}\n",
        )
        embed.set_thumbnail(url=pfp_url)
        embed.url = url_base

        view = UserButtons(ctx, cased_username, soup)
        view.set_embed(embed)
        await ctx.send(embed=embed, view=view)


class UserButtons(SentinelView):
    def __init__(self, ctx: SentinelContext, username: str, soup: bs4.BeautifulSoup):
        super().__init__(ctx)
        self.username = username
        self.soup = soup
        self.original_embed: discord.Embed
        self.embed: discord.Embed
        self.state = UserMenuStatus.MAIN

    def set_embed(self, embed: discord.Embed):
        self.original_embed = embed.copy()
        self.embed = embed.copy()

    @discord.ui.button(
        label="View Posts", style=discord.ButtonStyle.primary, emoji="\N{Newspaper}"
    )
    async def view_posts(self, itx: discord.Interaction, button: discord.ui.Button):
        if not await self.check_status(itx, self.view_posts, UserMenuStatus.POSTS):
            return

        upload_button_path = "/html/body/div[5]/div/div[2]/section/ul/li[1]/a"  # lmao copilot how did you know this
        upload_button = self.ctx.bot.driver.driver.find_element(
            By.XPATH, upload_button_path
        )
        upload_button.click()
        await asyncio.sleep(0.5)

        posts_selector = "div > article"
        posts = self.soup.select(posts_selector)
        posts = [
            container
            for p in posts
            if p["data-type"] == "1"
            and (container := p.select_one("div.item-aux-container")) is not None
        ]  # cannot link to videos
        # TODO: gifs work, but it's a different process and a pain
        posts_data: list[MemeDroidPost] = [
            MemeDroidPost.fromRaw(post) for post in posts
        ]

        view = PostsPaginator(self.ctx, self.username, posts_data)
        await view.update()
        embed = await view.embed(view.displayed_values)
        await itx.response.send_message(embed=embed, view=view)
        view.message = await itx.original_response()

    @discord.ui.button(
        label="View Stats", style=discord.ButtonStyle.primary, emoji="\N{Memo}"
    )
    async def view_stats(self, itx: discord.Interaction, button: discord.ui.Button):
        if not await self.check_status(itx, self.view_stats, UserMenuStatus.STATS):
            return

        stats_button_path = "/html/body/div[5]/div/div[2]/section/ul/li[2]/a"
        stats_button = self.ctx.bot.driver.driver.find_element(
            By.XPATH, stats_button_path
        )
        stats_button.click()
        await asyncio.sleep(0.1)

        stats_selector = "ul.stats-list > li.row"
        stats = self.soup.select(stats_selector)
        formatted_stats: dict[str, str] = {stat.select_one("div").text: stat.select_one("div > span.size-15").text for stat in stats}  # type: ignore

        self.embed.title = f"{self.embed.title} - Stats"
        self.embed.description = "\n".join(
            f"**{k.strip('*')}:** `{v}`" for k, v in formatted_stats.items()
        )
        # self.embed.description += "\n*\\*On mobile app only*"

        await itx.response.edit_message(embed=self.embed, view=self)

    def reset_button_styles(self, success_button: discord.ui.Button | None = None):
        self.view_posts.style = discord.ButtonStyle.primary
        self.view_stats.style = discord.ButtonStyle.primary

        if success_button is not None:
            success_button.style = discord.ButtonStyle.success

    async def check_status(
        self,
        itx: discord.Interaction,
        button: discord.ui.Button,
        status: "UserMenuStatus",
    ) -> bool:
        if self.state == status:
            self.state = UserMenuStatus.MAIN
            self.reset_button_styles()
            await itx.response.edit_message(embed=self.original_embed, view=self)
            return False

        self.reset_button_styles(success_button=button)
        self.state = status
        return True


class UserMenuStatus(Enum):
    MAIN = 0
    POSTS = 1
    STATS = 2


@dataclass
class MemeDroidPost:
    title: str
    post_url: str
    image_url: str
    upvotes: int
    vote_count: int
    date: datetime.datetime

    @classmethod
    def fromRaw(cls, raw: bs4.element.Tag) -> "MemeDroidPost":
        return MemeDroidPost(
            title=raw.select_one("a.dyn-link > picture > img")["alt"],  # type: ignore
            post_url="https://memedroid.com" + raw.select_one("a.dyn-link")["href"],  # type: ignore
            image_url=raw.select_one("a.dyn-link > picture > img")["src"],  # type: ignore
            upvotes=raw.select_one("div.item-rating-container")["data-positive-votes"],  # type: ignore
            vote_count=raw.select_one("div.item-rating-container")["data-votes"],  # type: ignore
            date=datetime.datetime.fromtimestamp(int(raw.select_one("header.item-header")["data-ts"])),  # type: ignore
        )


class PostsPaginator(Paginator):
    def __init__(self, ctx: SentinelContext, username: str, posts: list[MemeDroidPost]):
        super().__init__(ctx, tuple(posts), 1)
        self.username = username
        self.posts = posts

    async def embed(self, value_range: tuple[MemeDroidPost]) -> discord.Embed:
        post = value_range[0]
        # print(post)
        embed = self.ctx.embed(
            title=post.title.rstrip(" - meme") + f" - {self.username}",
            description=f"**Upvotes:** {post.upvotes}\n"
            f"**Downvotes:** {int(post.vote_count) - int(post.upvotes)}\n"
            f"**Rating:** {round(int(post.upvotes) / int(post.vote_count) * 100, 2)}%\n"
            f"**Date:** <t:{int(post.date.timestamp())}:F>",
        )
        embed.url = post.post_url
        embed.set_image(url=post.image_url)

        return embed


async def setup(bot: Sentinel):
    await bot.add_cog(MemeDroid(bot))
