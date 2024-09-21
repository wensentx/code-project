import datetime
import re

import discord
import pytz
from discord import app_commands
from discord.ext import commands

from cogs.femida.database.connection import create_tables
from cogs.femida.database.functions import FemidaDB


class TimeConverter:
    def __init__(self):
        self.regex = re.compile(r"(\d{1,5})([hmsd])")
        self.time_dict = {'h': 3600, 's': 1, 'm': 60, 'd': 86400}

    async def convert(self, argument: str) -> int:
        args = argument.lower()
        matches = re.findall(self.regex, args)
        time = 0
        for value, key in matches:
            try:
                time += self.time_dict[key] * float(value)
            except KeyError:
                raise commands.BadArgument(f"{key} is an invalid key. h|s|m|d are valid")
            except ValueError:
                raise commands.BadArgument(f"{value} is not a number")
        time: int = round(time)
        return time


class LogsPaginator(discord.ui.View):
    def __init__(self, embeds):
        self.current = 0
        self.embeds = embeds
        super().__init__(timeout=None)

    async def update_buttons(self):
        if self.current == 0:
            self.previous_page.disabled = True
            self.next_page.disabled = False

        if self.current == len(self.embeds) - 1:
            self.next_page.disabled = True
            self.previous_page.disabled = False

        if len(self.embeds) == 1:
            self.previous_page.disabled = True
            self.next_page.disabled = True

    @discord.ui.button(label='Назад', style=discord.ButtonStyle.gray)
    async def previous_page(self, interaction, _):
        self.current -= 1
        await self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

    @discord.ui.button(label='Вперед', style=discord.ButtonStyle.gray)
    async def next_page(self, interaction, _):
        self.current += 1
        await self.update_buttons()
        await interaction.response.edit_message(embed=self.embeds[self.current], view=self)

    @discord.ui.button(label='Закрыть', style=discord.ButtonStyle.red)
    async def close(self, interaction, _):
        await interaction.response.defer()
        await interaction.delete_original_response()


async def get_embeds_logs(interaction, member):
    logs = await FemidaDB().get_logs_by_user_id(member.id)
    pages = []
    label = ""
    k = 0
    for n, i in enumerate(logs, start=1):
        k += 1
        user = interaction.guild.get_member(i.moderator_id)
        user = user.mention if user is not None else "Пользователь не найден"
        start_time = discord.utils.format_dt(datetime.datetime.strptime(i.start_time, '%Y-%m-%d %H:%M:%S.%f'), 'f')
        finish_time = discord.utils.format_dt(datetime.datetime.strptime(i.finish_time, '%Y-%m-%d %H:%M:%S.%f'), 'f')
        reasons_map = {
            'MUTE': 'Мут',
            'UNMUTE': 'Размут',
            'WARN': 'Предупреждение'
        }
        label += f"> **Модератор:** {user}\n" \
                 f"> **Действие:** {reasons_map[i.action]}\n" \
                 f"> **Причина:** {i.reason}\n" \
                 f"> **Время начала:** {start_time}\n" \
                 f"> **Время окончания:** {finish_time}\n\n"
        if k % 5 == 0 or k == len(logs):
            embed = discord.Embed(title='— • Логи пользователя', color=0x2F3136)
            embed.set_thumbnail(url=interaction.user.display_avatar)
            embed.description = label
            pages.append(embed)
            label = ""
    return pages


