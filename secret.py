import os

# 🚨 CORE CREDENTIALS 🚨
BOT_TOKEN = os.getenv("BOT_TOKEN", "8599301566:AAGAVXJN7hi-LxklclAMPQMRZt6aPN6v1aw")
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://LastPerson07:N7z0DRcklsZzqCzd@storagebot.5fuk3xn.mongodb.net/?appName=StorageBot")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1633472140"))

# 🔥 REQUIRED FOR 4GB STREAMING (Get from my.telegram.org)
API_ID = int(os.getenv("API_ID", "20601073")) # REPLACE WITH YOUR API ID
API_HASH = os.getenv("API_HASH", "a99848cf240773df26d3efad8195c194") # REPLACE WITH YOUR API HASH

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

TMDB_KEYS = ['fb7bb23f03b6994dafc674c074d01761','e55425032d3d0f371fc776f302e7c09b','8301a21598f8b45668d5711a814f01f6','8cf43ad9c085135b9479ad5cf6bbcbda','da63548086e399ffc910fbc08526df05','13e53ff644a8bd4ba37b3e1044ad24f3','269890f657dddf4635473cf4cf456576','a2f888b27315e62e471b2d587048f32e','8476a7ab80ad76f0936744df0430e67c','5622cafbfe8f8cfe358a29c53e19bba0','ae4bd1b6fce2a5648671bfc171d15ba4','257654f35e3dff105574f97fb4b97035','2f4038e83265214a0dcd6ec2eb3276f5','9e43f45f94705cc8e1d5a0400d19a7b7','af6887753365e14160254ac7f4345dd2','06f10fc8741a672af455421c239a1ffc','09ad8ace66eec34302943272db0e8d2c']
OMDB_KEYS = ['4b447405','eb0c0475','7776cbde','ff28f90b','6c3a2d45','b07b58c8','ad04b643','a95b5205','777d9323','2c2c3314','b5cff164','89a9f57d','73a9858a','efbd8357']

TMDB_GENRES = {28: "Action", 12: "Adventure", 16: "Animation", 35: "Comedy", 80: "Crime", 99: "Documentary", 18: "Drama", 10751: "Family", 14: "Fantasy", 36: "History", 27: "Horror", 10402: "Music", 9648: "Mystery", 10749: "Romance", 878: "Sci-Fi", 10770: "TV Movie", 53: "Thriller", 10752: "War", 37: "Western", 10759: "Action & Adv", 10762: "Kids", 10763: "News", 10764: "Reality", 10765: "Sci-Fi & Fantasy"}
LANG_MAP = {'hi': 'Hindi', 'en': 'English', 'ja': 'Japanese', 'ta': 'Tamil', 'te': 'Telugu', 'ml': 'Malayalam', 'kn': 'Kannada', 'mr': 'Marathi', 'gu': 'Gujarati', 'ko': 'Korean', 'es': 'Spanish', 'fr': 'French', 'ru': 'Russian', 'zh': 'Chinese', 'th': 'Thai', 'in': 'Indonesian', 'vi': 'Vietnamese'}

START_TEXT = """<b><u><blockquote>The Updated Renamer 😎</blockquote></u></b> <b>Hey {name}! Welcome aboard ⚡️</b> <blockquote>I’m here to make renaming, organizing, and sharing your media simple and hassle-free.</blockquote> <b>What I can do for you:</b> ├ 🎬 <b>Accurate Details:</b> Fetches trusted IMDb & TMDB information. ├ 🔎 <b>Smart Detection:</b> Automatically recognizes Anime, K-Dramas, Movies, and Series. ├ 🎧 <b>Media Analysis:</b> Identifies audio languages and video quality with precision. ├ 🔗 <b>File-to-Link:</b> Instantly converts your files into shareable download links. ╰ 🖼 <b>Clean Results:</b> Keeps posters and thumbnails intact for a polished look."""
HELP_TEXT = """<b><u><blockquote>The Updated Renamer 😎</blockquote></u></b> <b>🛠️ How to Use</b> <blockquote>1️⃣ <b>Send or forward</b> any movie, series, anime, or media file. 2️⃣ I’ll clean unnecessary tags and organize the filename. 3️⃣ Then I search trusted databases to fetch accurate details. 4️⃣ Finally, you’ll receive a neatly renamed file with proper thumbnails — and you can even convert it into a shareable link.</blockquote>"""







