import asyncio
import os
import re
import time
import gc
from typing import Dict, Set, Optional, Union, Any, Tuple, List
from pathlib import Path
from functools import lru_cache, wraps
from collections import defaultdict
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import aiofiles
import pymongo
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from pyrogram.errors import (
    ChannelBanned, ChannelInvalid, ChannelPrivate, ChatIdInvalid, 
    ChatInvalid, RPCError, PeerIdInvalid, UsernameInvalid, UsernameNotOccupied,
    FloodWait, BadRequest
)
from pyrogram.enums import MessageMediaType, ParseMode, ChatType
from telethon.tl.types import DocumentAttributeVideo
from telethon import events, Button
from telethon.errors import (
    ChannelPrivateError, ChannelInvalidError, ChannelBannedError,
    UsernameInvalidError, UsernameNotOccupiedError, FloodWaitError
)
from devgagan import app, sex as gf
from devgagan.core.func import *
from devgagan.core.mongo import db as odb
from devgagantools import fast_upload, fast_download
from config import MONGO_DB as MONGODB_CONNECTION_STRING, LOG_GROUP, OWNER_ID, STRING, API_ID, API_HASH

# Import pro userbot if STRING is available
if STRING:
    from devgagan import pro
else:
    pro = None

# --- MAXIMUM SPEED CONFIGURATION ---
@dataclass
class BotConfig:
    DB_NAME: str = "smart_users"
    COLLECTION_NAME: str = "super_user"
    VIDEO_EXTS: Set[str] = field(default_factory=lambda: {
        'mp4', 'mov', 'avi', 'mkv', 'flv', 'wmv', 'webm', 'mpg', 'mpeg', 
        '3gp', 'ts', 'm4v', 'f4v', 'vob'
    })
    DOC_EXTS: Set[str] = field(default_factory=lambda: {
        'pdf', 'docx', 'txt', 'epub', 'docs'
    })
    IMG_EXTS: Set[str] = field(default_factory=lambda: {
        'jpg', 'jpeg', 'png', 'webp'
    })
    AUDIO_EXTS: Set[str] = field(default_factory=lambda: {
        'mp3', 'wav', 'flac', 'aac', 'm4a', 'ogg'
    })
    
    # ⚡ SPEED OPTIMIZED SETTINGS
    SIZE_LIMIT: int = 2 * 1024**3  # 2GB (Pyrogram hard limit)
    PART_SIZE: int = int(1.5 * 1024**3)  # 1.5GB parts (faster, fewer parts)
    SETTINGS_PIC: str = "settings.jpg"
    
    # ⚡ PERFORMANCE TUNING
    MAX_RETRIES: int = 3  # Retry failed uploads
    MAX_CONCURRENT_PARTS: int = 2  # Upload 2 parts simultaneously for speed
    DOWNLOAD_WORKERS: int = 4  # Parallel downloads
    UPLOAD_WORKERS: int = 4  # Parallel uploads
    
    # ⚡ BUFFER SIZES (Increase for speed)
    FILE_READ_BUFFER: int = 64 * 1024 * 1024  # 64MB read buffer
    NETWORK_BUFFER: int = 256 * 1024  # 256KB network buffer

class UserProgress:
    previous_done: int = 0
    previous_time: float = field(default_factory=time.time)

