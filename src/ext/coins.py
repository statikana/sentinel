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
from ..db_managers import UserDataManager


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
        balance = await self.bot.udm.get_balance(member.id)
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
        giver_bal = await self.bot.udm.get_balance(ctx.author.id)
        rec_bal = await self.bot.udm.get_balance(member.id)
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

        view = GiveCoinsConfirmation(ctx, self.bot.udm, ctx.author, member, amount)
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
        giver_bal = await self.bot.udm.get_balance(member.id)
        rec_bal = await self.bot.udm.get_balance(ctx.author.id)
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

        view = GiveCoinsConfirmation(ctx, self.bot.udm, member, ctx.author, amount)
        await ctx.send(content=member.mention, embed=embed, view=view)
    
    @coins.command()
    @commands.guild_only()
    async def hourly(self, ctx: SentinelContext):
        hourly_coins = 100
        if isinstance(ctx.author, discord.User):
            return
        result = await self.bot.udm.try_hourly(ctx.author.id, hourly_coins)
        if result:
            embed = ctx.embed(
                title="Hourly Coins Claimed",
                description=f"You have claimed your hourly coins and received \N{Coin}`{hourly_coins:,}`",
            )
        else:
            remaining = await self.bot.udm.get_next_hourly(ctx.author.id)
            embed = ctx.embed(
                title="Hourly Coins Already Claimed",
                description=f"You have already claimed your hourly coins. You can claim them again <t:{int(remaining.timestamp())}:R> at <t:{int(remaining.timestamp())}:F>",
                color=discord.Color.red(),
            )
        await ctx.send(embed=embed)

    @coins.command()
    @commands.guild_only()
    async def daily(self, ctx: SentinelContext):
        """Claim your daily coins"""
        daily_coins = 200
        if isinstance(ctx.author, discord.User):
            return
        result = await self.bot.udm.try_daily(ctx.author.id, daily_coins)
        if result:
            embed = ctx.embed(
                title="Daily Coins Claimed",
                description=f"You have claimed your daily coins and received \N{Coin}`{daily_coins:,}`",
            )
        else:
            remaining = await self.bot.udm.get_next_daily(ctx.author.id)
            embed = ctx.embed(
                title="Daily Coins Already Claimed",
                description=f"You have already claimed your daily coins. You can claim them again <t:{int(remaining.timestamp())}:R> at <t:{int(remaining.timestamp())}:F>",
                color=discord.Color.red(),
            )
        await ctx.send(embed=embed)

    @coins.command()
    @commands.guild_only()
    async def weekly(self, ctx: SentinelContext):
        """Claim your weekly coins"""
        weekly_coins = 1000
        if isinstance(ctx.author, discord.User):
            return
        result = await self.bot.udm.try_weekly(ctx.author.id, weekly_coins)
        if result:
            embed = ctx.embed(
                title="Weekly Coins Claimed",
                description=f"You have claimed your weekly coins and received \N{Coin}`{weekly_coins:,}`",
            )
        else:
            remaining = await self.bot.udm.get_next_weekly(ctx.author.id)
            embed = ctx.embed(
                title="Weekly Coins Already Claimed",
                description=f"You have already claimed your weekly coins. You can claim them again <t:{int(remaining.timestamp())}:R> at <t:{int(remaining.timestamp())}:F>",
                color=discord.Color.red(),
            )
        await ctx.send(embed=embed)
    
    @coins.command()
    @commands.guild_only()
    async def monthly(self, ctx: SentinelContext):
        """Claim your monthly coins"""
        monthly_coins = 5000
        if isinstance(ctx.author, discord.User):
            return
        result = await self.bot.udm.try_monthly(ctx.author.id, monthly_coins)
        if result:
            embed = ctx.embed(
                title="Monthly Coins Claimed",
                description=f"You have claimed your monthly coins and received \N{Coin}`{monthly_coins:,}`",
            )
        else:
            remaining = await self.bot.udm.get_next_monthly(ctx.author.id)
            embed = ctx.embed(
                title="Monthly Coins Already Claimed",
                description=f"You have already claimed your monthly coins. You can claim them again <t:{int(remaining.timestamp())}:R> at <t:{int(remaining.timestamp())}:F>",
                color=discord.Color.red(),
            )
        await ctx.send(embed=embed)

    @commands.command()
    @commands.is_owner()
    async def set_coin_balance(
        self, ctx: SentinelContext, member: discord.Member, amount: int
    ):
        await self.bot.udm.set_balance(member.id, amount)
        await ctx.send(f"Set `{member}`'s balance to \N{Coin}`{amount:,}`")


# noinspection PyUnusedLocal
class GiveCoinsConfirmation(SentinelView):
    def __init__(
        self,
        ctx: SentinelContext,
        usm: UserDataManager,
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
