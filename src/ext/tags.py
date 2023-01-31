import discord
from discord.ext import commands
from discord.app_commands import describe

from ..command_types import TagEntry
from ..command_util import ParamDefaults, fuzz
from ..converters import StringParam, LowerString, fuzz


from ..sentinel import (
    Sentinel,
    SentinelCog,
    SentinelContext,
    SentinelErrors,
)
from ..command_util import Paginator


class Tags(SentinelCog, emoji="\N{Label}"):
    """Create guild-specific tags for use in the server"""

    @commands.hybrid_group()
    async def tags(self, ctx: SentinelContext):
        """Manage tags"""
        if ctx.invoked_subcommand:
            return

        return await self.all.callback(self, ctx)

    @tags.command()
    @commands.guild_only()
    @describe(
        name="The name of the tag to retrieve",
    )
    async def get(self, ctx: SentinelContext, name: StringParam = LowerString):
        """Get a tag"""
        await self.bot.usm.ensure_user(ctx.author.id)
        if ctx.guild is None:
            raise commands.CommandInvokeError(
                Exception("This command can only be used in a guild")
            )

        tag = await self.bot.tgm.get_tag_by_name(ctx.guild.id, name)
        if tag is None:
            raise commands.BadArgument("That tag doesn't exist")

        await self.bot.tgm.increment_tag_uses(tag.tag_id)

        embed = ctx.embed(
            title=f"**`{tag.tag_name}`**", description=f"{tag.tag_content}"
        )
        await ctx.send(embed=embed)

    @tags.command()
    @commands.guild_only()
    @describe(
        name="The name of the tag to get info about",
    )
    async def info(self, ctx: SentinelContext, name: StringParam = LowerString):
        """Get info about a tag"""
        await self.bot.usm.ensure_user(ctx.author.id)
        if ctx.guild is None:
            raise commands.CommandInvokeError(
                Exception("This command can only be used in a guild")
            )

        tag = await self.bot.tgm.get_tag_by_name(ctx.guild.id, name)
        if tag is None:
            raise commands.BadArgument("That tag doesn't exist")

        await self.bot.tgm.increment_tag_uses(tag.tag_id)

        embed = ctx.embed(
            title=f"Tag Info - `{tag.tag_name}`",
            description=f"""
            **Tag ID:** `{tag.tag_id}`
            **Owner:** `{ctx.guild.get_member(tag.owner_id) or 'USERID ' + str(tag.owner_id)}`
            **Created:** <t:{int(tag.created_at.timestamp())}:R> [<t:{int(tag.created_at.timestamp())}:F>)]
            **Uses:** `{tag.uses}`""",
        )
        await ctx.send(embed=embed)

    @tags.command()
    @commands.guild_only()
    @describe(
        name="The name of the new tag",
        content="The content of the new tag",
    )
    async def new(
        self, ctx: SentinelContext, name: StringParam = LowerString, *, content: str
    ):
        """Create a new tag"""
        await self.bot.usm.ensure_user(ctx.author.id)
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
            and await self.bot.tgm.get_tag_by_name(ctx.guild.id, name) is not None
        ):  # Checking if guild exists for linter
            raise SentinelErrors.TagNameExists("A tag with that name already exists")

        tag = await self.bot.tgm.create_tag(name, content, ctx.author.id, ctx.guild.id)
        embed = ctx.embed(
            title=f"Tag Created - `{tag.tag_name}`", description=f"{tag.tag_content}"
        )
        await ctx.send(embed=embed)

    @tags.command()
    @commands.guild_only()
    @describe(
        name="The name of the tag to delete",
        content="The content of the new tag",
    )
    async def edit(
        self, ctx: SentinelContext, name: StringParam = LowerString, *, content: str
    ):
        """Edit a tag. You must be the owner of the tag to edit it"""
        await self.bot.usm.ensure_user(ctx.author.id)
        if ctx.guild is None:
            raise commands.CommandInvokeError(
                Exception("This command can only be used in a guild")
            )

        if len(content) > 2000:
            raise commands.BadArgument("Tag content must be under 2000 characters")

        successful = await self.bot.tgm.edit_tag_by_name(
            name, ctx.guild.id, content, True, True, ctx.author.id
        )
        if not successful:
            raise commands.BadArgument(
                "Either that tag doesn't exist or you don't have permission to edit it"
            )

        embed = ctx.embed(title=f"Tag Edited - `{name}`", description=f"{content}")
        await ctx.send(embed=embed)

    @tags.command()
    @commands.guild_only()
    @describe(
        name="The name of the tag to delete",
    )
    async def delete(self, ctx: SentinelContext, name: StringParam = LowerString):
        """Delete a tag. You must be the owner of the tag to delete it"""
        await self.bot.usm.ensure_user(ctx.author.id)
        if ctx.guild is None:
            raise commands.CommandInvokeError(
                Exception("This command can only be used in a guild")
            )

        successful = await self.bot.tgm.delete_tag_by_name(
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

    @tags.command()
    @commands.guild_only()
    @describe(
        member="The member to transfer the tag to",
        name="The name of the tag to transfer",
    )
    async def transfer(
        self,
        ctx: SentinelContext,
        member: discord.Member,
        name: StringParam = LowerString,
    ):
        """Transfer a tag to another user. You must be the owner of the tag to transfer it"""
        await self.bot.usm.ensure_user(ctx.author.id)
        if ctx.guild is None:
            raise commands.CommandInvokeError(
                Exception("This command can only be used in a guild")
            )

        tag = await self.bot.tgm.get_tag_by_name(ctx.guild.id, name)
        if tag is None:
            raise SentinelErrors.TagNotFound("That tag doesn't exist")

        if tag.owner_id != ctx.author.id:
            raise SentinelErrors.MissingVaguePermissions("You don't own that tag")
        if member.id == ctx.author.id:
            raise SentinelErrors.BadMemberInput("You can't transfer a tag to yourself")
        if member.bot:
            raise SentinelErrors.BadMemberInput("You can't transfer a tag to a bot")

        await self.bot.tgm.transfer_tag_ownership(tag.tag_id, member.id)

        embed = ctx.embed(
            title=f"Tag Transferred",
            description=f"**`{name}`** has been transferred to **`{member}`**",
        )
        await ctx.send(embed=embed)

    @tags.command()
    @commands.guild_only()
    @describe(
        query="The name of the tag to search for",
        fuzzy_ratio_minmum="The minimum fuzzy ratio to search for. The closer to one, the more accurate results need to be to be returned",
    )
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

        guild_tags = await self.bot.tgm.get_tags_in_guild(ctx.guild.id)
        searched_tags: list[tuple[TagEntry, float]] = []
        for tag in guild_tags:
            if (ratio := fuzz(query, tag.tag_name)) > fuzzy_ratio_minmum:
                searched_tags.append((tag, ratio))
        searched_tags.sort(key=lambda x: x[1], reverse=True)
        view = TagSearchPaginator(ctx, [t[0] for t in searched_tags], query)
        embed = await view.embed(view.displayed_values)
        message = await ctx.send(embed=embed)
        view.message = message
        await view.update()

    @tags.command()
    @commands.guild_only()
    @describe(
        member="The member to view the tags of",
    )
    async def by(
        self, ctx: SentinelContext, member: discord.Member = ParamDefaults.member
    ):
        """View all tags owned by a member"""
        if ctx.guild is None:
            raise commands.CommandInvokeError(
                Exception("This command can only be used in a guild")
            )

        member_tags = await self.bot.tgm.get_tags_by_owner(member.id)
        view = MemberTagsPaginator(ctx, member_tags, member)
        embed = await view.embed(view.displayed_values)
        message = await ctx.send(embed=embed)
        view.message = message
        await view.update()

    @tags.command()
    @commands.guild_only()
    async def all(self, ctx: SentinelContext):
        """View all tags in a guild"""
        if ctx.guild is None:
            raise commands.CommandInvokeError(
                Exception("This command can only be used in a guild")
            )

        guild_tags = await self.bot.tgm.get_tags_in_guild(ctx.guild.id)
        view = AllTagsPaginator(ctx, guild_tags)
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
            title=f'Tag Search - `"{self.query}"`: Page `{self.current_page+1}/{self.max_page+1}`',
            description=descirption,
        )
        return embed