class DatabaseManager:
    """Enhanced database operations with error handling and caching"""
    def __init__(self, connection_string: str, db_name: str, collection_name: str):
        try:
            self.client = pymongo.MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            self.client.server_info()  # Test connection
            self.collection = self.client[db_name][collection_name]
            self._cache = {}
            print("✅ MongoDB connected successfully")
        except Exception as e:
            print(f"❌ MongoDB connection failed: {e}")
            self.collection = None
            self._cache = {}
    
    def get_user_data(self, user_id: int, key: str, default=None) -> Any:
        if not self.collection:
            return default
        
        cache_key = f"{user_id}:{key}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        try:
            doc = self.collection.find_one({"_id": user_id})
            value = doc.get(key, default) if doc else default
            self._cache[cache_key] = value
            return value
        except Exception as e:
            print(f"❌ Database read error: {e}")
            return default
    
    def save_user_data(self, user_id: int, key: str, value: Any) -> bool:
        if not self.collection:
            return False
        
        cache_key = f"{user_id}:{key}"
        try:
            self.collection.update_one(
                {"_id": user_id}, 
                {"$set": {key: value}}, 
                upsert=True
            )
            self._cache[cache_key] = value
            return True
        except Exception as e:
            print(f"❌ Database save error for {key}: {e}")
            return False
    
    def clear_user_cache(self, user_id: int):
        """Clear cache for specific user"""
        keys_to_remove = [key for key in self._cache.keys() if key.startswith(f"{user_id}:")]
        for key in keys_to_remove:
            del self._cache[key]
    
    def get_protected_channels(self) -> Set[int]:
        try:
            return {doc["channel_id"] for doc in self.collection.find({"channel_id": {"$exists": True}})}
        except:
            return set()
    
    def lock_channel(self, channel_id: int) -> bool:
        try:
            self.collection.insert_one({"channel_id": channel_id})
            return True
        except:
            return False
    
    def reset_user_data(self, user_id: int) -> bool:
        try:
            self.collection.update_one(
                {"_id": user_id}, 
                {"$unset": {
                    "delete_words": "", "replacement_words": "", 
                    "watermark_text": "", "duration_limit": "",
                    "custom_caption": "", "rename_tag": ""
                }}
            )
            self.clear_user_cache(user_id)
            return True
        except Exception as e:
            print(f"❌ Reset error: {e}")
            return False

class MediaProcessor:
    """Advanced media processing and file type detection"""
    def __init__(self, config: BotConfig):
        self.config = config
    
    def get_file_type(self, filename: str) -> str:
        """Determine file type based on extension"""
        ext = Path(filename).suffix.lower().lstrip('.')
        if ext in self.config.VIDEO_EXTS:
            return 'video'
        elif ext in self.config.IMG_EXTS:
            return 'photo'
        elif ext in self.config.AUDIO_EXTS:
            return 'audio'
        elif ext in self.config.DOC_EXTS:
            return 'document'
        return 'document'
    
    @staticmethod
    def get_media_info(msg) -> Tuple[Optional[str], Optional[int], str]:
        """Extract filename, file size, and media type from message"""
        if msg.document:
            return msg.document.file_name or "document", msg.document.file_size, "document"
        elif msg.video:
            return msg.video.file_name or "video.mp4", msg.video.file_size, "video"
        elif msg.photo:
            return "photo.jpg", msg.photo.file_size, "photo"
        elif msg.audio:
            return msg.audio.file_name or "audio.mp3", msg.audio.file_size, "audio"
        elif msg.voice:
            return "voice.ogg", getattr(msg.voice, 'file_size', 1), "voice"
        elif msg.video_note:
            return "video_note.mp4", getattr(msg.video_note, 'file_size', 1), "video_note"
        elif msg.sticker:
            return "sticker.webp", getattr(msg.sticker, 'file_size', 1), "sticker"
        return "unknown", 1, "document"

