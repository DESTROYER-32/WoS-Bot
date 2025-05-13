from pyrogram import Client, filters
from pyrogram.types import Message

from bot import ADMINS, logger
from bot.modules.gift_code import update_gift_codes


@Client.on_message(filters.command("checkgiftcodes") & filters.private)
async def check_gift_codes_command(client: Client, message: Message):
    """Handle the /checkgiftcodes command to manually trigger gift code checking (admin only)."""
    if message.from_user.id not in ADMINS:
        await message.reply("🚫 You are not authorized to use this command.")
        logger.warning(f"Unauthorized user {message.from_user.id} attempted to use /checkgiftcodes")
        return

    try:
        await message.reply("🔄 Starting gift code check...")
        logger.info(f"Manual gift code check triggered by admin {message.from_user.id}")
        await update_gift_codes(client)
        await message.reply("✅ Gift code check completed successfully.")
        logger.info("Manual gift code check completed")
    except Exception as e:
        await message.reply(f"❌ Failed to check gift codes: {str(e)}")
        logger.error(f"Error during manual gift code check: {str(e)}")
