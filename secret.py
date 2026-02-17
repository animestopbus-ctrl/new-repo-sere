import os

# 🚨 CORE CREDENTIALS 🚨
BOT_TOKEN = os.getenv("BOT_TOKEN", "7940504106:AAGo7wvSTxcu8Uq80ltFZ9wpOxZiigHrGTw")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://LastPerson07:N7z0DRcklsZzqCzd@storagebot.5fuk3xn.mongodb.net/?appName=StorageBot")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1633472140"))

# 🔥 REQUIRED FOR 4GB STREAMING (Get from my.telegram.org)
API_ID = int(os.getenv("API_ID", "34857357")) # REPLACE WITH YOUR API ID
API_HASH = os.getenv("API_HASH", "1e8f2a02989b22ef1e55340375bbdaa8") # REPLACE WITH YOUR API HASH

LOG_CHANNEL_STR = os.getenv("LOG_CHANNEL_ID", "-1003144372708")
try: LOG_CHANNEL_ID = int(LOG_CHANNEL_STR)
except ValueError: LOG_CHANNEL_ID = None

FSUB_CHANNEL_ID_STR = os.getenv("FSUB_CHANNEL_ID", "-1001557378145") 
try: FSUB_CHANNEL_ID = int(FSUB_CHANNEL_ID_STR)
except ValueError: FSUB_CHANNEL_ID = None
FSUB_CHANNEL_LINK = os.getenv("FSUB_CHANNEL_LINK", "https://t.me/THEUPDATEDGUYS")

WORKERS = int(os.getenv("WORKERS", "10")) 

WEB_URL = "https://new-repo-sere.onrender.com"

EMOJIS = ["👍", "❤️", "🔥", "🥰", "👏", "🎉", "🤩", "🙏", "👌", "💯", "⚡", "🏆", "🤝", "🫡", "👨‍💻", "👀", "🐳"]
MESSAGE_EFFECTS = [
    "5104841245755180586", # 🔥 Fire
    "5159385139981059251", # ❤️ Heart (NEW FIXED ID)
    "5046509860389126442", # 🎉 Party
    "5107584321108051014"  # 👍 Thumbs Up
]

LOADING_STICKERS = [
    "CAACAgUAAxkBAAEQLstpXRZxNxFMteYSkppBZ63fuBhVtQACFBgAAtDQQVbGUaezY8jttzgE",
    "CAACAgIAAxkBAAEQh0Vpkr5IZlLv91IqBxjc-ZjMIW0JeQACEI0AAv5fcEtLVL-tOoN-qDoE",
    "CAACAgUAAxkBAAEQh0Npkr4_7PwIgwzNtlgWFZgln6HX9QACjiQAAkgC0Fe1pmm8vcmK9DoE",
    "CAACAgIAAxkBAAEQh0Fpkr4yhjz_V-ulAc3-RxoAASt0cCAAAuNuAAK1NYBLhfPrulNjzWY6BA",
    "CAACAgIAAxkBAAEQMCBpXe5yQV2dAAH9B9ijN5mQH6UuM54AAteBAAL18UBI0d94BVfSNXY4BA"
]

IMAGE_LINKS = [
    "https://plus.unsplash.com/premium_photo-1666700698920-d2d2bba589f8?q=80&w=1332&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D", "https://plus.unsplash.com/premium_photo-1675148247638-fb5c8db249a2?q=80&w=1408&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D", 
    "https://images.unsplash.com/photo-1542051841857-5f90071e7989?q=80&w=1170&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D", "https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?q=80&w=1170&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D", 
    "https://images.unsplash.com/photo-1606044466411-207a9a49711f?q=80&w=1170&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D", "https://images.unsplash.com/photo-1564284369929-026ba231f89b?q=80&w=1170&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D", "https://images.unsplash.com/photo-1618588072798-9683fe469847?q=80&w=1170&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D"  
]

TMDB_KEYS = ['fb7bb23f03b6994dafc674c074d01761', 'e55425032d3d0f371fc776f302e7c09b']
OMDB_KEYS = ['4b447405', 'eb0c0475']
TMDB_GENRES = {28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western", 10759: "Action & Adv", 10762: "Kids", 10763: "News", 10764: "Reality", 10765: "Sci-Fi & Fantasy"}
LANG_MAP = {'hi': 'Hindi', 'en': 'English', 'ja': 'Japanese', 'ta': 'Tamil', 'te': 'Telugu', 'ml': 'Malayalam', 'kn': 'Kannada', 'mr': 'Marathi', 'gu': 'Gujarati', 'ko': 'Korean', 'es': 'Spanish', 'fr': 'French', 'ru': 'Russian', 'zh': 'Chinese', 'th': 'Thai', 'in': 'Indonesian', 'vi': 'Vietnamese'}

START_TEXT = """<b><u><blockquote>The Updated Renamer 😎</blockquote></u></b>\n\n<b>Welcome, {name}! ⚡️</b>\n<blockquote>I am the most advanced Media AI on Telegram.</blockquote>\n\n<b>Core Capabilities:</b>\n├ 🎬 <b>Precision Extraction:</b> Pulls high-fidelity IMDb & TMDB data.\n├ ✨ <b>Smart Recognition:</b> Auto-detects Anime, K-Dramas, & Global Cinema.\n├ 🔊 <b>Deep Scanning:</b> Pinpoints exact audio languages & true pixel resolution.\n╰ 💎 <b>Artwork Preservation:</b> Retains pristine HD posters and media thumbnails."""
HELP_TEXT = """<b><u><blockquote>The Updated Renamer 😎</blockquote></u></b>\n\n<b>🛠️ HOW TO USE THE ENGINE</b>\n\n<blockquote>1️⃣ <b>Send or Forward</b> any raw movie, series, or anime file to me.\n2️⃣ I will aggressively strip out garbage tags from the file.\n3️⃣ The Omni-Search engine scans global databases for a match.\n4️⃣ I generate a beautiful layout and send the file back with HD thumbnails.</blockquote>"""


