# Gift Code Bot for Whiteout Survival

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

This is a Telegram bot designed to manage player data and redeem gift codes for the game *Whiteout Survival*. The bot supports adding, removing, and listing players, redeeming gift codes for multiple players, and updating player ranks. It uses a SQLite database for efficient data storage and includes pagination for listing players.

The base code for this bot was developed by [zenpaiang](https://github.com/zenpaiang). This project builds upon their work, incorporating additional features and optimizations. Special thanks to zenpaiang for their foundational contributions.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Setup and Installation](#setup-and-installation)
- [Commands](#commands)
- [Troubleshooting](#troubleshooting)
- [Credits](#credits)
- [License](#license)

## Features

- **Gift Code Redemption**: Redeem gift codes for all registered players with rate-limiting to comply with API restrictions.
- **Auto Gift Code Redemption**: Uses RSS to get and Redeem gift codes for all registered players with scheduling.
- **Player Management**: Add, remove, and update player ranks (1–5) with validation.
- **Player Listing**: Display players grouped by rank with pagination for easy navigation.
- **SQLite Database**: Store player data (ID, name, rank) efficiently using SQLite.
- **External Configuration**: Load bot settings (API keys, admin IDs, etc.) from a `config.yml` file.
- **Auto-Rename**: Automatically update player names during redemption if enabled.
- **Public Commands**: `/start` and `/help` commands accessible to all users, with a GitHub repository link in the help message.
- **Admin Commands**: Restricted commands for authorized users to manage players and redeem codes.
- **Logging**: Real-time logging to the terminal for monitoring bot activity.

## Prerequisites

To run the bot, ensure you have the following installed:

- Python 3.11 or higher
- A Telegram bot token (obtained from [BotFather](https://t.me/BotFather))
- A *Whiteout Survival* game API implementation (not included; see `api/api.py` placeholder)

## Setup and Installation

### 1. Clone the Repository
Clone this repository to your local machine:

```bash
git clone https://github.com/DESTROYER-32/WoS-Bot
cd WoS-Bot
```

### 2. Install Dependencies
Install the required Python packages using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

### 3. Configure the Bot
Create a `config.yml` file in the project root with the following structure:

```
telegram:
  api_id: 1234567
  api_hash: "your_api_hash"
  bot_token: "your_bot_token"
  admins: [123456789, 987654321]

database:
  schema: "sqlite+aiosqlite:///players.db"

misc:
  auto_rename_users: true
  rss_url: "https://wosgiftcodes.com/rss.php"
  rss_interval: 3600
```

- **telegram.api_id** and **telegram.api_hash**: Obtain these from [my.telegram.org](https://my.telegram.org) by creating an app.
- **telegram.bot_token**: Get this from [BotFather](https://t.me/BotFather) by creating a new bot.
- **telegram.admins**: List of Telegram user IDs (integers) authorized to use admin commands. To find your user ID, message `@userinfobot`. Replace `[123456789, 987654321]` with the actual user IDs of the admins.
- **database.schema**: Specifies the SQLite database connection string. The default value (`sqlite+aiosqlite:///players.db`) creates a `players.db` file in the project root.
- **misc.auto_rename_users**: Set to `true` to enable automatic name updates during redemption, or `false` to disable.
- **misc.rss_url**: The URL of the RSS feed for gift codes. The default is `https://wosgiftcodes.com/rss.php`.
- **misc.rss_interval**: The interval (in seconds) for checking the RSS feed. The default is `3600` (1 hour).


### 4. Implement the Game API
The bot requires an API implementation for *Whiteout Survival* to handle login and gift code redemption. The placeholder `api/api.py` file must be replaced with a working implementation. Ensure it provides the following methods:
- `init_session()`: Initialize the API session.
- `login_user(player_id)`: Log in a player and return user data.
- `redeem_code(code, player_id)`: Redeem a gift code for a player.

Refer to the original [wos-bot](https://github.com/zenpaiang/wos-bot) by zenpaiang for guidance on implementing the API.

### 5. Set Up the SQLite Database
The bot automatically creates a `players.db` SQLite database with a `players` table when run for the first time. No manual setup is required.

### 6. Run the Bot
Start the bot by running the main script:

```bash
python -m bot
```

The bot will connect to Telegram and begin processing commands. Logs will be displayed in the terminal.

## Commands

The bot supports the following commands, all of which are used in private chats:

### Public Commands
- **/start**: Displays a welcome message.
  - Example: `/start`
  - Response: "Welcome to the Gift Code Bot! 🎉 Use /help to see available commands."
- **/help**: Shows a list of commands with a button linking to the GitHub repository.
  - Example: `/help`
  - Response: Lists all commands and includes a "GitHub Repository" button.

### Admin-Only Commands
These commands are restricted to users listed in the `ADMINS` array in `config.json`:
- **/redeem CODE**: Redeems a gift code for all players in the database.
  - Example: `/redeem ABC123`
  - Response: Progress updates and a final report (e.g., successful, already claimed, retries).
- **/add ID RANK**: Adds a new player with the specified ID and rank (1–5).
  - Example: `/add 123456789 5`
  - Response: "✅ Added user [Name] to the database with rank R5."
  - Example: `/add 123456789` (Adds with player rank as 1)
- **/remove ID**: Removes a player by their ID.
  - Example: `/remove 123456789`
  - Response: "✅ Removed user [Name] from the database."
- **/list**: Lists all players grouped by rank with pagination.
  - Example: `/list`
  - Response: Displays players with navigation buttons (Previous, Next, Close).
- **/setrank ID RANK**: Updates a player's rank (1–5).
  - Example: `/setrank 123456789 4`
  - Response: "✅ Successfully set [Name]'s rank to R4."
- **/giftcodecheck**: Manually check RSS for new gift code.

## Troubleshooting

- **Bot Not Responding**: Verify the `BOT_TOKEN`, `API_ID`, and `API_HASH` in `config.json`. Ensure the bot is running and connected to Telegram.
- **Database Errors**: Check if `players.db` is accessible and writable. Delete and recreate the database if corrupted.
- **API Errors**: Ensure the `api/api.py` implementation is correct and the *Whiteout Survival* API is accessible.
- **Command Restrictions**: Confirm your Telegram user ID is in the `ADMINS` list for admin commands.

## Credits

- **Original Author**: [zenpaiang](https://github.com/zenpaiang) for the base code and inspiration from the [wos-bot](https://github.com/zenpaiang/wos-bot) project.
- **Contributors**: DESTROYER-32.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

*Happy botting! If you encounter issues or have suggestions, open an issue on the [GitHub repository](https://github.com/DESTROYER-32/WoS-Bot).*