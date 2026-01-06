# ---------------------------------------------------
# File Name: shrink.py
# Description: Token verification system for free access
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# License: MIT License
# ---------------------------------------------------

import asyncio
import random
import string
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_DB, WEBSITE_URL, AD_API
from devgagan import app
from devgagan.core.func import subscribe, chk_user
from datetime import datetime, timedelta
import aiohttp

# Database setup
tclient = AsyncIOMotorClient(MONGO_DB)
tdb = tclient["telegram_bot"]
token_collection = tdb["tokens"]

# Cache for active tokens
Param = {}

async def create_ttl_index():
    """Create TTL index for auto-expiry"""
    try:
        await token_collection.create_index("expires_at", expireAfterSeconds=0)
        print("✅ Token TTL index created")
    except:
        pass

async def generate_param(length=8):
    """Generate random parameter"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

async def get_shortened_url(deep_link):
    """Get short URL from API"""
    if not WEBSITE_URL or not AD_API:
        return deep_link
    
    try:
        api_url = f"https://{WEBSITE_URL}/api?api={AD_API}&url={deep_link}"
        async with aiohttp.ClientSession() as session:
            async with session.get(api_url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return data.get("shortenedUrl")
    except Exception as e:
        print(f"Shortener error: {e}")
    
    return deep_link

async def is_user_verified(user_id):
    """Check if user has active token"""
    try:
        session = await token_collection.find_one({"user_id": user_id})
        return session is not None
    except:
        return False

@app.on_message(filters.command("start") & filters.private)
async def token_handler(_, message):
    """Handle start with token parameter"""
    join = await subscribe(_, message)
    if join == 1:
        return
    
    user_id = message.from_user.id
    
    # Show welcome if no parameter
    if len(message.command) <= 1:
        await show_welcome(message)
        return
    
    param = message.command[1]
    is_premium = await chk_user(message, user_id) != 1
    
    if is_premium:
        await message.reply("✨ You are already premium! No token needed.")
        return
    
    if await is_user_verified(user_id):
        await message.reply("✅ Your free session is already active!")
        return
    
    # Verify token
    if user_id in Param and Param[user_id] == param:
        await token_collection.insert_one({
            "user_id": user_id,
            "param": param,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=3),
        })
        del Param[user_id]
        await message.reply("🎉 **Verified!** Enjoy 3 hours of free access!")
    else:
        await message.reply("❌ **Invalid token!** Use /token to generate new one.")

@app.on_message(filters.command("token") & filters.private)
async def generate_token(_, message):
    """Generate verification token"""
    user_id = message.from_user.id
    
    if await chk_user(message, user_id) != 1:
        await message.reply("✨ You are already premium! No token needed.")
        return
    
    if await is_user_verified(user_id):
        await message.reply("✅ Your free session is already active!")
        return
    
    param = await generate_param()
    Param[user_id] = param
    
    deep_link = f"https://t.me/{_.me.username}?start={param}"
    short_url = await get_shortened_url(deep_link)
    
    button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔑 Verify Access", url=short_url)]]
    )
    
    await message.reply(
        "🎲 **Generate 3-Hour Access Token**\n\n"
        "✅ Click below to get free access:\n"
        "⏰ Valid for 3 hours\n"
        "🔓 All features unlocked",
        reply_markup=button
    )

async def show_welcome(message):
    """Show welcome message"""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Join Channel", url="https://t.me/+5H5tJB8hlJo2MjU1")],
        [InlineKeyboardButton("Get Premium", url="https://t.me/Divyanshshukla7")]
    ])
    
    await message.reply_photo(
        photo="https://straightforward-pink-s9qrn3ua0z-7cjo3r7zez.edgeone.dev/1766497138025-10b1c2ab-8536-4189-9e4a-8932e9f372c8.png",
        caption=(
            f"👋 **Hi {message.from_user.first_name}**\n\n"
            "🔒 Save restricted content from any channel\n"
            "📥 Download from YouTube, Instagram, etc.\n"
            "📌 Just send me a link!\n\n"
            "💡 Need help? → /help\n\n"
            "**__Powered by ༺⚡༻ 𝑫𝒊𝒗𝒚𝒂𝒏𝒔𝒉 𝒔𝒉𝒖𝒌𝒍𝒂 ༺⚡༻ __**"
        ),
        reply_markup=keyboard
    )

# Initialize TTL index
asyncio.create_task(create_ttl_index())
