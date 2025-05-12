import time

from pyrogram import filters
from pyrogram.client import Client
from pyrogram.types import Message

from bot import ADMINS, api, logger
from bot.database.players import list_players
from bot.helpers.api import API
from bot.helpers.misc import recursive_redeem


@Client.on_message(filters.command("redeem") & filters.private)
async def redeem_code(client: Client, message: Message):
    """Handle the /redeem command to redeem a gift code for all players."""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ You are not authorized to use this command.")
        return

    if len(message.command) < 2:
        await message.reply("❌ Usage: /redeem CODE")
        return

    code = message.command[1]
    if api.inUse:
        await message.reply("❌ Error: The API is currently in use by another command.")
        return
    if api.lastUsed + 60 > time.time():
        await message.reply("❌ Error: Waiting for API cooldown.")
        return

    await api.init_session()
    api.inUse = True

    try:
        playersObj = await list_players()
        players = [(player[0], 0) for player in playersObj]
    except Exception as e:
        api.inUse = False
        await message.reply(f"❌ Database error: {str(e)}")
        return

    await recursive_redeem(message, code, players)

    api.lastUsed = time.time()
    api.inUse = False
    await api.session.close()