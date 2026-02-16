import logging
import random
import datetime
from telegram import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Import the Keep Alive Server
from keep_alive import keep_alive

# Import Secrets & Modules
import secret
import script
import admin 

# Configure Logging (SILENCING HTTPX SPAM)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logging.getLogger("httpx").setLevel(logging.WARNING) 
logging.getLogger("httpcore").setLevel(logging.WARNING)

async def startup_log(app):
    """Fires exactly when the bot boots up and logs to the channel."""
    if secret.LOG_CHANNEL_ID:
        try:
            msg = (
                f"🚀 <b>BOT ENGINE INITIATED</b>\n\n"
                f"<blockquote>"
                f"🤖 <b>Bot Name:</b> @{app.bot.username}\n"
                f"🌍 <b>Hosted On:</b> Render.com\n"
                f"🕒 <b>Time:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST\n"
                f"⚙️ <b>Workers:</b> {secret.WORKERS} Parallel Threads Active\n"
                f"🗄️ <b>Database:</b> MongoDB Synchronized"
                f"</blockquote>"
            )
            await app.bot.send_message(
                chat_id=secret.LOG_CHANNEL_ID, 
                text=msg, 
                parse_mode=ParseMode.HTML,
                message_effect_id=random.choice(secret.MESSAGE_EFFECTS)
            )
        except Exception as e:
            logging.error(f"Startup log failed: {e}")

if __name__ == '__main__':
    print("🚀 TITANIUM 29.0 (EFFECTS & PARALLEL WORKERS) IS ONLINE.")
    
    keep_alive()
    
    # 🔥 MASSIVE CONCURRENCY & PARALLEL WORKING BOOST
    app = (
        ApplicationBuilder()
        .token(secret.BOT_TOKEN)
        .connection_pool_size(secret.WORKERS) # Allow multiple concurrent connections
        .concurrent_updates(True)             # Process multiple users parallelly 
        .post_init(startup_log)               # Send Startup log
        .build()
    )
    
    # Core User Commands
    app.add_handler(CommandHandler("start", script.start))
    app.add_handler(CommandHandler("alive", script.alive_cmd))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, script.handle_media))
    
    # 💎 Premium Custom Caption Commands
    app.add_handler(CommandHandler("set_caption", script.set_cap))
    app.add_handler(CommandHandler("del_caption", script.del_cap))
    app.add_handler(CommandHandler("my_caption", script.my_cap))
    
    # 👑 ADMIN COMMANDS
    app.add_handler(CommandHandler("panel", admin.panel))
    app.add_handler(CommandHandler("stats", admin.stats_cmd)) 
    app.add_handler(CommandHandler("broadcast", admin.broadcast)) 
    app.add_handler(CommandHandler("addpremium", admin.add_premium))
    app.add_handler(CommandHandler("removepremium", admin.remove_premium))
    app.add_handler(CommandHandler("ban", admin.ban))
    app.add_handler(CommandHandler("unban", admin.unban))
    
    # Callback Routers
    app.add_handler(CallbackQueryHandler(admin.admin_callback, pattern=r"^admin_"))
    app.add_handler(CallbackQueryHandler(script.callback_router))
    
    app.run_polling()
