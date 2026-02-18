import os
import math
import re
import random
import logging
import requests
import tempfile
import time
import asyncio
from guessit import guessit
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from telegram import Update, ReactionTypeEmoji, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, WebAppInfo
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest
import secret
from database.db import db
import admin
from filetolink import timer
import fsub 

# 🔥 DYNAMIC DOMAIN ENGINE
DOMAIN = os.getenv("RENDER_EXTERNAL_URL", os.getenv("WEB_URL", "https://new-repo-sere.onrender.com")).rstrip('/')

# 🛡️ ANTI-SPAM CACHE (Memory)
SPAM_CACHE = {}

# ================= UTILITIES =================
async def get_img():
    db_img = await db.get_bot_image()
    return db_img if db_img else random.choice(secret.IMAGE_LINKS)

def esc(text):
    if not text or str(text).lower() in ['none', 'nan', 'null']: return "N/A"
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def format_size(size_bytes):
    if size_bytes == 0: return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

def pre_clean_filename(filename):
    f = str(filename)
    f = re.sub(r'@[a-zA-Z0-9_]+', '', f)
    f = re.sub(r'(?i)DA Rips', '', f)
    f = re.sub(r'(?i)t\.me/[a-zA-Z0-9_]+', '', f)
    f = re.sub(r'\[.*?\]', '', f)
    f = re.sub(r'[\.\_]+', ' ', f)
    return f.strip()

def detect_languages(filename, guessit_langs):
    found_langs = []
    fname_lower = filename.lower()
    is_esub = 'esub' in fname_lower or 'e-sub' in fname_lower
    
    if guessit_langs:
        if not isinstance(guessit_langs, list): guessit_langs = [guessit_langs]
        for l in guessit_langs:
            lang_str = str(l).lower()
            if lang_str in ['es', 'spanish'] and is_esub and 'spanish' not in fname_lower: continue
            found_langs.append(secret.LANG_MAP.get(lang_str, lang_str.capitalize()))
            
    if 'dual' in fname_lower: found_langs.append('Dual Audio')
    if 'multi' in fname_lower: found_langs.append('Multi Audio')
    if 'hin' in fname_lower and 'Hindi' not in found_langs: found_langs.append('Hindi')
    if 'tam' in fname_lower and 'Tamil' not in found_langs: found_langs.append('Tamil')
    if 'tel' in fname_lower and 'Telugu' not in found_langs: found_langs.append('Telugu')
    if 'kor' in fname_lower and 'Korean' not in found_langs: found_langs.append('Korean')
    if 'eng' in fname_lower and 'English' not in found_langs: found_langs.append('English')
    
    unique_langs = list(dict.fromkeys(found_langs))
    if not unique_langs: return "Unknown"
    return " & ".join(unique_langs)

async def get_real_resolution(file_id, context):
    try:
        tg_file = await context.bot.get_file(file_id)
        file_url = f"https://api.telegram.org/file/bot{secret.BOT_TOKEN}/{tg_file.file_path}"
        chunk = requests.get(file_url, headers={"Range": "bytes=0-1048576"}, timeout=10).content
        with tempfile.NamedTemporaryFile(suffix=".mkv", delete=False) as tmp:
            tmp.write(chunk)
            tmp_path = tmp.name
        parser = createParser(tmp_path)
        res_display = None
        if parser:
            with parser:
                meta = extractMetadata(parser)
                if meta:
                    w, h = meta.get('width'), meta.get('height')
                    if w >= 3800 or h >= 2100: res_display = "4K (2160p)"
                    elif w >= 2500 or h >= 1400: res_display = "2K (1440p)"
                    elif w >= 1900 or h >= 1000: res_display = "FHD (1080p)"
                    elif w >= 1200 or h >= 700: res_display = "HD (720p)"
                    elif w >= 800 or h >= 480: res_display = "SD (480p)"
                    else: res_display = f"{w}x{h}p"
        os.unlink(tmp_path)
        return res_display
    except: return None

