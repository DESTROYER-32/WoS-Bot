from uuid import uuid4

from pyrogram import filters
from pyrogram.client import Client
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from bot import ADMINS, api, logger
from bot.database.players import (add_player, list_players, remove_player,
                                  set_rank)
from bot.helpers.api import API
from bot.helpers.misc import is_valid_id, sanitize_username

pagination_data = {}


@Client.on_message(filters.command("add") & filters.private)
async def add_user(client: Client, message: Message):
    """Handle the /add command to add a new player to the database."""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ You are not authorized to use this command.")
        return

    if len(message.command) < 3:
        await message.reply("❌ Usage: /add ID RANK (1-5)")
        return

    player_id, rank = message.command[1], message.command[2]
    if not is_valid_id(player_id):
        await message.reply("❌ Invalid user ID.")
        return

    try:
        rank = int(rank)
        if rank not in range(1, 6):
            raise ValueError
    except ValueError:
        await message.reply("❌ Rank must be a number between 1 and 5.")
        return

    await api.init_session()
    err, _, _, user_data = await api.login_user(player_id)

    if not err:
        name = sanitize_username(user_data["data"]["nickname"])
        success = await add_player(player_id, name, rank)
        if success:
            await message.reply(f"✅ Added user {name} to the database with rank R{rank}.")
        else:
            await message.reply("❌ User ID already exists in the database.")
    else:
        await message.reply("❌ Error: API returned invalid data.")

    await api.session.close()


@Client.on_message(filters.command("remove") & filters.private)
async def remove_user(client: Client, message: Message):
    """Handle the /remove command to delete a player from the database."""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ You are not authorized to use this command.")
        return

    if len(message.command) < 2:
        await message.reply("❌ Usage: /remove ID")
        return

    player_id = message.command[1]
    name = await remove_player(player_id)

    if name:
        await message.reply(f"✅ Removed user {name} from the database.")
    else:
        await message.reply("❌ User ID not found in the database.")


@Client.on_message(filters.command("list") & filters.private)
async def list_users(client: Client, message: Message):
    """Handle the /list command to display all players with pagination."""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ You are not authorized to use this command.")
        return

    players = await list_players()
    if not players:
        await message.reply("📋 No players in the database.")
        return

    rank_lists = {1: [], 2: [], 3: [], 4: [], 5: []}
    for player_id, name, rank in players:
        rank_lists[rank].append((name, player_id))

    sorted_ranks = [rank_lists[rank] for rank in range(5, 0, -1)]
    ranks = range(1, 6)
    rank_lines = [[] for _ in range(5)]

    for index, rank in enumerate(sorted_ranks):
        rank_lines[index].append(f"**R{ranks[-(index + 1)]}**")
        rank_lines[index].append("")
        for name, player_id in rank:
            rank_lines[index].append(f"**{name}** (`{player_id}`)")
        rank_lines[index].extend(["" for _ in range(10 - (len(rank_lines[index]) % 10))])

    lines = sum(rank_lines, [])
    embeds_content = ["\n".join(lines[i:i + 10]) for i in range(0, len(lines), 10)]

    if not embeds_content:
        await message.reply("📋 No players to display.")
        return

    session_id = str(uuid4())
    pagination_data[session_id] = {
        "pages": embeds_content,
        "current_page": 0,
        "total_players": len(players),
        "user_id": message.from_user.id
    }

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Previous", callback_data=f"prev_{session_id}"),
            InlineKeyboardButton("Next", callback_data=f"next_{session_id}"),
            InlineKeyboardButton("Close", callback_data=f"close_{session_id}")
        ]
    ])

    content = embeds_content[0]
    await message.reply(
        f"📋 **Players List**\n**Total players:** {len(players)}\n**Page 1/{len(embeds_content)}**\n\n{content}",
        reply_markup=keyboard
    )


@Client.on_callback_query()
async def handle_pagination(client: Client, callback_query):
    """Handle pagination button clicks."""
    data = callback_query.data
    session_id = data.split("_")[1]
    action = data.split("_")[0]

    if session_id not in pagination_data:
        await callback_query.answer("This session has expired.")
        return

    session = pagination_data[session_id]
    if callback_query.from_user.id != session["user_id"]:
        await callback_query.answer("You are not authorized to use these buttons.")
        return

    if action == "close":
        await callback_query.message.delete()
        del pagination_data[session_id]
        return

    current_page = session["current_page"]
    total_pages = len(session["pages"])

    if action == "next" and current_page < total_pages - 1:
        session["current_page"] += 1
    elif action == "prev" and current_page > 0:
        session["current_page"] -= 1
    else:
        await callback_query.answer("No more pages in this direction.")
        return

    content = session["pages"][session["current_page"]]
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Previous", callback_data=f"prev_{session_id}"),
            InlineKeyboardButton("Next", callback_data=f"next_{session_id}"),
            InlineKeyboardButton("Close", callback_data=f"close_{session_id}")
        ]
    ])

    await callback_query.message.edit_text(
        f"📋 **Players List**\n**Total players:** {session['total_players']}\n**Page {session['current_page'] + 1}/{total_pages}**\n\n{content}",
        reply_markup=keyboard
    )
    await callback_query.answer()


@Client.on_message(filters.command("setrank") & filters.private)
async def set_rank_command(client: Client, message: Message):
    """Handle the /setrank command to update a player's rank."""
    if message.from_user.id not in ADMINS:
        await message.reply("❌ You are not authorized to use this command.")
        return

    if len(message.command) < 3:
        await message.reply("❌ Usage: /setrank ID RANK (1-5)")
        return

    player_id, rank = message.command[1], message.command[2]
    try:
        rank = int(rank)
        if rank not in range(1, 6):
            raise ValueError
    except ValueError:
        await message.reply("❌ Rank must be a number between 1 and 5.")
        return

    name = await set_rank(player_id, rank)
    if name:
        await message.reply(f"✅ Successfully set {name}'s rank to R{rank}.")
    else:
        await message.reply("❌ User ID not found in the database.")