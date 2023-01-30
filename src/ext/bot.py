import discord
from discord.ext import commands
from discord.app_commands import describe


from ..sentinel import Sentinel, SentinelCog, SentinelContext, SentinelView


class Bot(SentinelCog, emoji="\N{Robot Face}"):
    """Bot-related commands"""

    @commands.hybrid_group()
    async def bot(self, ctx: SentinelContext):
        """Bot-related commands"""
        pass

    @bot.command()
    async def invite(self, ctx: SentinelContext):
        """Invite the bot to your server!"""
        embed = ctx.embed(title="Invite the bot to your server!")
        view = SentinelView(ctx, timeout=None)
        view.add_item(
            discord.ui.Button(
                label="Invite",
                url="https://discord.com/oauth2/authorize?client_id=1061346504335425576&permissions=8&scope=applications.commands%20bot",
                style=discord.ButtonStyle.link,
                emoji="\N{Link Symbol}",
            )
        )
        await ctx.send(embed=embed, view=view)

    @commands.hybrid_command(name="invite")
    async def invite_(self, ctx: SentinelContext):
        return await self.invite(ctx)

    @bot.command()
    async def source(self, ctx: SentinelContext):
        """View the source code!"""


async def setup(bot: Sentinel):
    await bot.add_cog(Bot(bot))