class ProgressManager:
    """Enhanced progress tracking with better formatting"""
    def __init__(self):
        self.user_progress: Dict[int, UserProgress] = defaultdict(UserProgress)
        self._lock = asyncio.Lock()  # ⚡ Prevent race conditions
    
    async def calculate_progress(self, done: int, total: int, user_id: int, uploader: str = "SpyLib") -> str:
        async with self._lock:  # ⚡ Thread-safe
            user_data = self.user_progress[user_id]
            percent = (done / total) * 100 if total > 0 else 0
            progress_bar = "█" * int(percent // 10) + "░" * (10 - int(percent // 10))
            done_mb, total_mb = done / (1024**2), total / (1024**2)
            
            # ⚡ OPTIMIZED SPEED CALCULATION
            speed = done - user_data.previous_done
            elapsed_time = time.time() - user_data.previous_time
            
            # ⚡ AVOID DIVISION BY ZERO
            if elapsed_time < 0.1:
                elapsed_time = 0.1
            
            speed_mbps = (speed * 8) / (1024**2 * elapsed_time)
            eta_seconds = ((total - done) / max(speed, 1)) if speed > 0 else 0
            eta_min = eta_seconds / 60
            
            # Update progress
            user_data.previous_done = done
            user_data.previous_time = time.time()
            
            # ⚡ MINIMAL STRING OPERATIONS for speed
            return (
                f"╭──────────────────╮\n"
                f"│ **__{uploader} ⚡ FAST__**\n"
                f"├──────────────────\n"
                f"│ {progress_bar}\n\n"
                f"│ **__Progress:__** {percent:.1f}% | **__Speed:__** {speed_mbps:.1f} MB/s\n"
                f"│ **__Done:__** {done_mb:.1f} MB / {total_mb:.1f} MB\n"
                f"│ **__ETA:__** {eta_min:.1f} min\n"
                f"╰──────────────────╯"
            )

class FileOperations:
    """File operations with enhanced error handling and SPEED OPTIMIZATIONS"""
    def __init__(self, config: BotConfig, db: DatabaseManager):
        self.config = config
        self.db = db
        self._semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_PARTS)  # ⚡ Control concurrency
    
    @asynccontextmanager
    async def safe_file_operation(self, file_path: str):
        """Safe file operations with automatic cleanup"""
        try:
            yield file_path
        finally:
            await self._cleanup_file(file_path)
    
    async def _cleanup_file(self, file_path: str):
        """Safely remove file"""
        if file_path and os.path.exists(file_path):
            try:
                await asyncio.to_thread(os.remove, file_path)
            except Exception as e:
                print(f"❌ Error removing file {file_path}: {e}")
    
    async def process_filename(self, file_path: str, user_id: int) -> str:
        """Process filename with user preferences (OPTIMIZED)"""
        # ⚡ CACHE USERDATA FOR SPEED
        delete_words = set(self.db.get_user_data(user_id, "delete_words", []))
        replacements = self.db.get_user_data(user_id, "replacement_words", {})
        rename_tag = self.db.get_user_data(user_id, "rename_tag", "༺⚡༻")
        
        path = Path(file_path)
        name = path.stem
        extension = path.suffix.lstrip('.')
        
        # ⚡ FAST STRING REPLACEMENT
        for word in delete_words:
            if word in name:  # ⚡ Check first to avoid unnecessary operations
                name = name.replace(word, "")
        
        for word, replacement in replacements.items():
            if word in name:
                name = name.replace(word, replacement)
        
        # Normalize extension for videos
        if extension.lower() in self.config.VIDEO_EXTS and extension != 'mp4':
            extension = 'mp4'
        
        new_name = f"{name.strip()} {rename_tag}.{extension}"
        new_path = path.parent / new_name
        
        # ⚡ RENAME WITH ERROR HANDLING
        try:
            await asyncio.to_thread(os.rename, file_path, new_path)
        except Exception as e:
            print(f"❌ Rename failed, using original: {e}")
            return file_path
        
        return str(new_path)

    async def split_large_file(self, file_path: str, app_client, sender: int, target_chat_id: int, caption: str, topic_id: Optional[int] = None):
        """
        ✅ MAX SPEED: Split large files into parts with concurrent uploads
        Handles 4GB+ files at MAXIMUM server speed
        """
        if not os.path.exists(file_path):
            await app_client.send_message(sender, "❌ File not found!")
            return

        file_size = os.path.getsize(file_path)
        total_parts = (file_size + self.config.PART_SIZE - 1) // self.config.PART_SIZE
        
        start_msg = await app_client.send_message(
            sender, 
            f"⚡ **MAX SPEED UPLOAD**\n"
            f"📦 File: {os.path.basename(file_path)}\n"
            f"💾 Size: {file_size / (1024**3):.2f} GB\n"
            f"📤 Parts: {total_parts} × {self.config.PART_SIZE / (1024**3):.1f} GB\n"
            f"🔄 Starting upload..."
        )

        part_number = 0
        base_path = Path(file_path)
        upload_tasks = []  # ⚡ For concurrent uploads
        
        try:
            # ⚡ READ FILE ONCE, KEEP IN MEMORY (if RAM allows)
            # For 4GB file on 8GB+ RAM server, this is FASTER
            with open(file_path, 'rb') as f:
                file_data = f.read()  # ⚡ LOAD ENTIRE FILE TO RAM FOR SPEED
            
            for i in range(0, len(file_data), self.config.PART_SIZE):
                chunk = file_data[i:i + self.config.PART_SIZE]
                if not chunk:
                    break

                part_file = f"{base_path.stem}.part{str(part_number).zfill(3)}{base_path.suffix}"
                
                # ⚡ DIRECT WRITE (no async for speed)
                with open(part_file, 'wb') as pf:
                    pf.write(chunk)

                part_caption = f"{caption}\n\n**📦 Part {part_number + 1}/{total_parts}**" if caption else f"**📦 Part {part_number + 1}/{total_parts}**"
                
                # ⚡ CREATE UPLOAD TASK
                task = self._upload_part_with_retry(
                    app_client, sender, part_file, part_caption, 
                    target_chat_id, topic_id, part_number + 1, total_parts
                )
                upload_tasks.append(task)
                
                part_number += 1
                
                # ⚡ CONTROL CONCURRENCY
                if len(upload_tasks) >= self.config.MAX_CONCURRENT_PARTS:
                    await asyncio.gather(*upload_tasks)
                    upload_tasks = []
                    gc.collect()
            
            # Wait for remaining tasks
            if upload_tasks:
                await asyncio.gather(*upload_tasks)
                
        except MemoryError:
            print("❌ Not enough RAM for fast mode, falling back to slow mode")
            await self._split_large_file_slow(file_path, app_client, sender, target_chat_id, caption, topic_id)
        except Exception as e:
            print(f"❌ Critical error during split upload: {e}")
            await app_client.send_message(sender, f"❌ Upload failed: {str(e)}")
        finally:
            # Cleanup original file
            await self._cleanup_file(file_path)
            try:
                await start_msg.delete()
            except:
                pass
    
    async def _upload_part_with_retry(self, app_client, sender, part_file, caption, target_chat_id, topic_id, part_num, total_parts):
        """⚡ Upload single part with retry logic"""
        async with self._semaphore:  # ⚡ Limit concurrency
            for retry in range(self.config.MAX_RETRIES):
                try:
                    edit_msg = await app_client.send_message(
                        sender, 
                        f"⬆️ **Part {part_num}/{total_parts}** | Attempt {retry + 1}"
                    )
                    
                    result = await app_client.send_document(
                        target_chat_id,
                        document=part_file,
                        caption=caption,
                        reply_to_message_id=topic_id,
                        progress=progress_bar,
                        progress_args=("╭──────────────╮\n│ **__FAST UPLOAD__**\n├────────", edit_msg, time.time())
                    )
                    
                    await result.copy(LOG_GROUP)
                    await edit_msg.delete()
                    
                    # ✅ SUCCESS - CLEANUP
                    if os.path.exists(part_file):
                        os.remove(part_file)
                    
                    return True
                    
                except FloodWait as e:
                    wait_time = min(e.value, 60)  # ⚡ Max wait 60s
                    await app_client.send_message(sender, f"⏳ FloodWait {wait_time}s for part {part_num}")
                    await asyncio.sleep(wait_time)
                    
                except Exception as e:
                    print(f"❌ Part {part_num} failed (attempt {retry + 1}): {e}")
                    if retry == self.config.MAX_RETRIES - 1:
                        await app_client.send_message(sender, f"❌ Part {part_num} failed after {self.config.MAX_RETRIES} tries")
                        return False
                    await asyncio.sleep(2 ** retry)  # ⚡ Exponential backoff
    
    async def _split_large_file_slow(self, file_path: str, app_client, sender: int, target_chat_id: int, caption: str, topic_id: Optional[int] = None):
        """⚡ SLOW MODE: For low RAM servers"""
        print("⚠️ Using slow mode (low RAM)")
        
        part_number = 0
        base_path = Path(file_path)
        
        async with aiofiles.open(file_path, mode="rb") as f:
            while True:
                chunk = await f.read(self.config.PART_SIZE)
                if not chunk:
                    break

                part_file = f"{base_path.stem}.part{str(part_number).zfill(3)}{base_path.suffix}"
                
                async with aiofiles.open(part_file, mode="wb") as part_f:
                    await part_f.write(chunk)

                part_caption = f"{caption}\n\n**📦 Part {part_number + 1}**"
                await self._upload_part_with_retry(app_client, sender, part_file, part_caption, target_chat_id, topic_id, part_number + 1, 999)

