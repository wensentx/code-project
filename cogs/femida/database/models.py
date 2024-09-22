from sqlalchemy import Column, Integer, String, Boolean, BigInteger
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass


class Log(Base):
    __tablename__ = 'logs'

    id = Column(Integer, primary_key=True, autoincrement="auto", index=True)
    moderator_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    action = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    finish_time = Column(String, nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)

    def __repr__(self):
        return (
            f"<Log(id={self.id}, moderator_id={self.moderator_id}, user_id={self.user_id}, action={self.action}, "
            f"reason={self.reason}, start_time={self.start_time}, finish_time={self.finish_time}, "
            f"is_deleted={self.is_deleted})>"
        )
