import json
import os

import aiofiles
import discord
import discord.ext.commands
from discord.ext import commands, tasks
from dotenv import load_dotenv

from cogs.room.database.connection import create_tables
from cogs.room.database.functions import *

load_dotenv()

GUILD_ID = int(os.getenv('DISCORD_GUILD'))


async def is_owner(interaction, title) -> bool:
    """
    Проверка на владельца комнаты
    :param interaction: discord.MessageInteraction
    :param title: str
    :return: bool
    """
    if interaction.user.voice:
        voice_id = interaction.user.voice.channel.id
        room = await ChannelFunc().get_channel_by_user_and_channel(interaction.user.id, voice_id)
        if room is None:
            embed = discord.Embed(
                title=title, color=0x2F3136,
                description=(
                    f"{interaction.user.mention}, Вы **не являетесь** владельцем комнаты!"
                )).set_thumbnail(url=interaction.user.display_avatar)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
    return True


async def is_voice(interaction, title) -> bool:
    """
    Проверка на нахождение в голосовом канале
    :param interaction: discord.MessageInteraction
    :param title: str
    :return: bool
    """
    if interaction.user.voice is None:
        embed = discord.Embed(
            title=title, color=0x2F3136,
            description=(
                f"{interaction.user.mention}, Вы **не находитесь** в голосовом канале!"
            )
        ).set_thumbnail(url=interaction.user.display_avatar)
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return False
    return True


async def is_accept(interaction, title: str) -> bool:
    """
    Проверка на нахождение в голосовом канале и владельца комнаты
    :param interaction: discord.MessageInteraction
    :param title: str
    :return: bool
    """
    if await is_voice(interaction, title) and await is_owner(interaction, title):
        return True
    return False


async def is_channel_member(interaction, member: discord.Member, title: str) -> bool:
    """
    Проверка на нахождение пользователя в голосовом канале
    :param interaction: discord.MessageInteraction
    :param member: discord.Member
    :param title: str
    :return: bool
    """
    if member not in interaction.user.voice.channel.members:
        embed = discord.Embed(
            title=title, color=0x2F3136,
            description=(
                f"{interaction.user.mention}, {member.mention} **не находится** в Вашем приватном "
                f"голосовом канале."
            )).set_thumbnail(url=member.display_avatar)
        await interaction.response.edit_message(embed=embed, view=None)
        return False
    return True


class UserView(discord.ui.View):
    def __init__(self, mode: str):
        self.mode = mode
        super().__init__(timeout=30)
        if self.mode == "setowner":
            self.add_item(SetOwner())
        elif self.mode == "kick":
            self.add_item(KickUser())
        elif self.mode == "accept":
            self.add_item(AcceptUser())
        elif self.mode == "deny":
            self.add_item(DenyUser())
        elif self.mode == "mute":
            self.add_item(MuteUser())
        else:
            self.add_item(UnmuteUser())


class SetOwner(discord.ui.UserSelect):
    def __init__(self):
        super().__init__(max_values=1, placeholder="Выберите пользователя")

    async def callback(self, interaction):
        member = self.values[0]

        if not await is_accept(interaction, "Передать владение комнатой"):
            return

        if await is_channel_member(interaction, member, "Передать владение комнатой") is False:
            return

        room = await ChannelFunc().get_channel_by_user(member.id)
        if room is not None:
            embed = discord.Embed(
                title="Передать владение комнатой", color=0x2F3136,
                description=(
                    f"{interaction.user.mention}, пользователь {member.mention} **уже является** "
                    f"владельцем комнаты."
                )).set_thumbnail(url=interaction.user.display_avatar)
            return await interaction.response.edit_message(embed=embed, view=None)

        embed = discord.Embed(
            title="Передать владение комнатой", color=0x2F3136,
            description=(
                f"{interaction.user.mention}, Вы успешно **передали владение** Вашей комнатой "
                f"пользователю {member.mention}."
            )).set_thumbnail(url=interaction.user.display_avatar)
        await ChannelFunc().update_channel_by_channel(interaction.user.voice.channel.id, 'user_id', member.id)
        await interaction.response.edit_message(embed=embed, view=None)


