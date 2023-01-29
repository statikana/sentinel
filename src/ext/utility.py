from typing import Optional
import discord
from discord.ext import commands
import time

from ..sentinel import Sentinel, SentinelCog, SentinelContext, SentinelView
from ..command_util import ParamDefaults
from config import READTHEDOCS_URL, WOLFRAM_API_URL
from env import WOLFRAM_APPID
from urllib import parse
import aiohttp
from bs4 import BeautifulSoup
from ..command_util import Paginator
from ..command_types import RTFMMeta
from discord.app_commands import describe


class Utility(SentinelCog):
    """
    Commands that provide small, yet useful, services"""

    def __init__(self, bot: Sentinel):
        super().__init__(bot, "\N{Input Symbol for Numbers}")

    @commands.hybrid_command()
    async def ping(self, ctx: SentinelContext):
        """Get the latency of the bot."""
        description = (
            f"\N{Shinto Shrine} **Gateway:** {round(self.bot.latency * 1000, 3)}ms\n"
        )

        start = time.perf_counter()
        await self.bot.apg.fetch("SELECT 1")
        description += f"<:postgreSQL:1061456211897225309> **Database:** {round((time.perf_counter() - start) * 1000, 3)}ms\n"

        await self.bot.session.get("https://google.com")
        description += f"\N{Globe with Meridians} **API:** {round((time.perf_counter() - start) * 1000, 3)}ms\n"

        embed = ctx.embed(
            title="Pong! \N{Table Tennis Paddle and Ball}", description=description
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @commands.cooldown(1, 90, commands.BucketType.user)
    @describe(
        question="The question you want to ask Wolfram Alpha. Must be an objective query",
    )
    async def wolfram(self, ctx: SentinelContext, *, question: str):
        await ctx.send(question)
        question = parse.quote_plus(question)
        url = f"{WOLFRAM_API_URL}"
        url += f"?appid={WOLFRAM_APPID}&i={question}"

        try:
            response = await self.bot.session.get(url)
            title = (await response.read()).decode("utf-8")
        except aiohttp.ClientResponseError:
            title = "I could not answer that. Please make sure the question is objective, and try again later."
            self.wolfram.reset_cooldown(ctx)

        embed = ctx.embed(title=title)
        await ctx.send(embed=embed)

    @commands.hybrid_command()
    @describe(
        member="The user you want to get the avatar of. Defaults to the author of the command"
    )
    async def avatar(
        self,
        ctx: SentinelContext,
        member: discord.Member = ParamDefaults.member,
    ):
        embed = ctx.embed(
            title=f"`{member}`'s Avatar", description="Showing Guild Avatar"
        )
        view = AvatarGuildView(ctx, member)
        embed.set_image(url=member.display_avatar)
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command()
    @commands.cooldown(2, 20, commands.BucketType.user)
    @describe(
        project="The project you want to search for",
        query="The query you want to search for, within the project",
        version="The version of the project you want to search for. Defaults to 'stable'",
        lang="The language of the project you want to search for. Defaults to 'en'",
    )
    async def rtfm(
        self,
        ctx: SentinelContext,
        project: str,
        query: str,
        version: Optional[str] = "stable",
        lang="en",
    ):
        """Read the F*%#ing Manual! Searches the documentation for a project on ReadTheDocs"""
        # TODO: Cacheing?
        if ctx.interaction:
            await ctx.interaction.response.defer()
        project = project.lower().replace(" ", "").replace(".", "")
        ref_url = f"https://{parse.quote_plus(project)}.readthedocs.io/{lang}/{version}"
        search_url = ref_url + "/search.html?q=" + parse.quote_plus(query)
        data = await self.bot.driver.get(search_url, wait=0.75)

        soup = BeautifulSoup(data, "html.parser")
        selector = "html > body > div.main-grid > main.grid-item > div#search-results > ul.search > li"
        results = soup.select(selector)

        if not results:
            raise Exception("Cannot find any results for your query")

        formatted_results: list[RTFMMeta] = []
        for result in results:
            if (
                (name := result.select_one("a"))
                and (href := result.select_one("a"))
                and (source := result.select_one("span"))
            ):
                name = name.text
                source = source.text.strip().strip("()")
                formatted_results.append(
                    RTFMMeta(
                        name=name,
                        href=ref_url + "/" + str(href["href"]),
                        source_description=source,
                    )
                )

        view = RTFMPaginator(
            ctx, tuple(formatted_results), 10, project, query, search_url
        )
        embed = await view.embed(view.displayed_values)
        message = await ctx.send(embed=embed, view=view)
        view.message = message
        await view.update()

    @commands.hybrid_command()
    @describe(
        member="The member you want to get the roles of. Defaults to the author of the command"
    )
    async def roles(
        self, ctx: SentinelContext, member: discord.Member = ParamDefaults.member
    ):
        description = f"**Highest Role:** {member.top_role.mention}\n"
        description += f"-- **All Roles** [*Descending*] --\n" + "\n".join(
            role.mention
            for role in sorted(
                member.roles, key=lambda role: role.position, reverse=True
            )[:-1][:20]
        )
        embed = ctx.embed(
            title=f"Role Information: `{member}`", description=description
        )
        await ctx.send(embed=embed)


class AvatarGuildView(SentinelView):
    def __init__(self, ctx: SentinelContext, member: discord.Member):
        super().__init__(ctx)
        self.member = member
        self.guild = True

    @discord.ui.button(label="View Global Avatar", style=discord.ButtonStyle.grey)
    async def global_avatar(self, itx: discord.Interaction, button: discord.ui.Button):
        embed = self.ctx.embed(
            title=f"`{self.member}`'s Avatar", description="Showing Global Avatar"
        )
        embed.set_image(url=(self.member.avatar or self.member.display_avatar))
        await itx.response.edit_message(
            embed=embed, view=AvatarGlobalView(self.ctx, self.member)
        )


class AvatarGlobalView(SentinelView):
    def __init__(self, ctx: SentinelContext, member: discord.Member):
        super().__init__(ctx)
        self.member = member
        self.guild = False

    @discord.ui.button(label="View Guild Avatar", style=discord.ButtonStyle.grey)
    async def guild_avatar(self, itx: discord.Interaction, button: discord.ui.Button):
        embed = self.ctx.embed(
            title=f"`{self.member}`'s Avatar", description="Showing Guild Avatar"
        )
        embed.set_image(url=self.member.display_avatar)
        await itx.response.edit_message(
            embed=embed, view=AvatarGuildView(self.ctx, self.member)
        )


class RTFMPaginator(Paginator):
    def __init__(
        self,
        ctx: SentinelContext,
        values: tuple,
        page_size: int,
        project: str,
        query: str,
        search_url: str,
    ):
        super().__init__(ctx, values, page_size)
        self.project = project
        self.query = query
        self.search_url = search_url

    async def embed(self, value_range: tuple[RTFMMeta]) -> discord.Embed:
        description = "\n".join(
            f"`{i + self.display_values_index_start + 1}:` **[{result.name}]({result.href})** *{result.source_description}*"
            for i, result in enumerate(value_range)
        )
        embed = self.ctx.embed(
            title=f'`{self.project} - "{self.query}":` Page `{self.current_page + 1}/{self.max_page + 1}`',
            description=description,
        )
        embed.url = self.search_url
        return embed


async def setup(bot: Sentinel):
    await bot.add_cog(Utility(bot))
