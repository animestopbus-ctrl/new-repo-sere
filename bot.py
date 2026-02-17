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
from database.db import db # 🔥 Imported DB to trigger the TTL Index!

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logging.getLogger("httpx").setLevel(logging.WARNING) 
logging.getLogger("httpcore").setLevel(logging.WARNING)

async def startup_setup(app):
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
    try: await app.bot.set_my_commands(menu_commands)
    except: pass

    # 🔥 INITIALIZE SELF-DESTRUCT TIMER INDEX IN MONGODB
    await db.setup_ttl_index()

    if secret.LOG_CHANNEL_ID:
        try:
            msg = f"🚀 <b>BOT ENGINE INITIATED</b>\n\n<blockquote>🤖 <b>Bot Name:</b> @{app.bot.username}\n🌍 <b>Hosted On:</b> Render.com\n🕒 <b>Time:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST\n⚙️ <b>Workers:</b> {secret.WORKERS} Active\n⏳ <b>TTL Index:</b> Online</blockquote>"
            await app.bot.send_message(chat_id=secret.LOG_CHANNEL_ID, text=msg, parse_mode=ParseMode.HTML, disable_notification=True)
        except: pass


if __name__ == '__main__':
    print("🚀 TITANIUM 39.0 (FILE-TO-LINK FOUNDATION ONLINE).")
    
    keep_alive()
    app = ApplicationBuilder().token(secret.BOT_TOKEN).connection_pool_size(secret.WORKERS).concurrent_updates(True).post_init(startup_setup).build()
    
    # 🟢 USER COMMANDS
    app.add_handler(CommandHandler("start", script.start))
    app.add_handler(CommandHandler("help", script.help_cmd))
    app.add_handler(CommandHandler("info", script.info_cmd))
    app.add_handler(CommandHandler("settings", script.settings_cmd))
    app.add_handler(CommandHandler("feedback", script.feedback_cmd))
    app.add_handler(CommandHandler("alive", script.alive_cmd))
    app.add_handler(CommandHandler("ping", script.ping_cmd))
    app.add_handler(CommandHandler("id", script.id_cmd))
    app.add_handler(CommandHandler("status", script.status_cmd))
    
    # 🎥 MEDIA ENGINE
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, script.handle_media))
    
    # 🔥 RANDOM TEXT ENGINE (Reacts to non-cmd messages with Effects)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, script.handle_text))
    
    # 💎 PREMIUM
    app.add_handler(CommandHandler("set_caption", script.set_cap))
    app.add_handler(CommandHandler("del_caption", script.del_cap))
    app.add_handler(CommandHandler("my_caption", script.my_cap))
    
    # 👑 ADMIN
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
    
    # 🔥 FIXED CALLBACK HANDLERS 🔥
    app.add_handler(CallbackQueryHandler(admin.admin_callback, pattern=r"^(admin_|cmd_help_)"))
    app.add_handler(CallbackQueryHandler(script.callback_router))
    
    app.run_polling()
