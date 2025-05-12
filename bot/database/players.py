from typing import List, Optional, Tuple

from sqlalchemy import Column, Integer, String, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from bot import SCHEMA, logger

BASE = declarative_base()

engine = create_async_engine(SCHEMA)
async_session = async_sessionmaker(bind=engine, autoflush=True, expire_on_commit=False)


class Player(BASE):
    __tablename__ = "players"

    player_id = Column(String, primary_key=True, nullable=False)
    name = Column(String, nullable=True)
    rank = Column(Integer, nullable=True)

    def __init__(self, player_id: str, name: str = None, rank: int = None):
        self.player_id = player_id
        self.name = name
        self.rank = rank

    def __repr__(self):
        return f"<Player player_id={self.player_id}, name={self.name}, rank={self.rank}>"


async def add_player(player_id: str, name: str, rank: int) -> bool:
    """Add a new player to the database."""
    try:
        async with async_session() as session:
            existing_player = await session.execute(
                select(Player).filter_by(player_id=player_id)
            )
            if existing_player.scalar_one_or_none():
                return False

            new_player = Player(player_id=player_id, name=name, rank=rank)
            session.add(new_player)
            await session.commit()
            return True
    except SQLAlchemyError as e:
        logger.error(f"Failed to add player {player_id}: {str(e)}")
        await session.rollback()
        return False


async def remove_player(player_id: str) -> Optional[str]:
    """Remove a player from the database and return their name if found."""
    try:
        async with async_session() as session:
            player = await session.execute(
                select(Player).filter_by(player_id=player_id)
            )
            player = player.scalar_one_or_none()
            if not player:
                return None

            name = player.name
            await session.delete(player)
            await session.commit()
            return name
    except SQLAlchemyError as e:
        logger.error(f"Failed to remove player {player_id}: {str(e)}")
        await session.rollback()
        return None


async def list_players() -> List[Tuple[str, str, int]]:
    """Retrieve all players from the database, returning a list of (player_id, name, rank)."""
    try:
        async with async_session() as session:
            result = await session.execute(
                select(Player.player_id, Player.name, Player.rank)
            )
            return result.all()
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving players: {str(e)}")
        return []


async def set_rank(player_id: str, rank: int) -> Optional[str]:
    """Update a player's rank and return their name if found."""
    try:
        async with async_session() as session:
            player = await session.execute(
                select(Player).filter_by(player_id=player_id)
            )
            player = player.scalar_one_or_none()
            if not player:
                return None

            name = player.name
            player.rank = rank
            await session.commit()
            return name
    except SQLAlchemyError as e:
        logger.error(f"Failed to set rank for {player_id}: {str(e)}")
        await session.rollback()
        return None


async def edit_local_name(player_id: str, new_name: str) -> bool:
    """Update a player's name in the database."""
    try:
        async with async_session() as session:
            player = await session.execute(
                select(Player).filter_by(player_id=player_id)
            )
            player = player.scalar_one_or_none()

            if player:
                player.name = new_name
            else:
                player = Player(player_id=player_id, name=new_name)
                session.add(player)

            await session.commit()
            return True
    except SQLAlchemyError as e:
        logger.error(f"Failed to update name for {player_id}: {str(e)}")
        await session.rollback()
        return False


async def get_local_name(player_id: str) -> Optional[str]:
    """Retrieve a player's name from the database."""
    try:
        async with async_session() as session:
            player = await session.execute(
                select(Player).filter_by(player_id=player_id)
            )
            player = player.scalar_one_or_none()
            return player.name if player else None
    except SQLAlchemyError as e:
        logger.error(f"Error retrieving name for {player_id}: {str(e)}")
        return None