import pkgutil

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from bot import SCHEMA, logger

BASE = declarative_base()


async def start_db() -> None:
    engine = create_async_engine(SCHEMA)
    logger.info("[ORM] Connecting to database...")
    async_session = async_sessionmaker(
        bind=engine, autoflush=True, expire_on_commit=False
    )

    async with async_session() as session:
        async with session.begin():
            logger.info("[ORM] Creating tables inside database now...")
            async with engine.begin() as conn:
                for _, name, _ in pkgutil.iter_modules(["bot/database"]):
                    __import__(f"bot.database.{name}", fromlist=[""])
                await conn.run_sync(BASE.metadata.create_all)
            logger.info("[ORM] Connection successful, session started.")
