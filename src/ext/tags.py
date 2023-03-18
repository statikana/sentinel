from typing import Optional
import discord
from discord.ext import commands
from discord.app_commands import describe


from ..sentinel import Sentinel, SentinelContext, SentinelCog, SentinelErrors
from ..command_util import Paginator, fuzz
from ..db_managers import ReturnCode
from ..command_types import TagEntry, MetaTagEntry
from ..converters import LowerStringParam, StringAnnotation, OptionalLowerStringParam
from config import RESERVED_TAG_NAMES, TAG_NAME_REGEX
import re


class Tags(SentinelCog, emoji="\N{Label}"):
    """Store text snippets for later use"""
    @commands.hybrid_group()
    @commands.guild_only()
    async def tags(
        self,
        ctx: SentinelContext,
        *,
        tag_name: StringAnnotation = OptionalLowerStringParam,
    ):
        if ctx.invoked_subcommand is not None:
            return
        if tag_name is None:
            return await self.list_.callback(self, ctx)
        try:
            user = await commands.UserConverter().convert(
                ctx, tag_name.lstrip("<@").rstrip(">").strip("!").strip()
            )
            mem = self.bot.get_user(user.id)
            if mem is None:
                raise commands.BadArgument("User is not a member of this server")
            return await self.list_.callback(self, ctx, member=user)
        except (commands.BadArgument, commands.UserNotFound):
            return await self.get.callback(self, ctx, tag_name)

    @tags.command()
    @commands.guild_only()
    async def get(
        self, ctx: SentinelContext, tag_name: StringAnnotation = LowerStringParam
    ):
        tag = await self.bot.tdm.get_tag_by_name(
            ctx.guild.id, tag_name, allow_redirect=True
        )
        if tag is None:
            raise SentinelErrors.TagNotFound(f"Cannot find tag: `{tag_name}`")
        await self.bot.tdm.increment_tag_uses(tag.tag_id)
        if tag.redirected_from is not None:
            await self.bot.tdm.increment_tag_uses(tag.redirected_from.tag_id)
        embed = ctx.embed(
            title=f"`{tag.tag_name}`"
            + (
                f" [Redirected from `{tag.redirected_from.tag_name}`]"
                if tag.redirected_from is not None
                else ""
            ),
            description=tag.tag_content,
        )
        await ctx.send(embed=embed)

    @tags.command()
    @commands.guild_only()
    async def new(
        self,
        ctx: SentinelContext,
        tag_name: StringAnnotation = LowerStringParam,
        *,
        tag_content: str,
    ):
        result = await self.bot.tdm.create_tag(
            tag_name, tag_content, ctx.author.id, ctx.guild.id
        )
        if result == ReturnCode.ALREADY_EXISTS:
            raise SentinelErrors.TagNameExists(f"Tag: `{tag_name}` already exists")
        if len(tag_content) >= 2000:
            raise commands.BadArgument("Tag content must be less than 2000 characters")
        if not self._is_valid_tag_name(tag_name):
            raise SentinelErrors.BadTagName(
                f"Tag name: `{tag_name}` is not valid (alphanumberic and underscores only)"
            )
        embed = ctx.embed(
            title=f"Tag `{tag_name}` Created",
            description=tag_content,
        )
        await ctx.send(embed=embed)

    @tags.command()
    @commands.guild_only()
    async def edit(
        self,
        ctx: SentinelContext,
        tag_name: StringAnnotation = LowerStringParam,
        *,
        tag_content: str,
    ):
        result = await self.bot.tdm.edit_tag_by_name(
            tag_name, tag_content, ctx.author.id, owner_id=ctx.guild.id
        )
        if result == ReturnCode.NOT_FOUND:
            raise SentinelErrors.TagNotFound(f"Cannot find tag: `{tag_name}`")
        if result == ReturnCode.MISSING_PERMISSIONS:
            raise SentinelErrors.MissingPermissions(
                f"You do not have permission to edit tag: `{tag_name}`"
            )
        if len(tag_content) >= 2000:
            raise commands.BadArgument("Tag content must be less than 2000 characters")
        embed = ctx.embed(
            title=f"Tag `{tag_name}` Edited",
            description=tag_content,
        )
        await ctx.send(embed=embed)

    @tags.command()
    @commands.guild_only()
    async def delete(
        self, ctx: SentinelContext, tag_name: StringAnnotation = LowerStringParam
    ):
        result = await self.bot.tdm.delete_tag_by_name(
            tag_name, ctx.author.id, owner_id=ctx.guild.id
        )
        if result == ReturnCode.NOT_FOUND:
            raise SentinelErrors.TagNotFound(f"Cannot find tag: `{tag_name}`")
        if result == ReturnCode.MISSING_PERMISSIONS:
            raise SentinelErrors.MissingPermissions(
                f"You do not have permission to delete tag: `{tag_name}`"
            )
        embed = ctx.embed(
            title=f"Tag `{tag_name}` Deleted",
        )
        await ctx.send(embed=embed)

    @tags.command(name="list")
    @commands.guild_only()
    async def list_(
        self, ctx: SentinelContext, member: Optional[discord.Member] = None
    ):
        if member is None:
            return await self.list_guild_tags(ctx)
        return await self.list_member_tags(ctx, member)

    async def list_guild_tags(self, ctx: SentinelContext):
        tags = tuple(await self.bot.tdm.get_tags_in_guild(ctx.guild.id))
        if len(tags) == 0:
            raise SentinelErrors.TagNotFound("No tags found")
        view = GuildTagsPaginator(ctx, tags, 10)
        await view.update()
        embed = await view.embed(view.displayed_values)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    async def list_member_tags(self, ctx: SentinelContext, member: discord.Member):
        tags = tuple(await self.bot.tdm.get_tags_by_owner(member.id))
        if len(tags) == 0:
            raise SentinelErrors.TagNotFound("No tags found by " + member.mention)
        view = MemberTagsPaginator(ctx, member, tags, 10)
        await view.update()
        embed = await view.embed(view.displayed_values)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @tags.command()
    @commands.guild_only()
    async def info(
        self, ctx: SentinelContext, tag_name: StringAnnotation = LowerStringParam
    ):
        # TODO: Info for aliases?
        tag = await self.bot.tdm.get_tag_by_name(
            ctx.guild.id, tag_name, allow_redirect=True
        )
        if tag is None:
            raise SentinelErrors.TagNotFound(f"Cannot find tag: `{tag_name}`")

        await self.bot.tdm.increment_tag_uses(tag.tag_id)
        if tag.redirected_from is not None:
            await self.bot.tdm.increment_tag_uses(tag.redirected_from.tag_id)
        embed = ctx.embed(title=f"Tag: `{tag_name}`")
        user = self.bot.get_user(tag.owner_id)
        if user is None:
            user = "Unknown User"
        else:
            user = user.mention
        embed.add_field(name="Owner", value=f"{user} | `{tag.owner_id}`", inline=False)
        embed.add_field(name="Uses", value=f"`{tag.uses+1}`", inline=False)
        embed.add_field(
            name="Created At",
            value=f"<t:{round(tag.created_at.timestamp())}:F>",
            inline=False,
        )
        embed.add_field(name="Tag ID [Internal]", value=f"`{tag.tag_id}`", inline=False)
        if tag.alias_to is not None:
            embed.add_field(
                name="Redirected From Alias:", value=f"`{tag_name}`", inline=False
            )
        await ctx.send(embed=embed)

    @tags.command()
    @commands.guild_only()
    async def search(
        self,
        ctx: SentinelContext,
        query: StringAnnotation = LowerStringParam,
        fuzzy_ratio_minmum: float = 0.25,
    ):
        if fuzzy_ratio_minmum < 0 or fuzzy_ratio_minmum > 1:
            raise commands.BadArgument("Fuzzy ratio must be between 0 and 1")
        if not self._is_valid_tag_name(query):
            raise commands.BadArgument("Query must be a valid tag name")

        guild_tags = await self.bot.tdm.get_tags_in_guild(ctx.guild.id)
        searched_tags: list[tuple[TagEntry, float]] = []
        for tag in guild_tags:
            if (ratio := fuzz(query, tag.tag_name)) > fuzzy_ratio_minmum:
                searched_tags.append((tag, ratio))
        searched_tags.sort(key=lambda x: x[1], reverse=True)
        if len(searched_tags) == 0:
            raise SentinelErrors.TagNotFound(
                f"Cannot any matching tags for query: `{query}`"
            )
        view = SearchTagsPaginator(ctx, tuple(searched_tags), query, 10)
        await view.update()
        embed = await view.embed(view.displayed_values)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @tags.group()
    @commands.guild_only()
    async def alias(self, ctx: SentinelContext):
        pass

    @alias.command(name="new")
    @commands.guild_only()
    async def alias_new(
        self,
        ctx: SentinelContext,
        alias_name: StringAnnotation = LowerStringParam,
        tag_name: StringAnnotation = LowerStringParam,
    ):
        tag = await self.bot.tdm.get_tag_by_name(
            ctx.guild.id, tag_name, allow_redirect=True
        )
        if tag is None:
            raise SentinelErrors.TagNotFound(f"Cannot find tag: `{tag_name}`")
        if isinstance(tag, MetaTagEntry):
            raise SentinelErrors.TagNotFound(
                f"Cannot create alias for an alias: `{tag_name}`"
            )
        if not self._is_valid_tag_name(alias_name):
            raise SentinelErrors.BadTagName(f"Invalid tag name: `{alias_name}`")
        result = await self.bot.tdm.create_alias(
            alias_name, tag.tag_id, ctx.author.id, ctx.guild.id
        )
        if result == ReturnCode.ALREADY_EXISTS:
            raise SentinelErrors.TagNameExists(f"Tag: `{alias_name}` already exists")
        embed = ctx.embed(
            title=f"Alias `{alias_name}` created",
            description=f"Alias for tag `{tag.tag_name}`",
        )
        await ctx.send(embed=embed)

    @alias.command(name="delete")
    @commands.guild_only()
    async def alias_delete(
        self, ctx: SentinelContext, alias_name: StringAnnotation = LowerStringParam
    ):
        result = await self.bot.tdm.delete_alias(
            alias_name, ctx.author.id, ctx.guild.id
        )
        if result == ReturnCode.NOT_FOUND:
            raise SentinelErrors.TagNotFound(f"Cannot find alias: `{alias_name}`")
        if result == ReturnCode.MISSING_PERMISSIONS:
            raise SentinelErrors.MissingPermissions(
                f"You do not have permission to delete alias: `{alias_name}`"
            )
        if result == ReturnCode.NOT_ALIAS:
            raise SentinelErrors.TagNotFound(
                f"This name is not an alias, but a tag name: `{alias_name}`"
            )
        embed = ctx.embed(
            title=f"Alias `{alias_name}` Deleted",
        )
        await ctx.send(embed=embed)

    def _is_valid_tag_name(self, tag_name: str) -> bool:
        return (
            re.match(TAG_NAME_REGEX, tag_name) is not None
            and tag_name not in RESERVED_TAG_NAMES
        )


