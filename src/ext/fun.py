from enum import Enum
import random
import discord
from discord.ext import commands
from discord.app_commands import describe
import asyncio

from ..command_util import fuzz
from ..sentinel import Sentinel, SentinelCog, SentinelContext, SentinelView

from ..converters import FigletFont, FigletFontParam, Range
import pyfiglet


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


    @commands.hybrid_command()
    async def font(self, ctx: SentinelContext, text: str, font: FigletFontParam = FigletFont):
        """Converts your text into a Figlet font!"""
        embed = ctx.embed(
            description=f"```{font.renderText(text)}```",
        )
        await ctx.send(embed=embed)
    
    @font.autocomplete("font")
    async def font_autocomplete(self, interaction: discord.Interaction, current: str):
        return sorted(
            [
                discord.app_commands.Choice(name=font, value=font)
                for font in pyfiglet.FigletFont.getFonts()
                if fuzz(current, font) > 0.2 or not current
            ][:25],
            key=lambda c: c.name, # type: ignore
        )
    
    @commands.hybrid_command()
    async def ascii(self, ctx: SentinelContext, text: str):
        """Converts your text into ASCII!"""
        embed = ctx.embed(
            description=f"```{pyfiglet.figlet_format(text)}```",
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command()
    async def roll(self, ctx: SentinelContext, sides: int = Range(int, 1, 10000), times: int = Range(int, 1, 20)):
        """Rolls a die with the given number of sides!"""
        if times == 1:
            embed = ctx.embed(
                title=f"You rolled a `{random.randint(1, sides)}`!",
            )
        else:
            desc = [f"Roll `{i+1}`: `{random.randint(1, sides)}`" for i in range(times)]
            embed = ctx.embed(
                title=f"You rolled a `{sides}`-sided die `{times}` times",
                description="\n".join(desc),
            )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command()
    async def flip(self, ctx: SentinelContext):
        embed = ctx.embed(
            title=f"You flipped... `{random.choice(('heads', 'tails'))}`!",
        )
        await ctx.send(embed=embed)
    
    @commands.hybrid_command()
    async def tictactoe(self, ctx: SentinelContext, other: discord.Member):
        """Play a game of tic tac toe with another user!"""
        embed = ctx.embed(
            title="Accept Tic Tac Toe Challenge?",
            description=f"{other.mention}, please select an option below to accept or decline this challenge.",
        )
        await ctx.send(embed=embed, view=TicTacToeAcceptView(ctx, other))


class TicTacToeAcceptView(SentinelView):
    def __init__(self, ctx: SentinelContext, other: discord.Member):
        super().__init__(ctx, timeout=60)
        self.other = other

    async def interaction_check(self, itx: discord.Interaction) -> bool:
        if not (itx.user.id == self.other.id) and (itx.channel is not None) and (itx.channel.id == self.ctx.channel.id):
            await itx.response.send_message("You cannot accept this challenge.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
    async def accept(self, itx: discord.Interaction, button: discord.ui.Button):
        embed = self.ctx.embed(
            title="Tic Tac Toe",
            description=f"{self.ctx.author.mention} vs {self.other.mention}",
        )
        view = TicTacToeGameView(self.ctx, self.other)
        await itx.response.edit_message(content=f"Your move, {self.other.mention}", embed=embed, view=view)
        view.message = itx.message

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.danger)
    async def decline(self, itx: discord.Interaction, button: discord.ui.Button):
        embed = self.ctx.embed(
            title="Tic Tac Toe Challenge Declined",
            description=f"{self.other.mention} has declined your challenge.",
        )
        await itx.response.edit_message(content=self.ctx.author.mention, embed=embed)


class TicTacToeGameView(SentinelView):
    def __init__(self, ctx: SentinelContext, other: discord.Member):
        super().__init__(ctx, timeout=60)
        self.other = other
        self.board_state = [[0, 0, 0], [0, 0, 0], [0, 0, 0]] # 0 = empty, 1 = 0, 2 = X
        self.turn: discord.Member = self.other
        self.turn_count = 0

    async def interaction_check(self, itx: discord.Interaction) -> bool:
        return itx.user.id == self.turn.id and itx.channel is not None and itx.channel.id == self.ctx.channel.id
    
    @discord.ui.button(label=" - ", style=discord.ButtonStyle.secondary)
    async def button_1(self, itx: discord.Interaction, button: discord.ui.Button):
        await self.update_board_state(itx, button, 0, 0)

    @discord.ui.button(label=" - ", style=discord.ButtonStyle.secondary)
    async def button_2(self, itx: discord.Interaction, button: discord.ui.Button):
        await self.update_board_state(itx, button, 0, 1)
    
    @discord.ui.button(label=" - ", style=discord.ButtonStyle.secondary)
    async def button_3(self, itx: discord.Interaction, button: discord.ui.Button):
        await self.update_board_state(itx, button, 0, 2)
    
    @discord.ui.button(label=" - ", style=discord.ButtonStyle.secondary, row=1)
    async def button_4(self, itx: discord.Interaction, button: discord.ui.Button):
        await self.update_board_state(itx, button, 1, 0)
    
    @discord.ui.button(label=" - ", style=discord.ButtonStyle.secondary, row=1)
    async def button_5(self, itx: discord.Interaction, button: discord.ui.Button):
        await self.update_board_state(itx, button, 1, 1)
    
    @discord.ui.button(label=" - ", style=discord.ButtonStyle.secondary, row=1)
    async def button_6(self, itx: discord.Interaction, button: discord.ui.Button):
        await self.update_board_state(itx, button, 1, 2)
    
    @discord.ui.button(label=" - ", style=discord.ButtonStyle.secondary, row=2)
    async def button_7(self, itx: discord.Interaction, button: discord.ui.Button):
        await self.update_board_state(itx, button, 2, 0)
    
    @discord.ui.button(label=" - ", style=discord.ButtonStyle.secondary, row=2)
    async def button_8(self, itx: discord.Interaction, button: discord.ui.Button):
        await self.update_board_state(itx, button, 2, 1)

    @discord.ui.button(label=" - ", style=discord.ButtonStyle.secondary, row=2)
    async def button_9(self, itx: discord.Interaction, button: discord.ui.Button):
        await self.update_board_state(itx, button, 2, 2)

    async def update_board_state(self, itx: discord.Interaction, button: discord.ui.Button, x: int, y: int):
        button.disabled = True
        self.turn_count += 1
        if self.turn == self.other:
            self.board_state[x][y] = 2
            button.label = "X"
            button.style = discord.ButtonStyle.danger
        else:
            self.board_state[x][y] = 1
            button.label = "O"
            button.style = discord.ButtonStyle.success
        embed = self.ctx.embed(
            title="Tic Tac Toe",
            description=f"{self.ctx.author.mention} vs {self.other.mention}",
        )
        if itx.message:
            await itx.message.edit(content=f"Your move, {self.turn.mention}", embed=embed, view=self)
            status = self.get_game_status()
            if status is TicTacToeGameStatus.WIN: # winner is self.turn
                embed = self.ctx.embed(
                    title=f"`{self.turn}` beat `{self._get_opposite(self.turn)}` in Tic Tac Toe",
                    description=f"{self.ctx.author.mention} vs {self.other.mention}",
                )
                await itx.response.edit_message(content=None, embed=embed)
                await self.on_timeout()
            
            elif status is TicTacToeGameStatus.DRAW:
                embed = self.ctx.embed(
                    title=f"`{self.turn}` drew with `{self._get_opposite(self.turn)}` in Tic Tac Toe",
                    description=f"{self.ctx.author.mention} vs {self.other.mention}",
                )
                await itx.response.edit_message(content=None, embed=embed)
                await self.on_timeout()
            else:
                await itx.response.defer(ephemeral=True)
                self.turn = self._get_opposite(self.turn)
    
    def _get_opposite(self, player: discord.Member) -> discord.Member:
        return self.other if player == self.ctx.author else self.ctx.author # type: ignore
        
        
        
    def get_game_status(self) -> "TicTacToeGameStatus":
        # check rows
        for row in self.board_state:
            if row[0] == row[1] == row[2] and row[0] != 0:
                return TicTacToeGameStatus.WIN
        # check columns
        for i in range(3):
            if self.board_state[0][i] == self.board_state[1][i] == self.board_state[2][i] and self.board_state[0][i] != 0:
                return TicTacToeGameStatus.WIN
        # check diagonals
        if self.board_state[0][0] == self.board_state[1][1] == self.board_state[2][2] and self.board_state[0][0] != 0:
            return TicTacToeGameStatus.WIN
        if self.board_state[0][2] == self.board_state[1][1] == self.board_state[2][0] and self.board_state[0][2] != 0:
            return TicTacToeGameStatus.WIN
        # check draw
        if self.turn_count == 9:
            return TicTacToeGameStatus.DRAW # I could actually check if it's possible to actually win but I can do that later
        return TicTacToeGameStatus.IN_PROGRESS


class TicTacToeGameStatus(Enum):
    IN_PROGRESS = 0
    DRAW = 1
    WIN = 2
    


    
        




async def setup(bot: Sentinel):
    await bot.add_cog(Fun(bot))
