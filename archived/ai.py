# import asyncio
# import discord
# from discord.ext import commands

# from ..src.sentinel import Sentinel, SentinelCog, SentinelContext, SentinelView
# from ..src.converters import URLClean, URLCleanParam

# import openai


# class AI(SentinelCog, emoji="\N{Brain}"):
#     @commands.hybrid_group()
#     async def ai(self, ctx: SentinelContext):
#         pass


#     @ai.command()
#     async def prompt(self, ctx: SentinelContext, *, prompt: str):
#         """Works a prompt to complete or edit text"""
#         print(prompt)
#         thread = asyncio.to_thread(
#             openai.Completion.create, 
#             model="text-babbage-001",
#             prompt=prompt,
#             temperature=0.75,
#             max_tokens=64,
#         )
#         response = await thread
#         await ctx.send(str(response))


# async def setup(bot: Sentinel):
#     await bot.add_cog(AI(bot))
        