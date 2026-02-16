import random
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import secret
from database.db import db

# ================= ADMIN SECURITY =================
def is_admin(user_id):
    return user_id == secret.ADMIN_ID

# ================= ADMIN TEXT COMMANDS =================
async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        target_id = int(context.args[0])
        days = int(context.args[1])
        await db.grant_premium(target_id, days)
        await update.message.reply_text(f"💎 <b>SUCCESS:</b> User <code>{target_id}</code> granted Premium for {days} days!", parse_mode=ParseMode.HTML)
    except (IndexError, ValueError):
        await update.message.reply_text("❌ <b>Format:</b> <code>/addpremium [User_ID] [Days]</code>", parse_mode=ParseMode.HTML)

async def remove_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        target_id = int(context.args[0])
        await db.revoke_premium(target_id)
        await update.message.reply_text(f"🚫 <b>SUCCESS:</b> Premium revoked from <code>{target_id}</code>.", parse_mode=ParseMode.HTML)
    except (IndexError, ValueError):
        await update.message.reply_text("❌ <b>Format:</b> <code>/removepremium [User_ID]</code>", parse_mode=ParseMode.HTML)

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        target_id = int(context.args[0])
        await db.ban_user(target_id)
        await update.message.reply_text(f"🔨 <b>BANNED:</b> User <code>{target_id}</code> has been banned.", parse_mode=ParseMode.HTML)
    except (IndexError, ValueError):
        await update.message.reply_text("❌ <b>Format:</b> <code>/ban [User_ID]</code>", parse_mode=ParseMode.HTML)

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        target_id = int(context.args[0])
        await db.unban_user(target_id)
        await update.message.reply_text(f"✅ <b>UNBANNED:</b> User <code>{target_id}</code> has been restored.", parse_mode=ParseMode.HTML)
    except (IndexError, ValueError):
        await update.message.reply_text("❌ <b>Format:</b> <code>/unban [User_ID]</code>", parse_mode=ParseMode.HTML)

# ================= THE GRAPHICAL UI PANEL =================
def get_panel_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📜 User List", callback_data="admin_list_0", api_kwargs={"style": "primary"}),
            InlineKeyboardButton("📊 Database Stats", callback_data="admin_stats", api_kwargs={"style": "success"})
        ],
        [
            InlineKeyboardButton("🔒 Close Panel", callback_data="admin_close", api_kwargs={"style": "danger"})
        ]
    ])

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    
    # 1. Send Sticker
    try: await update.message.reply_sticker(sticker=random.choice(secret.LOADING_STICKERS))
    except: pass
    
    # 2. Send Graphical UI
    caption = "<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n🛡️ <b>ADMIN CONTROL PANEL</b>\n\nSelect an option below to manage the engine."
    await update.message.reply_photo(
        photo=random.choice(secret.IMAGE_LINKS),
        caption=caption,
        parse_mode=ParseMode.HTML,
        reply_markup=get_panel_markup()
    )

# ================= ADMIN CALLBACK ROUTER =================
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update.effective_user.id):
        await query.answer("❌ You are not authorized.", show_alert=True)
        return
    
    data = query.data
    await query.answer()

    if data == "admin_close":
        await query.message.delete()

    elif data == "admin_stats":
        total = await db.total_users_count()
        size = await db.get_db_stats()
        text = f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n📊 <b>SYSTEM STATS</b>\n├ 👥 Total Users: <code>{total}</code>\n╰ 🗄️ DB Size: <code>{size}</code>"
        try: await query.edit_message_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=get_panel_markup())
        except: pass

    elif data.startswith("admin_list_"):
        page = int(data.split("_")[2])
        limit = 5
        skip = page * limit
        users = await db.get_users_page(skip, limit)
        total = await db.total_users_count()

        text = f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n📜 <b>USER DATABASE (Page {page+1})</b>\n\n"
        for u in users:
            status = "💎 VIP" if u.get('is_premium') else ("🔨 BANNED" if u.get('is_banned') else "🆓 FREE")
            text += f"👤 <b>{u['name']}</b> [<code>{u['id']}</code>]\n├ <i>Tier:</i> {status}\n╰ <i>Processed:</i> {u.get('files_processed', 0)}\n\n"

        buttons = []
        if page > 0: buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"admin_list_{page-1}", api_kwargs={"style": "primary"}))
        if skip + limit < total: buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_list_{page+1}", api_kwargs={"style": "primary"}))
        
        markup = InlineKeyboardMarkup([buttons, [InlineKeyboardButton("🏠 Back to Panel", callback_data="admin_stats", api_kwargs={"style": "danger"})]])
        
        try: await query.edit_message_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=markup)
        except: pass
