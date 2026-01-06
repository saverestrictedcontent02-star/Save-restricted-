# ---------------------------------------------------
# File Name: start.py
# Description: Bot start, help, terms and plan commands
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# License: MIT License
# ---------------------------------------------------

import logging
from pyrogram import filters, Client
from pyrogram.types import (
    BotCommand, InlineKeyboardMarkup, InlineKeyboardButton, 
    CallbackQuery, Message
)
from config import OWNER_ID
from devgagan import app
from devgagan.core.func import subscribe

# Configure logging
logger = logging.getLogger(__name__)

# Help pages content
HELP_PAGES = [
    """📝 **Bot Commands Overview (1/2)**:

1. **/add userID** - Add user to premium (Owner only)
2. **/rem userID** - Remove user from premium (Owner only)
3. **/transfer userID** - Transfer premium to others (Premium members)
4. **/get** - Get all user IDs (Owner only)
5. **/lock** - Protect channel from extraction (Owner only)
6. **/dl link** - Download videos (Not in v3)
7. **/adl link** - Download audio (Not in v3)
8. **/login** - Log into the bot for private channel access
9. **/batch** - Bulk extraction for posts

💡 **Use /help to see page 2**
""",
    """📝 **Bot Commands Overview (2/2)**:

10. **/logout** - Logout from the bot
11. **/stats** - Get bot stats
12. **/plan** - Check premium plans
13. **/speedtest** - Test server speed
14. **/terms** - Terms and conditions
15. **/cancel** - Cancel ongoing batch
16. **/myplan** - Get your plan details
17. **/session** - Generate Pyrogram v2 session
18. **/settings** - Personalize settings

⚙️ **Settings include:** SETCHATID, SETRENAME, CAPTION, REPLACEWORDS, RESET
"""
]

# Terms text (shared between command and callback)
TERMS_TEXT = """> 📜 **Terms and Conditions** 📜

✨ We are not responsible for user deeds, and we do not promote copyrighted content. If any user engages in such activities, it is solely their responsibility.
✨ Upon purchase, we do not guarantee the uptime, downtime, or the validity of the plan. __Authorization and banning of users are at our discretion; we reserve the right to ban or authorize users at any time.__
✨ Payment to us **__does not guarantee__** authorization for the /batch command. All decisions regarding authorization are made at our discretion and mood."""

# Plan text (shared between command and callback)
PLAN_TEXT = """> 💰 **Premium Price**: Contact Owner

📥 **Download Limit**: Up to 100,000 files per batch
🛑 **Batch Modes**: /bulk and /batch
⚠️ **Note**: Users must wait for auto-cancellation before new downloads

📜 **Terms**: Send /terms for full details"""

@app.on_message(filters.command("set") & filters.user(OWNER_ID))
async def set_bot_commands(_, message: Message):
    """Set bot commands menu (Owner only)"""
    try:
        await app.set_bot_commands([
            BotCommand("start", "🚀 Start the bot"),
            BotCommand("batch", "🫠 Extract in bulk"),
            BotCommand("login", "🔑 Get into the bot"),
            BotCommand("logout", "🚪 Get out of the bot"),
            BotCommand("token", "🎲 Get 3 hours free access"),
            BotCommand("adl", "👻 Download audio from 30+ sites"),
            BotCommand("dl", "💀 Download videos from 30+ sites"),
            BotCommand("freez", "🧊 Remove all expired users"),
            BotCommand("pay", "₹ Pay for subscription"),
            BotCommand("status", "⟳ Refresh Payment status"),
            BotCommand("transfer", "💘 Gift premium to others"),
            BotCommand("myplan", "⌛ Get your plan details"),
            BotCommand("add", "➕ Add user to premium"),
            BotCommand("rem", "➖ Remove from premium"),
            BotCommand("session", "🧵 Generate Pyrogramv2 session"),
            BotCommand("settings", "⚙️ Personalize things"),
            BotCommand("stats", "📊 Get bot stats"),
            BotCommand("plan", "🗓️ Check premium plans"),
            BotCommand("terms", "🥺 Terms and conditions"),
            BotCommand("speedtest", "🚅 Server speed"),
            BotCommand("lock", "🔒 Protect channel from extraction"),
            BotCommand("gcast", "⚡ Broadcast to users"),
            BotCommand("help", "❓ Show help menu"),
            BotCommand("cancel", "🚫 Cancel batch process")
        ])
        await message.reply("✅ **Bot commands configured successfully!**")
    except Exception as e:
        logger.error(f"Error setting commands: {e}")
        await message.reply(f"❌ **Error:** {str(e)}")

async def send_help_page(client: Client, message: Message, page: int):
    """Send help message with pagination"""
    if not (0 <= page < len(HELP_PAGES)):
        return
    
    buttons = []
    if page > 0:
        buttons.append(InlineKeyboardButton("◀️ Previous", callback_data=f"help_{page-1}"))
    if page < len(HELP_PAGES) - 1:
        buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"help_{page+1}"))
    
    keyboard = InlineKeyboardMarkup([buttons]) if buttons else None
    
    try:
        await message.edit_text(
            HELP_PAGES[page],
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Help page error: {e}")

@app.on_message(filters.command("help") & filters.private)
async def help_command(_, message: Message):
    """Show help menu"""
    if await subscribe(_, message):
        return
    
    try:
        await message.reply(
            HELP_PAGES[0],
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Next ▶️", callback_data="help_1")]
            ]) if len(HELP_PAGES) > 1 else None,
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"Help command error: {e}")
        await message.reply("❌ **Error loading help menu**")

@app.on_callback_query(filters.regex(r"help_(\d+)"))
async def help_navigation(_, callback_query: CallbackQuery):
    """Navigate help pages"""
    try:
        page = int(callback_query.data.split("_")[1])
        await send_help_page(_, callback_query.message, page)
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Help nav error: {e}")
        await callback_query.answer("❌ Error", show_alert=True)

@app.on_message(filters.command(["terms", "tos"]) & filters.private)
async def terms_command(_, message: Message):
    """Show terms and conditions"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 See Plans", callback_data="show_plan")],
        [InlineKeyboardButton("💬 Contact Owner", url="https://t.me/Divyanshshukla7")]
    ])
    
    try:
        await message.reply(TERMS_TEXT, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Terms command error: {e}")

@app.on_message(filters.command("plan") & filters.private)
async def plan_command(_, message: Message):
    """Show premium plans"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 See Terms", callback_data="show_terms")],
        [InlineKeyboardButton("💬 Contact Owner", url="https://t.me/Divyanshshukla7")]
    ])
    
    try:
        await message.reply(PLAN_TEXT, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Plan command error: {e}")

@app.on_callback_query(filters.regex(r"show_(plan|terms)"))
async def show_content(_, callback_query: CallbackQuery):
    """Show plan or terms in callback"""
    try:
        content_type = callback_query.data.split("_")[1]
        
        if content_type == "plan":
            text = PLAN_TEXT
            buttons = [[
                InlineKeyboardButton("📜 See Terms", callback_data="show_terms"),
                InlineKeyboardButton("💬 Contact", url="https://t.me/Divyanshshukla7")
            ]]
        else:
            text = TERMS_TEXT
            buttons = [[
                InlineKeyboardButton("📋 See Plans", callback_data="show_plan"),
                InlineKeyboardButton("💬 Contact", url="https://t.me/Divyanshshukla7")
            ]]
        
        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        await callback_query.answer()
    except Exception as e:
        logger.error(f"Callback query error: {e}")
        await callback_query.answer("❌ Error", show_alert=True)
        