class KickUser(discord.ui.MentionableSelect):
    def __init__(self):
        super().__init__(max_values=1, placeholder="Выберите пользователя или роль")

    async def callback(self, interaction):
        choice = self.values[0]
        if not await is_accept(interaction, "Выгнать из комнаты"):
            return

        member = interaction.guild.get_member(self.values[0].id)
        channel = interaction.user.voice.channel
        if member:
            if member.id == interaction.user.id:
                embed = discord.Embed(
                    title="Выгнать из комнаты", color=0x2F3136,
                    description=(
                        f"{interaction.user.mention}, Вы **не можете выгнать** из "
                        f"Вашей приватной комнаты самого себя."
                    )).set_thumbnail(url=interaction.user.display_avatar)
                return await interaction.response.edit_message(embed=embed, view=None)

            if not await is_channel_member(interaction, choice, "Выгнать из комнаты"):
                return

            embed = discord.Embed(
                title="Выгнать из комнаты", color=0x2F3136,
                description=(
                    f"{interaction.user.mention}, Вы успешно **выгнали** пользователя {member.mention} "
                    f"из Вашей приватной комнаты.")
            )
            await member.move_to(channel=None)

        else:
            embed = discord.Embed(title="Выгнать из комнаты", color=0x2F3136)
            queue_members = [m for m in channel.members if member != interaction.user and choice in member.roles]
            if len(queue_members) == 0:
                embed.description = (
                    f"{interaction.user.mention}, в Вашей приватной комнате **нет пользователей** "
                    f"с ролью {choice.mention}."
                )
                embed.set_thumbnail(url=interaction.user.display_avatar)
                return await interaction.response.edit_message(embed=embed, view=None)
            embed.description = (
                f"{interaction.user.mention}, Вы успешно **выгнали** пользователей с ролью "
                f"{choice.mention} из Вашей приватной комнаты."
            )
            for m in queue_members:
                await m.move_to(channel=None)
        embed.set_thumbnail(url=interaction.user.display_avatar)
        await interaction.response.edit_message(embed=embed, view=None)


class AcceptUser(discord.ui.MentionableSelect):
    def __init__(self):
        super().__init__(max_values=1, placeholder="Выберите пользователя или роль")

    async def callback(self, interaction):
        if not await is_accept(interaction, "Выдать доступ в комнату"):
            return

        member = interaction.guild.get_member(self.values[0].id)
        embed = discord.Embed(title="Выдать доступ в комнату", color=0x2F3136)
        if member is True:
            description1 = (
                f"{interaction.user.mention}, Вы успешно **разрешили** доступ "
                f"пользователю {self.values[0].mention} к Вашей приватной комнате."
            )
            description2 = (
                f"{interaction.user.mention}, У {self.values[0].mention} уже **есть "
                f"доступ** к Вашей приватной комнате."
            )
        else:
            description1 = (
                f"{interaction.user.mention}, Вы успешно **разрешили** доступ "
                f"пользователям роли {self.values[0].mention} к Вашей приватной комнате."
            )
            description2 = (
                f"{interaction.user.mention}, У пользователей с ролью {self.values[0].mention} "
                f"уже **есть доступ** к Вашей приватной комнате."
            )
        if self.values[0] not in interaction.user.voice.channel.overwrites:
            embed.description = description2
        elif interaction.user.voice.channel.overwrites[self.values[0]].connect is False or \
                interaction.user.voice.channel.overwrites[self.values[0]].connect is None:
            embed.description = description1
        else:
            embed.description = description2
        embed.set_thumbnail(url=interaction.user.display_avatar)
        await interaction.user.voice.channel.set_permissions(self.values[0], connect=True)
        await interaction.response.edit_message(embed=embed, view=None)


