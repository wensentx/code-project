import json

import aiofiles
import discord
from discord import app_commands
from discord.ext import commands


class Forum(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = None
        self.bot.loop.create_task(self.load_config())

    async def load_config(self):
        async with aiofiles.open('cogs/forum/config.json', 'r', encoding='utf-8') as f:
            content = await f.read()
            self.config = json.loads(content)

    async def save_config(self):
        async with aiofiles.open('cogs/forum/config.json', 'w', encoding='utf-8') as f:
            await f.write(json.dumps(self.config, indent=4, ensure_ascii=False))

    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        await self.load_config()
        if thread.parent.id == self.config['forum']['PARENT_ID']:
            help_tag = thread.parent.get_tag(self.config['forum']['HELP_TAG_ID'])
            if help_tag is None:
                help_tag = await thread.parent.create_tag(
                    name="Нужна помощь!",
                    emoji="❓",
                    moderated=True,
                    reason="Отсутствует тег помощи"
                )
                self.config['forum']['HELP_TAG_ID'] = help_tag.id
                await self.save_config()

            await thread.edit(applied_tags=thread.applied_tags + [help_tag])
            embed = discord.Embed(
                title='— • Форум помощи',
                colour=0x2F3136,
                description=(
                    'Не держите тикет **открытым**, если ваш первоначальный вопрос **решен**. '
                    'Если вы хотите, чтобы тикет был **закрыт**, нажмите на **кнопку** ниже.'
                )
            ).set_thumbnail(url=thread.owner.display_avatar.url)
            view = discord.ui.View().add_item(
                discord.ui.Button(
                    label='Решение подтверждено',
                    style=discord.ButtonStyle.grey,
                    custom_id='solved'
                )
            )
            message = await thread.send(embed=embed, view=view)
            await message.pin()

    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        await self.load_config()
        helper_role = interaction.guild.get_role(self.config['forum']['HELPER_ROLE_ID'])
        if "custom_id" in interaction.data and interaction.data["custom_id"] == "solved":

            if (
                    not isinstance(interaction.channel, discord.Thread)
                    or interaction.channel.parent.id != self.config['forum']['PARENT_ID']
            ):
                return await interaction.response.send_message(
                    embed=discord.Embed(
                        title="— • Форум помощи",
                        description=(
                            f"{interaction.user.mention}, Эта кнопка может быть использована только в тикетах."
                        ),
                        color=0x2F3136
                    ).set_thumbnail(url=interaction.user.display_avatar.url),
                    ephemeral=True
                )

            if helper_role not in interaction.user.roles and interaction.user != interaction.channel.owner:
                embed = discord.Embed(
                    title="— • Форум помощи",
                    description=(
                        f"{interaction.user.mention}, Только владелец или пользователь "
                        f"с ролью {helper_role.mention}."
                    ),
                    color=0x2F3136
                ).set_thumbnail(url=interaction.user.display_avatar.url)
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            solved_tag = interaction.channel.parent.get_tag(self.config['forum']['SOLVED_TAG_ID'])
            if solved_tag is None:
                solved_tag = await interaction.channel.parent.create_tag(
                    name="Решение подтверждено",
                    reason="Отсутствует тег решения"
                )
                self.config['forum']['SOLVED_TAG_ID'] = solved_tag.id
                await self.save_config()

            if solved_tag in interaction.channel.applied_tags:
                embed = discord.Embed(
                    title="— • Форум помощи",
                    description=(
                        f"{interaction.user.mention}, Данный тикет уже имеет статус **Решение подтверждено**."
                    ),
                    color=0x2F3136
                ).set_thumbnail(url=interaction.user.display_avatar.url)
                return await interaction.response.send_message(embed=embed, ephemeral=True)

            try:
                embed = discord.Embed(
                    title="— • Форум помощи",
                    description=(
                        f"{interaction.user.mention}, Сообщение было закрыто и ему присвоен тег "
                        f"**Решение подтверждено**."
                    ),
                    color=0x2F3136
                ).set_thumbnail(url=interaction.user.display_avatar.url)
                await interaction.response.send_message(embed=embed, ephemeral=True)
            except:
                pass

            help_tag = interaction.channel.parent.get_tag(self.config['forum']['HELP_TAG_ID'])
            applied_tags = interaction.channel.applied_tags

            if help_tag in applied_tags:
                applied_tags.remove(help_tag)

            applied_tags.append(solved_tag)

            await interaction.channel.edit(
                archived=True,
                locked=True,
                applied_tags=applied_tags
            )

    @app_commands.command(name="solved", description="Закрыть тикет")
    async def solved(self, interaction):
        await self.load_config()
        if (
                not isinstance(interaction.channel, discord.Thread)
                or interaction.channel.parent.id != self.config['forum']['PARENT_ID']
        ):
            embed = discord.Embed(
                title="— • Форум помощи",
                description=(
                    f"{interaction.user.mention}, Эта команда может быть использована только в тикетах."
                )
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        helper_role = interaction.guild.get_role(self.config['forum']['HELPER_ROLE_ID'])
        if helper_role not in interaction.user.roles and interaction.user != interaction.channel.owner:
            embed = discord.Embed(
                title="— • Форум помощи",
                description=(
                    f"{interaction.user.mention}, закрыть тикет может только владелец или пользователь "
                    f"с ролью {helper_role.mention}."
                )
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        solved_tag = interaction.channel.parent.get_tag(self.config['forum']['SOLVED_TAG_ID'])
        if solved_tag is None:
            solved_tag = await interaction.channel.parent.create_tag(
                name="Решение подтверждено",
                reason="Отсутствует тег решения"
            )
            self.config['forum']['SOLVED_TAG_ID'] = solved_tag.id
            await self.save_config()


        if solved_tag in interaction.channel.applied_tags:
            embed = discord.Embed(
                title="— • Форум помощи",
                description=(
                    f"{interaction.user.mention}, Данный тикет уже имеет статус **Решение подтверждено**"
                ),
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        try:
            embed = discord.Embed(
                title="— • Форум помощи",
                description=(
                    f"{interaction.user.mention}, Сообщение было закрыто и ему присвоен тег "
                    f"**Решение подтверждено**."
                ),
                color=0x2F3136
            ).set_thumbnail(url=interaction.user.display_avatar.url)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            pass

        help_tag = interaction.channel.parent.get_tag(self.config['forum']['HELP_TAG_ID'])
        applied_tags = interaction.channel.applied_tags

        if help_tag in applied_tags:
            applied_tags.remove(help_tag)

        applied_tags.append(solved_tag)

        await interaction.channel.edit(
            archived=True,
            locked=True,
            applied_tags=applied_tags
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(Forum(bot))