class FemidaService(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        await create_tables()

    @app_commands.command(name='mute', description='Замутить пользователя')
    @app_commands.describe(member='укажите пользователя', time='укажите время', reason='укажите причину')
    @app_commands.rename(member='пользователь', time='время', reason='причина')
    async def mute(self, interaction,
                   member: discord.Member,
                   time: str,
                   reason: app_commands.Range[str, 1, 300]
                   ):
        if member.id == interaction.user.id:
            embed = discord.Embed(
                title="— • Мут пользователя",
                description=f"{interaction.user.mention}, вы не можете замутить себя.",
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            return await interaction.response.send_message(embed=embed, ephemeral=True)
        if member.timed_out_until is not None:
            timeout_finished = discord.utils.format_dt(member.timed_out_until, 'R')
            embed = discord.Embed(
                title="— • Мут пользователя",
                description=(
                    f"{interaction.user.mention}, указанный пользователь ({member.mention}) уже имеет наказание."
                    f" Его наказание закончится {timeout_finished}"
                ),
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if member.bot is True:
            embed = discord.Embed(
                title="— • Мут пользователя",
                description=f"{interaction.user.mention}, вы не можете замутить бота.",
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        time: int = await TimeConverter().convert(time)
        if time > 604800:
            embed = discord.Embed(
                title="— • Мут пользователя",
                description=f"{interaction.user.mention}, вы не можете выдать мут на более чем 7 дней.",
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        current = datetime.datetime.now(tz=pytz.timezone('Europe/Moscow'))
        finished_at = current + datetime.timedelta(seconds=time)
        await member.timeout(finished_at, reason=f'{interaction.user} | {reason}')
        await FemidaDB().add_log(
            moderator_id=interaction.user.id,
            user_id=member.id,
            action='MUTE',
            reason=reason,
            start_time=str(current.replace(tzinfo=None)),
            finish_time=str(finished_at.replace(tzinfo=None))
        )
        timeout_finished = discord.utils.format_dt(finished_at, 'R')
        embed = discord.Embed(
            title="— • Мут пользователя",
            description=f"{interaction.user.mention}, вы замутили пользователя {member.mention}. "
                        f"Мут закончится {timeout_finished}",
            color=0x2F3136
        ).set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            message = (
                f'Вы получили таймаут на сервере {interaction.guild}\nПричина: {reason}.\n'
                f'Вас замутил(а) {interaction.user.mention} ({interaction.user}).\n'
            )
            await member.send(message)
        except discord.errors.Forbidden:
            pass
        for channel in interaction.guild.text_channels:
            async for c in channel.history(after=datetime.datetime.now() - datetime.timedelta(minutes=5)):
                if c.author == member:
                    try:
                        await c.delete()
                    except Exception as e:
                        print(f'{e}')

    @app_commands.command(name='warn', description='Выдать предупреждение пользователю')
    @app_commands.describe(member='укажите пользователя', reason='укажите причину')
    @app_commands.rename(member='пользователь', reason='причина')
    async def warn(
            self,
            interaction,
            member: discord.Member,
            reason: app_commands.Range[str, 1, 300]
    ):

        if member.id == interaction.user.id:
            embed = discord.Embed(
                title="— • Предупреждение пользователя",
                description=f"{interaction.user.mention}, вы не можете выдать предупреждение самому себе.",
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if member.bot is True:
            embed = discord.Embed(
                title="— • Предупреждение пользователя",
                description=f"{interaction.user.mention}, вы не можете выдать предупреждение боту.",
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        current = datetime.datetime.now(tz=pytz.timezone('Europe/Moscow'))
        finished_at = current + datetime.timedelta(seconds=300)
        await member.timeout(finished_at, reason=f'{interaction.user} | {reason}')
        await FemidaDB().add_log(
            moderator_id=interaction.user.id,
            user_id=member.id,
            action='WARN',
            reason=reason,
            start_time=str(current.replace(tzinfo=None)),
            finish_time=str(finished_at.replace(tzinfo=None))
        )
        embed = discord.Embed(
            title="— • Предупреждение пользователя",
            description=(
                f"{interaction.user.mention}, вы выдали предупреждение пользователю {member.mention}."
            ),
            color=0x2F3136
        ).set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            message = (
                f'Вы получили предупреждение на сервере {interaction.guild}\nПричина: {reason}.\n'
                f'Вас предупредил(а) {interaction.user.mention} ({interaction.user}).\n'
            )
            await member.send(message)
        except discord.errors.Forbidden:
            pass

    @app_commands.command(name='unmute', description='Размутить пользователя')
    @app_commands.describe(member='укажите пользователя', reason='укажите причину')
    @app_commands.rename(member='пользователь', reason='причина')
    async def unmute(self, interaction: discord,
                     member: discord.Member,
                     reason: app_commands.Range[str, 1, 300]):

        if member.id == interaction.user.id:
            embed = discord.Embed(
                title="— • Размут пользователя",
                description=f"{interaction.user.mention}, вы не можете снять тайм-аут с себя.",
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if member.timed_out_until is None:
            embed = discord.Embed(
                title="— • Размут пользователя",
                description=f"{interaction.user.mention}, указанный пользователь ({member.mention}) не имеет наказания.",
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        current = datetime.datetime.now().astimezone(pytz.timezone('Europe/Moscow'))
        await member.timeout(None, reason=f'{interaction.user} | {reason}')
        await FemidaDB().add_log(
            moderator_id=interaction.user.id,
            user_id=member.id,
            action='UNMUTE',
            reason=reason,
            start_time=str(current.replace(tzinfo=None)),
            finish_time=str(current.replace(tzinfo=None))
        )
        embed = discord.Embed(
            title="— • Размут пользователя",
            description=(
                f"{interaction.user.mention}, вы сняли тайм-аут с пользователя {member.mention}."
            ),
            color=0x2F3136
        ).set_thumbnail(url=interaction.user.display_avatar.url)
        await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            message = (
                f'Вы были размучены на сервере {interaction.guild}\nПричина: {reason}.\n'
                f'С вас снял(а) тайм-аут {interaction.user.mention} ({interaction.user}).\n'
            )
            await member.send(message)
        except discord.errors.Forbidden:
            pass

    @app_commands.command(name='logs', description='Посмотреть логи пользователя')
    @app_commands.describe(member='укажите пользователя')
    @app_commands.rename(member='пользователь')
    async def logs(
            self,
            interaction,
            member: discord.Member):
        logs = await FemidaDB().get_logs_by_user_id(member.id)
        if not logs:
            embed = discord.Embed(
                title="— • Логи пользователя",
                description=(
                    f"{interaction.user.mention}, Вы запросили логи пользователя {member.mention}."
                    f" На данный момент у пользователя нет логов."
                ),
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embeds = await get_embeds_logs(interaction, member)
        view = LogsPaginator(embeds)
        await view.update_buttons()
        await interaction.response.send_message(embed=embeds[0], view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(FemidaService(bot))
