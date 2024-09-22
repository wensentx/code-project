import json
import os

import aiofiles
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()
DISCORD_GUILD = int(os.getenv('DISCORD_GUILD'))


class Statistic(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.count = 0
        self.config = None
        self.bot.loop.create_task(self.load_config())

    async def load_config(self):
        async with aiofiles.open('cogs/feedback/config.json', 'r', encoding='utf-8') as f:
            content = await f.read()
            self.config = json.loads(content)

    async def save_config(self):
        async with aiofiles.open('cogs/feedback/config.json', 'w', encoding='utf-8') as f:
            await f.write(json.dumps(self.config, indent=4, ensure_ascii=False))

    @tasks.loop(seconds=10)
    async def update_member_count(self):
        await self.load_config()
        guild = self.bot.get_guild(DISCORD_GUILD)
        channel = self.bot.get_channel(self.config['statistic']['CHANNEL_ID'])
        if channel is None:
            return

        if self.count != guild.member_count:
            self.count = guild.member_count

            await channel.edit(name=f'👥 Участники: {guild.member_count}')

    @commands.Cog.listener()
    async def on_ready(self):
        self.update_member_count.start()


async def setup(bot: commands.Bot):
    await bot.add_cog(Statistic(bot))