class DenyUser(discord.ui.MentionableSelect):
    def __init__(self):
        super().__init__(max_values=1, placeholder="Выберите пользователя или роль")

    async def callback(self, interaction):
        if not await is_accept(interaction, "Забрать доступ в комнату"):
            return

        member = interaction.guild.get_member(self.values[0].id)
        embed = discord.Embed(title="Забрать доступ в комнату", color=0x2F3136)
        if member:
            if member.id == interaction.user.id:
                embed = discord.Embed(
                    title="Забрать доступ в комнату", color=0x2F3136,
                    description=(
                        f"{interaction.user.mention}, Вы **не можете забрать доступ** в "
                        f"Вашу приватную комнату у самого себя."
                    )).set_thumbnail(url=interaction.user.display_avatar)
                return await interaction.response.edit_message(embed=embed, view=None)

            description1 = (
                f"{interaction.user.mention}, Вы успешно **запретили** доступ "
                f"пользователю {self.values[0].mention} к Вашей приватной комнате."
            )
            description2 = (
                f"{interaction.user.mention}, У {self.values[0].mention} уже **отсутствует "
                f"доступ** к Вашей приватной комнате."
            )
        else:
            description1 = (
                f"{interaction.user.mention}, Вы успешно **запретили** доступ "
                f"пользователям роли {self.values[0].mention} к Вашей приватной комнате."
            )
            description2 = (
                f"{interaction.user.mention}, У пользователей с ролью {self.values[0].mention} "
                f"уже **отсутствует доступ** к Вашей приватной комнате."
            )
        channel = interaction.user.voice.channel
        if self.values[0] not in channel.overwrites:
            embed.description = description1
        elif channel.overwrites[self.values[0]].connect is True or \
                channel.overwrites[self.values[0]].connect is None:
            embed.description = description1
        else:
            embed.description = description2
        embed.set_thumbnail(url=interaction.user.display_avatar)
        await channel.set_permissions(self.values[0], connect=False)
        await interaction.response.edit_message(embed=embed, view=None)


class MuteUser(discord.ui.MentionableSelect):
    def __init__(self):
        super().__init__(max_values=1, placeholder="Выберите пользователя или роль")

    async def callback(self, interaction):
        if not await is_accept(interaction, "Забрать право говорить"):
            return

        member = interaction.guild.get_member(self.values[0].id)
        embed = discord.Embed(title="Забрать право говорить", color=0x2F3136)
        if member:
            if member.id == interaction.user.id:
                embed = discord.Embed(
                    title="Забрать право говорить", color=0x2F3136,
                    description=(
                        f"{interaction.user.mention}, Вы **не можете забрать право говорить** в "
                        f"Вашей приватной комнате у самого себя."
                    )).set_thumbnail(url=interaction.user.display_avatar)
                return await interaction.response.edit_message(embed=embed, view=None)

            description1 = (
                f"{interaction.user.mention}, Вы успешно **забрали** право говорить у "
                f"пользователя {self.values[0].mention} в Вашей приватной комнате.")
            description2 = (
                f"{interaction.user.mention}, У {self.values[0].mention} уже **отсутствует право "
                f"говорить** в Вашей приватной комнате."
            )
        else:
            description1 = (
                f"{interaction.user.mention}, Вы успешно **забрали** право говорить всем "
                f"пользователям роли {self.values[0].mention} в Вашей приватной комнате.")
            description2 = (
                f"{interaction.user.mention}, У пользователей с ролью {self.values[0].mention} "
                f"уже **отсутствует право говорить** в Вашей приватной комнате."
            )
        if self.values[0] not in interaction.user.voice.channel.overwrites:
            embed.description = description1
        elif interaction.user.voice.channel.overwrites[self.values[0]].speak is True or \
                interaction.user.voice.channel.overwrites[self.values[0]].speak is None:
            embed.description = description1
        else:
            embed.description = description2
        embed.set_thumbnail(url=interaction.user.display_avatar)
        await interaction.user.voice.channel.set_permissions(self.values[0], speak=False)
        await interaction.response.edit_message(embed=embed, view=None)


