# Fixed Core Functions
import math
import time
import re
import cv2
import asyncio
import subprocess
import os
from datetime import datetime as dt
from pyrogram import enums
from config import CHANNEL_ID, OWNER_ID
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.errors import FloodWait, UserAlreadyParticipant, UserNotParticipant

PROGRESS_BAR = """\n
│ **__Completed:__** {1}/{2}
│ **__Bytes:__** {0}%
│ **__Speed:__** {3}/s
│ **__ETA:__** {4}
╰─────────────────────╯
"""

async def chk_user(message, user_id):
    from devgagan.core.mongo.plans_db import premium_users
    user = await premium_users()
    if user_id in user or user_id in OWNER_ID:
        return 0
    return 1

async def gen_link(app, chat_id):
    try:
        link = await app.export_chat_invite_link(chat_id)
        return link
    except:
        return None

async def subscribe(app, message):
    if not CHANNEL_ID:
        return None
    try:
        user = await app.get_chat_member(CHANNEL_ID, message.from_user.id)
        if user.status == enums.ChatMemberStatus.BANNED:
            await message.reply_text("You are Banned. Contact: @Divyanshshukla7")
            return 1
    except UserNotParticipant:
        url = await gen_link(app, CHANNEL_ID)
        if url:
            await message.reply_photo(
                photo="https://img.sanishtech.com/u/678cc73aea37a785300d8836adb19783.png",
                caption="Join our channel to use the bot",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Now", url=url)]])
            )
            return 1
    except Exception as e:
        print(f"Subscribe error: {e}")
        await message.reply_text("Something went wrong. Contact: @Divyanshshukla7")
        return 1
    return None

async def get_seconds(time_string):
    value, unit = "", ""
    index = 0
    while index < len(time_string) and time_string[index].isdigit():
        value += time_string[index]
        index += 1
    unit = time_string[index:].lstrip()
    if value:
        value = int(value)
    if unit == 's': return value
    elif unit == 'min': return value * 60
    elif unit == 'hour': return value * 3600
    elif unit == 'day': return value * 86400
    elif unit == 'month': return value * 86400 * 30
    elif unit == 'year': return value * 86400 * 365
    return 0

def humanbytes(size):
    if not size: return ""
    power, n = 2**10, 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {Dic_powerN[n]}B"

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
          ((str(hours) + "h, ") if hours else "") + \
          ((str(minutes) + "m, ") if minutes else "") + \
          ((str(seconds) + "s, ") if seconds else "") + \
          ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]

def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return f"{int(hour):02d}:{int(minutes):02d}:{int(seconds):02d}"

def get_link(string):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex, string)
    try:
        return [x[0] for x in url][0]
    except:
        return None

