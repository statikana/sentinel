from typing import Annotated
import discord
from discord.ext import commands
from discord.app_commands import describe

from difflib import SequenceMatcher

from ..command_types import TagEntry
from ..command_util import StringArgParse, StringParam, LowerString

from ..sentinel import (
    Sentinel,
    SentinelCog,
    SentinelContext,
    SentinelView,
    SentinelErrors,
)
from ..command_util import Paginator
from ..db_managers import TagsManager


class Tags(SentinelCog):
    def __init__(self, bot: Sentinel):
        self.tgm = TagsManager(bot.apg)
        super().__init__(bot, "\N{Label}")

    @commands.hybrid_group()
    async def tag(self, ctx: SentinelContext):
        """Manage tags"""
        pass

    @tag.command()
    @commands.guild_only()
    @describe(
        name="The name of the tag to retrieve",
    )
    async def get(self, ctx: SentinelContext, name: StringParam = LowerString):
        """Get a tag"""
        if ctx.guild is None:
            raise commands.CommandInvokeError(
                Exception("This command can only be used in a guild")
            )

        tag = await self.tgm.get_tag_by_name(ctx.guild.id, name)
        if tag is None:
            raise commands.BadArgument("That tag doesn't exist")

        await self.tgm.increment_tag_uses(tag.tag_id)

        embed = ctx.embed(
            title=f"**`{tag.tag_name}`**", description=f"{tag.tag_content}"
        )
        await ctx.send(embed=embed)

    @tag.command()
    @commands.guild_only()
    @describe(
        name="The name of the tag to get info about",
    )
    async def info(self, ctx: SentinelContext, name: StringParam = LowerString):
        """Get info about a tag"""
        if ctx.guild is None:
            raise commands.CommandInvokeError(
                Exception("This command can only be used in a guild")
            )

        tag = await self.tgm.get_tag_by_name(ctx.guild.id, name)
        if tag is None:
            raise commands.BadArgument("That tag doesn't exist")

        await self.tgm.increment_tag_uses(tag.tag_id)

        embed = ctx.embed(
            title=f"Tag Info - `{tag.tag_name}`",
            description=f"""
            **Tag ID:** `{tag.tag_id}`
            **Owner:** `{ctx.guild.get_member(tag.owner_id) or 'USERID ' + str(tag.owner_id)}`
            **Created:** <t:{int(tag.created_at.timestamp())}:R> [<t:{int(tag.created_at.timestamp())}:F>)]
            **Uses:** `{tag.uses}`""",
        )
        await ctx.send(embed=embed)

    @tag.command()
    @commands.guild_only()
    @describe(
        name="The name of the new tag",
        content="The content of the new tag",
    )
    async def new(
        self, ctx: SentinelContext, name: StringParam = LowerString, *, content: str
    ):
        """Create a new tag"""
        if ctx.guild is None:
            raise commands.CommandInvokeError(
                Exception("This command can only be used in a guild")
            )
        if len(name) > 32:
            raise SentinelErrors.BadTagName("Tag names must be under 32 characters")

        if len(content) > 2000:
            raise SentinelErrors.BadTagContent(
                "Tag content must be under 2000 characters"
            )

        if (
            ctx.guild is not None
            and await self.tgm.get_tag_by_name(ctx.guild.id, name) is not None
        ):  # Checking if guild exists for linter
            raise SentinelErrors.TagNameExists("A tag with that name already exists")

        tag = await self.tgm.create_tag(name, content, ctx.author.id, ctx.guild.id)
        embed = ctx.embed(
            title=f"Tag Created - `{tag.tag_name}`", description=f"{tag.tag_content}"
        )
        await ctx.send(embed=embed)

    @tag.command()
    @commands.guild_only()
    async def edit(
        self, ctx: SentinelContext, name: StringParam = LowerString, *, content: str
    ):
        """Edit a tag"""
        if ctx.guild is None:
            raise commands.CommandInvokeError(
                Exception("This command can only be used in a guild")
            )

        if len(content) > 2000:
            raise commands.BadArgument("Tag content must be under 2000 characters")

        successful = await self.tgm.edit_tag_by_name(
            name, ctx.guild.id, content, True, True, ctx.author.id
        )
        if not successful:
            raise commands.BadArgument(
                "Either that tag doesn't exist or you don't have permission to edit it"
            )

        embed = ctx.embed(title=f"Tag Edited - `{name}`", description=f"{content}")
        await ctx.send(embed=embed)

    @tag.command()
    @commands.guild_only()
    async def delete(self, ctx: SentinelContext, name: StringParam = LowerString):
        """Delete a tag"""
        if ctx.guild is None:
            raise commands.CommandInvokeError(
                Exception("This command can only be used in a guild")
            )

        successful = await self.tgm.delete_tag_by_name(
            name, ctx.guild.id, True, True, ctx.author.id
        )
        if not successful:
            raise commands.BadArgument(
                "Either that tag doesn't exist or you don't have permission to delete it"
            )

        embed = ctx.embed(
            title=f"Tag Deleted - `{name}`",
            description=f"Tag `{name}` has been deleted",
        )
        await ctx.send(embed=embed)

    @tag.command()
    @commands.guild_only()
    async def search(
        self,
        ctx: SentinelContext,
        query: StringParam = LowerString,
        fuzzy_ratio_minmum: float = 0.25,
    ):
        """Search for a tag"""
        if ctx.guild is None:
            raise commands.CommandInvokeError(
                Exception("This command can only be used in a guild")
            )
        if fuzzy_ratio_minmum < 0 or fuzzy_ratio_minmum > 1:
            raise commands.BadArgument("Fuzzy ratio must be between 0 and 1")

        guild_tags = await self.tgm.get_tags_in_guild(ctx.guild.id)
        searched_tags = []
        for tag in guild_tags:
            ratio = SequenceMatcher(isjunk=None, a=query, b=tag.tag_name).ratio()
            if ratio >= fuzzy_ratio_minmum:
                searched_tags.append(tag)

        view = TagSearchPaginator(ctx, searched_tags, query)
        embed = await view.embed(view.displayed_values)
        message = await ctx.send(embed=embed)
        view.message = message
        await view.update()


class TagSearchPaginator(Paginator):
    def __init__(self, ctx: SentinelContext, tags: list[TagEntry], query: str):
        super().__init__(ctx, tuple(tags), page_size=10)
        self.query = query

    async def embed(self, value_range: tuple[TagEntry]) -> discord.Embed:
        descirption = ""
        for i, tag in enumerate(self.displayed_values):
            descirption += (
                f"`{i + self.display_values_index_start + 1}:` **`{tag.tag_name}`**\n"
            )

        embed = self.ctx.embed(
            title=f'Tag Search - `"{self.query}"`: Page `{self.current_page}/{self.max_page}`',
            description=descirption,
        )
        return embed


async def setup(bot: Sentinel):
    await bot.add_cog(Tags(bot))
