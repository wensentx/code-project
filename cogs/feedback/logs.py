import datetime
import json
import os
from email.policy import default

import aiofiles
import discord
import pytz
from discord.ext import commands
from dotenv import load_dotenv
from cogs.feedback.database.functions import *
from cogs.feedback.database.connection import create_tables

load_dotenv()
DISCORD_GUILD = int(os.getenv('DISCORD_GUILD'))


class Joiner(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.config = None
        self.invites = {}
        self.bot.loop.create_task(self.load_config())

    async def load_config(self):
        async with aiofiles.open('cogs/feedback/config.json', 'r', encoding='utf-8') as f:
            content = await f.read()
            self.config = json.loads(content)

    async def save_config(self):
        async with aiofiles.open('cogs/feedback/config.json', 'w', encoding='utf-8') as f:
            await f.write(json.dumps(self.config, indent=4, ensure_ascii=False))

    @commands.Cog.listener()
    async def on_ready(self):
        await create_tables()
        guild_invites = await self.bot.get_guild(DISCORD_GUILD).invites()
        invites = {}
        for invite in guild_invites:
            invites[invite.code] = {
                'uses': invite.uses,
                'inviter': invite.inviter.id if invite.inviter else None
            }
        self.invites = invites

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        self.invites[invite.code] = {
            'uses': invite.uses,
            'inviter': invite.inviter.id if invite.inviter else None
        }

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        del self.invites[invite.code]

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.guild != self.bot.get_guild(DISCORD_GUILD):
            return

        staff_channel = before.guild.get_channel(self.config['logs']['LOGS_STAFF_CHANNEL_ID'])
        if after.guild.premium_subscriber_role in before.roles and \
                after.guild.premium_subscriber_role not in after.roles:
            await staff_channel.send(
                f'Пользователь {after.mention}. Перестал бустить сервер.'
            )

        if after.guild.premium_subscriber_role in after.roles and \
                after.guild.premium_subscriber_role not in before.roles:
            await staff_channel.send(
                f'Пользователь {after.mention}. Забустил сервер.'
            )

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild != self.bot.get_guild(DISCORD_GUILD):
            return

        if member.bot is True:
            await member.kick(reason='Боты не допускаются на сервере')

        user = await UserDB().get_or_create_user(member.id)
        roles = []
        if user.is_dumb:
            newbie_role = member.guild.get_role(self.config['skills']['NEWBIE_ROLE_ID'])
            roles.append(newbie_role)

        default_role = member.guild.get_role(self.config['skills']['DEFAULT_ROLE_ID'])
        await member.add_roles(default_role, *roles)

        guild_invites = await member.guild.invites()
        for invite in guild_invites:
            if invite.uses > self.invites[invite.code]['uses']:
                self.invites[invite.code]['uses'] = invite.uses
                self.invites[invite.code]['inviter'] = invite.inviter.id if invite.inviter else None

            channel = member.guild.get_channel(self.config['logs']['LOGS_MEMBER_CHANNEL_ID'])
            member_create = (
                f'{discord.utils.format_dt(member.created_at, "F")} '
                f'{discord.utils.format_dt(member.created_at, "R")}'
            )
            embed = discord.Embed(
                color=0x2F3136,
                description=(
                    f"{member.mention} | {member} ({member.id})\n\n"
                    f"**Дата создания аккаунта:**\n{member_create}\n"
                ),
                timestamp=datetime.datetime.now()
            ).set_author(
                name="Пользователь зашел на сервер",
                icon_url="https://i.imgur.com/PTc6d3H.png"
            ).set_thumbnail(
                url=member.display_avatar
            ).set_footer(
                text=member, icon_url=member.display_avatar
            )
            embed.add_field(
                name="Приглашен",
                value=f"・{invite.inviter.mention}\n・`{invite.inviter}`\n",
                inline=True
            )

            embed.add_field(
                name="Использован код",
                value=f"・[{invite.code}](https://discord.gg/{invite.code})\n・`{invite.uses}` использований\n",
                inline=True
            )
            embed.set_footer(text=f"Теперь на сервере {len(member.guild.members)} участников")
            await channel.send(embed=embed)
            break

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        if member.guild != self.bot.get_guild(DISCORD_GUILD):
            return
        if member.bot is True:
            return

        role_list = [r.mention for r in member.roles if r != member.guild.default_role]
        embed = discord.Embed(
            color=0x2F3136,
            timestamp=datetime.datetime.now(),
            description=(
                f"{member.mention} | {member} ({member.id})\n\nРоли на сервере: {", ".join(role_list)}"
            )
        ).set_author(
            name='Пользователь вышел с сервера',
            icon_url='https://i.imgur.com/wSwpqAS.png'
        ).set_thumbnail(
            url=member.display_avatar
        ).set_footer(
            text=f"Теперь на сервере {len(member.guild.members)} участников"
        )
        await self.bot.get_channel(self.config['logs']['LOGS_MEMBER_CHANNEL_ID']).send(embed=embed)

    @commands.Cog.listener()
    async def on_voice_state_update(
            self,
            member: discord.Member,
            before: discord.VoiceState,
            after: discord.VoiceState
    ):
        if member.guild != self.bot.get_guild(DISCORD_GUILD) or before.self_deaf != after.self_deaf:
            return

        if before.channel is None:
            await self.send_voice_update(
                member,
                after.channel,
                'Участник зашел в голосовой канал',
                'https://i.imgur.com/AoaFhiq.png',
                0x51b581
            )
        elif after.channel is None:
            await self.send_voice_update(
                member,
                before.channel,
                'Участник вышел из голосового канала',
                'https://i.imgur.com/Lh8mqxa.png',
                0xed4245
            )
        elif before.channel != after.channel:
            await self.send_voice_update(
                member,
                after.channel,
                'Участник сменил голосовой канал',
                'https://i.imgur.com/Xksydy0.png',
                0xb9bbbe,
                before.channel
            )

    async def send_voice_update(self, member, channel, title, icon_url, color, old_channel=None):
        embed = discord.Embed(
            color=color
        ).set_thumbnail(
            url=member.display_avatar.url
        ).set_footer(
            text=datetime.datetime.now().astimezone(tz=pytz.timezone('Europe/Moscow')).strftime('%Y-%m-%d %H:%M')
        ).set_author(
            name=title,
            icon_url=icon_url
        ).add_field(
            name='Участник',
            value=f'{member.mention}\n({member.id})',
            inline=True
        ).add_field(
            name='_ _',
            value=f'_ _',
            inline=True
        ).add_field(
            name='Канал',
            value=f':microphone2: {channel}\n({channel.id})',
            inline=True
        )
        if old_channel:
            embed.add_field(
                name='Старый канал',
                value=f':microphone2: {old_channel}\n({old_channel.id})',
                inline=True
            )
        await self.bot.get_channel(self.config['logs']['LOGS_VOICE_CHANNEL_ID']).send(embed=embed)


async def setup(bot):
    await bot.add_cog(Joiner(bot))
