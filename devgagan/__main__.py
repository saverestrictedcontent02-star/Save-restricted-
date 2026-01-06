# ---------------------------------------------------
# File Name: __main__.py
# Description: Main bot entry point with error handling & scheduler
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# License: MIT License
# ---------------------------------------------------

import asyncio
import importlib
import logging
import sys
from pyrogram import idle
from devgagan.modules import ALL_MODULES
from devgagan.core.mongo.plans_db import check_and_remove_expired_users
from aiojobs import create_scheduler

# Configure logging
logging.basicConfig(
    format="[%(levelname) 5s/%(asctime)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Global scheduler
scheduler = None

async def load_modules():
    """Load all modules with error handling"""
    loaded = []
    failed = []
    
    for module_name in ALL_MODULES:
        try:
            importlib.import_module(f"devgagan.modules.{module_name}")
            loaded.append(module_name)
        except Exception as e:
            failed.append((module_name, str(e)))
            logger.error(f"❌ Failed to load {module_name}: {e}", exc_info=True)
    
    logger.info(f"✅ Loaded {len(loaded)}/{len(ALL_MODULES)} modules")
    if failed:
        logger.warning(f"⚠️ Failed modules: {[m[0] for m in failed]}")
    
    return loaded, failed

async def schedule_expiry_check():
    """Remove expired premium users every hour"""
    global scheduler
    
    try:
        scheduler = await create_scheduler()
        logger.info("✅ Premium expiry scheduler started")
        
        while True:
            try:
                removed = await check_and_remove_expired_users()
                if removed:
                    logger.info(f"🧹 Removed {len(removed)} expired users")
                
                await asyncio.sleep(3600)  # Check every 1 hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Scheduler error: {e}")
                await asyncio.sleep(300)  # Retry after 5 min
    
    finally:
        if scheduler:
            await scheduler.close()
            logger.info("🔒 Scheduler closed")

async def devggn_boot():
    """Main bot initialization"""
    logger.info("🚀 Starting bot initialization...")
    
    # Load all modules
    loaded, failed = await load_modules()
    
    # Startup banner
    banner = f"""
╔═══════════════════════════════════════════════════╗
║          ⚡ ༺⚡༻ 𝑫𝒊𝒗𝒚𝒂𝒏𝒔𝒉 𝒔𝒉𝒖𝒌𝒍𝒂 ༺⚡༻ ⚡          ║
╠═══════════════════════════════════════════════════╣
║ 📂 Version: 2.0.5                                 ║
║ 👨‍💻 Author: Gagan                                 ║
║ 🌐 GitHub: github.com/devgaganin                 ║
║ 📝 Modules: {len(loaded):>2}/{len(ALL_MODULES):<2} loaded                            ║
║ ⏰ Premium Check: Every 1 hour                    ║
╚═══════════════════════════════════════════════════╝
"""
    print(banner)
    
    # Start background tasks
    asyncio.create_task(schedule_expiry_check())
    logger.info("✅ Bot deployed successfully! Press Ctrl+C to stop")
    
    # Keep bot alive
    try:
        await idle()
    except KeyboardInterrupt:
        logger.info("🛑 Shutdown signal received")
    finally:
        logger.info("🔴 Bot stopped")

if __name__ == "__main__":
    try:
        asyncio.get_event_loop().run_until_complete(devggn_boot())
    except Exception as e:
        logger.critical(f"❌ Bot crashed: {e}", exc_info=True)
        sys.exit(1)
        