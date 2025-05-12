import asyncio
import re
import time
from typing import Final

from bot import AUTO_RENAME_USERS, api, logger
from bot.database.players import edit_local_name, get_local_name
from bot.helpers.api import API

START_UNIX_TIME: Final[int] = int(time.time())

def get_start_time() -> int:
    return START_UNIX_TIME


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
                    local_name = await get_local_name(player)
                    if new_name != local_name:
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