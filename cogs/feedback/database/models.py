from sqlalchemy import Column, Integer, String, Boolean, BigInteger
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement="auto", index=True)
    user_id = Column(BigInteger, nullable=False)
    is_dumb = Column(Boolean, nullable=False, default=False)


    def __repr__(self):
        return (
            f"<User(id={self.id}, user_id={self.user_id}, is_dumb={self.is_dumb})>"
        )