class UnmuteUser(discord.ui.MentionableSelect):
    def __init__(self):
        super().__init__(max_values=1, placeholder="Выберите пользователя или роль")

    async def callback(self, interaction):
        if not await is_accept(interaction, "Забрать право говорить"):
            return

        member = interaction.guild.get_member(self.values[0].id)
        embed = discord.Embed(title="Забрать право говорить", color=0x2F3136)
        if member:
            description1 = (
                f"{interaction.user.mention}, Вы успешно **выдали** право говорить "
                f"пользователю {self.values[0].mention} в Вашей приватной комнате."
            )
            description2 = (
                f"{interaction.user.mention}, У {self.values[0].mention} уже **есть право "
                f"говорить** в Вашей приватной комнате."
            )
        else:
            description1 = (
                f"{interaction.user.mention}, Вы успешно **выдали** право говорить всем "
                f"пользователям роли {self.values[0].mention} в Вашей приватной комнате."
            )
            description2 = (
                f"{interaction.user.mention}, У пользователей с ролью {self.values[0].mention} "
                f"уже **есть право говорить** в Вашей приватной комнате."
            )
        channel = interaction.user.voice.channel
        if self.values[0] not in channel.overwrites:
            embed.description = description2
        elif channel.overwrites[self.values[0]].speak is False or channel.overwrites[self.values[0]].speak is None:
            embed.description = description1
        else:
            embed.description = description2
        embed.set_thumbnail(url=interaction.user.display_avatar)
        await channel.set_permissions(self.values[0], speak=True)
        await interaction.response.edit_message(embed=embed, view=None)


class EditRoomName(discord.ui.Modal):
    def __init__(self, channel: discord.VoiceChannel):
        self.channel = channel
        super().__init__(title="Изменить название комнаты")

    name = discord.ui.TextInput(
        label="Название комнаты",
        custom_id="pr_edit_name",
        style=discord.TextStyle.short,
        max_length=100,
        min_length=1,
        placeholder="Введите название комнаты",
        required=True
    )

    async def on_submit(self, interaction):
        log = await LogFunc().get_log_by_user(interaction.user.id, "CHANGE_NAME")
        embed = discord.Embed(
            title="Изменение названия комнаты",
            color=0x2F3136,

        )
        if (log is None or log and
                datetime.datetime.now() - datetime.timedelta(minutes=10) >
                datetime.datetime.strptime(log.created_at, "%Y-%m-%d %H:%M:%S.%f")):
            embed.description = (
                f"{interaction.user.mention}, Вы успешно **изменили** "
                f"название Вашей приватной комнаты на **`{self.name.value}`**."
            )
            await self.channel.edit(name=self.name.value)
            await LogFunc().add_log(interaction.user.id, "CHANGE_NAME")
            await SettingsFunc().update_settings_by_user(interaction.user.id, "title", self.name.value)
        else:
            cooldown_time = datetime.datetime.strptime(log.created_at, "%Y-%m-%d %H:%M:%S.%f")
            cooldown_time += datetime.timedelta(minutes=10)
            beautiful_time = discord.utils.format_dt(cooldown_time, style="R")
            embed.description = (
                f"{interaction.user.mention}, Вы недавно **уже изменяли** "
                f"название Вашей приватной комнаты! Вы сможете **изменить повторно** "
                f"{beautiful_time}."
            )

        embed.set_thumbnail(url=interaction.user.display_avatar)
        await interaction.response.send_message(embed=embed, ephemeral=True)


