import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from cogs.room.database.models import Base

load_dotenv()

ROOMS_USER = os.getenv('ROOMS_USER')
ROOMS_PASSWORD = os.getenv('ROOMS_PASSWORD')
ROOMS_DB = os.getenv('ROOMS_DB')

DATABASE_URL = f"postgresql+asyncpg://{ROOMS_DB}:{ROOMS_PASSWORD}@postgres:5432/{ROOMS_DB}"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession, future=True)


@asynccontextmanager
async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        return
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
