import re
import discord
from discord.ext import commands


from discord.app_commands import describe
from typing import Optional

from ..sentinel import Sentinel, SentinelCog, SentinelContext, SentinelView
from ..command_util import Paginator, lim
from urllib import parse
import bs4


class Web(SentinelCog, emoji="\N{Globe with Meridians}"):
    @commands.hybrid_group()
    async def web(self, ctx: SentinelContext, *, query: Optional[str] = None):
        if ctx.invoked_subcommand is not None:
            return
        
        if query is not None:
            return await self.search.callback(self, ctx, query=query)
        

    @web.command()
    async def search(self, ctx: SentinelContext, *, query: str):
        parsed = parse.quote_plus(query)
        search_base = f"https://duckduckgo.com/?q={parsed}&atb=v361-3&ia=web"
        page_content = await self.bot.driver.get(search_base)

        soup = bs4.BeautifulSoup(page_content, "html.parser")
        selector = "div#links.results.js-results > div.nrn-react-div > article"
        results = soup.select(selector)

        view = WebGetPaginator(ctx, query, tuple(results))
        await view.update()
        embed = await view.embed(view.displayed_values)
        message = await ctx.send(embed=embed, view=view)
        view.message = message
    
    @web.command()
    async def image(self, ctx: SentinelContext, *, query: str):
        parsed = parse.quote_plus(query)
        search_base = f"https://duckduckgo.com/?q={parsed}"
        page_content = await self.bot.driver.get(search_base, wait=1)

        soup = bs4.BeautifulSoup(page_content, "html.parser")
        selector = "div#links > div > div > div > div"
        results = soup.select(selector)

        view = WebImagePaginator(ctx, query, tuple(results))
        await view.update()
        embed = await view.embed(view.displayed_values)
        message = await ctx.send(embed=embed, view=view)
        view.message = message


class WebGetPaginator(Paginator):
    def __init__(self, ctx: SentinelContext, query: str, results: tuple[bs4.element.Tag]):
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

            description = result.select_one("div.E2eLOJr8HctVnDOTM8fs > div > span") # may or may not break in the near future
            if description is None:
                continue
            description = description.text

            embed.add_field(
                name=title,
                value=f"[{lim(description, 75)}]({url} \"Go to {url}\")",
                inline=False
            )
        return embed
        

class WebImagePaginator(Paginator):
    def __init__(self, ctx: SentinelContext, query: str, results: tuple[bs4.element.Tag]):
        self.query = query
        self.results = results
        super().__init__(ctx, results, page_size=1)
    
    async def embed(self, displayed_values: tuple[bs4.element.Tag]) -> discord.Embed:
        val = displayed_values[0]
        url = val["data-id"]
        alt = val.select_one("a > img")
        if alt is None:
            alt = "No alt text"
        else:
            alt = alt["alt"]


        title = f"Image Search: `{self.query}` - Page `{self.current_page+1}`/`{self.max_page+1}`"
        embed = self.ctx.embed(title=title, description=f"*{alt}*")
        embed.set_image(url=url)
        return embed


async def setup(bot: Sentinel):
    await bot.add_cog(Web(bot))