class EditRoomLimit(discord.ui.Modal):
    def __init__(self, channel: discord.VoiceChannel):
        self.channel = channel
        super().__init__(title="Изменить лимит комнаты")

    limit = discord.ui.TextInput(
        label="Лимит пользователей",
        custom_id="pr_edit_limit",
        style=discord.TextStyle.short,
        max_length=2,
        min_length=1,
        placeholder="Введите лимит пользователей",
        required=True
    )

    async def on_submit(self, interaction):
        embed = discord.Embed(title="Изменение лимита комнаты", color=0x2F3136)
        if self.limit.value.isdigit() is False:
            embed.description = (
                f"{interaction.user.mention}, Вы **неверно** указали лимит "
                f"пользователей! Лимит должен быть **числом**."
            )
            embed.set_thumbnail(url=interaction.user.display_avatar)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        if int(self.limit.value) > 99 or int(self.limit.value) < 0:
            embed.description = (
                f"{interaction.user.mention}, Вы **неверно** указали лимит "
                f"пользователей! Пожалуйста, введите число от **0** до **99**."
            )
            embed.set_thumbnail(url=interaction.user.display_avatar)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed.description = (
            f"{interaction.user.mention}, Вы успешно **изменили** "
            f"лимит Вашей приватной комнаты на **`{self.limit.value}`**."
        )
        embed.set_thumbnail(url=interaction.user.display_avatar)
        await self.channel.edit(user_limit=int(self.limit.value))
        await SettingsFunc().update_settings_by_user(interaction.user.id, "limit", int(self.limit.value))
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RoomsView(discord.ui.View):
    def __init__(self, bot):
        self.bot = bot
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:hide:1245465909301346477>", custom_id="pr_hide", row=0)
    async def hide(self, interaction, _):
        if not await is_accept(interaction, "Скрыть комнату для всех"):
            return

        channel = interaction.user.voice.channel
        role = interaction.guild.default_role
        embed_hide = discord.Embed(title="Скрыть комнату для всех", color=0x2F3136)
        embed_hide.description = f"{interaction.user.mention}, Вы успешно **скрыли** " \
                                 f"Вашу приватную комнату для всех."
        embed_hide.set_thumbnail(url=interaction.user.display_avatar)

        embed_open = discord.Embed(title="Отобразить комнату для всех", color=0x2F3136)
        embed_open.description = f"{interaction.user.mention}, Вы успешно **отобразили** " \
                                 f"Вашу приватную комнату для всех."
        embed_open.set_thumbnail(url=interaction.user.display_avatar)
        if role not in channel.overwrites:
            await channel.set_permissions(role, view_channel=False)
            await interaction.response.send_message(embed=embed_hide, ephemeral=True)
        elif channel.overwrites[role].view_channel is True or channel.overwrites[role].view_channel is None:
            await channel.set_permissions(role, view_channel=False)
            await interaction.response.send_message(embed=embed_hide, ephemeral=True)
        else:
            await channel.set_permissions(role, view_channel=True)
            await interaction.response.send_message(embed=embed_open, ephemeral=True)

    @discord.ui.button(emoji="<:edit:1245465914061754398>", custom_id="pr_name", row=0)
    async def name(self, interaction, _):
        if not await is_accept(interaction, "Изменить название комнаты"):
            return

        await interaction.response.send_modal(EditRoomName(interaction.user.voice.channel))

    @discord.ui.button(emoji="<:owner:1245465917878566982>", custom_id="pr_setowner", row=0)
    async def setowner(self, interaction, _):
        if not await is_accept(interaction, "Передать владение комнатой"):
            return

        embed = discord.Embed(title="Передать владение комнатой", color=0x2F3136)
        embed.description = f"{interaction.user.mention}, **выберите** пользователя, которому Вы хотите " \
                            f"**передать** владение комнатой."
        embed.set_thumbnail(url=interaction.user.display_avatar)
        await interaction.response.send_message(embed=embed, ephemeral=True, view=UserView('setowner'))

    @discord.ui.button(emoji="<:kick:1245465922718662686>", custom_id="pr_kick", row=0)
    async def kick(self, interaction, _):
        if not await is_accept(interaction, "Выгнать из комнаты"):
            return

        embed = discord.Embed(
            title="Выгнать из комнаты", color=0x2F3136,
            description=(
                f"{interaction.user.mention}, **выберите** пользователя или роль, которого(ую) "
                f"Вы хотите **выгнать** из Вашей комнаты."
            )).set_thumbnail(url=interaction.user.display_avatar)
        await interaction.response.send_message(embed=embed, ephemeral=True, view=UserView('kick'))

    @discord.ui.button(emoji="<:accept:1245465926363779219>", custom_id="pr_accept", row=0)
    async def accept(self, interaction, _):
        if not await is_accept(interaction, "Выдать доступ к комнате"):
            return

        embed = discord.Embed(
            title="Выдать доступ к комнате", color=0x2F3136,
            description=(
                f"{interaction.user.mention}, **выберите** пользователя или роль, которому(ой) "
                f"Вы хотите **выдать** доступ к Вашей комнате."
            )).set_thumbnail(url=interaction.user.display_avatar)
        await interaction.response.send_message(embed=embed, ephemeral=True, view=UserView('accept'))

    @discord.ui.button(emoji="<:reject:1245465933875515432>", custom_id="pr_deny", row=1)
    async def deny(self, interaction, _):
        if not await is_accept(interaction, "Запретить доступ к комнате"):
            return

        embed = discord.Embed(
            title="Запретить доступ к комнате", color=0x2F3136,
            description=(
                f"{interaction.user.mention}, **выберите** пользователя или роль, которому(ой) "
                f"Вы хотите **запретить** доступ к Вашей комнате."
            )).set_thumbnail(url=interaction.user.display_avatar)
        await interaction.response.send_message(embed=embed, ephemeral=True, view=UserView('deny'))

    @discord.ui.button(emoji="<:unmute:1245465940636864573>", custom_id="pr_unmute", row=1)
    async def unmute(self, interaction, _):
        if not await is_accept(interaction, "Выдать право говорить"):
            return

        embed = discord.Embed(
            title="Выдать право говорить", color=0x2F3136,
            description=(
                f"{interaction.user.mention}, **выберите** пользователя или роль, которому(ой) "
                f"Вы хотите **выдать** право говорить в Вашей комнате."
            )).set_thumbnail(url=interaction.user.display_avatar)
        await interaction.response.send_message(embed=embed, ephemeral=True, view=UserView('unmute'))

    @discord.ui.button(emoji="<:mute:1245465947691683923>", custom_id="pr_mute", row=1)
    async def mute(self, interaction, _):
        if not await is_accept(interaction, "Забрать право говорить"):
            return

        embed = discord.Embed(
            title="Забрать право говорить", color=0x2F3136,
            description=(
                f"{interaction.user.mention}, **выберите** пользователя или роль, которому(ой) "
                f"Вы хотите **запретить** говорить в Вашей комнате."
            )).set_thumbnail(url=interaction.user.display_avatar)
        await interaction.response.send_message(embed=embed, ephemeral=True, view=UserView('mute'))

    @discord.ui.button(emoji="<:limit:1245465954817806336>", custom_id="pr_limit")
    async def limit(self, interaction, _):
        if not await is_accept(interaction, "Изменить лимит пользователей"):
            return

        await interaction.response.send_modal(EditRoomLimit(interaction.user.voice.channel))

    @discord.ui.button(emoji="<:close:1245465959888850954>", custom_id="pr_close")
    async def close(self, interaction, _):
        if not await is_accept(interaction, "Открыть/Закрыть комнату для всех"):
            return

        channel = interaction.user.voice.channel
        role = interaction.guild.default_role
        if role not in channel.overwrites:
            await channel.set_permissions(role, connect=False)
            embed = discord.Embed(
                title="Открыть комнату для всех", color=0x2F3136,
                description=(
                    f"{interaction.user.mention}, Вы успешно **открыли** Вашу приватную комнату для всех."
                )).set_thumbnail(url=interaction.user.display_avatar)

        elif channel.overwrites[role].connect is True or channel.overwrites[role].connect is None:
            await channel.set_permissions(role, connect=False)
            embed = discord.Embed(
                title="Закрыть комнату для всех", color=0x2F3136,
                description=(
                    f"{interaction.user.mention}, Вы успешно **закрыли** Вашу приватную комнату для всех."
                )).set_thumbnail(url=interaction.user.display_avatar)

        else:
            await channel.set_permissions(role, connect=True)
            embed = discord.Embed(
                title="Открыть комнату для всех", color=0x2F3136,
                description=(
                    f"{interaction.user.mention}, Вы успешно **открыли** Вашу приватную комнату для всех."
                )).set_thumbnail(url=interaction.user.display_avatar)

        await interaction.response.send_message(embed=embed, ephemeral=True)