def fetch_smart_metadata(title, year, original_filename):
    tm_key = random.choice(secret.TMDB_KEYS)
    om_key = random.choice(secret.OMDB_KEYS)
    query = title.strip()
    data = {"title": title, "rating": "N/A", "genres": "Misc", "date": "N/A", "type": "movie"}
    is_anime_hint = 'anime' in original_filename.lower() or 'judas' in original_filename.lower()

    try:
        url = f"https://api.themoviedb.org/3/search/multi?api_key={tm_key}&query={requests.utils.quote(query)}"
        res = requests.get(url, timeout=5).json()
        if res.get('results'):
            best_item = res['results'][0] 
            if year:
                for item in res['results']:
                    item_date = item.get('release_date') or item.get('first_air_date') or ""
                    if str(year) in item_date:
                        best_item = item
                        break
            data['type'] = 'series' if best_item.get('media_type') == 'tv' else 'movie'
            genre_list = [secret.TMDB_GENRES.get(g_id) for g_id in best_item.get('genre_ids', []) if g_id in secret.TMDB_GENRES]
            if genre_list: data['genres'] = ", ".join(genre_list[:3])
            
            country = best_item.get('origin_country', [''])[0] if best_item.get('origin_country') else ''
            language = best_item.get('original_language', '')
            is_animation = 16 in best_item.get('genre_ids', [])
            
            if is_animation and (country == 'JP' or language == 'ja'): data['type'] = 'anime'
            elif data['type'] == 'series':
                if country == 'KR' or language == 'ko': data['type'] = 'kdrama'
                elif country == 'CN' or language == 'zh': data['type'] = 'cdrama'
                elif country == 'JP' or language == 'ja': data['type'] = 'jdrama'
            elif data['type'] == 'movie':
                if country == 'IN' or language in ['hi', 'ta', 'te', 'ml']: data['type'] = 'indian'
                elif country == 'KR' or language == 'ko': data['type'] = 'kmovie'
                elif country == 'JP' or language == 'ja': data['type'] = 'jmovie'
                
            data['title'] = best_item.get('title') or best_item.get('name') or title
            data['rating'] = f"{round(best_item.get('vote_average', 0), 1)} ⭐" if best_item.get('vote_average') else "N/A"
            data['date'] = (best_item.get('release_date') or best_item.get('first_air_date') or "N/A")[:4]
    except: pass

    if data['rating'] == 'N/A' and data['type'] in ['series', 'kdrama', 'cdrama', 'jdrama']:
        try:
            res = requests.get(f"https://api.tvmaze.com/singlesearch/shows?q={requests.utils.quote(query)}", timeout=5).json()
            if res:
                data['title'] = res.get('name', data['title'])
                if res.get('rating', {}).get('average'): data['rating'] = f"{res['rating']['average']} ⭐"
                data['date'] = res.get('premiered', data['date'])[:4] if res.get('premiered') else data['date']
                if res.get('genres'): data['genres'] = ", ".join(res['genres'][:3])
        except: pass

    if data['type'] == 'anime' or is_anime_hint:
        try:
            res = requests.get(f"https://api.jikan.moe/v4/anime?q={requests.utils.quote(query)}&limit=1", timeout=5).json()
            if res.get('data'):
                anime = res['data'][0]
                data['title'] = anime.get('title_english') or anime.get('title') or data['title']
                data['rating'] = f"{anime.get('score', 'N/A')} ⭐"
                data['date'] = str(anime.get('year') or data['date'])
                genres = [g['name'] for g in anime.get('genres', [])]
                if genres: data['genres'] = ", ".join(genres[:3])
                data['type'] = 'anime'
                return data
        except: pass
    return data

async def safe_reply(msg_obj, text, **kwargs):
    """Attempts to send message with effect. Falls back to normal text if Telegram rejects the effect ID."""
    try:
        return await msg_obj.reply_text(text, **kwargs)
    except BadRequest as e:
        if "effect" in str(e).lower() or "invalid" in str(e).lower():
            kwargs.pop('message_effect_id', None)
            return await msg_obj.reply_text(text, **kwargs)
        raise e

