import datetime

from sqlalchemy import select, update

from cogs.room.database.connection import get_session
from cogs.room.database.models import Channel, Settings, Log


class ChannelFunc:

    async def add_channel(self, user_id: int, channel_id: int):
        async with get_session() as session:
            async with session.begin():
                query = Channel(
                    user_id=user_id,
                    channel_id=channel_id
                )
                session.add(query)

    async def update_channel_by_user(self, user_id: int, column: str, value):
        async with get_session() as session:
            async with session.begin():
                query = update(Channel).filter_by(user_id=user_id, is_deleted=False).values({column: value})
                await session.execute(query)

    async def update_channel_by_channel(self, channel_id: int, column: str, value):
        async with get_session() as session:
            async with session.begin():
                query = update(Channel).filter_by(channel_id=channel_id, is_deleted=False).values({column: value})
                await session.execute(query)

    async def get_channel_by_user(self, user_id: int):
        async with get_session() as session:
            async with session.begin():
                query = select(Channel).filter_by(user_id=user_id, is_deleted=False)
                result = await session.execute(query)
                return result.scalar_one_or_none()

    async def get_channel_by_channel(self, channel_id: int):
        async with get_session() as session:
            async with session.begin():
                query = select(Channel).filter_by(channel_id=channel_id, is_deleted=False)
                result = await session.execute(query)
                return result.scalar_one_or_none()

    async def get_channel_by_user_and_channel(self, user_id: int, channel_id: int):
        async with get_session() as session:
            async with session.begin():
                query = select(Channel).filter_by(user_id=user_id, channel_id=channel_id, is_deleted=False)
                result = await session.execute(query)
                return result.scalar_one_or_none()

    async def get_channels(self) -> list[Channel]:
        async with get_session() as session:
            async with session.begin():
                query = select(Channel).filter_by(is_deleted=False)
                result = await session.execute(query)
                return result.scalars().all()


class SettingsFunc:

    async def add_settings(self, user_id: int, title: str, limit: int):
        async with get_session() as session:
            async with session.begin():
                query = Settings(
                    user_id=user_id,
                    title=title,
                    limit=limit
                )
                session.add(query)

    async def get_settings_by_user(self, user_id: int):
        async with get_session() as session:
            async with session.begin():
                query = select(Settings).filter_by(user_id=user_id)
                result = await session.execute(query)
                return result.scalar_one_or_none()

    async def update_settings_by_user(self, user_id: int, column: str, value):
        async with get_session() as session:
            async with session.begin():
                query = update(Settings).filter_by(user_id=user_id).values({column: value})
                await session.execute(query)


class LogFunc:

    async def add_log(self, user_id: int, action: str):
        async with get_session() as session:
            async with session.begin():
                query = Log(
                    user_id=user_id,
                    action=action,
                    created_at=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                )
                session.add(query)

    async def get_log_by_user(self, user_id: int, action: str):
        async with get_session() as session:
            async with session.begin():
                query = select(Log).filter_by(user_id=user_id, action=action).order_by(Log.created_at.desc())
                result = await session.execute(query)
                return result.scalars().first()
