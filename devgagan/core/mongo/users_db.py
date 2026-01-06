# ---------------------------------------------------
# File Name: users_db.py
# Description: User tracking with optimized queries
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# License: MIT License
# ---------------------------------------------------

from config import MONGO_DB
from motor.motor_asyncio import AsyncIOMotorClient as MongoCli
import asyncio

mongo = MongoCli(MONGO_DB)
db = mongo.users
users_db = db.users_db

async def ensure_indexes():
    """Create indexes for performance"""
    try:
        await users_db.create_index("user", unique=True)
        print("✅ User DB indexes created")
    except:
        pass

async def get_users():
    """Get all user IDs"""
    try:
        users = []
        async for user in users_db.find({"user": {"$gt": 0}}):
            users.append(user['user'])
        return users
    except Exception as e:
        print(f"❌ Error getting users: {e}")
        return []

async def get_user(user_id):
    """Check if user exists"""
    try:
        user = await users_db.find_one({"user": user_id})
        return user is not None
    except Exception as e:
        print(f"❌ Error checking user: {e}")
        return False

async def add_user(user_id):
    """Add new user (idempotent)"""
    try:
        if not await get_user(user_id):
            await users_db.insert_one({"user": user_id})
            print(f"✅ New user tracked: {user_id}")
        return True
    except Exception as e:
        print(f"❌ Error adding user: {e}")
        return False

async def del_user(user_id):
    """Delete user"""
    try:
        await users_db.delete_one({"user": user_id})
        print(f"✅ User removed: {user_id}")
        return True
    except Exception as e:
        print(f"❌ Error removing user: {e}")
        return False

# Initialize indexes on import
asyncio.create_task(ensure_indexes())
