import asyncio

from pyrogram.client import Client

from bot import API_HASH, API_ID, BOT_TOKEN, logger
from bot.database import start_db

app = Client(
    "WoS-Bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="bot/modules"),
)

if __name__ == "__main__":

    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_db())

    logger.info("Starting the Pyrogram Client now...")

    app.run()