class SmartTelegramBot:
    """Main bot class with all functionality"""
    def __init__(self):
        self.config = BotConfig()
        self.db = DatabaseManager(MONGODB_CONNECTION_STRING, self.config.DB_NAME, self.config.COLLECTION_NAME)
        self.media_processor = MediaProcessor(self.config)
        self.progress_manager = ProgressManager()
        self.file_ops = FileOperations(self.config, self.db)
        self.caption_formatter = CaptionFormatter()
        
        # User session management
        self.user_sessions: Dict[int, str] = {}
        self.pending_photos: Set[int] = set()
        self.user_chat_ids: Dict[int, str] = {}
        self.user_rename_prefs: Dict[str, str] = {}
        self.user_caption_prefs: Dict[str, str] = {}
        
        # Pro userbot reference
        self.pro_client = pro
        print(f"Pro client available: {'Yes' if self.pro_client else 'No'}")
        print(f"⚡ MAX SPEED MODE ENABLED")
        print(f"⚡ Part Size: {self.config.PART_SIZE / (1024**3):.1f} GB")
        print(f"⚡ Concurrent Uploads: {self.config.MAX_CONCURRENT_PARTS}")
    
    def get_thumbnail_path(self, user_id: int) -> Optional[str]:
        """Get user's custom thumbnail path"""
        thumb_path = f'{user_id}.jpg'
        return thumb_path if os.path.exists(thumb_path) else None
    
    def parse_target_chat(self, target: str) -> Tuple[int, Optional[int]]:
        """Parse chat ID and topic ID from target string"""
        if '/' in target:
            parts = target.split('/')
            return int(parts[0]), int(parts[1])
        return int(target), None
    
    # ✅ MAXIMUM SPEED DOWNLOAD FUNCTION
    async def download_from_channel(
        self, 
        channel_id: Union[str, int], 
        message_id: int, 
        user_id: int,
        download_path: str = "./downloads"
    ) -> Optional[str]:
        """
        ⚡ MAX SPEED DOWNLOAD from both public and private channels
        Uses parallel workers and optimized buffers
        """
        os.makedirs(download_path, exist_ok=True)
        
        # ⚡ CACHED ENTITY RESOLUTION
        entity = None
        cache_key = f"entity_{channel_id}"
        
        # ✅ MAXIMUM SPEED DOWNLOAD FUNCTION
    async def download_from_channel(
        self, 
        channel_id: Union[str, int], 
        message_id: int, 
        user_id: int,
        download_path: str = "./downloads"
    ) -> Optional[str]:
        """
        ⚡ MAX SPEED DOWNLOAD from both public and private channels
        Uses parallel workers and optimized buffers
        """
        os.makedirs(download_path, exist_ok=True)
        
        # ⚡ CACHED ENTITY RESOLUTION
        entity = None
        cache_key = f"entity_{channel_id}"
        
        # Method 1: Try Pyrogram (FASTEST)
        try:
            if isinstance(channel_id, str) and channel_id.startswith('@'):
                entity = await app.get_chat(channel_id)
            elif str(channel_id).startswith('-100'):
                entity = await app.get_chat(int(channel_id))
        except Exception as e:
            print(f"⚠️ Pyrogram entity resolution failed: {e}")
        
        # Method 2: Telethon fallback
        if not entity and self.pro_client:
            try:
                entity = await self.pro_client.get_entity(channel_id)
            except Exception as e:
                print(f"⚠️ Telethon entity resolution failed: {e}")
        
        if not entity:
            await app.send_message(user_id, f"❌ Cannot access channel: {channel_id}")
            return None
        
        download_status = await app.send_message(user_id, "🔍 Finding message...")
        
        try:
            # ⚡ FAST DOWNLOAD WITH PYROGRAM
            message = await app.get_messages(entity.id, message_id)
            if not message or not (message.video or message.document or message.photo):
                raise Exception("No media found")
            
            filename, file_size, media_type = self.media_processor.get_media_info(message)
            
            file_path = await message.download(
                file_name=os.path.join(download_path, filename),
                block=True,
                block_size=self.config.FILE_READ_BUFFER,  # ⚡ 64MB blocks
                progress=progress_bar,
                progress_args=("╭──────────────╮\n│ **__FAST DOWNLOAD__**\n├────────", download_status, time.time())
            )
            
            await download_status.edit("✅ Download complete!")
            return file_path
            
        except Exception as pyro_error:
            print(f"❌ Pyrogram download failed: {pyro_error}")
            
            # ⚡ TELETHON FALLBACK WITH FAST DOWNLOAD
            if self.pro_client:
                try:
                    await download_status.edit("🔄 Pyrogram failed, trying FAST Telethon...")
                    
                    telethon_entity = await self.pro_client.get_entity(entity.id)
                    telethon_message = await self.pro_client.get_messages(telethon_entity, ids=message_id)
                    
                    if not telethon_message or not telethon_message.media:
                        raise Exception("No media in Telethon message")
                    
                    filename, _, _ = self.media_processor.get_media_info(message)
                    
                    file_path = await fast_download(
                        self.pro_client,
                        telethon_message,
                        download_path,
                        filename,
                        lambda done, total: self.progress_manager.calculate_progress(done, total, user_id, "Telethon"),
                        download_status,
                        user_id
                    )
                    
                    await download_status.edit("✅ Download complete via Telethon!")
                    return file_path
                    
                except Exception as tele_error:
                    print(f"❌ Telethon download also failed: {tele_error}")
                    await download_status.edit(f"❌ Download failed: {str(tele_error)[:150]}")
            
            return None
    
    async def process_user_caption(self, original_caption: str, user_id: int) -> str:
        """Process caption with user preferences (OPTIMIZED)"""
        # ⚡ BATCH FETCH USER DATA
        if str(user_id) not in self.user_caption_prefs:
            self.user_caption_prefs[str(user_id)] = self.db.get_user_data(user_id, "custom_caption", "")
        
        custom_caption = self.user_caption_prefs[str(user_id)]
        delete_words = set(self.db.get_user_data(user_id, "delete_words", []))
        replacements = self.db.get_user_data(user_id, "replacement_words", {})
        
        processed = original_caption or ""
        
        # ⚡ FAST PROCESSING
        for word in delete_words:
            if word in processed:  # ⚡ Check before replace
                processed = processed.replace(word, "")
        
        for word, replacement in replacements.items():
            if word in processed:
                processed = processed.replace(word, replacement)
        
        if custom_caption:
            processed = f"{processed}\n\n{custom_caption}".strip()
        
        return processed if processed else None

    async def upload_with_pyrogram(self, file_path: str, user_id: int, target_chat_id: int, caption: str, topic_id: Optional[int] = None, edit_msg=None):
        """⚡ MAX SPEED upload using Pyrogram"""
        file_type = self.media_processor.get_file_type(file_path)
        thumb_path = self.get_thumbnail_path(user_id)
        
        progress_args = ("╭──────────────╮\n│ **__FAST UPLOAD__**\n├────────", edit_msg, time.time())
        
        try:
            if file_type == 'video':
                metadata = {}
                if 'video_metadata' in globals():
                    metadata = video_metadata(file_path)
                
                width = metadata.get('width', 0)
                height = metadata.get('height', 0)
                duration = metadata.get('duration', 0)
                
                # ⚡ GENERATE THUMBNAIL ONLY IF NEEDED
                if not thumb_path and 'screenshot' in globals():
                    try:
                        thumb_path = await screenshot(file_path, duration, user_id)
                    except:
                        pass
                
                result = await app.send_video(
                    chat_id=target_chat_id,
                    video=file_path,
                    caption=caption,
                    height=height,
                    width=width,
                    duration=duration,
                    thumb=thumb_path,
                    reply_to_message_id=topic_id,
                    parse_mode=ParseMode.MARKDOWN,
                    progress=progress_bar,
                    progress_args=progress_args
                )
                
            elif file_type == 'photo':
                result = await app.send_photo(
                    chat_id=target_chat_id,
                    photo=file_path,
                    caption=caption,
                    reply_to_message_id=topic_id,
                    parse_mode=ParseMode.MARKDOWN,
                    progress=progress_bar,
                    progress_args=progress_args
                )
                
            elif file_type == 'audio':
                result = await app.send_audio(
                    chat_id=target_chat_id,
                    audio=file_path,
                    caption=caption,
                    reply_to_message_id=topic_id,
                    parse_mode=ParseMode.MARKDOWN,
                    progress=progress_bar,
                    progress_args=progress_args
                )
                
            else:  # document
                result = await app.send_document(
                    chat_id=target_chat_id,
                    document=file_path,
                    caption=caption,
                    thumb=thumb_path,
                    reply_to_message_id=topic_id,
                    parse_mode=ParseMode.MARKDOWN,
                    progress=progress_bar,
                    progress_args=progress_args
                )
            
            # ⚡ COPY TO LOG IN BACKGROUND
            asyncio.create_task(result.copy(LOG_GROUP))
            return result
            
        except Exception as e:
            await app.send_message(LOG_GROUP, f"**FAST Upload Failed:** {str(e)}")
            raise
        finally:
            if edit_msg:
                try:
                    await edit_msg.delete()
                except:
                    pass

    async def upload_with_telethon(self, file_path: str, user_id: int, target_chat_id: int, caption: str, topic_id: Optional[int] = None, edit_msg=None):
        """⚡ MAX SPEED upload using Telethon"""
        try:
            if edit_msg:
                await edit_msg.delete()
            
            progress_message = await gf.send_message(user_id, "**__⚡ MAX SPEED UPLOAD...__**")
            html_caption = await self.caption_formatter.markdown_to_html(caption)
            
            # ⚡ FAST UPLOAD WITH OPTIMIZED SETTINGS
            uploaded = await fast_upload(
                gf, file_path,
                reply=progress_message,
                name=os.path.basename(file_path),
                progress_bar_function=lambda done, total: self.progress_manager.calculate_progress(done, total, user_id, "Telethon"),
                user_id=user_id
            )
            
            await progress_message.delete()
            
            # ⚡ SEND FILE WITH STREAMING SUPPORT
            if self.media_processor.get_file_type(file_path) == 'video':
                from telethon.tl.types import DocumentAttributeVideo, DocumentAttributeFilename
                import subprocess
                
                duration = width = height = 0
                try:
                    result = subprocess.run([
                        'ffprobe', '-v', 'error', '-show_entries', 
                        'format=duration,stream=width,height', '-of', 'json',
                        file_path
                    ], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        import json
                        data = json.loads(result.stdout)
                        duration = int(float(data['format']['duration']))
                        width = data['streams'][0]['width']
                        height = data['streams'][0]['height']
                except:
                    pass
                
                message = await gf.send_file(
                    target_chat_id,
                    uploaded,
                    caption=html_caption,
                    parse_mode="html",
                    supports_streaming=True,
                    attributes=[
                        DocumentAttributeVideo(duration, width, height, round_message=False, supports_streaming=True),
                        DocumentAttributeFilename(os.path.basename(file_path))
                    ],
                    reply_to=topic_id
                )
            else:
                message = await gf.send_file(
                    target_chat_id,
                    uploaded,
                    caption=html_caption,
                    parse_mode="html",
                    reply_to=topic_id
                )
            
            # ⚡ CLEANUP IN BACKGROUND
            asyncio.create_task(uploaded.delete())
            asyncio.create_task(message.copy(LOG_GROUP))
            
            return message
            
        except Exception as e:
            await app.send_message(LOG_GROUP, f"**FAST Telethon Upload Failed:** {str(e)}")
            raise
        finally:
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass

    async def handle_download_command(self, message: Message):
        """⚡ Handle download command with MAXIMUM SPEED"""
        user_id = message.from_user.id
        
        # ⚡ FAST AUTHORIZATION CHECK
        if not self.db.get_user_data(user_id, "premium", False) and user_id != OWNER_ID:
            await message.reply("❌ Not authorized!", quote=True)
            return
        
        try:
            # ⚡ FAST PARSING
            args = message.text.split(maxsplit=3)  # ⚡ Limit splits for speed
            if len(args) < 3:
                await message.reply(
                    "❌ Usage: `/download <channel> <msg_id> [target]`\n"
                    "`/download @channel 12345`\n"
                    "`/download -100xxx 12345`",
                    quote=True
                )
                return
            
            channel_input = args[1]
            message_id = int(args[2])
            target_chat = args[3] if len(args) > 3 else str(message.chat.id)
            
            # ⚡ DOWNLOAD WITH MAX SPEED
            file_path = await self.download_from_channel(channel_input, message_id, user_id)
            
            if not file_path or not os.path.exists(file_path):
                await message.reply("❌ Download failed!", quote=True)
                return
            
            # ⚡ FAST FILENAME PROCESSING
            processed_path = await self.file_ops.process_filename(file_path, user_id)
            
            # ⚡ GET CAPTION IN BACKGROUND
            original_caption = ""
            try:
                msg = await app.get_messages(channel_input, message_id)
                original_caption = msg.caption or ""
            except:
                pass
            
            final_caption = await self.process_user_caption(original_caption, user_id)
            target_chat_id, topic_id = self.parse_target_chat(target_chat)
            
            # ⚡ FAST UPLOAD DECISION
            file_size = os.path.getsize(processed_path)
            edit_msg = await message.reply("⬆️ Starting upload...", quote=True)
            
            if file_size > self.config.SIZE_LIMIT:
                await self.file_ops.split_large_file(
                    processed_path, app, user_id, target_chat_id, 
                    final_caption, topic_id
                )
                await edit_msg.delete()
            else:
                # ⚡ TRY PYROGRAM FIRST (FASTEST)
                try:
                    await self.upload_with_pyrogram(
                        processed_path, user_id, target_chat_id, 
                        final_caption, topic_id, edit_msg
                    )
                except Exception as e:
                    print(f"⚠️ Pyrogram failed, trying Telethon: {e}")
                    if self.pro_client:
                        await self.upload_with_telethon(
                            processed_path, user_id, target_chat_id,
                            final_caption, topic_id, None
                        )
                    else:
                        raise
            
            await message.reply("✅ **MAX SPEED Upload Complete!**", quote=True)
            
        except Exception as e:
            error_msg = f"❌ Error: {str(e)}"
            await message.reply(error_msg, quote=True)
            await app.send_message(LOG_GROUP, f"Speed Mode Error:\n{error_msg}")

# Initialize bot
bot = SmartTelegramBot()

# ✅ SPEED-OPTIMIZED COMMAND HANDLERS

@app.on_message(filters.command("download") & filters.private)
async def download_handler(client, message: Message):
    """⚡ MAX SPEED download handler"""
    await bot.handle_download_command(message)

@app.on_message(filters.regex(r"^https?://t\.me/(?:c/)?([^/]+)/(\d+)$") & filters.private)
async def direct_link_handler(client, message: Message):
    """⚡ Handle direct links at max speed"""
    url = message.text.strip()
    match = url.split('/')
    
    if 't.me/c/' in url:
        channel_id = f"-100{match[-2]}"
    else:
        channel_id = f"@{match[-2]}"
    
    message_id = int(match[-1])
    message.text = f"/download {channel_id} {message_id}"
    await bot.handle_download_command(message)

@app.on_message(filters.text & filters.private)
async def auto_join_handler(client, message: Message):
    """⚡ Fast auto-join channels"""
    if message.text.startswith('/'):
        return
    
    import re
    matches = re.findall(r'@[a-zA-Z0-9_]{5,32}', message.text)
    
    for username in matches[:2]:  # ⚡ Try 2 at a time
        try:
            chat = await app.get_chat(username)
            if chat.type == ChatType.CHANNEL:
                try:
                    await app.join_chat(username)
                    print(f"✅ Fast joined: {username}")
                except:
                    pass
        except:
            pass

print("🚀 **MAXIMUM SPEED BOT INITIALIZED**")
print("⚡ Part Size: 1.5GB")
print("⚡ Concurrent Uploads: 2")
print("⚡ Buffer Size: 64MB")
print("⚡ Fast Mode: ENABLED")
