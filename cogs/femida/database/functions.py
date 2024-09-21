from sqlalchemy.future import select

from cogs.femida.database.connection import get_session
from cogs.femida.database.models import Log


class FemidaDB:

    async def add_log(
            self, moderator_id: int, user_id: int, action: str, reason: str,
            start_time: str, finish_time: str
    ):
        """
        Add log to the database

        :param moderator_id:
        :param user_id:
        :param action:
        :param reason:
        :param start_time:
        :param finish_time:
        :return:
        """
        async with get_session() as session:
            async with session.begin():
                session.add(Log(
                    moderator_id=moderator_id,
                    user_id=user_id,
                    action=action,
                    reason=reason,
                    start_time=start_time,
                    finish_time=finish_time
                ))
                await session.commit()

    async def get_logs_by_user_id(self, user_id: int):
        """
        Get logs by user id
        :param user_id:
        :return:
        """
        async with get_session() as session:
            async with session.begin():
                result = await session.execute(select(Log).filter_by(user_id=user_id))
                logs = result.scalars().all()
                return logs



