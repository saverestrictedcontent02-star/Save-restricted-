# ---------------------------------------------------
# File Name: speedtest.py
# Description: Server speedtest with proper error handling
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# License: MIT License
# ---------------------------------------------------

import os
import asyncio
import traceback
from time import time
from speedtest import Speedtest
from telethon import events
from devgagan import botStartTime
from devgagan import sex as gagan

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

def get_readable_time(seconds: int) -> str:
    """Convert seconds to readable format"""
    result = ''
    days, remainder = divmod(seconds, 86400)
    if days := int(days):
        result += f'{days}d'
    hours, remainder = divmod(remainder, 3600)
    if hours := int(hours):
        result += f'{hours}h'
    minutes, seconds = divmod(remainder, 60)
    if minutes := int(minutes):
        result += f'{minutes}m'
    if seconds := int(seconds):
        result += f'{seconds}s'
    return result or '0s'

def get_readable_file_size(size_in_bytes) -> str:
    """Convert bytes to human readable format"""
    if not size_in_bytes:
        return '0B'
    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1
    return f'{round(size_in_bytes, 2)}{SIZE_UNITS[index]}'

def speed_convert(size, is_bits=True):
    """Convert speed from bits/s to human readable"""
    if not is_bits:
        size *= 8  # Convert bytes to bits
    power, zero = 2 ** 10, 0
    units = {0: "B/s", 1: "KB/s", 2: "MB/s", 3: "GB/s", 4: "TB/s"}
    while size > power and zero < 4:
        size /= power
        zero += 1
    return f"{round(size, 2)} {units[zero]}"

@gagan.on(events.NewMessage(incoming=True, pattern='^/speedtest$', from_users=OWNER_ID))
async def speedtest(event):
    """Run speedtest - OWNER ONLY"""
    status_msg = await event.reply("🚀 **Running Speed Test...**\nPlease wait ~30 seconds.")
    
    try:
        # Run speedtest
        test = Speedtest()
        test.get_best_server()
        test.download()
        test.upload()
        test.results.share()
        result = test.results.dict()
        
        # Build result string
        current_time = get_readable_time(time() - botStartTime)
        string_speed = f'''
╭─《 🚀 SPEEDTEST INFO 》
├ <b>Upload:</b> <code>{speed_convert(result['upload'])}</code>
├ <b>Download:</b> <code>{speed_convert(result['download'])}</code>
├ <b>Ping:</b> <code>{result['ping']} ms</code>
├ <b>Time:</b> <code>{result['timestamp']}</code>
├ <b>Data Sent:</b> <code>{get_readable_file_size(result['bytes_sent'])}</code>
╰ <b>Data Received:</b> <code>{get_readable_file_size(result['bytes_received'])}</code>
╭─《 🌐 SERVER 》
├ <b>Name:</b> <code>{result['server']['name']}</code>
├ <b>Country:</b> <code>{result['server']['country']}, {result['server']['cc']}</code>
├ <b>Sponsor:</b> <code>{result['server']['sponsor']}</code>
├ <b>Latency:</b> <code>{result['server']['latency']} ms</code>
╰ <b>Location:</b> <code>{result['server']['lat']:.2f}, {result['server']['lon']:.2f}</code>
╭─《 👤 CLIENT 》
├ <b>IP:</b> <code>{result['client']['ip']}</code>
├ <b>ISP:</b> <code>{result['client']['isp']}</code>
├ <b>Country:</b> <code>{result['client']['country']}</code>
╰ <b>Bot Uptime:</b> <code>{current_time}</code>
'''
        
        # Get image path safely
        image_path = result.get('share')
        
        # Send with image if available
        if image_path and os.path.exists(image_path):
            await event.reply(string_speed, file=image_path, parse_mode='html')
            os.remove(image_path)  # Cleanup
        else:
            await event.reply(string_speed, parse_mode='html')
        
        await status_msg.delete()
            
    except Exception as e:
        error_trace = traceback.format_exc()
        await status_msg.edit(f"❌ **Speedtest Failed:**\n`{str(e)[:300]}`")
        print(f"Speedtest Error:\n{error_trace}")
        