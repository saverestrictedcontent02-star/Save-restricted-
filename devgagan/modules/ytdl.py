# ---------------------------------------------------
# File Name: ytdl.py (Fixed & Optimized)
# Description: YouTube/Instagram/Social Media Downloader
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# License: MIT License
# ---------------------------------------------------

import yt_dlp
import os
import tempfile
import time
import asyncio
import random
import string
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

import aiohttp
import aiofiles
from mutagen.id3 import ID3, TIT2, TPE1, COMM, APIC
from mutagen.mp3 import MP3

from telethon import events
from telethon.tl.types import DocumentAttributeVideo

from devgagan import sex as telethon_client, app as pyrogram_client
from devgagan.core.func import screenshot, video_metadata

logger = logging.getLogger(__name__)

# Thread pool for blocking operations
thread_pool = ThreadPoolExecutor(max_workers=3)

# Active downloads tracker
ongoing_downloads = {}

def get_random_string(length=7):
    """Generate random string for filenames"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

async def download_thumbnail(url, path):
    """Async thumbnail download"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    async with aiofiles.open(path, 'wb') as f:
                        await f.write(await response.read())
                    return path
    except Exception as e:
        logger.error(f"Thumbnail download failed: {e}")
    return None

async def extract_info(url, ydl_opts):
    """Extract video info in thread pool"""
    def sync_extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)
    return await asyncio.get_event_loop().run_in_executor(thread_pool, sync_extract)

async def download_media(url, ydl_opts):
    """Download media in thread pool"""
    def sync_download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
    return await asyncio.get_event_loop().run_in_executor(thread_pool, sync_download)

async def process_audio(event, url, cookies_env_var=None):
    """Process and upload audio"""
    user_id = event.sender_id
    download_path = None
    temp_cookie_path = None
    
    try:
        # Check if already downloading
        if user_id in ongoing_downloads:
            await event.reply("⚠️ You already have an ongoing download!")
            return
        
        ongoing_downloads[user_id] = True
        
        # Setup cookies if needed
        cookies = os.getenv(cookies_env_var) if cookies_env_var else None
        if cookies:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(cookies)
                temp_cookie_path = f.name
        
        # Generate download path
        random_name = get_random_string()
        download_path = f"{random_name}.mp3"
        
        # Download options
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': f"{random_name}.%(ext)s",
            'cookiefile': temp_cookie_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192'
            }],
            'quiet': True,
            'noplaylist': True,
        }
        
        # Download and extract
        progress_msg = await event.reply("🎵 **Downloading audio...**")
        info_dict = await extract_info(url, ydl_opts)
        
        if not info_dict:
            return
        
        await download_media(url, ydl_opts)
        title = info_dict.get('title', 'Unknown Title')
        
        # Edit metadata
        await progress_msg.edit("🎵 **Adding metadata...**")
        await edit_audio_metadata(download_path, title, info_dict.get('thumbnail'))
        
        # Upload
        await progress_msg.edit("📤 **Uploading...**")
        await upload_audio(telethon_client, event.chat_id, download_path, title)
        
    except Exception as e:
        logger.error(f"Audio processing error: {e}", exc_info=True)
        await event.reply(f"❌ **Error:** {str(e)}")
    
    finally:
        ongoing_downloads.pop(user_id, None)
        # Cleanup
        for path in [download_path, temp_cookie_path]:
            if path and os.path.exists(path):
                os.remove(path)

async def edit_audio_metadata(file_path, title, thumbnail_url):
    """Edit MP3 metadata"""
    try:
        audio = MP3(file_path, ID3=ID3)
        try:
            audio.add_tags()
        except:
            pass
        
        audio.tags["TIT2"] = TIT2(encoding=3, text=title)
        audio.tags["TPE1"] = TPE1(encoding=3, text="༺⚡༻ 𝑫𝒊𝒗𝒚𝒂𝒏𝒔𝒉 𝒔𝒉𝒖𝒌𝒍𝒂 ༺⚡༻")
        audio.tags["COMM"] = COMM(encoding=3, lang="eng", desc="Comment", text="Processed by Team SPY")
        
        if thumbnail_url:
            thumb_path = os.path.join(tempfile.gettempdir(), f"{get_random_string()}.jpg")
            if await download_thumbnail(thumbnail_url, thumb_path):
                async with aiofiles.open(thumb_path, 'rb') as img:
                    audio.tags["APIC"] = APIC(
                        encoding=3, mime='image/jpeg', type=3, desc='Cover', data=await img.read()
                    )
                os.remove(thumb_path)
        
        audio.save()
    except Exception as e:
        logger.error(f"Metadata editing failed: {e}")

async def upload_audio(client, chat_id, file_path, title):
    """Upload audio file"""
    try:
        message = await client.send_file(
            chat_id,
            file_path,
            caption=f"**{title}**\n\n**__Powered by ༺⚡༻ 𝑫𝒊𝒗𝒚𝒂𝒏𝒔𝒉 𝒔𝒉𝒖𝒌𝒍𝒂 ༺⚡༻__**",
            progress_callback=lambda current, total: progress_callback(current, total, chat_id)
        )
        return message
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise

