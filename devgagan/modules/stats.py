# ---------------------------------------------------
# File Name: stats.py
# Description: Bot statistics and user tracking
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# License: MIT License
# ---------------------------------------------------

import time
import sys
import logging
from pyrogram import filters
from devgagan import app, botStartTime
from devgagan.core.mongo.users_db import get_users, add_user, get_user
from devgagan.core.mongo.plans_db import premium_users
from config import OWNER_ID

# Configure logging
logger = logging.getLogger(__name__)

# Bot start time tracking
start_time = botStartTime

@app.on_message(group=10)
async def chat_watcher_func(_, message):
    """Track new users automatically"""
    try:
        if message.from_user and not await get_user(message.from_user.id):
            await add_user(message.from_user.id)
    except Exception as e:
        logger.error(f"Chat watcher error: {e}")

def time_formatter() -> str:
    """Convert uptime to readable format"""
    uptime = int(time.time() - start_time)
    days, remainder = divmod(uptime, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds or not parts:
        parts.append(f"{seconds}s")
    
    return ":".join(parts)

def get_mongo_version():
    """Safely get MongoDB version"""
    try:
        import motor
        return motor.version
    except:
        return "Unknown"

@app.on_message(filters.command("stats") & filters.user(OWNER_ID))
async def stats(client, message):
    """Show bot statistics (Owner only)"""
    try:
        # Calculate ping
        ping_start = time.time()
        bot_info = await client.get_me()
        ping = round((time.time() - ping_start) * 1000)
        
        # Get user stats
        users = await get_users() or []
        premium = await premium_users() or []
        
        # Build stats message
        stats_text = f"""
**Stats of {bot_info.mention}:

🏓 **Ping**: `{ping}ms`

📊 **Total Users**: `{len(users)}`
📈 **Premium Users**: `{len(premium)}`
⚙️ **Uptime**: `{time_formatter()}`

🎨 **Python**: `{sys.version.split()[0]}`
📑 **MongoDB**: `{get_mongo_version()}`
"""
        await message.reply_text(stats_text)
        
    except Exception as e:
        logger.error(f"Stats command error: {e}")
        await message.reply_text(f"❌ **Error generating stats:**\n`{str(e)}`")
        