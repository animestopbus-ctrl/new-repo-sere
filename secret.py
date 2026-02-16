import os

# 🚨 CORE CREDENTIALS 🚨
BOT_TOKEN = os.getenv("BOT_TOKEN", "7940504106:AAGo7wvSTxcu8Uq80ltFZ9wpOxZiigHrGTw")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://LastPerson07:N7z0DRcklsZzqCzd@storagebot.5fuk3xn.mongodb.net/?appName=StorageBot")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1633472140"))

LOG_CHANNEL_STR = os.getenv("LOG_CHANNEL_ID", "-1003144372708")
try:
    LOG_CHANNEL_ID = int(LOG_CHANNEL_STR)
except ValueError:
    LOG_CHANNEL_ID = None

# 🛑 FORCE SUBSCRIBE (FSUB) CONFIG 🛑
FSUB_CHANNEL_ID_STR = os.getenv("FSUB_CHANNEL_ID", "-1001557378145") 
try:
    FSUB_CHANNEL_ID = int(FSUB_CHANNEL_ID_STR)
except ValueError:
    FSUB_CHANNEL_ID = None
FSUB_CHANNEL_LINK = os.getenv("FSUB_CHANNEL_LINK", "https://t.me/THEUPDATEDGUYS")

# ⚙️ PERFORMANCE CONFIG ⚙️
WORKERS = int(os.getenv("WORKERS", "10")) # Number of parallel users handled simultaneously

# ================= ASSETS & EFFECTS =================
# 2026 Telegram Message Effects
MESSAGE_EFFECTS = [
    "5104841245755180586", # 🔥 Fire
    "5044134455711629726", # ❤️ Heart
    "5046509860389126442", # 🎉 Party
    "5107584321108051014"  # 👍 Thumbs Up
]

EMOJIS = ["🌟", "🔥", "🎉", "⚡", "🏆", "💎", "💯", "😎", "✨", "🚀"]

LOADING_STICKERS = [
    "CAACAgUAAxkBAAEQLstpXRZxNxFMteYSkppBZ63fuBhVtQACFBgAAtDQQVbGUaezY8jttzgE",
    "CAACAgIAAxkBAAEQh0Vpkr5IZlLv91IqBxjc-ZjMIW0JeQACEI0AAv5fcEtLVL-tOoN-qDoE",
    "CAACAgUAAxkBAAEQh0Npkr4_7PwIgwzNtlgWFZgln6HX9QACjiQAAkgC0Fe1pmm8vcmK9DoE",
    "CAACAgIAAxkBAAEQh0Fpkr4yhjz_V-ulAc3-RxoAASt0cCAAAuNuAAK1NYBLhfPrulNjzWY6BA",
    "CAACAgIAAxkBAAEQMCBpXe5yQV2dAAH9B9ijN5mQH6UuM54AAteBAAL18UBI0d94BVfSNXY4BA"
]

IMAGE_LINKS = [
    "https://images.unsplash.com/photo-1519638399535-1b036603ac77?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8YW5pbWV8ZW58MHx8MHx8fDA%3D", "https://images.unsplash.com/photo-1528360983277-13d401cdc186?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8NHx8YW5pbWV8ZW58MHx8MHx8fDA%3D", 
    "https://images.unsplash.com/photo-1640903581708-8d491706515b?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Nnx8YW5pbWV8ZW58MHx8MHx8fDA%3D", "https://plus.unsplash.com/premium_photo-1674718013659-6930c469e641?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTN8fGFuaW1lfGVufDB8fDB8fHww", 
    "https://images.unsplash.com/photo-1601850494422-3cf14624b0b3?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTZ8fGFuaW1lfGVufDB8fDB8fHww", 
]

# ================= API KEYS & MAPS =================
TMDB_KEYS = ['fb7bb23f03b6994dafc674c074d01761', 'e55425032d3d0f371fc776f302e7c09b', '8301a21598f8b45668d5711a814f01f6', '8cf43ad9c085135b9479ad5cf6bbcbda', 'da63548086e399ffc910fbc08526df05', '13e53ff644a8bd4ba37b3e1044ad24f3', '269890f657dddf4635473cf4cf456576', 'a2f888b27315e62e471b2d587048f32e', '8476a7ab80ad76f0936744df0430e67c', '5622cafbfe8f8cfe358a29c53e19bba0', 'ae4bd1b6fce2a5648671bfc171d15ba4', '257654f35e3dff105574f97fb4b97035', '2f4038e83265214a0dcd6ec2eb3276f5', '9e43f45f94705cc8e1d5a0400d19a7b7', 'af6887753365e14160254ac7f4345dd2', '06f10fc8741a672af455421c239a1ffc', '09ad8ace66eec34302943272db0e8d2c']
OMDB_KEYS = ['4b447405', 'eb0c0475', '7776cbde', 'ff28f90b', '6c3a2d45', 'b07b58c8', 'ad04b643', 'a95b5205', '777d9323', '2c2c3314', 'b5cff164', '89a9f57d', '73a9858a', 'efbd8357']
TMDB_GENRES = {28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western", 10759: "Action & Adv", 10762: "Kids", 10763: "News", 10764: "Reality", 10765: "Sci-Fi & Fantasy"}
LANG_MAP = {'hi': 'Hindi', 'en': 'English', 'ja': 'Japanese', 'ta': 'Tamil', 'te': 'Telugu', 'ml': 'Malayalam', 'kn': 'Kannada', 'mr': 'Marathi', 'gu': 'Gujarati', 'ko': 'Korean', 'es': 'Spanish', 'fr': 'French', 'ru': 'Russian', 'zh': 'Chinese', 'th': 'Thai', 'in': 'Indonesian', 'vi': 'Vietnamese'}

START_TEXT = """<b><u><blockquote>The Updated Renamer 😎</blockquote></u></b>

<b>Welcome, {name}! ⚡️</b>
I am the most advanced Media AI on Telegram. 

<b>Core Capabilities:</b>
├ 🎬 <b>Precision Extraction:</b> Pulls high-fidelity IMDb & TMDB data.
├ ✨ <b>Smart Recognition:</b> Auto-detects Anime, K-Dramas, & Global Cinema.
├ 🔊 <b>Deep Scanning:</b> Pinpoints exact audio languages & true pixel resolution.
╰ 💎 <b>Artwork Preservation:</b> Retains pristine HD posters and media thumbnails.

<i>Drop any raw video file or document below to initiate the engine.</i>"""

HELP_TEXT = """<b><u><blockquote>The Updated Renamer 😎</blockquote></u></b>

<b>🛠️ HOW TO USE THE ENGINE</b>

1️⃣ <b>Send or Forward</b> any raw movie, series, or anime file to me.
2️⃣ I will aggressively strip out garbage tags from the file.
3️⃣ The Omni-Search engine scans 4 different global databases for a match.
4️⃣ I generate a beautiful, categorized layout and send the file back to you with its original HD thumbnail perfectly intact!

<i>💡 <b>Pro Tip:</b> If the AI catches the wrong movie, tap the "🔄 RE-VERIFY" button!</i>"""

