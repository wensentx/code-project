import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = discord.Object(id=int(os.getenv('DISCORD_GUILD')))


class Code(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=discord.Intents.all(),
            test_guilds=[int(os.getenv('DISCORD_GUILD'))]
        )

    async def on_ready(self):
        print(f'Bot is ready as {self.user}')

    async def setup_hook(self):
        await self.load_cogs()
        self.tree.copy_global_to(guild=GUILD_ID)
        await self.tree.sync(guild=GUILD_ID)

    async def load_cogs(self):
        for filename in os.listdir('./cogs'):
            for file in os.listdir(f'./cogs/{filename}'):
                if file.endswith('.py') and not file.startswith('_'):
                    await self.load_extension(f'cogs.{filename}.{file[:-3]}')
                    print(f'Loaded cog: {file[:-3]}')


client = Code()
if __name__ == "__main__":
    client.run(DISCORD_TOKEN, reconnect=True)