# ================= KEYBOARDS =================
def get_main_menu_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 JOIN OFFICIAL CHANNEL", url="https://t.me/THEUPDATEDGUYS", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("📚 How to Use", callback_data="help_menu", api_kwargs={"style": "danger"}), InlineKeyboardButton("⚙️ Settings", callback_data="settings_menu", api_kwargs={"style": "success"})],
        [InlineKeyboardButton("👨‍💻 Developer", web_app=WebAppInfo(url="https://github.com/LastPerson07")), InlineKeyboardButton("🤝 Affiliated Dev", web_app=WebAppInfo(url="https://github.com/abhinai2244"))],
        [InlineKeyboardButton("ℹ️ Bot Info", callback_data="info_menu", api_kwargs={"style": "danger"})]
    ])

def get_help_menu_markup():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu", api_kwargs={"style": "danger"})]])

# 🔥 BUG FIX: Self-Locking Button System added here
def get_media_markup(title, is_generated=False):
    imdb_url = f"https://www.imdb.com/find/?q={requests.utils.quote(title.replace(' ', '+'))}"
    buttons = []
    
    # If links are generated, turn the button gray and disable it.
    if not is_generated:
        buttons.append([InlineKeyboardButton("🔗 Generate Direct Links", callback_data="ask_timer", api_kwargs={"style": "primary"})])
    else:
        buttons.append([InlineKeyboardButton("✅ Links Generated Below", callback_data="ignore", api_kwargs={"style": "danger"})])
        
    buttons.append([InlineKeyboardButton("🎬 IMDB INFO", url=imdb_url, api_kwargs={"style": "danger"}), InlineKeyboardButton("📢 JOIN CHANNEL", url="https://t.me/THEUPDATEDGUYS", api_kwargs={"style": "success"})])
    
    return InlineKeyboardMarkup(buttons)

def get_timer_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🕒 1 Hour", callback_data="timer_1", api_kwargs={"style": "primary"}), InlineKeyboardButton("🕒 6 Hours", callback_data="timer_6", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("🕒 12 Hours", callback_data="timer_12", api_kwargs={"style": "primary"}), InlineKeyboardButton("🕒 24 Hours", callback_data="timer_24", api_kwargs={"style": "danger"})],
        [InlineKeyboardButton("⬅️ Cancel", callback_data="cancel_timer", api_kwargs={"style": "danger"})]
    ])

def get_url_markup(hash_id):
    dl_url = f"{DOMAIN}/dl/{hash_id}"
    watch_url = f"{DOMAIN}/watch/{hash_id}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 FAST DOWNLOAD", url=dl_url, api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("🖥️ INSTANT STREAM", web_app=WebAppInfo(url=watch_url))]
    ])

async def send_recon_log(user, context):
    if not secret.LOG_CHANNEL_ID: return
    username_fmt = f"@{user.username}" if user.username else "N/A"
    last_name = user.last_name if user.last_name else "N/A"
    log_text = f"🆕 <b>NEW USER DETECTED</b>\n\n<blockquote>👤 <b>First Name:</b> {esc(user.first_name)}\n🗣 <b>Last Name:</b> {esc(last_name)}\n🔗 <b>Username:</b> {esc(username_fmt)}\n🆔 <b>User ID:</b> <code>{user.id}</code>\n🌐 <b>Language:</b> {esc(user.language_code)}</blockquote>"
    try:
        photos = await context.bot.get_user_profile_photos(user.id)
        if photos.total_count > 0: await context.bot.send_photo(chat_id=secret.LOG_CHANNEL_ID, photo=photos.photos[0][-1].file_id, caption=log_text, parse_mode=ParseMode.HTML, disable_notification=True)
        else: await context.bot.send_message(chat_id=secret.LOG_CHANNEL_ID, text=log_text, parse_mode=ParseMode.HTML, disable_notification=True)
    except Exception as e: pass

# ================= UTILITY & DIAGNOSTIC COMMANDS =================
async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass
    start_t = time.time()
    msg = await update.message.reply_text("📶 Pinging Server...", parse_mode=ParseMode.HTML)
    end_t = time.time()
    await msg.edit_text(f"🏓 <b>Pong!</b>\n<blockquote>Latency: <code>{round((end_t - start_t) * 1000)}ms</code></blockquote>", parse_mode=ParseMode.HTML)

