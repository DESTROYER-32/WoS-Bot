from pyrogram import filters
from pyrogram.client import Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot import logger


@Client.on_message(filters.command("help"))
async def help_command(_: Client, message: Message):
    """Handle the /help command, accessible to all users, with a GitHub button."""
    help_text = (
        "📚 **Gift Code Bot Help**\n\n"
        "Available commands:\n"
        "- /start: Start the bot and get a welcome message.\n"
        "- /help: Show this help message.\n"
        "- /redeem CODE: Redeem a gift code for all players (admin only).\n"
        "- /add ID RANK: Add a new player with ID and rank (1-5) (admin only).\n"
        "- /remove ID: Remove a player by ID (admin only).\n"
        "- /list: List all players with pagination (admin only).\n"
        "- /setrank ID RANK: Update a player's rank (1-5) (admin only).\n\n"
        "For more details, visit the GitHub repository:"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("GitHub Repository", url="https://github.com/DESTROYER-32/WoS-Bot")]
    ])
    await message.reply(help_text, reply_markup=keyboard)


@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Handle the /start command, accessible to all users."""
    await message.reply("Welcome to the Gift Code Bot! 🎉 Use /help to see available commands.")
