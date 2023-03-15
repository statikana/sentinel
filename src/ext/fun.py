import random
import discord
from discord.ext import commands
from discord.app_commands import describe
import asyncio
from ..sentinel import Sentinel, SentinelCog, SentinelContext

from ..converters import Range


class Fun(SentinelCog, emoji="\N{Party Popper}"):
    """
    Some fun commands to play around with! On some games, you can even do a lil' gambling!
    """

    @commands.hybrid_command()
    @describe(
        lower="The lower bound of the range, 0-10000 [inclusive]",
        upper="The upper bound of the range, 0-10000 [inclusive]",
        maximum_attempts="The maximum number of attempts you can have, 1-20 [inclusive]. Defaults to 3",
        gamble_amount="The amount of money you want to gamble. The riskier the game, the more your money will be multiplied! Defaults to 0",
    )
    async def highlow(
        self,
        ctx: SentinelContext,
        lower: int = Range(int, 0, 10000),
        upper: int = Range(int, 0, 10000),
        maximum_attempts: int = Range(int, 1, 20),
        gamble_amount: int = Range(int, 0, default=0),
    ):
        """Try to guess a number between a given range!"""
        attempts = 0
        gamble_amount *= round(
            (upper - lower) / maximum_attempts
        )  # simple formula to make the game more risky the higher the range is and the less attempts you have

        number = random.randint(lower, upper)

        if lower > upper:
            raise commands.BadArgument("Lower bound must be less than upper bound")
        if lower + 10 > upper:
            raise commands.BadArgument("You make it too easy!")

        embed = ctx.embed(
            title=f"Guess a Number between `{lower}` and `{upper}`...",
            description=f"You have `{maximum_attempts - attempts}` more attempts to guess the number. Type `cancel` to cancel the game.",
        )
        message = await ctx.send(embed=embed)
        guesses: list[int] = []
        while attempts < maximum_attempts:
            attempts += 1

            try:
                response: discord.Message = await self.bot.wait_for(
                    "message",
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                    timeout=30,
                )
            except asyncio.TimeoutError:
                await message.edit(
                    embed=ctx.embed(
                        title="You took too long to respond!",
                        description="Better luck next time!",
                    )
                )
                return

            if response.content.lower() == "cancel":
                embed = ctx.embed(
                    title="Game cancelled!",
                    description=f"""The number was `{number}`. Better luck next time!
                    **Guess History:**\n{self._highlow_format_guesses(guesses, number)}\N{Broken Heart}""",
                )
                await message.edit(embed=embed)
                await response.delete()
                return

            try:
                guess = int(response.content)
                guesses.append(guess)
            except ValueError:
                attempts -= 1
                embed = ctx.embed(
                    title="Invalid input!",
                    description=f"""You have `{maximum_attempts - attempts}` more attempts to guess the number. Type `cancel` to cancel the game.
                    **Guess History:**\n{self._highlow_format_guesses(guesses, number)}""",
                )
                await message.edit(embed=embed)
                await response.add_reaction("\N{Exclamation Question Mark}")
                continue

            if guess < number:
                embed = ctx.embed(
                    title="Too low!",
                    description=f"""You have `{maximum_attempts - attempts}` more attempts to guess the number. Type `cancel` to cancel the game.
                    **Guess History:**\n{self._highlow_format_guesses(guesses, number)}""",
                )
                await message.edit(embed=embed)
            elif guess > number:
                embed = ctx.embed(
                    title="Too high!",
                    description=f"""
                    You have `{maximum_attempts - attempts}` more attempts to guess the number. Type `cancel` to cancel the game.
                    **Guess History:**\n{self._highlow_format_guesses(guesses, number)}""",
                )
                await message.edit(embed=embed)
            else:
                embed = ctx.embed(
                    title="You got it!",
                    description=f"""The number was `{guess}`! You used `{attempts}` out of `{maximum_attempts}` attempts.
                    **Guess History:**\n{self._highlow_format_guesses(guesses, number)}""",
                )
                await message.edit(embed=embed)
                await response.delete()
                return
            try:
                await response.delete()
            except discord.Forbidden:
                pass
        else:
            embed = ctx.embed(
                title="You ran out of attempts!",
                description=f"""The number was `{number}`. Better luck next time!
                **Guess History:**\n{self._highlow_format_guesses(guesses, number)}""",
            )
            await message.edit(embed=embed)
            return

    def _highlow_format_guesses(self, guesses: list[int], number: int):
        formatted_guesses = ""
        for guess in guesses:
            formatted_guesses += f"`{guess}`"
            if guess > number:
                formatted_guesses += "\N{Down-Pointing Red Triangle}"
            elif guess < number:
                formatted_guesses += "\N{Up-Pointing Red Triangle}"
            else:
                formatted_guesses += "\N{White Heavy Check Mark}"
            formatted_guesses += "\n"
        return formatted_guesses


async def setup(bot: Sentinel):
    await bot.add_cog(Fun(bot))
