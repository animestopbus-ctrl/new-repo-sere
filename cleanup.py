import os
import gc
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import secret
from database.db import db
import script # To access and clear the SPAM_CACHE

logger = logging.getLogger(__name__)

# Helper to get RAM usage (Works natively on Linux/Render)
def get_ram_usage():
    try:
        import resource
        # Convert kilobytes to Megabytes
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except ImportError:
        return 0.0

async def check_admin(user_id):
    return user_id == secret.ADMIN_ID

# ================= /kill COMMAND (LINK TERMINATOR) =================
async def kill_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id):
        return
    await send_kill_page(update, context, page=0)

async def send_kill_page(update: Update, context, page: int, edit_msg=None):
    limit = 5
    skip = page * limit
    
    # Get stats from MongoDB
    total_links = await db.links.count_documents({})
    total_pages = max(1, (total_links + limit - 1) // limit)
    
    links = await db.links.find({}).skip(skip).limit(limit).to_list(length=limit)
    
    text = (
        f"<b><u><blockquote>🗑️ LINK TERMINATION PROTOCOL</blockquote></u></b>\n\n"
        f"<i>\"A clean database is a fast database.\"</i>\n\n"
        f"📊 <b>Total Active Links:</b> <code>{total_links}</code>\n"
        f"📄 <b>Page:</b> <code>{page + 1}/{total_pages}</code>\n\n"
        f"<b>Active Links on this page:</b>\n"
    )
    
    if not links:
        text += "<blockquote>No active links found. Database is completely clean! ✨</blockquote>"
    else:
        for l in links:
            # Show the first 20 chars of the filename
            short_name = str(l.get('file_name', 'Unknown'))[:20]
            text += f"├ <code>{l['_id']}</code> | {short_name}...\n"
        text += "╰───────────────────"
        
    buttons = []
    nav_row = []
    
    # Pagination Logic
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Back", callback_data=f"kill_page_{page-1}"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"kill_page_{page+1}"))
        
    if nav_row:
        buttons.append(nav_row)
        
    if total_links > 0:
        buttons.append([InlineKeyboardButton("🚨 KILL ALL LINKS 🚨", callback_data="kill_confirm")])
        
    buttons.append([InlineKeyboardButton("❌ Close Panel", callback_data="close_ui")])
    
    reply_markup = InlineKeyboardMarkup(buttons)
    
    if edit_msg:
        await edit_msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

# ================= /cleanram COMMAND (MEMORY FLUSHER) =================
async def cleanram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id):
        return
    await run_ram_cleaner(update, context)

async def run_ram_cleaner(update: Update, context, edit_msg=None):
    ram_before = get_ram_usage()
    
    # 1. Force Python Garbage Collection (Destroys unreferenced memory)
    collected = gc.collect()
    
    # 2. Clear Internal Bot Caches
    script.SPAM_CACHE.clear()
    
    ram_after = get_ram_usage()
    freed = max(0, ram_before - ram_after)
    
    text = (
        f"<b><u><blockquote>🚀 RAM OPTIMIZATION PROTOCOL</blockquote></u></b>\n\n"
        f"<i>\"Flushing the memory buffers...\"</i>\n\n"
        f"🧠 <b>Garbage Objects Destroyed:</b> <code>{collected}</code>\n"
        f"🛡️ <b>Spam Cache:</b> <code>Wiped Clean</code>\n\n"
        f"📉 <b>RAM Before:</b> <code>{ram_before:.2f} MB</code>\n"
        f"📈 <b>RAM After:</b> <code>{ram_after:.2f} MB</code>\n"
        f"✅ <b>Total Memory Freed:</b> <code>{freed:.2f} MB</code>"
    )
    
    buttons = [
        [InlineKeyboardButton("🔄 Run Deep Clean Again", callback_data="ram_run")],
        [InlineKeyboardButton("❌ Close Panel", callback_data="close_ui")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    if edit_msg:
        await edit_msg.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=reply_markup)

# ================= UI CALLBACK ROUTER =================
async def cleanup_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    
    if not await check_admin(user_id):
        return await query.answer("🛑 Security Alert: Admin Only!", show_alert=True)
        
    if data.startswith("kill_page_"):
        page = int(data.split("_")[2])
        await send_kill_page(update, context, page, edit_msg=query.message)
        await query.answer()
        
    elif data == "kill_confirm":
        text = (
            f"<b><u><blockquote>⚠️ CRITICAL WARNING</blockquote></u></b>\n\n"
            f"You are about to <b>TERMINATE ALL ACTIVE LINKS</b> in the database.\n"
            f"Users currently streaming or downloading will be instantly cut off.\n\n"
            f"Are you absolutely sure you want to proceed?"
        )
        buttons = [
            [InlineKeyboardButton("🔥 YES, DESTROY THEM ALL", callback_data="kill_execute")],
            [InlineKeyboardButton("⬅️ Cancel", callback_data="kill_page_0")]
        ]
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer("Awaiting confirmation...", show_alert=False)
        
    elif data == "kill_execute":
        # Delete everything from the links collection
        deleted = await db.links.delete_many({})
        count = deleted.deleted_count
        text = (
            f"<b><u><blockquote>☠️ MASSACRE COMPLETE</blockquote></u></b>\n\n"
            f"<i>\"I am become Death, the destroyer of links.\"</i>\n\n"
            f"💀 <b>Total Links Terminated:</b> <code>{count}</code>\n\n"
            f"The database has been fully purged of all stream and download links."
        )
        buttons = [[InlineKeyboardButton("❌ Close Panel", callback_data="close_ui")]]
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))
        await query.answer(f"Success! {count} links obliterated.", show_alert=True)
        
    elif data == "ram_run":
        await query.answer("Initiating Deep Memory Clean...", show_alert=False)
        await run_ram_cleaner(update, context, edit_msg=query.message)
        
    elif data == "close_ui":
        await query.message.delete()
        await query.answer()
