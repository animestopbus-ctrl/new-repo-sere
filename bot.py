import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# Import the Keep Alive Server
from keep_alive import keep_alive

# Import Secrets & Scripts
import secret
import script

# Configure Logging (SILENCING HTTPX SPAM)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING) # <--- THIS KILLS THE TERMINAL SPAM!
logging.getLogger("httpcore").setLevel(logging.WARNING)

if __name__ == '__main__':
    print("🚀 TITANIUM 26.1 (UI POLISHED & SPAM FIXED) IS ONLINE.")
    
    # 1. Start Web Server for Render
    keep_alive()
    
    # 2. Build the Telegram Bot
    app = ApplicationBuilder().token(secret.BOT_TOKEN).build()
    
    # 3. Mount all Handlers from script.py
    app.add_handler(CommandHandler("start", script.start))
    app.add_handler(CommandHandler("alive", script.alive_cmd))
    app.add_handler(CommandHandler("stats", script.stats_cmd))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, script.handle_media))
    app.add_handler(CallbackQueryHandler(script.callback_router))
    
    # 4. Ignite the Engine
    app.run_polling()
