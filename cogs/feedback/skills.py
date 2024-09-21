import json

import aiofiles
import discord
from discord import app_commands
from discord.ext import commands

from cogs.feedback.database.functions import UserDB


class Skills(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = None
        self.bot.loop.create_task(self.load_config())

    async def load_config(self):
        async with aiofiles.open('cogs/feedback/config.json', 'r', encoding='utf-8') as f:
            content = await f.read()
            self.config = json.loads(content)

    async def save_config(self):
        async with aiofiles.open('cogs/feedback/config.json', 'w', encoding='utf-8') as f:
            await f.write(json.dumps(self.config, indent=4, ensure_ascii=False))

    @app_commands.command(name='dumb', description='Ограничить доступ к каналу помощи')
    @app_commands.describe(member='укажите пользователя')
    @app_commands.rename(member='пользователь')
    async def dumb(
            self,
            interaction,
            member: discord.Member
    ):

        if member.id == interaction.user.id:
            embed = discord.Embed(
                title="— • Ограничение доступа",
                description=(
                    f"{interaction.user.mention}, вы **не можете** ограничить доступ себе!"
                ),
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if member.bot:
            embed = discord.Embed(
                title="— • Ограничение доступа",
                description=(
                    f"{interaction.user.mention}, вы **не можете** ограничить доступ боту!"
                ),
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await UserDB().get_or_create_user(member.id)
        role = interaction.guild.get_role(self.config['skills']['NEWBIE_ROLE_ID'])
        if role in member.roles:
            await member.remove_roles(role)

            await UserDB().update_user(user_id=member.id, is_dumb=False)
            embed = discord.Embed(
                title="— • Ограничение доступа",
                description=(
                    f"{interaction.user.mention}, Вы **разрешили** доступ к каналу помощи "
                    f"пользователю {member.mention}!"
                ),
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)

        else:
            await member.add_roles(role)
            await UserDB().update_user(user_id=member.id, is_dumb=True)
            embed = discord.Embed(
                title="— • Ограничение доступа",
                description=(
                    f"{interaction.user.mention}, Вы **запретили** доступ к каналу помощи "
                    f"пользователю {member.mention}!"
                ),
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Skills(bot))
