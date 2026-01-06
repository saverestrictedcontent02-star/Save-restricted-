# devgagan - Fixed Configuration
from os import getenv

# VPS --- FILL COOKIES in triple quotes if needed
INST_COOKIES = """
# write insta cookies here if needed
"""

YTUB_COOKIES = """
# write yt cookies here if needed
"""

API_ID = int(getenv("API_ID", "28389286"))
API_HASH = getenv("API_HASH", "b88da5f4f338cca30f8ea5fb53cb083b")
BOT_TOKEN = getenv("BOT_TOKEN", "8459491597:AAEHPvc1ICgTKwokUtqD461CKLBZmTS3wTM")
OWNER_ID = list(map(int, getenv("OWNER_ID", "6334323103").split()))
MONGO_DB = getenv("MONGO_DB", "mongodb+srv://divyanshshukla5375_db_user:1kZ2dsVTktdMljpr@cluster0.lo5qk5v.mongodb.net/?appName=Cluster0")
LOG_GROUP = int(getenv("LOG_GROUP", "-1002026313336"))
CHANNEL_ID = int(getenv("CHANNEL_ID", "-1003651358527"))
FREEMIUM_LIMIT = int(getenv("FREEMIUM_LIMIT", "10"))
PREMIUM_LIMIT = int(getenv("PREMIUM_LIMIT", "500000000"))
WEBSITE_URL = getenv("WEBSITE_URL", "upshrink.com")
AD_API = getenv("AD_API", "")
STRING = getenv("STRING", None)  # Premium session
DEFAULT_SESSION = getenv("DEFAULT_SESSION", None)
YT_COOKIES = getenv("YT_COOKIES", YTUB_COOKIES)
INSTA_COOKIES = getenv("INSTA_COOKIES", INST_COOKIES)

# ⚡ SPEED OPTIMIZATION
CHUNK_SIZE = 64 * 1024 * 1024  # 64MB chunks
MAX_CONCURRENT = 2  # Parallel uploads
PART_SIZE = 1.5 * 1024**3  # 1.5GB parts
