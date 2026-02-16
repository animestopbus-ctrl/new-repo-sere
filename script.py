import os
import math
import re
import random
import logging
import requests
import tempfile
import time
import datetime
from guessit import guessit

# Hachoir for Resolution
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata

# Telegram Imports
from telegram import Update, ReactionTypeEmoji, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from telegram.error import BadRequest

# Import Secrets & DB
import secret
from database.db import db

# Uptime Tracker
BOT_START_TIME = time.time()

def get_uptime():
    delta = time.time() - BOT_START_TIME
    d = datetime.timedelta(seconds=delta)
    return str(d).split('.')[0] 

# ================= UTILITIES =================
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
    
    # 🔥 ESUB BUG FIX: Prevents "es" from being flagged as Spanish if it's just Esub
    is_esub = 'esub' in fname_lower or 'e-sub' in fname_lower
    
    if guessit_langs:
        if not isinstance(guessit_langs, list): guessit_langs = [guessit_langs]
        for l in guessit_langs:
            lang_str = str(l).lower()
            if lang_str in ['es', 'spanish'] and is_esub and 'spanish' not in fname_lower:
                continue # Ignore false Spanish match
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

# ================= API ENGINE =================
def fetch_smart_metadata(title, year, original_filename, force_reverify=False):
    tm_key = random.choice(secret.TMDB_KEYS)
    om_key = random.choice(secret.OMDB_KEYS)
    query = title.strip()
    
    # 🔥 RE-VERIFY FIX: If re-verify is clicked, we aggressively shorten the query to the first word
    if force_reverify: 
        query = query.split(' ')[0].split('.')[0]

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

# ================= KEYBOARDS =================
def get_main_menu_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 JOIN OFFICIAL CHANNEL", url="https://t.me/THEUPDATEDGUYS", api_kwargs={"style": "primary"})],
        [
            InlineKeyboardButton("📚 How to Use", callback_data="help_menu", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("🤝 Affiliated Dev", web_app={"url": "https://github.com/abhinai2244"}, api_kwargs={"style": "success"})
        ],
        [InlineKeyboardButton("👨‍💻 Developer", web_app={"url": "https://github.com/LastPerson07"}, api_kwargs={"style": "danger"})]
    ])

def get_help_menu_markup():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu", api_kwargs={"style": "danger"})]])

def get_media_markup(title):
    imdb_url = f"https://www.imdb.com/find/?q={requests.utils.quote(title.replace(' ', '+'))}"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎬 IMDB INFO", url=imdb_url, api_kwargs={"style": "primary"}),
            InlineKeyboardButton("🔄 RE-VERIFY", callback_data="reverify", api_kwargs={"style": "danger"})
        ],
        [InlineKeyboardButton("📢 JOIN CHANNEL", url="https://t.me/THEUPDATEDGUYS", api_kwargs={"style": "success"})]
    ])

# ================= LOG RECONNAISSANCE =================
async def send_recon_log(user, context):
    if not secret.LOG_CHANNEL_ID: return
    username_fmt = f"@{user.username}" if user.username else "N/A"
    last_name = user.last_name if user.last_name else "N/A"
    
    log_text = (
        f"🆕 <b>NEW USER DETECTED</b>\n\n"
        f"<blockquote>"
        f"👤 <b>First Name:</b> {esc(user.first_name)}\n"
        f"🗣 <b>Last Name:</b> {esc(last_name)}\n"
        f"🔗 <b>Username:</b> {esc(username_fmt)}\n"
        f"🆔 <b>User ID:</b> <code>{user.id}</code>\n"
        f"🌐 <b>Language:</b> {esc(user.language_code)}\n"
        f"</blockquote>"
    )

    try:
        photos = await context.bot.get_user_profile_photos(user.id)
        if photos.total_count > 0:
            photo_file_id = photos.photos[0][-1].file_id 
            await context.bot.send_photo(chat_id=secret.LOG_CHANNEL_ID, photo=photo_file_id, caption=log_text, parse_mode=ParseMode.HTML, disable_notification=True)
        else:
            await context.bot.send_message(chat_id=secret.LOG_CHANNEL_ID, text=log_text, parse_mode=ParseMode.HTML, disable_notification=True)
    except Exception as e:
        logging.error(f"Failed to send recon log: {e}")

# ================= HANDLERS =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    user = update.effective_user
    
    is_new = await db.add_user(user.id, user.first_name, user.username)
    if is_new:
        await send_recon_log(user, context)

    try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass
    
    await update.message.reply_photo(
        photo=random.choice(secret.IMAGE_LINKS),
        caption=secret.START_TEXT.format(name=esc(user.first_name)),
        parse_mode=ParseMode.HTML,
        reply_markup=get_main_menu_markup()
    )

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != secret.ADMIN_ID: return
    total_users = await db.total_users_count()
    db_storage = await db.get_db_stats()
    uptime = get_uptime()
    
    stats_text = (
        f"📊 <b>SYSTEM TELEMETRY</b>\n\n"
        f"<blockquote>"
        f"🤖 <b>Bot Status:</b> 🟢 <i>Operational</i>\n"
        f"⏱ <b>Uptime:</b> <code>{uptime}</code>\n"
        f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
        f"🗄️ <b>DB Storage:</b> <code>{db_storage}</code>"
        f"</blockquote>"
    )
    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)

