from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.util.config import config
from sqlalchemy.future import select
from app.db.models import Base


DATABASE_URL = config.DB_URL
try:
    async_session_maker = async_sessionmaker(
        bind=create_async_engine(DATABASE_URL, echo=True),
        expire_on_commit=False,
        class_=AsyncSession
    )
except OperationalError as e:
    print(f'Database connection error: {e}\nDATABASE URL: {DATABASE_URL}')
    exit(1)


@asynccontextmanager
async def connect_database() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


async def check_database():
    async with async_session_maker() as session:
        try:
            tables = list(Base.metadata.tables.keys())
            await session.execute(select(1))
            return {'status': 'ok', 'tables': tables}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
