# ---------------------------------------------------
# File Name: login.py
# Description: Secure user login via phone number
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# License: MIT License
# ---------------------------------------------------

import os
import asyncio
from pyrogram import filters, Client
from devgagan import app
from config import API_ID as api_id, API_HASH as api_hash
from devgagan.core.mongo import db
from pyrogram.errors import (
    ApiIdInvalid, PhoneNumberInvalid, PhoneCodeInvalid,
    PhoneCodeExpired, SessionPasswordNeeded, PasswordHashInvalid
)

def generate_session_name(user_id):
    return f"sessions/session_{user_id}"

async def delete_session_files(user_id):
    """Clean up session files and DB entry"""
    session_file = f"session_{user_id}.session"
    journal_file = f"session_{user_id}.session-journal"
    
    if os.path.exists(session_file):
        os.remove(session_file)
    if os.path.exists(journal_file):
        os.remove(journal_file)
    
    await db.remove_session(user_id)

@app.on_message(filters.command("logout") & filters.private)
async def logout(_, message):
    """Logout user and clean session"""
    user_id = message.from_user.id
    await delete_session_files(user_id)
    await message.reply("✅ Logged out successfully!")

@app.on_message(filters.command("login") & filters.private)
async def login_handler(_, message):
    """Handle user login flow"""
    user_id = message.from_user.id
    
    # Check existing session
    existing_data = await db.get_data(user_id)
    if existing_data and existing_data.get("session"):
        await message.reply("⚠️ You are already logged in! Use /logout first.")
        return
    
    try:
        # Ask for phone number
        phone_msg = await app.ask(
            user_id,
            "📱 **Enter your phone number with country code.**\nExample: `+19876543210`",
            timeout=120
        )
        phone = phone_msg.text.strip()
        
        # Initialize temporary client
        client = Client(
            generate_session_name(user_id),
            api_id=api_id,
            api_hash=api_hash
        )
        
        await client.connect()
        
        # Send verification code
        code_hash = await client.send_code(phone)
        
        # Ask for OTP
        otp_msg = await app.ask(
            user_id,
            "📲 **Enter the OTP sent to your Telegram account.**\nFormat: `1 2 3 4 5` (with spaces)",
            timeout=300
        )
        otp = otp_msg.text.replace(" ", "")
        
        # Try signing in
        try:
            await client.sign_in(phone, code_hash.phone_code_hash, otp)
        except SessionPasswordNeeded:
            # 2FA required
            password_msg = await app.ask(
                user_id,
                "🔐 **Your account has 2FA enabled. Enter your password:**",
                timeout=120
            )
            password = password_msg.text
            await client.check_password(password)
        
        # Save session
        session_string = await client.export_session_string()
        await db.set_session(user_id, session_string)
        
        # Cleanup
        await client.disconnect()
        await message.reply("✅ **Login successful!** You can now access private channels.")
        
    except asyncio.TimeoutError:
        await message.reply("⏰ **Timeout!** Please start again with /login")
    except Exception as e:
        await message.reply(f"❌ **Login failed:** {str(e)}")
        print(f"Login error for {user_id}: {e}")
        