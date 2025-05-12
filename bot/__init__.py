import logging
import sys
from typing import Final, List

from bot.helpers.api import API
from bot.helpers.yaml import load_config

# Initialize Logger
logger = logging.getLogger("[WoS-Bot]")
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%m/%d/%Y %I:%M:%S %p",
)
logger.setLevel(logging.INFO)
logger.info("WoS-Bot is starting...")

# Do a version check
if sys.version_info[0] < 3 or sys.version_info[1] < 10:
    logger.error(
        "You MUST have a python version of atleast 3.10! Multiple features depend on this. Bot quitting."
    )
    exit(1)

# YAML Loader
bot_config = load_config("config.yml")
telegram_config = bot_config["telegram"]
database_config = bot_config["database"]
misc_config = bot_config["misc"]

# Telegram Constants
API_ID: Final[int] = telegram_config.get("api_id")
API_HASH: Final[str] = telegram_config.get("api_hash")
BOT_TOKEN: Final[str] = telegram_config.get("bot_token")
ADMINS: Final[List[int]] = telegram_config.get("admins", [])

# Database Constants
SCHEMA: Final[str] = database_config.get("schema")

# Misc Constants
AUTO_RENAME_USERS: Final[str] = misc_config.get("auto_rename_users")

api: API = API()
logger.info("Global API instance initialized")