import logging
import discord
from discord.ext import commands
from typing import Optional, Sequence

from ..sentinel import NumT, Sentinel, SentinelCog, SentinelContext
from ..command_util import Paginator, ParamDefaults
from .events import Events


class Dev(SentinelCog, emoji="\N{Personal Computer}", hidden=True):
    @commands.command()
    @commands.is_owner()
    async def reload(self, ctx: SentinelContext):
        exts, utils = await self.bot.reload_extensions()
        description = [f"**{e}**" for e in exts]
        description.extend([f"*{u}*" for u in utils])
        embed = ctx.embed(
            title="Successful Reload \N{White Heavy Check Mark}",
            description="\n".join(description),
        )
        await ctx.send(embed=embed)
        logging.info(f"Reloaded {len(exts)} extensions and {len(utils)} utils")

    @commands.command()
    @commands.is_owner()
    async def sync(self, ctx: SentinelContext, guild_id: Optional[int]):
        await self.bot.tree.sync(guild=discord.Object(guild_id) if guild_id else None)
        embed = ctx.embed(
            title="Successful Sync \N{White Heavy Check Mark}",
            description=f"Synced {guild_id or 'all'}",
        )
        await ctx.send(embed=embed)

    @commands.group()
    @commands.is_owner()
    async def blacklist(self, ctx: SentinelContext, user: discord.User | None):
        """Shows the blacklist"""
        if ctx.invoked_subcommand:
            return
        if not user:

            class BLDisplay(Paginator):
                async def embed(self, displayed_values: tuple):
                    description = "\n".join(
                        f"`{i + self.display_values_index_start + 1}:` <@{user_id}> | `{user_id}`"
                        for i, user_id in enumerate(displayed_values)
                    )
                    return ctx.embed(
                        title=f"`Blacklisted Users:` Page `{self.current_page + 1}/{self.max_page + 1}`",
                        description=description,
                    )

            opts = tuple(
                user["user_id"]
                for user in await self.bot.apg.fetch("SELECT user_id FROM blacklist")
            )
            view = BLDisplay(ctx, opts, 10)
            embed = await view.embed(view.displayed_values)
            message = await ctx.send(embed=embed, view=view)
            view.message = message
            await view.update()
        else:
            return await self.add.callback(self, ctx, user)

    @blacklist.command()
    @commands.is_owner()
    async def add(self, ctx: SentinelContext, user: discord.User):
        """Add a user to the blacklist"""
        await self.bot.udm.ensure_user(user.id)
        await self.bot.apg.execute("INSERT INTO blacklist VALUES ($1)", user.id)
        embed = ctx.embed(
            title="Successful Blacklist \N{White Heavy Check Mark}",
            description=f"Blacklisted {user.mention} | `{user}`",
        )
        await ctx.send(embed=embed)

    @blacklist.command()
    @commands.is_owner()
    async def remove(self, ctx: SentinelContext, user: discord.User):
        """Remove a user from the blacklist"""
        await self.bot.apg.execute("DELETE FROM blacklist WHERE user_id = $1", user.id)
        embed = ctx.embed(
            title="Successful Whitelist \N{White Heavy Check Mark}",
            description=f"Whitelisted {user.mention} | `{user}`",
        )

        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def sql(self, ctx: SentinelContext, option: str, *, command: str):
        if option == "fetch":
            await ctx.send(str(list(await self.bot.apg.fetch(command))))
        else:
            await self.bot.apg.execute(command)
            await ctx.send("Executed: " + command)
    
    @commands.command()
    @commands.is_owner()
    async def reload_guilds(self, ctx: SentinelContext):
        guildlen = len(self.bot.guilds)
        for guild in self.bot.guilds:
            await self.bot.gdm.ensure_guild(guild.id)
            await self.bot.gcm.ensure_guild_config(guild.id)
        embed = ctx.embed(
            title="Successful Reload \N{White Heavy Check Mark}",
            description=f"Reloaded `{guildlen}` guilds",
        )
        await ctx.send(embed=embed)
    
    @commands.command()
    @commands.is_owner()
    async def reload_users(self, ctx: SentinelContext):
        userlen = len(self.bot.users)
        for user in self.bot.users:
            await self.bot.udm.ensure_user(user.id) # may take a very long time
        embed = ctx.embed(
            title="Successful Reload \N{White Heavy Check Mark}",
            description=f"Reloaded `{userlen}` users",
        )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def manual_function(self, ctx: SentinelContext):
        await ctx.send("send the func")
        text: discord.Message = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author)
        await ctx.send("send the trigger")
        trigger: discord.Message = await self.bot.wait_for("message", check=lambda m: m.author == ctx.author)
        await Events(self.bot).process_code(text.content.splitlines(), trigger)



async def setup(bot: Sentinel):
    await bot.add_cog(Dev(bot))
