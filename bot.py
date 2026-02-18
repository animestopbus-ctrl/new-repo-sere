import logging
import datetime
import asyncio
import os
import signal
from telegram import BotCommand
from telegram.constants import ParseMode 
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram.error import Conflict

import secret
import script
import admin 
from database.db import db
from filetolink.server import start_web_server 
from filetolink.stream import pyro_client 

# ================= LOGGING SETUP =================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO, 
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logging.getLogger("httpx").setLevel(logging.WARNING) 
logging.getLogger("pyrogram").setLevel(logging.WARNING)

# ================= MAIN ASYNC ENGINE =================
async def main():
    print("🚀 TITANIUM 39.0 (4GB STREAMING ENGINE ONLINE).")
    
    # 1. BOOT WEB SERVER IMMEDIATELY
    # This tells Render "I am healthy!" so Render begins killing the old bot instance.
    asyncio.create_task(start_web_server())
    
    # 2. INITIALIZE DATABASE
    await db.setup_ttl_index()

    # 3. BUILD TELEGRAM APP
    app = ApplicationBuilder().token(secret.BOT_TOKEN).connection_pool_size(secret.WORKERS).build()
    
    menu_commands = [
        BotCommand("start", "⚡ Boot up the engine"),
        BotCommand("settings", "⚙️ Account dashboard & limits"),
        BotCommand("help", "📚 How to use the bot"),
        BotCommand("info", "ℹ️ About the bot & developer"),
        BotCommand("ping", "📶 Check bot server latency"),
        BotCommand("id", "🆔 Get your Telegram ID"),
        BotCommand("status", "🟢 View bot uptime and health"),
        BotCommand("feedback", "📬 Send a message to the developer"),
        BotCommand("set_caption", "💎 Set custom caption"),
        BotCommand("panel", "👑 [Admin] Open Dashboard")
    ]
    
    # 4. REGISTER HANDLERS
    app.add_handler(CommandHandler("start", script.start))
    app.add_handler(CommandHandler("help", script.help_cmd))
    app.add_handler(CommandHandler("info", script.info_cmd))
    app.add_handler(CommandHandler("settings", script.settings_cmd))
    app.add_handler(CommandHandler("feedback", script.feedback_cmd))
    app.add_handler(CommandHandler("alive", script.alive_cmd))
    app.add_handler(CommandHandler("ping", script.ping_cmd))
    app.add_handler(CommandHandler("id", script.id_cmd))
    app.add_handler(CommandHandler("status", script.status_cmd))
    
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, script.handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, script.handle_text))
    
    app.add_handler(CommandHandler("set_caption", script.set_cap))
    app.add_handler(CommandHandler("del_caption", script.del_cap))
    app.add_handler(CommandHandler("my_caption", script.my_cap))
    
    app.add_handler(CommandHandler("panel", admin.panel))
    app.add_handler(CommandHandler("stats", admin.stats_cmd)) 
    app.add_handler(CommandHandler("broadcast", admin.broadcast)) 
    app.add_handler(CommandHandler("addpremium", admin.add_premium))
    app.add_handler(CommandHandler("removepremium", admin.remove_premium))
    app.add_handler(CommandHandler("ban", admin.ban))
    app.add_handler(CommandHandler("unban", admin.unban))
    app.add_handler(CommandHandler("speedtest", admin.speedtest_cmd))
    app.add_handler(CommandHandler("users", admin.users_cmd))
    app.add_handler(CommandHandler("logs", admin.logs_cmd))
    app.add_handler(CommandHandler("restart", admin.restart_cmd))
    app.add_handler(CommandHandler("update", admin.update_bot_cmd))
    app.add_handler(CommandHandler("maintenance", admin.maintenance_cmd))
    
    app.add_handler(CallbackQueryHandler(admin.admin_callback, pattern=r"^(admin_|cmd_help_)"))
    app.add_handler(CallbackQueryHandler(script.callback_router))
    
    # 5. INITIALIZE APP
    await app.initialize()
    try:
        await app.bot.set_my_commands(menu_commands)
    except Exception:
        pass
    await app.start()

    # Log Startup to Channel
    if secret.LOG_CHANNEL_ID:
        try:
            platform = "Heroku" if "WEB_URL" in os.environ else ("Render" if "RENDER" in os.environ else "Local")
            msg = f"🚀 <b>BOT ENGINE INITIATED</b>\n\n<blockquote>🤖 <b>Bot Name:</b> @{app.bot.username}\n🌍 <b>Hosted On:</b> {platform}\n🕒 <b>Time:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST\n⚙️ <b>Workers:</b> {secret.WORKERS} Active</blockquote>"
            await app.bot.send_message(chat_id=secret.LOG_CHANNEL_ID, text=msg, parse_mode=ParseMode.HTML, disable_notification=True)
        except: pass

    # 6. 🔥 THE ULTIMATE CONFLICT FIX 🔥
    logging.info("⏳ Securing Telegram Polling Lock...")
    while True:
        try:
            await app.updater.start_polling(drop_pending_updates=True)
            logging.info("✅ Telegram Polling Lock Secured! Bot is fully online.")
            break # Success! Break out of the loop.
        except Conflict:
            logging.warning("⚠️ Conflict detected! Old Render instance is currently dying. Waiting 5 seconds...")
            await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Unexpected Polling Error: {e}")
            await asyncio.sleep(5)

    # 7. KEEP EVENT LOOP ALIVE
    stop_signal = asyncio.Event()
    
    # Graceful Shutdown Handler
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_signal.set)
        
    await stop_signal.wait()
    
    # 8. CLEANUP ON SHUTDOWN
    logging.info("🛑 Shutting down bot gracefully...")
    await app.updater.stop()
    await app.stop()
    await app.shutdown()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user.")
