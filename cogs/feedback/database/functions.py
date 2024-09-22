from sqlalchemy.sql import select, update

from cogs.feedback.database.connection import get_session
from cogs.feedback.database.models import User


class UserDB:

    async def get_or_create_user(self, user_id: int) -> User:
        """
        Get or create user in database
        :param user_id:
        :return:
        """
        async with get_session() as session:
            async with session.begin():
                result = await session.execute(select(User).filter(User.user_id == user_id))
                user = result.scalars().first()
                if user:
                    return user
                user = User(user_id=user_id)
                session.add(user)
                return user


    async def get_users(self):
        """
        Get all users from database
        :return:
        """
        async with get_session() as session:
            async with session.begin():
                result = await session.execute(select(User))
                return result.scalars().all()

    async def update_user(self, user_id: int, is_dumb: bool):
        """
        Update user in database
        :param user_id:
        :param is_dumb:
        :return:
        """
        async with get_session() as session:
            async with session.begin():
                await session.execute(
                    update(User).filter(User.user_id == user_id).values(is_dumb=is_dumb)
                )
