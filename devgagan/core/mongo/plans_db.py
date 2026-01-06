# ---------------------------------------------------
# File Name: plans_db.py
# Description: Premium user management with auto-expiry
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# License: MIT License
# ---------------------------------------------------

import datetime
from motor.motor_asyncio import AsyncIOMotorClient as MongoCli
from config import MONGO_DB

mongo = MongoCli(MONGO_DB)
db = mongo.premium
premium_db = db.premium_db

async def add_premium(user_id, expire_date):
    """Add or update premium user"""
    try:
        await premium_db.update_one(
            {"_id": user_id},
            {"$set": {"expire_date": expire_date}},
            upsert=True
        )
        print(f"✅ Premium added for user: {user_id}")
        return True
    except Exception as e:
        print(f"❌ Error adding premium: {e}")
        return False

async def remove_premium(user_id):
    """Remove premium user"""
    try:
        await premium_db.delete_one({"_id": user_id})
        print(f"✅ Premium removed for user: {user_id}")
        return True
    except Exception as e:
        print(f"❌ Error removing premium: {e}")
        return False

async def check_premium(user_id):
    """Check if user has active premium"""
    try:
        data = await premium_db.find_one({"_id": user_id})
        if data and data.get("expire_date"):
            if data["expire_date"] > datetime.datetime.utcnow():
                return data
        return None
    except Exception as e:
        print(f"❌ Error checking premium: {e}")
        return None

async def premium_users():
    """Get all premium user IDs"""
    try:
        users = []
        async for user in premium_db.find({}):
            users.append(user["_id"])
        return users
    except Exception as e:
        print(f"❌ Error getting premium users: {e}")
        return []

async def check_and_remove_expired_users():
    """Remove expired premium users (runs every hour)"""
    current_time = datetime.datetime.utcnow()
    removed_users = []
    
    try:
        async for user in premium_db.find({}):
            expire_date = user.get("expire_date")
            if expire_date and expire_date < current_time:
                await premium_db.delete_one({"_id": user["_id"]})
                removed_users.append(user["_id"])
                print(f"🧹 Removed expired premium user: {user['_id']}")
        
        if removed_users:
            print(f"✅ Cleanup completed. Removed {len(removed_users)} expired users.")
        return removed_users
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
        return []
        