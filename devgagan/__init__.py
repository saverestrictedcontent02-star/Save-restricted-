# Fixed Main Bot Initialization
import asyncio
import logging
import time
from pyrogram import Client, enums
from config import API_ID, API_HASH, BOT_TOKEN, STRING, MONGO_DB, DEFAULT_SESSION
from telethon.sync import TelegramClient
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s",
    level=logging.INFO,
)

botStartTime = time.time()

# Pyrogram Bot
app = Client(
    "pyrobot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workers=100,  # ⚡ Max workers for speed
    parse_mode=enums.ParseMode.MARKDOWN
)

# Telethon Client
sex = TelegramClient('sexrepo', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Premium Userbot
pro = None
if STRING:
    pro = Client("ggbot", api_id=API_ID, api_hash=API_HASH, session_string=STRING)

# Default Userbot
userrbot = None
if DEFAULT_SESSION:
    userrbot = Client("userrbot", api_id=API_ID, api_hash=API_HASH, session_string=DEFAULT_SESSION)

# MongoDB
tclient = AsyncIOMotorClient(MONGO_DB)
tdb = tclient["telegram_bot"]
token = tdb["tokens"]

async def setup_database():
    """Setup TTL index"""
    try:
        await token.create_index("expires_at", expireAfterSeconds=0)
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ DB Error: {e}")

async def start_bot():
    global BOT_ID, BOT_NAME, BOT_USERNAME
    await setup_database()
    await app.start()
    getme = await app.get_me()
    BOT_ID = getme.id
    BOT_USERNAME = getme.username
    BOT_NAME = f"{getme.first_name} {getme.last_name}" if getme.last_name else getme.first_name
    
    if pro:
        await pro.start()
        print("✅ Premium userbot started")
    if userrbot:
        await userrbot.start()
        print("✅ Default userbot started")
    
    print(f"🚀 Bot @{BOT_USERNAME} started successfully!")

loop = asyncio.get_event_loop()
loop.run_until_complete(start_bot())
