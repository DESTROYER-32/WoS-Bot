import time
from typing import List, Optional, Tuple

from sqlalchemy import Column, Integer, String, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from bot import SCHEMA, logger
from bot.database import BASE

engine = create_async_engine(SCHEMA)
async_session = async_sessionmaker(bind=engine, autoflush=True, expire_on_commit=False)


class GiftCode(BASE):
    __tablename__ = "gift_code"

    code = Column(String, primary_key=True, nullable=False)
    pub_date = Column(String, nullable=False)
    status = Column(String, nullable=False)
    last_checked = Column(Integer, nullable=False)
    created_at = Column(Integer, nullable=False)

    def __init__(self, code: str, pub_date: str, status: str = "active", last_checked: int = None, created_at: int = None):
        self.code = code
        self.pub_date = pub_date
        self.status = status
        self.last_checked = last_checked or int(time.time())
        self.created_at = created_at or int(time.time())

    def __repr__(self):
        return f"<GiftCode code={self.code}, status={self.status}, pub_date={self.pub_date}>"
    
async def insert_gift_code(code: str, pub_date: str) -> bool:
    """Insert a new gift code into the database."""
    async with async_session() as session:
        try:
            async with session.begin():
                existing_code = await session.get(GiftCode, code)
                if existing_code:
                    return False
                new_code = GiftCode(code=code, pub_date=pub_date)
                session.add(new_code)
            logger.info(f"Inserted gift code: {code}")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to insert gift code {code}: {str(e)}")
            return False


async def update_gift_code_status(code: str, status: str) -> bool:
    """Update the status of a gift code."""
    async with async_session() as session:
        try:
            async with session.begin():
                result = await session.execute(
                    update(GiftCode).where(GiftCode.code == code).values(status=status, last_checked=int(time.time()))
                )
                if result.rowcount > 0:
                    logger.info(f"Updated gift code {code} to status: {status}")
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Failed to update gift code {code}: {str(e)}")
            return False


async def update_gift_code_last_checked(code: str) -> bool:
    """Update the last_checked timestamp for a gift code."""
    async with async_session() as session:
        try:
            async with session.begin():
                result = await session.execute(
                    update(GiftCode).where(GiftCode.code == code).values(last_checked=int(time.time()))
                )
                if result.rowcount > 0:
                    logger.info(f"Updated last_checked for gift code: {code}")
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Failed to update last_checked for gift code {code}: {str(e)}")
            return False


async def get_active_gift_codes() -> List[Tuple[str, str]]:
    """Retrieve all active gift codes."""
    async with async_session() as session:
        try:
            result = await session.execute(select(GiftCode.code, GiftCode.pub_date).where(GiftCode.status == "active"))
            codes = result.all()
            logger.info(f"Retrieved {len(codes)} active gift codes")
            return [(code, pub_date) for code, pub_date in codes]
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve active gift codes: {str(e)}")
            return []


async def get_all_gift_codes() -> List[str]:
    """Retrieve all gift codes in the database."""
    async with async_session() as session:
        try:
            result = await session.execute(select(GiftCode.code))
            codes = result.scalars().all()
            logger.info(f"Retrieved {len(codes)} gift codes")
            return codes
        except SQLAlchemyError as e:
            logger.error(f"Failed to retrieve all gift codes: {str(e)}")
            return []


async def delete_gift_code(code: str) -> bool:
    """Delete a gift code from the database."""
    async with async_session() as session:
        try:
            async with session.begin():
                gift_code = await session.get(GiftCode, code)
                if gift_code:
                    await session.delete(gift_code)
                    logger.info(f"Deleted gift code: {code}")
                    return True
                return False
        except SQLAlchemyError as e:
            logger.error(f"Failed to delete gift code {code}: {str(e)}")
            return False