class GuildTagsPaginator(Paginator):
    async def embed(self, value_range: tuple[TagEntry]) -> discord.Embed:
        desc = ""
        for i, tag in enumerate(value_range):
            desc += f"`{i + self.page_size * self.current_page + 1}:` `{tag.tag_name}` | `{tag.uses}` Uses\n"
        embed = self.ctx.embed(
            title=f"Tags in `{self.ctx.guild.name}`",
            description=desc,
        )
        return embed


class MemberTagsPaginator(Paginator):
    def __init__(
        self,
        ctx: SentinelContext,
        member: discord.Member,
        values: tuple[TagEntry],
        page_size: int,
    ):
        super().__init__(ctx, values, page_size)
        self.member = member

    async def embed(self, value_range: tuple[TagEntry]) -> discord.Embed:
        desc = ""
        for i, tag in enumerate(value_range):
            desc += f"`{i + self.page_size * self.current_page + 1}:` `{tag.tag_name}` | `{tag.uses}` Uses\n"
        embed = self.ctx.embed(
            title=f"Tags by `{self.member.name}`",
            description=desc,
        )
        return embed


class SearchTagsPaginator(Paginator):
    def __init__(
        self,
        ctx: SentinelContext,
        values: tuple[tuple[TagEntry, float]],
        query: str,
        page_size: int,
    ):
        super().__init__(ctx, values, page_size)
        self.query = query

    async def embed(self, value_range: tuple[tuple[TagEntry, float]]) -> discord.Embed:
        desc = ""
        for i, tag in enumerate(value_range):
            desc += f"`{i + self.page_size * self.current_page + 1}:` `{tag[0].tag_name}` | `{tag[1] * 100:.2f}%` | `{tag[0].uses}` Uses\n"
        embed = self.ctx.embed(
            title=f"Tags Matching `{self.query}`",
            description=desc,
        )
        return embed


async def setup(bot: Sentinel):
    await bot.add_cog(Tags(bot))
