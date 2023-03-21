import asyncio
import re
import discord
from discord.ext import commands


from discord.app_commands import describe
from typing import Optional

from ..sentinel import Sentinel, SentinelCog, SentinelContext, SentinelView
from ..command_util import Paginator, lim
from ..converters import URL, URLParam, Range
from urllib import parse
import bs4
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

class Web(SentinelCog, emoji="\N{Globe with Meridians}"):
    """Commands for navigating the great interwebs"""

    @commands.hybrid_group()
    async def web(self, ctx: SentinelContext, *, query: Optional[str] = None):
        """Search and view the web"""
        if ctx.invoked_subcommand is not None:
            return

        if query is not None:
            return await self.search.callback(self, ctx, query=query)

    @web.command()
    async def search(self, ctx: SentinelContext, *, query: str):
        """Searches duckduckgo.com for a query and returns a list of results"""
        parsed = parse.quote_plus(query)
        if parsed.startswith("nsfw:"):
            parsed = parsed.lstrip("nsfw:") + "+!safeoff"
        else:
            parsed = parsed + "+!safeon"
        search_base = f"https://duckduckgo.com/?q={parsed}&atb=v361-3&ia=web"
        page_content = await self.bot.driver.get(search_base)

        soup = bs4.BeautifulSoup(page_content, "html.parser")
        selector = "div#links.results.js-results > div.nrn-react-div > article"
        results = soup.select(selector)

        view = WebGetPaginator(ctx, parsed, tuple(results))
        await view.update()
        embed = await view.embed(view.displayed_values)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @web.command()
    async def image(self, ctx: SentinelContext, *, query: str):
        """Searches duckduckgo.com for a query and returns a list of images"""
        parsed = parse.quote_plus(query)
        search_base = f"https://duckduckgo.com/?t=ffab&q={parsed}&iar=images&iax=images&ia=images&kp=-2"
        page_content = await self.bot.driver.get(search_base, wait=1.5)

        soup = bs4.BeautifulSoup(page_content, "html.parser")
        selector = "div > div.tile-wrap > div > div.tile"
        results = soup.select(selector)

        view = WebImagePaginator(ctx, query, tuple(results[:-1]))
        await view.update()
        embed = await view.embed(view.displayed_values)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @web.command()
    async def ss(self, ctx: SentinelContext, url = URL, wait = Range(float, 0, 5, default=1)):
        """Gets a screenshot of a website"""
        embed = ctx.embed(
            title=f"Getting {url.netloc}...",
            description="Depending on the content size and server load, this may take a while",
        )
        message = await ctx.send(embed=embed)
        await asyncio.sleep(wait)
        content = await self.bot.driver.screenshot(url.geturl())
        embed = ctx.embed(title=url.netloc)
        embed.url = url.geturl()
        filename = f"{ctx.author.id}.png"
        file = discord.File(content, filename=filename)
        embed.set_image(url=f"attachment://{filename}")

        await message.edit(embed=embed, attachments=[file])


class WebGetPaginator(Paginator):
    def __init__(
        self, ctx: SentinelContext, query: str, results: tuple[bs4.element.Tag]
    ):
        self.query = query
        self.results = results
        super().__init__(ctx, results, page_size=10)

    async def embed(self, displayed_values: tuple[bs4.element.Tag]) -> discord.Embed:
        title = f"Web Seach: `{self.query}` - Page `{self.current_page+1}`/`{self.max_page+1}`"
        embed = self.ctx.embed(title=title)
        for result in displayed_values:
            url = result.select_one("div > a > span")
            if url is None:
                continue
            url = url.text
            if not url.startswith("https://"):
                url = "https://" + url

            title = result.select_one("div > h2 > a > span")
            if title is None:
                continue
            title = title.text

            description = result.select_one(
                "div.E2eLOJr8HctVnDOTM8fs > div > span"
            )  # may or may not break in the near future
            if description is None:
                continue
            description = description.text

            embed.add_field(
                name=title,
                value=f'[{lim(description, 75)}]({url} "Go to {url}")',
                inline=False,
            )
        return embed


class WebImagePaginator(Paginator):
    def __init__(
        self, ctx: SentinelContext, query: str, results: tuple[bs4.element.Tag]
    ):
        self.query = query
        self.results = results
        super().__init__(ctx, results, page_size=1)

    async def embed(self, displayed_values: tuple[bs4.element.Tag]) -> discord.Embed:
        # lazy loading
        if len(displayed_values) == 0:
            return self.ctx.embed(title="No results found")
        val = displayed_values[0]

        image_title = val.select_one("a > span")
        if image_title is None:
            image_title = "No title"
        else:
            image_title = image_title.text

        url = val.select_one("a > span.tile--img__domain")
        if url is None:
            url = "No URL"
        else:
            url = "https://" + url.text

        thumbnail = val.select_one(
            "div.tile--img__media > span.tile--img__media__i > img"
        )
        if thumbnail is None:
            thumbnail = "No thumbnail"
        else:
            thumbnail = "https:" + str(thumbnail["data-src"])

        title = f"Image Search: `{self.query}` - Page `{self.current_page+1}`/`{self.max_page+1}`"
        embed = self.ctx.embed(title=title, description=f"*{image_title}*")
        embed.set_image(url=thumbnail)
        embed.url = url
        return embed


async def setup(bot: Sentinel):
    await bot.add_cog(Web(bot))
