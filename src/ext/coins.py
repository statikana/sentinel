import discord
from discord.ext import commands
from discord.app_commands import describe

from ..sentinel import (
    Sentinel,
    SentinelCog,
    SentinelContext,
    SentinelView,
)
from ..converters import Range
from ..command_util import ParamDefaults
from ..db_managers import UserManager


class Coins(SentinelCog, emoji="\N{Banknote with Dollar Sign}"):
    """
    Sentinel's very own global currency system! You can earn by levelling up, logging in daily, gambling, and many more ways!"""

    @commands.hybrid_group()
    async def coins(
        self, ctx: SentinelContext, member: discord.Member = ParamDefaults.member
    ):
        """Coin-related commands"""
        if ctx.invoked_subcommand:
            return

        return await self.balance.callback(
            self, ctx, member
        )  # shortcut to balance command

    @coins.command()
    @commands.guild_only()
    @describe(
        member="The member to check the balance of. Defaults to the author",
    )
    async def balance(
        self, ctx: SentinelContext, member: discord.Member = ParamDefaults.member
    ):
        """Check your coins balance"""
        if member.bot:
            embed = ctx.embed(title="Bots don't have coins!", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        balance = await self.bot.usm.get_balance(member.id)
        embed = ctx.embed(
            title=f"`{member}`'s Balance", description=f"\N{Coin}{balance:,}"
        )
        await ctx.send(embed=embed)

    @coins.command()
    @commands.guild_only()
    @describe(
        member="The member to give coins to",
        amount="The amount of coins to give. Must be at least one, and no more than your balance",
    )
    async def give(
        self, ctx: SentinelContext, member: discord.Member, amount: int = Range(int, 1)
    ):
        """Give coins to another member"""
        if amount < 1:
            embed = ctx.embed(title="Invalid Amount", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        if member.bot:
            embed = ctx.embed(title="Cannot Give To Bots", color=discord.Color.red())
            await ctx.send(embed=embed)
            return
        giver_bal = await self.bot.usm.get_balance(ctx.author.id)
        rec_bal = await self.bot.usm.get_balance(member.id)
        if giver_bal < amount:
            embed = ctx.embed(
                title="Transaction Failed",
                description="You do not have enough \N{Coin} to complete this transaction.",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        description = f"`{ctx.author}` is giving `{member}` \N{Coin}`{amount:,}`\n"
        description += f"`{ctx.author}`'s Balance: \N{Coin}`{giver_bal:,}`\nNew Balance: \N{Coin}`{giver_bal - amount:,}`\n"
        description += f"`{member}`'s Balance: \N{Coin}`{rec_bal:,}`\nNew Balance: \N{Coin}`{rec_bal + amount:,}`"

        embed = ctx.embed(
            title="Confirm Transaction",
            description=description,
        )

        if isinstance(ctx.author, discord.User):
            return  # wha

        view = GiveCoinsConfirmation(ctx, self.bot.usm, ctx.author, member, amount)
        view.message = await ctx.send(embed=embed, view=view)

    @coins.command()
    @commands.guild_only()
    async def request(
        self, ctx: SentinelContext, member: discord.Member, amount: int = Range(int, 1)
    ):
        """Request coins from another member"""
        if amount < 1:
            raise commands.BadArgument("Invalid amount")
        if member.bot:
            raise commands.BadArgument("Cannot request from bots")
        giver_bal = await self.bot.usm.get_balance(member.id)
        rec_bal = await self.bot.usm.get_balance(ctx.author.id)
        if giver_bal < amount:
            embed = ctx.embed(
                title="Transaction Failed",
                description=f"`{member}` does not have enough \N{Coin} to complete this transaction.\n\n`{member}`'s Balance: \N{Coin}`{giver_bal:,}`",
                color=discord.Color.red(),
            )
            await ctx.send(embed=embed)
            return
        description = f"`{member}` is giving `{ctx.author}` **\N{Coin}`{amount:,}`**\n"
        description += f"`{member}` [Current]: \N{Coin}`{giver_bal:,}`\n`{member}` [New]: \N{Coin}`{giver_bal - amount:,}`\n"
        description += f"`{ctx.author}` [Current]: \N{Coin}`{rec_bal:,}`\n`{ctx.author}` [New]: \N{Coin}`{rec_bal + amount:,}`"

        embed = ctx.embed(
            title="Confirm Transaction",
            description=description,
        )

        if isinstance(ctx.author, discord.User):
            return

        view = GiveCoinsConfirmation(ctx, self.bot.usm, member, ctx.author, amount)
        await ctx.send(content=member.mention, embed=embed, view=view)

    @commands.command()
    @commands.is_owner()
    async def set_coin_balance(
        self, ctx: SentinelContext, member: discord.Member, amount: int
    ):
        await self.bot.usm.set_balance(member.id, amount)
        await ctx.send(f"Set `{member}`'s balance to \N{Coin}`{amount:,}`")


class GiveCoinsConfirmation(SentinelView):
    def __init__(
        self,
        ctx: SentinelContext,
        usm: UserManager,
        giver: discord.Member,
        receiver: discord.Member,
        amount: int,
    ):
        self.giver = giver
        self.receiver = receiver
        self.amount = amount
        self.usm = usm
        super().__init__(
            ctx, timeout=60 * 30, any_responder=True
        )  # Responses are handled by the buttons # 1/2 hour timeout

    @discord.ui.button(
        label="Accept",
        style=discord.ButtonStyle.green,
        emoji="\N{White Heavy Check Mark}",
    )
    async def accept(self, itx: discord.Interaction, button: discord.ui.Button):
        if itx.user.id != self.giver.id:
            embed = self.ctx.embed(
                title="Invalid User",
                description="You are not the giver in this transaction.",
                color=discord.Color.red(),
            )
            await itx.response.send_message(embed=embed, ephemeral=True)
            return
        successful, giver_bal, rec_bal = await self.usm.give_balance(
            self.giver.id, self.receiver.id, self.amount, True
        )
        if successful:
            embed = self.ctx.embed(
                title="Transaction Successful",
                description=f"`{self.giver}` gave `{self.receiver}` \N{Coin}`{self.amount:,}`\n`{self.giver}`'s Balance: \N{Coin}`{giver_bal:,}`\n`{self.receiver}`'s Balance: \N{Coin}`{rec_bal:,}`",
            )
            await itx.response.send_message(embed=embed)
        else:
            embed = self.ctx.embed(
                title="Transaction Failed",
                description="Something went wrong, please try again later.\nYour balance has not been affected.",
            )
            await itx.response.send_message(embed=embed)

    @discord.ui.button(
        label="Decline", style=discord.ButtonStyle.red, emoji="\N{Cross Mark}"
    )
    async def decline(self, itx: discord.Interaction, button: discord.ui.Button):
        if not (itx.user.id == self.giver.id or itx.user.id == self.receiver.id):
            embed = self.ctx.embed(
                title="Invalid User",
                description="You are not involved in this transaction.",
                color=discord.Color.red(),
            )
            await itx.response.send_message(embed=embed, ephemeral=True)
            return
        embed = self.ctx.embed(
            title=f"Transaction Declined by `{itx.user}`",
            description="The transaction has been cancelled.\nYour balance has not been affected.",
        )
        await itx.response.send_message(embed=embed)


async def setup(bot: Sentinel):
    await bot.add_cog(Coins(bot))
