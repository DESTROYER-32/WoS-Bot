import asyncio

from pyrogram.client import Client

from bot import API_HASH, API_ID, BOT_TOKEN, logger
from bot.database import start_db
from bot.modules.gift_code import periodic_gift_code_check

app = Client(
    "WoS-Bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="bot/modules"),
)

async def start_client():
    """Start the Pyrogram client and schedule the periodic gift code check."""
    await app.start()
    logger.info("Pyrogram Client is ready. Starting periodic gift code check...")
    task = asyncio.create_task(periodic_gift_code_check(app))
    logger.info("Periodic gift code check scheduled.")
    return task

async def stop_client(task: asyncio.Task):
    """Stop the Pyrogram client and cancel the periodic task."""
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Periodic gift code check task canceled.")
    await app.stop()
    logger.info("Pyrogram Client stopped.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    task = None
    try:
        loop.run_until_complete(start_db())
        task = loop.run_until_complete(start_client())
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt, shutting down...")
        if task:
            loop.run_until_complete(stop_client(task))
    finally:
        loop.close()
        logger.info("Event loop closed.")