@telethon_client.on(events.NewMessage(pattern="^/adl(?: |$)(.*)", incoming=True))
async def audio_handler(event):
    """Handle /adl command"""
    url = event.pattern_match.group(1).strip()
    if not url:
        await event.reply("**Usage:** `/adl <link>`\nSupports: YouTube, Instagram, etc.")
        return
    
    cookies_var = None
    if "instagram.com" in url:
        cookies_var = "INSTA_COOKIES"
    elif "youtube.com" in url or "youtu.be" in url:
        cookies_var = "YT_COOKIES"
    
    await process_audio(event, url, cookies_var)

@telethon_client.on(events.NewMessage(pattern="^/dl(?: |$)(.*)", incoming=True))
async def video_handler(event):
    """Handle /dl command"""
    url = event.pattern_match.group(1).strip()
    if not url:
        await event.reply("**Usage:** `/dl <link>`\nSupports: YouTube, Instagram, etc.")
        return
    
    cookies_var = None
    check_size = False
    
    if "instagram.com" in url:
        cookies_var = "INSTA_COOKIES"
    elif "youtube.com" in url or "youtu.be" in url:
        cookies_var = "YT_COOKIES"
        check_size = True
    
    # Note: You need to implement process_video similar to process_audio
    # For now, just send a placeholder message
    await process_video(event, url, cookies_var, check_size)

async def process_video(event, url, cookies_env_var=None, check_duration_and_size=False):
    """Process and upload video"""
    user_id = event.sender_id
    download_path = None
    temp_cookie_path = None
    
    try:
        if user_id in ongoing_downloads:
            await event.reply("⚠️ You already have an ongoing download!")
            return
        
        ongoing_downloads[user_id] = True
        
        # Setup cookies
        cookies = os.getenv(cookies_env_var) if cookies_env_var else None
        if cookies:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(cookies)
                temp_cookie_path = f.name
        
        # Generate download path
        random_name = get_random_string()
        download_path = f"{random_name}.mp4"
        
        # Download options
        ydl_opts = {
            'outtmpl': download_path,
            'format': 'best',
            'cookiefile': temp_cookie_path,
            'writethumbnail': True,
            'quiet': True,
        }
        
        # Download
        progress_msg = await event.reply("🎬 **Downloading video...**")
        info_dict = await extract_info(url, ydl_opts)
        
        if not info_dict:
            return
        
        # Check constraints
        if check_duration_and_size:
            duration = info_dict.get('duration', 0)
            if duration > 3 * 3600:
                await progress_msg.edit("❌ **Video is longer than 3 hours!**")
                return
            
            filesize = info_dict.get('filesize_approx', 0)
            if filesize > 2 * 1024**3:
                await progress_msg.edit("❌ **Video is larger than 2GB!**")
                return
        
        await download_media(url, ydl_opts)
        title = info_dict.get('title', 'Unknown')
        
        # Get metadata
        metadata = video_metadata(download_path)
        
        # Upload
        await progress_msg.edit("📤 **Uploading...**")
        await upload_video(
            telethon_client,
            event.chat_id,
            download_path,
            title,
            metadata,
            info_dict.get('thumbnail')
        )
        
        await progress_msg.delete()
        
    except Exception as e:
        logger.error(f"Video processing error: {e}", exc_info=True)
        await event.reply(f"❌ **Error:** {str(e)}")
    
    finally:
        ongoing_downloads.pop(user_id, None)
        # Cleanup
        for path in [download_path, temp_cookie_path]:
            if path and os.path.exists(path):
                os.remove(path)

async def upload_video(client, chat_id, file_path, title, metadata, thumbnail_url):
    """Upload video file"""
    try:
        # Download thumbnail if needed
        thumb_path = None
        if thumbnail_url:
            thumb_path = os.path.join(tempfile.gettempdir(), f"{get_random_string()}.jpg")
            if not await download_thumbnail(thumbnail_url, thumb_path):
                thumb_path = None
        
        # Use screenshot if no thumbnail
        if not thumb_path:
            thumb_path = await screenshot(file_path, metadata['duration'], chat_id)
        
        # Upload
        await client.send_file(
            chat_id,
            file_path,
            caption=f"**{title}**",
            thumb=thumb_path,
            attributes=[
                DocumentAttributeVideo(
                    duration=metadata['duration'],
                    w=metadata['width'],
                    h=metadata['height'],
                    supports_streaming=True
                )
            ],
            progress_callback=lambda current, total: progress_callback(current, total, chat_id)
        )
        
        # Cleanup thumbnail
        if thumb_path and os.path.exists(thumb_path):
            os.remove(thumb_path)
            
    except Exception as e:
        logger.error(f"Video upload error: {e}")
        raise

def progress_callback(current, total, user_id):
    """Progress callback for uploads"""
    # Calculate progress
    percent = (current / total) * 100
    done_mb = current / (1024 * 1024)
    total_mb = total / (1024 * 1024)
    
    # Speed calculation
    if user_id not in user_progress:
        user_progress[user_id] = {'done': 
        