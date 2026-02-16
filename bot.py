import logging
import random
import datetime
from telegram import BotCommand
from telegram.constants import ParseMode 
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

async def startup_setup(app):
    """Fires exactly when the bot boots up. Injects the Menu and logs to the channel."""
    
    # 1. 🎛️ INJECT THE TELEGRAM MENU COMMANDS
    menu_commands = [
        BotCommand("start", "⚡ Boot up the engine"),
        BotCommand("settings", "⚙️ Account dashboard & limits"),
        BotCommand("help", "📚 How to use the bot"),
        BotCommand("info", "ℹ️ About the bot & developer"),
        BotCommand("feedback", "📬 Send a message to the developer"),
        BotCommand("set_caption", "💎 [Premium] Set a custom caption"),
        BotCommand("my_caption", "💎 [Premium] View your custom caption")
    ]
    try:
        await app.bot.set_my_commands(menu_commands)
        logging.info("✅ Telegram Menu Commands Successfully Injected!")
    except Exception as e:
        logging.error(f"Failed to inject menu commands: {e}")

    # 2. 📢 SEND SILENT LOG TO CHANNEL ONLY (No Admin DM)
    if secret.LOG_CHANNEL_ID:
        try:
            msg = (
                f"🚀 <b>BOT ENGINE INITIATED</b>\n\n"
                f"<blockquote>"
                f"🤖 <b>Bot Name:</b> @{app.bot.username}\n"
                f"🌍 <b>Hosted On:</b> Render.com\n"
                f"🕒 <b>Time:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST\n"
                f"⚙️ <b>Workers:</b> {secret.WORKERS} Parallel Threads Active\n"
                f"🗄️ <b>Database:</b> MongoDB Synchronized\n"
                f"🎛️ <b>UI:</b> Telegram Menu Injected"
                f"</blockquote>"
            )
            await app.bot.send_message(
                chat_id=secret.LOG_CHANNEL_ID, 
                text=msg, 
                parse_mode=ParseMode.HTML,
                disable_notification=True
            )
        except Exception as e:
            logging.error(f"Channel Startup log failed: {e}")


if __name__ == '__main__':
    print("🚀 TITANIUM 32.0 (MENU INJECTOR & SILENT BOOT ONLINE).")
    
    keep_alive()
    
    # 🔥 MASSIVE CONCURRENCY & PARALLEL WORKING BOOST
    app = (
        ApplicationBuilder()
        .token(secret.BOT_TOKEN)
        .connection_pool_size(secret.WORKERS) 
        .concurrent_updates(True)             
        .post_init(startup_setup) # <--- Triggers Menu Injection & Logging             
        .build()
    )
    
    # 🟢 CORE USER UTILITIES 🟢
    app.add_handler(CommandHandler("start", script.start))
    app.add_handler(CommandHandler("help", script.help_cmd))
    app.add_handler(CommandHandler("info", script.info_cmd))
    app.add_handler(CommandHandler("settings", script.settings_cmd))
    app.add_handler(CommandHandler("feedback", script.feedback_cmd))
    app.add_handler(CommandHandler("alive", script.alive_cmd))
    
    # 🎥 MEDIA ENGINE
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, script.handle_media))
    
    # 💎 PREMIUM SETTINGS
    app.add_handler(CommandHandler("set_caption", script.set_cap))
    app.add_handler(CommandHandler("del_caption", script.del_cap))
    app.add_handler(CommandHandler("my_caption", script.my_cap))
    
    # 👑 ADMIN DASHBOARD
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
