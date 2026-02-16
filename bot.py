import logging
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

if __name__ == '__main__':
    print("🚀 TITANIUM 27.1 (SYSTEM ONLINE).")
    
    keep_alive()
    
    app = ApplicationBuilder().token(secret.BOT_TOKEN).build()
    
    # Core User Commands
    app.add_handler(CommandHandler("start", script.start))
    app.add_handler(CommandHandler("alive", script.alive_cmd))
    
    # 🔥 THE FIX: Pointed /stats back to script.py where it lives
    app.add_handler(CommandHandler("stats", script.stats_cmd))
    
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, script.handle_media))
    
    # 👑 ADMIN COMMANDS
    app.add_handler(CommandHandler("panel", admin.panel))
    app.add_handler(CommandHandler("addpremium", admin.add_premium))
    app.add_handler(CommandHandler("removepremium", admin.remove_premium))
    app.add_handler(CommandHandler("ban", admin.ban))
    app.add_handler(CommandHandler("unban", admin.unban))
    
    # Callback Routers (Catching standard buttons AND Admin Panel buttons)
    app.add_handler(CallbackQueryHandler(admin.admin_callback, pattern=r"^admin_"))
    app.add_handler(CallbackQueryHandler(script.callback_router))
    
    app.run_polling()