async def id_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass
    text = f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n<blockquote>👤 <b>Your User ID:</b> <code>{update.effective_user.id}</code>\n💬 <b>Chat ID:</b> <code>{update.effective_chat.id}</code></blockquote>"
    await safe_reply(update.message, text, parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass
    text = f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n<blockquote>🟢 <b>SYSTEM STATUS:</b> Online\n⏱ <b>Uptime:</b> <code>{admin.get_uptime()}</code>\n⚙️ <b>Workers:</b> {secret.WORKERS}</blockquote>"
    await safe_reply(update.message, text, parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))

async def alive_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass
    try: await update.message.reply_sticker(sticker=random.choice(secret.LOADING_STICKERS))
    except: pass
    await safe_reply(update.message, "<b>Yes darling, I am alive. Don't worry! 😘</b>", parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass
    await safe_reply(update.message, "<b>🚀 Send me any Movie, Series, or Anime file and I will process it instantly!</b>", parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    user = update.effective_user
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass

    if await db.get_maintenance() and user.id != secret.ADMIN_ID:
        return await update.message.reply_text("🚧 <b>MAINTENANCE MODE</b>\n\n<blockquote>The bot is currently undergoing upgrades. Please try again later.</blockquote>", parse_mode=ParseMode.HTML)

    is_new = await db.add_user(user.id, user.first_name, user.username)
    if is_new: await send_recon_log(user, context)
    
    if not await fsub.is_user_subscribed(context.bot, user.id):
        img = await get_img()
        sent_msg = await update.message.reply_photo(
            photo=img, 
            caption=fsub.get_fsub_text(esc(user.first_name)), 
            reply_markup=fsub.get_fsub_markup(), 
            parse_mode=ParseMode.HTML
        )
        try: await sent_msg.set_reaction(reaction=ReactionTypeEmoji("🛑"), is_big=True)
        except: pass
        return
    
    try:
        sticker_msg = await update.message.reply_sticker(sticker=random.choice(secret.LOADING_STICKERS))
        await asyncio.sleep(1.2)
        await sticker_msg.delete()
    except: pass

    img = await get_img()
    sent_msg = await update.message.reply_photo(
        photo=img, 
        caption=secret.START_TEXT.format(name=esc(user.first_name)), 
        parse_mode=ParseMode.HTML, 
        reply_markup=get_main_menu_markup()
    )
    try: await sent_msg.set_reaction(reaction=ReactionTypeEmoji("⚡"), is_big=True)
    except: pass

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass
    img = await get_img()
    sent_msg = await update.message.reply_photo(photo=img, caption=secret.HELP_TEXT, parse_mode=ParseMode.HTML, reply_markup=get_help_menu_markup())
    try: await sent_msg.set_reaction(reaction=ReactionTypeEmoji("📚"), is_big=True)
    except: pass

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass
    info_text = "<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n🤖 <b>ABOUT TITANIUM ENGINE</b>\n\nI am a state-of-the-art Media AI built for massive speed and precision.\n\n<blockquote>🟢 <b>Version:</b> 39.0 Pro (MTProto 4GB Streaming)\n👨‍💻 <b>Developer:</b> LastPerson07\n📚 <b>Framework:</b> Python Telegram Bot & Pyrogram\n🗄️ <b>Database:</b> MongoDB Async</blockquote>\n\n<i>For business inquiries or custom bot development, contact the owner.</i>"
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("👨‍💻 Contact Dev", url="https://t.me/LastPerson07", api_kwargs={"style": "primary"})]])
    img = await get_img()
    sent_msg = await update.message.reply_photo(photo=img, caption=info_text, parse_mode=ParseMode.HTML, reply_markup=markup)
    try: await sent_msg.set_reaction(reaction=ReactionTypeEmoji("ℹ️"), is_big=True)
    except: pass

