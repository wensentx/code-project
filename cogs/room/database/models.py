from sqlalchemy import Column, BIGINT, VARCHAR, INT, BOOLEAN
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Channel(Base):
    __tablename__ = 'channels'

    id = Column(BIGINT, primary_key=True, autoincrement="auto", index=True)
    user_id = Column(BIGINT, nullable=False, index=True)
    channel_id = Column(BIGINT, nullable=False, index=True, unique=True)
    is_deleted = Column(BOOLEAN, nullable=False, default=0)

    def __repr__(self):
        return (
            f"<Channel(id={self.id}, user_id={self.user_id}, channel_id={self.channel_id})>"
        )


class Settings(Base):
    __tablename__ = 'settings'

    id = Column(INT, primary_key=True, autoincrement="auto", index=True)
    user_id = Column(BIGINT, nullable=False, index=True, unique=True)
    title = Column(VARCHAR, nullable=True)
    limit = Column(INT, nullable=True, default=0)

    def __repr__(self):
        return (
            f"<Settings(id={self.id}, user_id={self.user_id}, title={self.title}, limit={self.limit})>"
        )


class Log(Base):
    __tablename__ = 'logs'

    id = Column(INT, primary_key=True, autoincrement="auto", index=True)
    user_id = Column(BIGINT, nullable=False, index=True)
    action = Column(VARCHAR, nullable=False)
    created_at = Column(VARCHAR, nullable=False)

    def __repr__(self):
        return (
            f"<Log(id={self.id}, user_id={self.user_id}, action={self.action}, created_at={self.created_at})>"
        )



