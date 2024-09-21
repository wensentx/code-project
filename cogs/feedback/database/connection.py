import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker


from cogs.feedback.database.models import Base

load_dotenv()

USERS_USER = os.getenv('USERS_USER')
USERS_PASSWORD = os.getenv('USERS_PASSWORD')
USERS_DB = os.getenv('USERS_DB')

DATABASE_URL = f"postgresql+asyncpg://{USERS_USER}:{USERS_PASSWORD}@localhost:5432/{USERS_DB}"

engine = create_async_engine(DATABASE_URL, echo=True)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession, future=True)


@asynccontextmanager
async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        pass
        # await conn.run_sync(Base.metadata.drop_all)
        # await conn.run_sync(Base.metadata.create_all)
