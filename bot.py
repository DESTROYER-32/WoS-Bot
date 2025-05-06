import json
import asyncio
import logging
import re
import time
import sqlite3
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from api.api import API
from uuid import uuid4

try:
    with open("config.json", "r") as f:
        config = json.load(f)
except FileNotFoundError:
    raise Exception("config.json not found.")

API_ID = config["API_ID"]
API_HASH = config["API_HASH"]
BOT_TOKEN = config["BOT_TOKEN"]
ADMINS = config["ADMINS"]
AUTO_RENAME_USERS = config["AUTO_RENAME_USERS"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()]
)

db = sqlite3.connect("players.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        player_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        rank INTEGER NOT NULL CHECK (rank BETWEEN 1 AND 5)
    )
""")
db.commit()

api = API()
app = Client("WoS_Bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

pagination_data = {}

def sanitize_username(name: str) -> str:
    """Sanitize a username by removing specific prefixes and replacing non-breaking spaces."""
    return re.sub(r"^\[[A-Za-z0-9]{3}\]", "", name.replace("\u00a0", " ")).strip()

def is_valid_id(player_id: str) -> bool:
    """Check if the player ID is a valid integer string."""
    try:
        int(player_id)
        return True
    except ValueError:
        return False

async def edit_local_name(player_id: str, new_name: str):
    """Update a player's name in the SQLite database."""
    try:
        cursor.execute("UPDATE players SET name = ? WHERE player_id = ?", (new_name, player_id))
        db.commit()
    except Exception as e:
        logging.error(f"Failed to update name for {player_id}: {str(e)}")