def video_metadata(file):
    default = {'width': 1280, 'height': 720, 'duration': 1}
    try:
        vcap = cv2.VideoCapture(file)
        if not vcap.isOpened():
            return default
        
        width = round(vcap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = round(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = vcap.get(cv2.CAP_PROP_FPS)
        frame_count = vcap.get(cv2.CAP_PROP_FRAME_COUNT)
        
        if fps <= 0:
            vcap.release()
            return default
        
        duration = round(frame_count / fps)
        if duration <= 0:
            vcap.release()
            return default
        
        vcap.release()
        return {'width': width, 'height': height, 'duration': duration}
    except:
        return default

async def screenshot(video, duration, sender):
    if os.path.exists(f'{sender}.jpg'):
        return f'{sender}.jpg'
    time_stamp = convert(int(duration)//2)
    out = f"thumb_{sender}_{int(time.time())}.jpg"
    cmd = [
        "ffmpeg", "-ss", time_stamp, "-i", video,
        "-frames:v", "1", "-q:v", "2", out, "-y"
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()
    return out if os.path.exists(out) else None

async def userbot_join(userbot, invite_link):
    try:
        await userbot.join_chat(invite_link)
        return "✅ Successfully joined!"
    except UserAlreadyParticipant:
        return "✅ Already a participant."
    except Exception as e:
        return f"❌ Failed to join: {str(e)}"

async def progress_bar(current, total, ud_type, message, start):
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion
        elapsed_time = TimeFormatter(milliseconds=elapsed_time)
        estimated_total_time = TimeFormatter(milliseconds=estimated_total_time)
        progress = "".join(["█" for _ in range(math.floor(percentage / 10))]) + \
                   "".join(["░" for _ in range(10 - math.floor(percentage / 10))])
        tmp = progress + PROGRESS_BAR.format(
            round(percentage, 2),
            humanbytes(current),
            humanbytes(total),
            humanbytes(speed),
            estimated_total_time if estimated_total_time != '' else "0 s"
        )
        try
            await message.edit(text=f"{ud_type}\n{tmp}")
        except:
            pass

def humanbytes(size):
    if not size:
        return ""
    power, n = 2**10, 0
    Dic_powerN = {0: ' ', 1: 'K', 2: 'M', 3: 'G', 4: 'T'}
    while size > power:
        size /= power
        n += 1
    return f"{round(size, 2)} {Dic_powerN[n]}B"

def TimeFormatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
          ((str(hours) + "h, ") if hours else "") + \
          ((str(minutes) + "m, ") if minutes else "") + \
          ((str(seconds) + "s, ") if seconds else "") + \
          ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]

def convert(seconds):
    seconds = seconds % (24 * 3600)
    hour = seconds // 3600
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return f"{int(hour):02d}:{int(minutes):02d}:{int(seconds):02d}"

def get_link(string):
    regex = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"
    url = re.findall(regex, string)
    try:
        return [x[0] for x in url][0]
    except:
        return None

def video_metadata(file):
    default = {'width': 1280, 'height': 720, 'duration': 1}
    try:
        import cv2
        vcap = cv2.VideoCapture(file)
        if not vcap.isOpened():
            return default
        
        width = round(vcap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = round(vcap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = vcap.get(cv2.CAP_PROP_FPS)
        frame_count = vcap.get(cv2.CAP_PROP_FRAME_COUNT)
        
        if fps <= 0:
            vcap.release()
            return default
        
        duration = round(frame_count / fps)
        if duration <= 0:
            vcap.release()
            return default
        
        vcap.release()
        return {'width': width, 'height': height, 'duration': duration}
    except:
        return default

async def screenshot(video, duration, sender):
    if os.path.exists(f'{sender}.jpg'):
        return f'{sender}.jpg'
    time_stamp = convert(int(duration)//2)
    out = f"thumb_{sender}_{int(time.time())}.jpg"
    cmd = [
        "ffmpeg", "-ss", time_stamp, "-i", video,
        "-frames:v", "1", "-q:v", "2", out, "-y"
    ]
    process = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()
    return out if os.path.exists(out) else None

async def userbot_join(userbot, invite_link):
    try:
        await userbot.join_chat(invite_link)
        return "✅ Successfully joined!"
    except UserAlreadyParticipant:
        return "✅ Already a participant."
    except Exception as e:
        return f"❌ Failed to join: {str(e)}"

# ⚡ ASYNC PROGRESS BAR FOR WATERMARKED UPLOADS
last_update_time = time.time()
async def progress_callback(current, total, progress_message):
    global last_update_time
    current_time = time.time()
    
    if current_time - last_update_time >= 5 or current % (10 * 1024 * 1024) == 0:
        percent = (current / total) * 100
        completed_blocks = int(percent // 10)
        remaining_blocks = 10 - completed_blocks
        progress_bar = "█" * completed_blocks + "░" * remaining_blocks
        current_mb = current / (1024 * 1024)
        total_mb = total / (1024 * 1024)
        
        await progress_message.edit(
            f"╭──────────────────╮\n"
            f"│ **__Uploading...__**\n"
            f"├──────────────────\n"
            f"│ {progress_bar}\n\n"
            f"│ **__Progress:__** {percent:.1f}%\n"
            f"│ **__Done:__** {current_mb:.1f} MB / {total_mb:.1f} MB\n"
            f"╰──────────────────╯"
        )
        last_update_time = current_time
        