class Rooms(commands.Cog):
    def __init__(self, bot):
        self.persistent_views_added = False
        self.bot = bot
        self.config = None
        self.bot.loop.create_task(self.load_config())

    async def load_config(self):
        async with aiofiles.open('cogs/room/config.json', 'r', encoding='utf-8') as f:
            content = await f.read()
            self.config = json.loads(content)

    async def save_config(self):
        async with aiofiles.open('cogs/room/config.json', 'w', encoding='utf-8') as f:
            await f.write(json.dumps(self.config, indent=4, ensure_ascii=False))

    @commands.command()
    async def create_voice(self, ctx):
        embed = discord.Embed(
            title="Управление приватной комнатой", color=0x2F3136,
            description=(
                "**Жми следующие кнопки, чтобы настроить свою приватную комнату.**\n"
                "Использовать их можно только когда у тебя есть приватный канал."
            )
        )
        embed.add_field(name="_ _", value="<:hide:1245465909301346477> — Отобразить/скрыть комнату\n"
                                          "<:edit:1245465914061754398> — Изменить название комнаты\n"
                                          "<:owner:1245465917878566982> — Передать владение комнатой\n"
                                          "<:kick:1245465922718662686> — Выгнать из комнаты\n"
                                          "<:accept:1245465926363779219> — Выдать доступ в комнату",
                        inline=True)
        embed.add_field(name="_ _", value="<:reject:1245465933875515432> — Забрать доступ в комнату\n"
                                          "<:unmute:1245465940636864573> — Выдать право говорить\n"
                                          "<:mute:1245465947691683923> — Забрать право говорить\n"
                                          "<:limit:1245465954817806336> — Изменить лимит пользователей\n"
                                          "<:close:1245465959888850954> — Открыть/закрыть комнату",
                        inline=True)
        await ctx.send(embed=embed, view=RoomsView(self.bot))

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        channels_data = await ChannelFunc().get_channels()
        channels = [channel.channel_id for channel in channels_data]
        if after.channel and after.channel.id == self.config['rooms']['create_channel']:
            current = datetime.datetime.now()
            logs = await LogFunc().get_log_by_user(member.id, "CREATE_ROOM")
            if logs is not None:
                created_at = datetime.datetime.strptime(logs.created_at, "%Y-%m-%d %H:%M:%S.%f")
                if current < created_at + datetime.timedelta(seconds=10):
                    embed = discord.Embed(
                        title="Создание комнаты", color=0x2F3136,
                        description=(
                            f"{member.mention}, Вы **недавно уже создавали** комнату! Попробуйте "
                            f"создать комнату **позже**."
                        )
                    ).set_thumbnail(url=member.display_avatar)
                    try:
                        await member.send(embed=embed, delete_after=60)
                    except:
                        pass
                    return
            await LogFunc().add_log(member.id, "CREATE_ROOM")
            settings = await SettingsFunc().get_settings_by_user(member.id)
            if settings is None:
                name = f"Комната {member.display_name}"
                limit = 0
                await SettingsFunc().add_settings(member.id, name, limit)

            else:
                name = settings.title
                limit = settings.limit
            category = self.bot.get_channel(self.config['rooms']['category_id'])
            channel2 = await member.guild.create_voice_channel(name, category=category)
            await member.move_to(channel2)
            overwrites = {
                self.bot.user: discord.PermissionOverwrite(view_channel=True),
                member: discord.PermissionOverwrite(connect=True, read_messages=True),
            }
            await channel2.edit(name=name, user_limit=limit, overwrites=overwrites)
            await ChannelFunc().add_channel(member.id, channel2.id)

            def check(_, __, ___):
                return len(channel2.members) == 0

            await self.bot.wait_for('voice_state_update', check=check)
            await ChannelFunc().update_channel_by_channel(channel2.id, "is_deleted", True)
            await channel2.delete()
        try:
            if before.channel and before.channel.id in channels:
                channel_info = await ChannelFunc().get_channel_by_channel(before.channel.id)
                if channel_info and channel_info.user_id == member.id:
                    await ChannelFunc().update_channel_by_channel(
                        before.channel.members[0].id, "channel_id", before.channel.id
                    )
        except IndexError:
            pass

    @tasks.loop(seconds=10)
    async def check_current_voice(self):
        channels = await ChannelFunc().get_channels()
        for channel in channels:
            channel = self.bot.get_channel(channel.channel_id)
            try:
                if len(channel.members) == 0:
                    await ChannelFunc().update_channel_by_channel(channel.id, "is_deleted", True)
                    await channel.delete()
            except AttributeError:
                await ChannelFunc().update_channel_by_channel(channel.id, "is_deleted", True)

    @commands.Cog.listener()
    async def on_ready(self):
        await create_tables()
        if self.persistent_views_added:
            return

        view_server = RoomsView(self.bot)
        self.bot.add_view(view_server, message_id=self.config['rooms']['message_id'])
        self.persistent_views_added = True
        self.check_current_voice.start()


async def setup(bot: commands.Bot):
    await bot.add_cog(Rooms(bot))