class AllTagsPaginator(Paginator):
    def __init__(self, ctx: SentinelContext, tags: list[TagEntry]):
        super().__init__(ctx, tuple(tags), page_size=10)

    async def embed(self, value_range: tuple[TagEntry]) -> discord.Embed:
        descirption = ""
        for i, tag in enumerate(self.displayed_values):
            descirption += (
                f"`{i + self.display_values_index_start + 1}:` **`{tag.tag_name}`**\n"
            )

        embed = self.ctx.embed(
            title=f"All Tags in `{self.ctx.guild.name if self.ctx.guild is not None else '...'}` - Page `{self.current_page+1}/{self.max_page+1}`",
            description=descirption,
        )
        return embed


class MemberTagsPaginator(Paginator):
    def __init__(
        self, ctx: SentinelContext, tags: list[TagEntry], member: discord.Member
    ):
        super().__init__(ctx, tuple(tags), page_size=10)
        self.member = member

    async def embed(self, value_range: tuple[TagEntry]) -> discord.Embed:
        descirption = ""
        for i, tag in enumerate(self.displayed_values):
            descirption += (
                f"`{i + self.display_values_index_start + 1}:` **`{tag.tag_name}`**\n"
            )

        embed = self.ctx.embed(
            title=f"`{self.member}`'s Tags - Page `{self.current_page+1}/{self.max_page+1}`",
            description=descirption,
        )
        return embed


async def setup(bot: Sentinel):
    await bot.add_cog(Tags(bot))
