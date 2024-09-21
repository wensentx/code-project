import discord
from discord.ext import commands


class Forum(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot: commands.Bot):
    await bot.add_cog(Forum(bot))