async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass
    user_id = update.effective_user.id
    user_data = await db.col.find_one({'id': int(user_id)})
    if not user_data: return await update.message.reply_text("❌ Please send /start first to register your account.")
    is_prem = user_data.get('is_premium', False)
    status = "💎 PREMIUM VIP" if is_prem else "🆓 FREE TIER"
    text = f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n⚙️ <b>YOUR ACCOUNT DASHBOARD</b>\n\n<blockquote>👤 <b>ID:</b> <code>{user_id}</code>\n📊 <b>Tier:</b> {status}\n📈 <b>Daily Limit:</b> {user_data.get('daily_usage', 0) if user_data else 0}/10 Files\n📁 <b>Total Lifetime:</b> {user_data.get('files_processed', 0) if user_data else 0} Files\n📝 <b>Caption:</b> {esc(user_data.get('caption', 'None (Default)') if user_data else 'None')}</blockquote>"
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("💎 Buy Premium", url="https://t.me/LastPerson07", api_kwargs={"style": "success"})], [InlineKeyboardButton("⬅️ Back", callback_data="main_menu", api_kwargs={"style": "danger"})]])
    img = await get_img()
    sent_msg = await update.message.reply_photo(photo=img, caption=text, parse_mode=ParseMode.HTML, reply_markup=markup)
    try: await sent_msg.set_reaction(reaction=ReactionTypeEmoji("⚙️"), is_big=True)
    except: pass

async def feedback_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass
    feedback_text = " ".join(context.args)
    if not feedback_text: return await update.message.reply_text("❌ <b>Format:</b> <code>/feedback [Type your message here]</code>\n\n<i>Example: /feedback The bot isn't catching Hindi language correctly.</i>", parse_mode=ParseMode.HTML)
    admin_msg = f"📬 <b>NEW USER FEEDBACK</b>\n\n<blockquote>👤 <b>From:</b> {esc(user.first_name)} [<code>{user.id}</code>]\n💬 <b>Message:</b> {esc(feedback_text)}</blockquote>"
    try:
        await context.bot.send_message(chat_id=secret.ADMIN_ID, text=admin_msg, parse_mode=ParseMode.HTML)
        await safe_reply(update.message, "✅ <b>Feedback Sent Successfully!</b>\n<blockquote>Thank you for helping us improve the engine.</blockquote>", parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))
    except Exception: await update.message.reply_text("❌ Failed to send feedback to the developer.", parse_mode=ParseMode.HTML)

# ================= PREMIUM COMMANDS =================
async def set_cap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass
    if not await db.check_premium_status(user_id): return await update.message.reply_text("💎 <b>PREMIUM FEATURE:</b>\n<blockquote>You must be a Premium user to set custom captions!</blockquote>", parse_mode=ParseMode.HTML)
    custom_text = " ".join(context.args)
    if not custom_text: return await update.message.reply_text("❌ <b>Format:</b> <code>/set_caption Your custom text here</code>", parse_mode=ParseMode.HTML)
    await db.set_caption(user_id, custom_text)
    await safe_reply(update.message, "✅ <b>SUCCESS:</b> Custom caption saved!\n<blockquote>It will now appear at the bottom of your files.</blockquote>", parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))

async def del_cap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass
    await db.del_caption(update.effective_user.id)
    await safe_reply(update.message, "🗑️ Custom caption removed. Reverted to default.", parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))

async def my_cap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass
    cap = await db.get_caption(update.effective_user.id)
    if cap: await safe_reply(update.message, f"📝 <b>Your Custom Caption:</b>\n\n<blockquote>{cap}</blockquote>", parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))
    else: await update.message.reply_text("You have no custom caption set. Using default.", parse_mode=ParseMode.HTML)