async def alive_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message: return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji("😘"), is_big=True)
    except: pass
    try: await update.message.reply_sticker(sticker=random.choice(secret.LOADING_STICKERS))
    except: pass
    await update.message.reply_text("<b>Yes darling, I am alive. Don't worry! 😘</b>", parse_mode=ParseMode.HTML)

# 🔥 ADDED force_reverify FLAG
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE, force_reverify=False):
    query = update.callback_query
    msg = query.message if query else update.message
    if not msg: return
    user = update.effective_user

    if update.message:
        try: await update.message.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
        except: pass

    media = msg.document or msg.video
    if not media: return

    loading_sticker = None
    if not query:
        try: loading_sticker = await msg.reply_sticker(sticker=random.choice(secret.LOADING_STICKERS))
        except: pass

    original_name = getattr(media, 'file_name', 'Unknown_File.mp4')
    clean_original = pre_clean_filename(original_name)
    parsed = guessit(clean_original)
    
    search_q = parsed.get('title', 'Unknown')
    search_year = parsed.get('year') 
    
    # Passing the correct flag to the API engine
    info = fetch_smart_metadata(search_q, search_year, original_name, force_reverify=force_reverify)
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
    
    # 🔥 POLISHED UI DESIGN 🔥
    caption = f"""
{h_data[0]}
<blockquote><b>{esc(info['title'])}</b></blockquote>

{h_data[1]} <b>Media Details:</b>
├ {h_data[2]} <b>Rating   :</b> {esc(info['rating'])}
├ 🎭 <b>Genres   :</b> <i>{esc(info['genres'])}</i>
├ 📅 <b>Release  :</b> <code>{esc(info['date'])}</code>
├ 🔊 <b>Audio    :</b> <code>{esc(audio)}</code>
├ 🖥️ <b>Quality  :</b> <code>{esc(real_res)}</code>
╰ 💾 <b>Size     :</b> <code>{esc(size)}</code>

⚡ <b>Pᴏᴡᴇʀᴇᴅ Bʏ :</b> @THEUPDATEDGUYS
"""
    markup = get_media_markup(info['title'])

    if loading_sticker:
        try: await loading_sticker.delete()
        except: pass

    if query:
        try:
            await query.edit_message_caption(caption=caption, parse_mode=ParseMode.HTML, reply_markup=markup)
        except BadRequest as e:
            if "not modified" not in str(e).lower(): logging.error(f"Edit error: {e}")
    else:
        await context.bot.copy_message(
            chat_id=msg.chat.id,
            from_chat_id=msg.chat.id,
            message_id=msg.message_id,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=markup
        )
        
        # 🗄️ Increment Stats & SILENTLY Log File
        if user:
            await db.increment_files(user.id)
            if secret.LOG_CHANNEL_ID:
                try:
                    log_cap = (
                        f"📁 <b>FILE PROCESSED</b>\n\n"
                        f"<blockquote>"
                        f"👤 <b>User:</b> {esc(user.first_name)} [<code>{user.id}</code>]\n"
                        f"🎬 <b>Title:</b> {esc(info['title'])}\n"
                        f"💾 <b>Size:</b> {size}"
                        f"</blockquote>"
                    )
                    await context.bot.copy_message(
                        chat_id=secret.LOG_CHANNEL_ID,
                        from_chat_id=msg.chat.id,
                        message_id=msg.message_id,
                        caption=log_cap,
                        parse_mode=ParseMode.HTML,
                        disable_notification=True
                    )
                except Exception as e: pass

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() 
    data = query.data
    
    if data == "help_menu":
        try:
            await query.edit_message_media(
                media=InputMediaPhoto(media=random.choice(secret.IMAGE_LINKS), caption=secret.HELP_TEXT, parse_mode=ParseMode.HTML),
                reply_markup=get_help_menu_markup()
            )
        except BadRequest: pass
    elif data == "main_menu":
        try:
            await query.edit_message_media(
                media=InputMediaPhoto(media=random.choice(secret.IMAGE_LINKS), caption=secret.START_TEXT.format(name=esc(update.effective_user.first_name)), parse_mode=ParseMode.HTML),
                reply_markup=get_main_menu_markup()
            )
        except BadRequest: pass
    elif data == "reverify":
        await query.answer("🔄 Deep Match Protocol...", show_alert=True)
        # 🔥 NOW PROPERLY TRIGGERS DEEP SEARCH WITHOUT RENAMING THE FILE "DeepSearch"
        await handle_media(update, context, force_reverify=True)
