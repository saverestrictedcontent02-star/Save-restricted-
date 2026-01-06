# ---------------------------------------------------
# File Name: main.py
# Description: Link & batch processing handler
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# License: MIT License
# ---------------------------------------------------

import time
import random
import string
import asyncio
from pyrogram import filters
from devgagan import app, userrbot
from config import API_ID, API_HASH, FREEMIUM_LIMIT, PREMIUM_LIMIT, OWNER_ID, DEFAULT_SESSION
from devgagan.core.get_func import get_msg
from devgagan.core.func import *
from devgagan.core.mongo import db
from devgagan.core.mongo.plans_db import check_premium
from devgagan.core.mongo.users_db import add_user
from devgagan.modules.shrink import is_user_verified
from pyrogram.errors import FloodWait
from datetime import datetime, timedelta
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

# Global state management
users_loop = {}
interval_set = {}

async def generate_random_name(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

async def check_interval(user_id, is_premium):
    """Check cooldown for free users"""
    if is_premium or user_id in OWNER_ID or await is_user_verified(user_id):
        return True, None

    now = datetime.now()
    if user_id in interval_set:
        cooldown_end = interval_set[user_id]
        if now < cooldown_end:
            remaining = int((cooldown_end - now).total_seconds())
            return False, f"⏳ Wait {remaining}s before next link.\n\n💡 Use /token for 3 hours free access!"
        else:
            del interval_set[user_id]
    
    return True, None

async def set_interval(user_id, interval_minutes=45):
    """Set cooldown for user"""
    interval_set[user_id] = datetime.now() + timedelta(minutes=interval_minutes)

@app.on_message(
    filters.regex(r'https?://(?:www\.)?t\.me/[^\s]+|tg://openmessage\?user_id=\w+&message_id=\d+')
    & filters.private
)
async def single_link(_, message):
    """Handle single link processing"""
    user_id = message.from_user.id
    await add_user(user_id)
    
    if await subscribe(_, message) == 1:
        return
    
    if users_loop.get(user_id, False):
        await message.reply("⚠️ You have an ongoing process. Use /cancel to stop it.", quote=True)
        return
    
    is_premium = await check_premium(user_id) is not None
    if not is_premium and FREEMIUM_LIMIT == 0 and user_id not in OWNER_ID:
        await message.reply("❌ Freemium is disabled. Upgrade to premium!", quote=True)
        return
    
    can_proceed, msg = await check_interval(user_id, is_premium)
    if not can_proceed:
        await message.reply(msg, quote=True)
        return
    
    link = message.text if "tg://openmessage" in message.text else get_link(message.text)
    if not link:
        await message.reply("❌ Invalid link format!", quote=True)
        return
    
    users_loop[user_id] = True
    status_msg = await message.reply("🔄 Processing...", quote=True)
    
    try:
        userbot = await initialize_userbot(user_id) if needs_userbot(link) else None
        
        if is_normal_tg_link(link):
            await process_and_upload_link(userbot, user_id, status_msg.id, link, 0, message)
            await set_interval(user_id, 45)
        else:
            await process_special_links(userbot, user_id, status_msg, link)
            
    except FloodWait as fw:
        await status_msg.edit(f'⏳ FloodWait: {fw.x} seconds. Please wait...')
    except Exception as e:
        await status_msg.edit(f"❌ Error: {str(e)}\n\nLink: `{link}`")
    finally:
        users_loop[user_id] = False
        try:
            await status_msg.delete()
        except:
            pass

async def process_and_upload_link(userbot, user_id, msg_id, link, retry_count, original_msg):
    """Process single link and upload"""
    try:
        await get_msg(userbot, user_id, msg_id, link, retry_count, original_msg)
        await asyncio.sleep(2)
    except Exception as e:
        raise e

def needs_userbot(link: str) -> bool:
    """Check if link requires userbot"""
    return any(x in link for x in ['t.me/+', 't.me/c/', 't.me/b/', 'tg://openmessage'])

def is_normal_tg_link(link: str) -> bool:
    """Check if normal Telegram link"""
    return 't.me/' in link and not needs_userbot(link)

async def process_special_links(userbot, user_id, msg, link):
    """Process special links requiring userbot"""
    if not userbot:
        await msg.edit("🔑 Please /login first for private content!")
        return
    
    if 't.me/+' in link:
        result = await userbot_join(userbot, link)
        await msg.edit(result)
        return
    
    await process_and_upload_link(userbot, user_id, msg.id, link, 0, msg)
    await set_interval(user_id, 45)

async def initialize_userbot(user_id):
    """Initialize userbot for user"""
    data = await db.get_data(user_id)
    if data and data.get("session"):
        try:
            userbot = Client(
                f"userbot_{user_id}",
                api_id=API_ID,
                api_hash=API_HASH,
                session_string=data["session"],
                device_model="iPhone 16 Pro"
            )
            await userbot.start()
            return userbot
        except Exception as e:
            await app.send_message(user_id, "❌ Session expired. Please /login again.")
            return None
    else:
        return userrbot if DEFAULT_SESSION else None

@app.on_message(filters.command("batch") & filters.private)
async def batch_link(_, message):
    """Handle batch processing"""
    if await subscribe(_, message) == 1:
        return
    
    user_id = message.from_user.id
    
    if users_loop.get(user_id, False):
        await message.reply("⚠️ You already have a batch running. Use /cancel to stop it.")
        return
    
    is_premium = await check_premium(user_id) is not None
    if not is_premium and FREEMIUM_LIMIT == 0 and user_id not in OWNER_ID:
        await message.reply("❌ Freemium batch is disabled. Upgrade to premium!")
        return
    
    max_batch = FREEMIUM_LIMIT if not is_premium else PREMIUM_LIMIT
    
    # Get start link
    start_msg = await app.ask(user_id, "Send the **start link** (e.g., `https://t.me/.../123`):", timeout=60)
    start_link = start_msg.text.strip()
    
    try:
        start_id = int(start_link.split("/")[-1])
    except:
        await message.reply("❌ Invalid start link format!")
        return
    
    # Get count
    count_msg = await app.ask(user_id, f"How many messages to process? (Max: {max_batch})", timeout=60)
    try:
        count = int(count_msg.text.strip())
        if count < 1 or count > max_batch:
            raise ValueError
    except:
        await message.reply(f"❌ Enter a number between 1 and {max_batch}!")
        return
    
    # Check cooldown
    can_proceed, msg = await check_interval(user_id, is_premium)
    if not can_proceed:
        await message.reply(msg)
        return
    
    users_loop[user_id] = True
    status = await message.reply(f"📦 Batch started: 0/{count} processed")
    
    try:
        userbot = await initialize_userbot(user_id) if needs_userbot(start_link) else None
        
        for i in range(count):
            if not users_loop.get(user_id, False):
                break
            
            link = f"{'/'.join(start_link.split('/')[:-1])}/{start_id + i}"
            
            try:
                await process_and_upload_link(userbot, user_id, status.id, link, 0, message)
                await status.edit(f"📦 Batch progress: {i+1}/{count}")
                await asyncio.sleep(2)
            except Exception as e:
                print(f"Batch error on {link}: {e}")
                continue
        
        await status.edit(f"✅ Batch completed! {count} messages processed.")
        
    except Exception as e:
        await status.edit(f"❌ Batch failed: {str(e)}")
    finally:
        users_loop[user_id] = False
        await set_interval(user_id, 300)

@app.on_message(filters.command("cancel"))
async def stop_batch(_, message):
    """Cancel active batch"""
    user_id = message.from_user.id
    
    if user_id in users_loop and users_loop[user_id]:
        users_loop[user_id] = False
        await message.reply("✅ Batch cancelled successfully!")
    else:
        await message.reply("ℹ️ No active batch to cancel.")
        