# ================= MEDIA ENGINE =================
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    msg = query.message if query else update.message
    if not msg: return
    user = update.effective_user

    if await db.get_maintenance() and user.id != secret.ADMIN_ID:
        return await msg.reply_text("🚧 <b>MAINTENANCE MODE</b>\n\n<blockquote>The bot is currently undergoing upgrades. Please try again later.</blockquote>", parse_mode=ParseMode.HTML)

    if not await fsub.is_user_subscribed(context.bot, user.id):
        img = await get_img()
        sent_msg = await msg.reply_photo(
            photo=img, 
            caption=fsub.get_fsub_text(esc(user.first_name)), 
            reply_markup=fsub.get_fsub_markup(), 
            parse_mode=ParseMode.HTML
        )
        try: await sent_msg.set_reaction(reaction=ReactionTypeEmoji("🛑"), is_big=True)
        except: pass
        return

    if user:
        if await db.is_banned(user.id): return await msg.reply_text("🔨 <b>ACCESS DENIED:</b> You are permanently banned.", parse_mode=ParseMode.HTML)
        if await db.check_limit(user.id): return await msg.reply_text("⚠️ <b>DAILY LIMIT REACHED!</b>\n<blockquote>You used your 10 free renames today.\n<i>Upgrade to Premium for unlimited!</i></blockquote>", parse_mode=ParseMode.HTML)

    media = msg.document or msg.video
    if not media: return

    if update.message:
        try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
        except: pass

    loading_sticker = None
    if not query:
        try:
            loading_sticker = await msg.reply_sticker(sticker=random.choice(secret.LOADING_STICKERS))
            await asyncio.sleep(1.2)
        except: pass

    original_name = getattr(media, 'file_name', 'Unknown_File.mp4')
    clean_original = pre_clean_filename(original_name)
    parsed = guessit(clean_original)
    
    search_q = parsed.get('title', 'Unknown')
    search_year = parsed.get('year') 
    
    info = fetch_smart_metadata(search_q, search_year, original_name)
    size = format_size(getattr(media, 'file_size', 0))
    audio = detect_languages(original_name, parsed.get('language'))
    real_res = await get_real_resolution(media.file_id, context)
    if not real_res:
        g_res = parsed.get('screen_size')
        real_res = f"FHD (1080p)" if str(g_res) == '1080p' else (f"HD (720p)" if str(g_res) == '720p' else str(g_res or 'FHD (1080p)'))

    header_map = {
        'kdrama': ("🎭 <b>𝗞-𝗗𝗥𝗔𝗠𝗔 𝗘𝗗𝗜𝗧𝗜𝗢𝗡</b> 🎭", "🍿", "🇰🇷"),
        'cdrama': ("🏮 <b>𝗖-𝗗𝗥𝗔𝗠𝗔 𝗘𝗗𝗜𝗧𝗜𝗢𝗡</b> 🏮", "🍿", "🇨🇳"),
        'jdrama': ("🎌 <b>𝗝-𝗗𝗥𝗔𝗠𝗔 𝗘𝗗𝗜𝗧𝗜𝗢𝗡</b> 🎌", "🍿", "🇯🇵"),
        'indian': ("🪷 <b>𝗜𝗡𝗗𝗜𝗔𝗡 𝗖𝗜𝗡𝗘𝗠𝗔</b> 🪷", "🎥", "🇮🇳"),
        'kmovie': ("🎬 <b>𝗞𝗢𝗥𝗘𝗔𝗡 𝗠𝗢𝗩𝗜𝗘</b> 🎬", "🎥", "🇰🇷"),
        'jmovie': ("👹 <b>𝗝𝗔𝗣𝗔𝗡𝗘𝗦𝗘 𝗠𝗢𝗩𝗜𝗘</b> 👹", "🎥", "🇯🇵"),
        'anime': ("✨ <b>𝗔𝗡𝗜𝗠𝗘 𝗘𝗗𝗜𝗧𝗜𝗢𝗡</b> ✨", "⛩️", "🎌"),
        'series': ("📺 <b>𝗦𝗘𝗥𝗜𝗘𝗦 𝗘𝗗𝗜𝗧𝗜𝗢𝗡</b> 📺", "🍿", "⭐"),
        'movie': ("🎬 <b>𝗠𝗢𝗩𝗜𝗘 𝗘𝗗𝗜𝗧𝗜𝗢𝗡</b> 🎬", "🎥", "⭐")
    }
    h_data = header_map.get(info['type'], header_map['movie'])
    
    custom_footer = "⚡ <b>Pᴏᴡᴇʀᴇᴅ Bʏ :</b> @THEUPDATEDGUYS"
    if await db.check_premium_status(user.id):
        user_cap = await db.get_caption(user.id)
        if user_cap: custom_footer = user_cap

    caption = f"""
{h_data[0]}
<blockquote><b>{esc(info['title'])}</b></blockquote>

{h_data[1]} <b>Media Details:</b>
├ {h_data[2]} <b>Rating   :</b> <code>{esc(info['rating'])}</code>
├ 🎭 <b>Genres   :</b> <i>{esc(info['genres'])}</i>
├ 📅 <b>Release  :</b> <code>{esc(info['date'])}</code>
├ 🔊 <b>Audio    :</b> <code>{esc(audio)}</code>
├ 🖥️ <b>Quality  :</b> <code>{esc(real_res)}</code>
╰ 💾 <b>Size     :</b> <code>{esc(size)}</code>

{custom_footer}
"""
    markup = get_media_markup(info['title'])

    if loading_sticker:
        try: await loading_sticker.delete()
        except: pass

    if query:
        try: await query.edit_message_caption(caption=caption, parse_mode=ParseMode.HTML, reply_markup=markup)
        except BadRequest as e:
            if "not modified" not in str(e).lower(): logging.error(f"Edit error: {e}")
    else:
        sent_msg = await context.bot.copy_message(chat_id=msg.chat.id, from_chat_id=msg.chat.id, message_id=msg.message_id, caption=caption, parse_mode=ParseMode.HTML, reply_markup=markup)
        try: await context.bot.set_message_reaction(chat_id=msg.chat.id, message_id=sent_msg.message_id, reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
        except: pass

        if user:
            await db.add_traffic(user.id)
            if secret.LOG_CHANNEL_ID:
                try:
                    log_cap = f"📁 <b>FILE PROCESSED</b>\n\n<blockquote>👤 <b>User:</b> {esc(user.first_name)} [<code>{user.id}</code>]\n🎬 <b>Title:</b> {esc(info['title'])}\n💾 <b>Size:</b> {size}</blockquote>"
                    await context.bot.copy_message(chat_id=secret.LOG_CHANNEL_ID, from_chat_id=msg.chat.id, message_id=msg.message_id, caption=log_cap, parse_mode=ParseMode.HTML, disable_notification=True)
                except Exception: pass

# ================= CALLBACK ROUTER =================
async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    # 🔥 ANTI-SPAM LOGIC: Silently reject rapid double-clicks
    user_id = update.effective_user.id
    now = time.time()
    if query.data in ["ask_timer"] or query.data.startswith("timer_"):
        if user_id in SPAM_CACHE and now - SPAM_CACHE[user_id] < 3:
            return await query.answer("⚠️ Please wait a moment... do not spam!", show_alert=True)
        SPAM_CACHE[user_id] = now

    await query.answer() 
    data = query.data
    img = await get_img()
    
    # Empty callback for the gray "Links Generated Below" button
    if data == "ignore":
        return

    if data == "check_fsub":
        if await fsub.is_user_subscribed(context.bot, update.effective_user.id):
            await query.answer("✅ Verified! Welcome to the bot.", show_alert=True)
            await query.message.delete()
            sent_msg = await context.bot.send_photo(
                chat_id=query.message.chat.id,
                photo=img, 
                caption=secret.START_TEXT.format(name=esc(update.effective_user.first_name)), 
                parse_mode=ParseMode.HTML, 
                reply_markup=get_main_menu_markup()
            )
            try: await sent_msg.set_reaction(reaction=ReactionTypeEmoji("⚡"), is_big=True)
            except: pass
        else:
            await query.answer("❌ You haven't joined the channel yet! Please join first.", show_alert=True)
        return

    if data == "ask_timer":
        media = query.message.document or query.message.video
        if not media: return await query.answer("❌ No file detected.", show_alert=True)
        await query.edit_message_reply_markup(reply_markup=get_timer_markup())

    elif data == "cancel_timer":
        media = query.message.document or query.message.video
        file_name = getattr(media, 'file_name', 'Unknown') if media else 'Unknown'
        await query.edit_message_reply_markup(reply_markup=get_media_markup(file_name))

    elif data.startswith("timer_"):
        hours = int(data.split("_")[1])
        media = query.message.document or query.message.video
        if not media: return await query.answer("❌ File not found.", show_alert=True)
        
        await query.answer("🔐 Generating 4GB MTProto Link...", show_alert=True)
        
        file_hash = timer.generate_hash()
        expires_at = timer.get_expiry_date(hours)
        file_name = getattr(media, 'file_name', 'Unknown.mkv')
        size = format_size(getattr(media, 'file_size', 0))
        
        chat_id = query.message.chat.id
        message_id = query.message.message_id
        await db.save_link(file_hash, chat_id, message_id, file_name, size, expires_at)
        
        link_text = (
            f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n"
            f"✅ <b>LINKS GENERATED SUCCESSFULLY</b>\n\n"
            f"<blockquote>🎬 <b>File:</b> <code>{esc(file_name)}</code>\n"
            f"💾 <b>Size:</b> <code>{esc(size)}</code>\n"
            f"⏳ <b>Valid For:</b> {hours} Hours</blockquote>\n\n"
            f"<i>⚠️ Do not share these links. They will auto-delete.</i>"
        )
        
        # 🔥 BUG FIX: Edit the original message to remove the "Generate Links" button
        await query.edit_message_reply_markup(reply_markup=get_media_markup(file_name, is_generated=True))
        
        await safe_reply(query.message, text=link_text, parse_mode=ParseMode.HTML, reply_markup=get_url_markup(file_hash), disable_web_page_preview=True, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))

    elif data == "help_menu":
        try: await query.edit_message_media(media=InputMediaPhoto(media=img, caption=secret.HELP_TEXT, parse_mode=ParseMode.HTML), reply_markup=get_help_menu_markup())
        except BadRequest: pass
    elif data == "info_menu":
        info_text = "<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n🤖 <b>ABOUT TITANIUM ENGINE</b>\n\nI am a state-of-the-art Media AI built for massive speed and precision.\n\n<blockquote>🟢 <b>Version:</b> 39.0 Pro (MTProto 4GB Streaming)\n👨‍💻 <b>Developer:</b> LastPerson07\n📚 <b>Framework:</b> Python Telegram Bot & Pyrogram\n🗄️ <b>Database:</b> MongoDB Async</blockquote>\n\n<i>For business inquiries or custom bot development, contact the owner.</i>"
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("👨‍💻 Contact Dev", url="https://t.me/LastPerson07", api_kwargs={"style": "primary"})], [InlineKeyboardButton("⬅️ Back", callback_data="main_menu", api_kwargs={"style": "danger"})]])
        try: await query.edit_message_media(media=InputMediaPhoto(media=img, caption=info_text, parse_mode=ParseMode.HTML), reply_markup=markup)
        except BadRequest: pass
    elif data == "settings_menu":
        user_id = update.effective_user.id
        user_data = await db.col.find_one({'id': int(user_id)})
        is_prem = user_data.get('is_premium', False) if user_data else False
        status = "💎 PREMIUM VIP" if is_prem else "🆓 FREE TIER"
        text = f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n⚙️ <b>YOUR ACCOUNT DASHBOARD</b>\n\n<blockquote>👤 <b>ID:</b> <code>{user_id}</code>\n📊 <b>Tier:</b> {status}\n📈 <b>Daily Limit:</b> {user_data.get('daily_usage', 0) if user_data else 0}/10 Files\n📁 <b>Total Lifetime:</b> {user_data.get('files_processed', 0) if user_data else 0} Files\n📝 <b>Caption:</b> {esc(user_data.get('caption', 'None (Default)') if user_data else 'None')}</blockquote>"
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("💎 Buy Premium", url="https://t.me/LastPerson07", api_kwargs={"style": "success"})], [InlineKeyboardButton("⬅️ Back", callback_data="main_menu", api_kwargs={"style": "danger"})]])
        try: await query.edit_message_media(media=InputMediaPhoto(media=img, caption=text, parse_mode=ParseMode.HTML), reply_markup=markup)
        except BadRequest: pass
    elif data == "main_menu":
        try: await query.edit_message_media(media=InputMediaPhoto(media=img, caption=secret.START_TEXT.format(name=esc(update.effective_user.first_name)), parse_mode=ParseMode.HTML), reply_markup=get_main_menu_markup())
        except BadRequest: pass
