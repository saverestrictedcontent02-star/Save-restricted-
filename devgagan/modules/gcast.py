# ---------------------------------------------------
# File Name: gcast.py
# Description: Broadcast system for bot
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# License: MIT License
# ---------------------------------------------------

import asyncio
import traceback
from pyrogram import filters, enums
from pyrogram.errors import (
    FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid
)
from config import OWNER_ID
from devgagan import app
from devgagan.core.mongo.users_db import get_users

# ⚡ FAST BROADCAST (0.1s delay)
async def send_msg(user_id, message):
    """Send message to single user with error handling"""
    try:
        # Send copy
        sent = await message.copy(chat_id=user_id)
        
        # Try to pin
        try:
            await sent.pin()
        except:
            try:
                await sent.pin(both_sides=True)
            except:
                pass  # Ignore pin errors
        
        return True, None
        
    except FloodWait as e:
        await asyncio.sleep(min(e.value, 60))  # Max 60s wait
        return await send_msg(user_id, message)  # Retry
        
    except InputUserDeactivated:
        return False, f"❌ {user_id} - Account deleted"
    except UserIsBlocked:
        return False, f"❌ {user_id} - Blocked bot"
    except PeerIdInvalid:
        return False, f"❌ {user_id} - Invalid user"
    except Exception as e:
        return False, f"❌ {user_id} - {str(e)}"

@app.on_message(filters.command("gcast") & filters.user(OWNER_ID))
async def broadcast(_, message):
    """Broadcast message to all bot users"""
    if not message.reply_to_message:
        await message.reply("❌ **Reply to a message to broadcast!**")
        return
    
    # Get all users
    users = await get_users()
    if not users:
        await message.reply("❌ **No users found!**")
        return
    
    status = await message.reply(f"📤 Broadcasting to {len(users)} users...")
    
    done = 0
    failed = 0
    errors = []
    
    # Broadcast with progress
    for user_id in users:
        success, error_msg = await send_msg(user_id, message.reply_to_message)
        
        if success:
            done += 1
        else:
            failed += 1
            errors.append(error_msg)
        
        # Update progress every 50 users
        if (done + failed) % 50 == 0:
            try:
                await status.edit(f"📤 **Progress:** {done}/{len(users)} | ✅ Success: {done} | ❌ Failed: {failed}")
            except:
                pass
        
        # Anti-flood delay
        await asyncio.sleep(0.1)
    
    # Final summary
    summary = f"✅ **Broadcast Complete!**\n\n📊 **Total:** {len(users)}\n✅ **Success:** {done}\n❌ **Failed:** {failed}"
    
    if errors and failed > 0:
        summary += f"\n\n**Errors:**\n" + "\n".join(errors[:5])  # Show first 5 errors
        if failed > 5:
            summary += f"\n... and {failed-5} more"
    
    await status.edit(summary)

@app.on_message(filters.command("acast") & filters.user(OWNER_ID))
async def forward_broadcast(_, message):
    """Forward message to all users (faster than copy)"""
    if not message.reply_to_message:
        await message.reply("❌ **Reply to a message to forward broadcast!**")
        return
    
    users = await get_users()
    if not users:
        await message.reply("❌ **No users found!**")
        return
    
    status = await message.reply(f"📤 Forwarding to {len(users)} users...")
    
    done = 0
    failed = 0
    
    for user_id in users:
        try:
            await message.reply_to_message.forward(user_id)
            done += 1
        except Exception as e:
            failed += 1
            print(f"Forward failed to {user_id}: {e}")
        
        # Progress update
        if (done + failed) % 50 == 0:
            try:
                await status.edit(f"📤 **Progress:** {done}/{len(users)} | ✅ Success: {done} | ❌ Failed: {failed}")
            except:
                pass
        
        await asyncio.sleep(0.05)  # 50ms delay (faster)
    
    await status.edit(
        f"✅ **Forward Broadcast Complete!**\n\n"
        f"📊 **Total:** {len(users)}\n"
        f"✅ **Success:** {done}\n"
        f"❌ **Failed:** {failed}"
    )
    