async def get_local_name(player_id: str) -> str:
    """Retrieve a player's name from the SQLite database."""
    try:
        cursor.execute("SELECT name FROM players WHERE player_id = ?", (player_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception:
        return None

async def recursive_redeem(message, code: str, players: list[tuple[str, float]], counters: dict = None, depth: int = 0):
    """Recursively redeem a gift code for a list of players with rate-limiting."""
    counters = counters or {"already_claimed": 0, "successfully_claimed": 0, "error": 0}
    batches = [(i, players[i:i + 20]) for i in range(0, len(players), 20)]
    retry = []

    if depth > 0:
        current_time = time.time()
        wait_time = 0
        for pid, last_called in players:
            ready_time = last_called + 20
            if current_time < ready_time:
                wait_time += ready_time - current_time
                current_time = ready_time
            current_time += 3
        first_player_ready_in = players[0][1] + 20 - time.time()
        initial_wait = max(0, first_player_ready_in)
        waited_initial_wait = initial_wait == 0
    else:
        wait_time = 0
        initial_wait = 0
        waited_initial_wait = True

    progress_message = await message.reply("Redeeming gift code... (0/{})".format(len(players)))

    for i, batch in batches:
        msg = "Redeeming gift code" if depth == 0 else f"Redeeming gift code (retry {depth})"
        next_update = int(1 + time.time() + (len(batch) * 3) + wait_time)
        await progress_message.edit_text(
            f"{msg}... ({min(i + len(batch), len(players))}/{len(players)})<t:{next_update}:R>"
        )

        if not waited_initial_wait:
            await asyncio.sleep(initial_wait)
            waited_initial_wait = True

        for player, ready in batch:
            if time.time() < (ready + 20):
                await asyncio.sleep(ready + 20 - time.time())

            start = time.time()
            exit, counter, result, player_data = await api.redeem_code(code, player)

            if exit:
                await progress_message.edit_text(f"❌ Error: {result}")
                return
            else:
                counters[counter] += 1
                if "error" in result:
                    retry.append((player, time.time()))
                if player_data and AUTO_RENAME_USERS:
                    new_name = sanitize_username(player_data["data"]["nickname"])
                    if new_name != await get_local_name(player):
                        await edit_local_name(player, new_name)

            await asyncio.sleep(max(0, 3 - (time.time() - start)))

    if retry:
        await recursive_redeem(message, code, retry, counters, depth + 1)
    else:
        summary = (
            f"📊 Report: Gift code `{code}`\n"
            f"✅ Successful: {counters['successfully_claimed']}\n"
            f"🔄 Already claimed: {counters['already_claimed']}\n"
            f"🔄 Retries: {depth}"
        )
        await progress_message.edit_text(summary)

@app.on_message(filters.command("start") & filters.private)
async def start_command(client, message):
    """Handle the /start command, accessible to all users."""
    await message.reply("Welcome to the Gift Code Bot! 🎉 Use /help to see available commands.")

@app.on_message(filters.command("help") & filters.private)
async def help_command(client, message):
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

@app.on_message(filters.command("redeem") & filters.private)
async def redeem_code(client, message):
    """Handle the /redeem command to redeem a gift code for all players."""
    if message.from_user.id not in ADMINS:
        return await message.reply("❌ You are not authorized to use this command.")

    if len(message.command) < 2:
        return await message.reply("❌ Usage: /redeem CODE")

    code = message.command[1]
    if api.inUse:
        return await message.reply("❌ Error: The API is currently in use by another command.")
    if api.lastUsed + 60 > time.time():
        return await message.reply("❌ Error: Waiting for API cooldown.")

    await api.init_session()
    api.inUse = True

    try:
        cursor.execute("SELECT player_id FROM players")
        playersObj = cursor.fetchall()
        players = [(player[0], 0) for player in playersObj]
    except Exception as e:
        api.inUse = False
        return await message.reply(f"❌ Database error: {str(e)}")

    await recursive_redeem(message, code, players)
    
    api.lastUsed = time.time()
    api.inUse = False
    await api.session.close()

@app.on_message(filters.command("add") & filters.private)
async def add_user(client, message):
    """Handle the /add command to add a new player to the database."""
    if message.from_user.id not in ADMINS:
        return await message.reply("❌ You are not authorized to use this command.")

    if len(message.command) < 3:
        return await message.reply("❌ Usage: /add ID RANK (1-5)")

    player_id, rank = message.command[1], message.command[2]
    if not is_valid_id(player_id):
        return await message.reply("❌ Invalid user ID.")
    try:
        rank = int(rank)
        if rank not in range(1, 6):
            raise ValueError
    except ValueError:
        return await message.reply("❌ Rank must be a number between 1 and 5.")

    cursor.execute("SELECT player_id FROM players WHERE player_id = ?", (player_id,))
    if cursor.fetchone():
        return await message.reply("❌ User ID already exists in the database.")

    await api.init_session()
    err, _, _, user_data = await api.login_user(player_id)
    
    if not err:
        name = sanitize_username(user_data["data"]["nickname"])
        try:
            cursor.execute("INSERT INTO players (player_id, name, rank) VALUES (?, ?, ?)", (player_id, name, rank))
            db.commit()
            await message.reply(f"✅ Added user {name} to the database with rank R{rank}.")
        except Exception as e:
            await message.reply(f"❌ Database error: {str(e)}")
    else:
        await message.reply("❌ Error: API returned invalid data.")
    
    await api.session.close()

@app.on_message(filters.command("remove") & filters.private)
async def remove_user(client, message):
    """Handle the /remove command to delete a player from the database."""
    if message.from_user.id not in ADMINS:
        return await message.reply("❌ You are not authorized to use this command.")

    if len(message.command) < 2:
        return await message.reply("❌ Usage: /remove ID")

    player_id = message.command[1]
    cursor.execute("SELECT name FROM players WHERE player_id = ?", (player_id,))
    result = cursor.fetchone()
    
    if not result:
        return await message.reply("❌ User ID not found in the database.")

    name = result[0]
    try:
        cursor.execute("DELETE FROM players WHERE player_id = ?", (player_id,))
        db.commit()
        await message.reply(f"✅ Removed user {name} from the database.")
    except Exception as e:
        await message.reply(f"❌ Database error: {str(e)}")

@app.on_message(filters.command("list") & filters.private)
async def list_users(client, message):
    """Handle the /list command to display all players with pagination."""
    if message.from_user.id not in ADMINS:
        return await message.reply("❌ You are not authorized to use this command.")

    try:
        cursor.execute("SELECT player_id, name, rank FROM players")
        players = cursor.fetchall()
    except Exception as e:
        return await message.reply(f"❌ Database error: {str(e)}")

    if not players:
        return await message.reply("📋 No players in the database.")

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
        return await message.reply("📋 No players to display.")

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

@app.on_callback_query()
async def handle_pagination(client, callback_query):
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

@app.on_message(filters.command("setrank") & filters.private)
async def set_rank(client, message):
    """Handle the /setrank command to update a player's rank."""
    if message.from_user.id not in ADMINS:
        return await message.reply("❌ You are not authorized to use this command.")

    if len(message.command) < 3:
        return await message.reply("❌ Usage: /setrank ID RANK (1-5)")

    player_id, rank = message.command[1], message.command[2]
    try:
        rank = int(rank)
        if rank not in range(1, 6):
            raise ValueError
    except ValueError:
        return await message.reply("❌ Rank must be a number between 1 and 5.")

    cursor.execute("SELECT name FROM players WHERE player_id = ?", (player_id,))
    result = cursor.fetchone()
    
    if not result:
        return await message.reply("❌ User ID not found in the database.")

    name = result[0]
    try:
        cursor.execute("UPDATE players SET rank = ? WHERE player_id = ?", (rank, player_id))
        db.commit()
        await message.reply(f"✅ Successfully set {name}'s rank to R{rank}.")
    except Exception as e:
        await message.reply(f"❌ Database error: {str(e)}")

app.run()