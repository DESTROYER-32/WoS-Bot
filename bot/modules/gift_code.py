import asyncio
import time
import xml.etree.ElementTree as ET
from datetime import datetime

import aiohttp
from pyrogram.client import Client
from pyrogram.types import Message

from bot import ADMINS, LOG_CHANNEL, RSS_INTERVAL, RSS_URL, api, logger
from bot.database.gift_code import (delete_gift_code, get_active_gift_codes,
                                    get_all_gift_codes, insert_gift_code,
                                    update_gift_code_last_checked,
                                    update_gift_code_status)
from bot.database.players import list_players
from bot.helpers.misc import recursive_redeem


async def fetch_rss_feed() -> str:
    """Fetch the RSS feed from the specified URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(RSS_URL, timeout=10) as response:
                response.raise_for_status()
                return await response.text()
    except Exception as e:
        logger.error(f"Failed to fetch RSS feed: {str(e)}")
        return ""

async def parse_rss_feed(xml_content: str) -> list[tuple[str, str]]:
    """Parse the RSS feed and extract gift codes and publication dates."""
    try:
        root = ET.fromstring(xml_content)
        codes = []
        for item in root.findall(".//item"):
            code = item.find("title").text.strip()
            pub_date = item.find("pubDate").text.strip()
            pub_date_dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
            pub_date_iso = pub_date_dt.isoformat()
            codes.append((code, pub_date_iso))
        logger.info(f"Parsed {len(codes)} gift codes from RSS feed")
        return codes
    except Exception as e:
        logger.error(f"Failed to parse RSS feed: {str(e)}")
        return []

async def update_gift_codes(client: Client):
    """Update gift codes in the database and redeem new/active codes."""
    xml_content = await fetch_rss_feed()
    if not xml_content:
        logger.warning("No RSS content fetched, skipping update")
        return

    rss_codes = await parse_rss_feed(xml_content)
    if not rss_codes:
        logger.warning("No codes parsed from RSS, skipping update")
        return

    rss_code_set = set(code for code, _ in rss_codes)
    new_codes = []
    for code, pub_date in rss_codes:
        if await insert_gift_code(code, pub_date):
            new_codes.append(code)
        else:
            await update_gift_code_last_checked(code)

    recipient = LOG_CHANNEL if LOG_CHANNEL else (ADMINS[0] if ADMINS else None)
    if new_codes and recipient:
        await client.send_message(
            recipient,
            f"New gift codes found: {', '.join(new_codes)}"
        )
        logger.info(f"Notified {recipient} about new gift codes: {', '.join(new_codes)}")

    db_codes = set(await get_all_gift_codes())
    expired_codes = db_codes - rss_code_set
    for code in expired_codes:
        if await update_gift_code_status(code, "expired"):
            logger.info(f"Marked gift code as expired: {code}")
        else:
            await delete_gift_code(code)

    active_codes = await get_active_gift_codes()
    if not active_codes:
        logger.info("No active gift codes to redeem")
        return

    try:
        players_obj = await list_players()
        players = [(player[0], 0) for player in players_obj]
        logger.info(f"Found {len(players)} players for redemption")
    except Exception as e:
        logger.error(f"Failed to fetch players: {str(e)}")
        return

    if not recipient:
        logger.error("No log channel or admins defined, cannot redeem codes")
        return

    async def send_dummy_message(content: str) -> Message:
        return await client.send_message(recipient, content)

    for code, _ in active_codes:
        if api.inUse:
            logger.warning("API is in use, waiting before redeeming")
            while api.inUse:
                await asyncio.sleep(5)
        if api.lastUsed + 60 > time.time():
            wait_time = api.lastUsed + 60 - time.time()
            logger.info(f"API on cooldown, waiting {wait_time} seconds")
            await asyncio.sleep(wait_time)

        await api.init_session()
        api.inUse = True

        try:
            progress_message = await send_dummy_message(f"Starting redemption for gift code `{code}`...")
            await recursive_redeem(progress_message, code, players)
            await update_gift_code_status(code, "redeemed")
            await client.send_message(recipient, f"Completed redemption for gift code `{code}`.")
            logger.info(f"Completed redemption for gift code: {code}")
        except Exception as e:
            await client.send_message(recipient, f"Failed to redeem gift code `{code}`: {str(e)}")
            logger.error(f"Failed to redeem gift code {code}: {str(e)}")
        finally:
            api.lastUsed = time.time()
            api.inUse = False
            await api.session.close()

async def periodic_gift_code_check(client: Client):
    while True:
        try:
            await update_gift_codes(client)
        except Exception as e:
            logger.error(f"Periodic gift code check failed: {str(e)}")
        await asyncio.sleep(RSS_INTERVAL)