# --------------------------------------------------
# File Name: db.py
# Description: A Pyrogram bot for downloading files from Telegram channels or groups 
#              and uploading them back to Telegram.
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# Telegram: https://t.me/team_spy_pro
# YouTube: https://youtube.com/@dev_gagan
# Created: 2025-01-11
# Last Modified: 2025-01-11
# Version: 2.0.5
# License: MIT License
# ---------------------------------------------------

import logging
from typing import Optional, List, Dict, Any
from config import MONGO_DB
from motor.motor_asyncio import AsyncIOMotorClient as MongoCli

# Configure logging
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database operations for user data."""
    
    def __init__(self, mongo_uri: str):
        """Initialize database connection."""
        self.mongo_client = MongoCli(mongo_uri)
        self.db = self.mongo_client.user_data
        self.users_collection = self.db.users_data_db
        
    async def get_user_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user data from database."""
        try:
            return await self.users_collection.find_one({"_id": user_id})
        except Exception as e:
            logger.error(f"Error getting user data for user_id {user_id}: {e}")
            return None
    
    async def update_or_insert_user(self, user_id: int, data: Dict[str, Any]) -> bool:
        """Update existing user or insert new user."""
        try:
            existing_data = await self.get_user_data(user_id)
            if existing_data:
                result = await self.users_collection.update_one(
                    {"_id": user_id}, 
                    {"$set": data}
                )
                return result.modified_count > 0
            else:
                data["_id"] = user_id
                await self.users_collection.insert_one(data)
                return True
        except Exception as e:
            logger.error(f"Error updating/inserting user data for user_id {user_id}: {e}")
            return False
    
    async def set_thumbnail(self, user_id: int, thumb: str) -> bool:
        """Set user thumbnail."""
        return await self.update_or_insert_user(user_id, {"thumb": thumb})
    
    async def set_caption(self, user_id: int, caption: str) -> bool:
        """Set user caption."""
        return await self.update_or_insert_user(user_id, {"caption": caption})
    
    async def set_replace_caption(self, user_id: int, replace_txt: str, to_replace: str) -> bool:
        """Set caption replacement rules."""
        return await self.update_or_insert_user(user_id, {
            "replace_txt": replace_txt, 
            "to_replace": to_replace
        })
    
    async def set_session(self, user_id: int, session: str) -> bool:
        """Set user session."""
        return await self.update_or_insert_user(user_id, {"session": session})
    
    async def add_clean_words(self, user_id: int, new_clean_words: List[str]) -> bool:
        """Add words to clean words list."""
        try:
            existing_data = await self.get_user_data(user_id)
            if existing_data:
                existing_words = existing_data.get("clean_words", [])
                if existing_words is None:
                    existing_words = []
                updated_words = list(set(existing_words + new_clean_words))
                result = await self.users_collection.update_one(
                    {"_id": user_id}, 
                    {"$set": {"clean_words": updated_words}}
                )
                return result.modified_count > 0
            else:
                await self.users_collection.insert_one({
                    "_id": user_id, 
                    "clean_words": new_clean_words
                })
                return True
        except Exception as e:
            logger.error(f"Error adding clean words for user_id {user_id}: {e}")
            return False
    
    async def remove_clean_words(self, user_id: int, words_to_remove: List[str]) -> bool:
        """Remove words from clean words list."""
        try:
            existing_data = await self.get_user_data(user_id)
            if existing_data:
                existing_words = existing_data.get("clean_words", [])
                updated_words = [word for word in existing_words if word not in words_to_remove]
                result = await self.users_collection.update_one(
                    {"_id": user_id}, 
                    {"$set": {"clean_words": updated_words}}
                )
                return result.modified_count > 0
            else:
                # User doesn't exist, create with empty clean_words
                await self.users_collection.insert_one({
                    "_id": user_id, 
                    "clean_words": []
                })
                return True
        except Exception as e:
            logger.error(f"Error removing clean words for user_id {user_id}: {e}")
            return False
    
    async def set_channel(self, user_id: int, chat_id: str) -> bool:
        """Set user channel."""
        return await self.update_or_insert_user(user_id, {"chat_id": chat_id})
    
    async def remove_field(self, user_id: int, field_name: str) -> bool:
        """Remove a field from user data."""
        try:
            result = await self.users_collection.update_one(
                {"_id": user_id}, 
                {"$unset": {field_name: ""}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error removing field {field_name} for user_id {user_id}: {e}")
            return False
    
    async def set_field_null(self, user_id: int, field_name: str) -> bool:
        """Set a field to null."""
        try:
            result = await self.users_collection.update_one(
                {"_id": user_id}, 
                {"$set": {field_name: None}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error setting field {field_name} to null for user_id {user_id}: {e}")
            return False
    
    async def all_words_remove(self, user_id: int) -> bool:
        """Remove all clean words."""
        return await self.set_field_null(user_id, "clean_words")
    
    async def remove_thumbnail(self, user_id: int) -> bool:
        """Remove user thumbnail."""
        return await self.set_field_null(user_id, "thumb")
    
    async def remove_caption(self, user_id: int) -> bool:
        """Remove user caption."""
        return await self.set_field_null(user_id, "caption")
    
    async def remove_replace(self, user_id: int) -> bool:
        """Remove caption replacement rules."""
        try:
            result = await self.users_collection.update_one(
                {"_id": user_id}, 
                {"$set": {"replace_txt": None, "to_replace": None}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error removing replace rules for user_id {user_id}: {e}")
            return False
    
    async def remove_session(self, user_id: int) -> bool:
        """Remove user session."""
        return await self.set_field_null(user_id, "session")
    
    async def remove_channel(self, user_id: int) -> bool:
        """Remove user channel."""
        return await self.set_field_null(user_id, "chat_id")
    
    async def delete_session(self, user_id: int) -> bool:
        """Delete the session associated with the given user_id from the database."""
        return await self.remove_field(user_id, "session")

# Initialize database manager
db_manager = DatabaseManager(MONGO_DB)

# Convenience functions for backward compatibility
async def get_data(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user data from database."""
    return await db_manager.get_user_data(user_id)

async def set_thumbnail(user_id: int, thumb: str) -> bool:
    """Set user thumbnail."""
    return await db_manager.set_thumbnail(user_id, thumb)

async def set_caption(user_id: int, caption: str) -> bool:
    """Set user caption."""
    return await db_manager.set_caption(user_id, caption)

async def replace_caption(user_id: int, replace_txt: str, to_replace: str) -> bool:
    """Set caption replacement rules."""
    return await db_manager.set_replace_caption(user_id, replace_txt, to_replace)

async def set_session(user_id: int, session: str) -> bool:
    """Set user session."""
    return await db_manager.set_session(user_id, session)

async def clean_words(user_id: int, new_clean_words: List[str]) -> bool:
    """Add words to clean words list."""
    return await db_manager.add_clean_words(user_id, new_clean_words)

async def remove_clean_words(user_id: int, words_to_remove: List[str]) -> bool:
    """Remove words from clean words list."""
    return await db_manager.remove_clean_words(user_id, words_to_remove)

async def set_channel(user_id: int, chat_id: str) -> bool:
    """Set user channel."""
    return await db_manager.set_channel(user_id, chat_id)

async def all_words_remove(user_id: int) -> bool:
    """Remove all clean words."""
    return await db_manager.all_words_remove(user_id)

async def remove_thumbnail(user_id: int) -> bool:
    """Remove user thumbnail."""
    return await db_manager.remove_thumbnail(user_id)

async def remove_caption(user_id: int) -> bool:
    """Remove user caption."""
    return await db_manager.remove_caption(user_id)

async def remove_replace(user_id: int) -> bool:
    """Remove caption replacement rules."""
    return await db_manager.remove_replace(user_id)

async def remove_session(user_id: int) -> bool:
    """Remove user session."""
    return await db_manager.remove_session(user_id)

async def remove_channel(user_id: int) -> bool:
    """Remove user channel."""
    return await db_manager.remove_channel(user_id)

async def delete_session(user_id: int) -> bool:
    """Delete the session associated with the given user_id from the database."""
    return await db_manager.delete_session(user_id)