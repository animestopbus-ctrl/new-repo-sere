import random
import time
import asyncio
import datetime
import os
import sys
import speedtest
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
import secret
from database.db import db

BOT_START_TIME = time.time()

# ================= HELPER FUNCTIONS =================
def get_uptime():
    d = datetime.timedelta(seconds=time.time() - BOT_START_TIME)
    return str(d).split('.')[0]

async def check_admin(user_id):
    """
    Checks if user is the Owner OR has admin privileges in DB.
    """
    # 1. Check Owner (Hardcoded in secret.py)
    if user_id == secret.ADMIN_ID:
        return True
        
    # 2. Check Database for granted privileges
    user = await db.col.find_one({'id': int(user_id)})
    if user and user.get('is_admin'):
        return True
        
    return False

# ================= COMMAND DIRECTORY =================
ADMIN_CMDS = {
    "speedtest": "⚡ <b>/speedtest</b>\nRuns network diagnostic & creates speed graph.",
    "broadcast": "📢 <b>/broadcast</b>\nReply to message to send it to all users.",
    "ban": "🔨 <b>/ban [ID]</b>\nPermanently block a user.",
    "unban": "✅ <b>/unban [ID]</b>\nRestore access for a user.",
    "users": "👥 <b>/users</b>\nShow total database user count.",
    "logs": "📄 <b>/logs</b>\nDownload system 'bot.log' file.",
    "restart": "🔄 <b>/restart</b>\nForce-restart the bot engine.",
    "update": "⬇️ <b>/update</b>\nGit pull latest code & restart.",
    "maintenance": "🚧 <b>/maintenance</b>\nToggle maintenance mode on/off.",
    "addpremium": "💎 <b>/addpremium [ID] [Days]</b>\nGrant VIP status.",
    "removepremium": "🚫 <b>/removepremium [ID]</b>\nRevoke VIP status.",
    "addadmin": "👮‍♂️ <b>/addadmin [ID]</b>\nGrant System Admin privileges.",
    "removeadmin": "🤡 <b>/removeadmin [ID]</b>\nRevoke Admin privileges.",
    "kill": "🗑️ <b>/kill</b>\n[UI] Manage & delete active links.",
    "cleanram": "🧹 <b>/cleanram</b>\n[UI] Flush memory & garbage collection."
}

# ================= SYSTEM COMMANDS =================
def run_speedtest_sync():
    st = speedtest.Speedtest()
    st.get_best_server()
    st.download()
    st.upload()
    return st.results.share()

async def speedtest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id): return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji("⚡"), is_big=True)
    except: pass
    msg = await update.message.reply_text("⏳ <b>Initializing Server Speedtest...</b>\n<i>This takes about 15 seconds.</i>", parse_mode=ParseMode.HTML)
    loop = asyncio.get_running_loop()
    try:
        img_url = await loop.run_in_executor(None, run_speedtest_sync)
        sent_photo = await update.message.reply_photo(photo=img_url, caption="<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n🚀 <b>SERVER SPEEDTEST COMPLETE</b>", parse_mode=ParseMode.HTML)
        await msg.delete()
        try: await sent_photo.set_reaction(reaction=ReactionTypeEmoji("🚀"), is_big=True)
        except: pass
    except Exception as e:
        await msg.edit_text(f"❌ <b>Speedtest Failed:</b> <code>{str(e)}</code>", parse_mode=ParseMode.HTML)

async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id): return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji("📄"), is_big=True)
    except: pass
    if os.path.exists("bot.log"): await update.message.reply_document(document=open("bot.log", "rb"), caption="📄 System Logs")
    else: await update.message.reply_text("❌ No bot.log file found.")

async def restart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id): return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji("🔄"), is_big=True)
    except: pass
    await update.message.reply_text("🔄 <b>Restarting Engine...</b>", parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))
    os.execl(sys.executable, sys.executable, *sys.argv)

async def update_bot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id): return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji("⬇️"), is_big=True)
    except: pass
    await update.message.reply_text("⬇️ <b>Pulling from GitHub...</b>", parse_mode=ParseMode.HTML)
    os.system("git pull")
    await update.message.reply_text("🔄 <b>Restarting to apply updates...</b>", parse_mode=ParseMode.HTML)
    os.execl(sys.executable, sys.executable, *sys.argv)

async def maintenance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id): return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji("🚧"), is_big=True)
    except: pass
    new_state = await db.toggle_maintenance()
    status = "🔴 ENABLED" if new_state else "🟢 DISABLED"
    await update.message.reply_text(f"🚧 <b>MAINTENANCE MODE:</b> {status}", parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))

# ================= USER MANAGEMENT =================
async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id): return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji("👥"), is_big=True)
    except: pass
    total = await db.total_users_count()
    await update.message.reply_text(f"👥 <b>Total Users:</b> <code>{total}</code>", parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id): return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji("📊"), is_big=True)
    except: pass
    total_users = await db.total_users_count()
    db_storage = await db.get_db_stats()
    stats_text = f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n📊 <b>SYSTEM TELEMETRY</b>\n\n<blockquote>🤖 <b>Status:</b> 🟢 <i>Operational</i>\n⏱ <b>Uptime:</b> <code>{get_uptime()}</code>\n👥 <b>Users:</b> <code>{total_users}</code>\n🗄️ <b>DB Storage:</b> <code>{db_storage}</code></blockquote>"
    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id): return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji("📢"), is_big=True)
    except: pass
    reply_msg = update.message.reply_to_message
    if not reply_msg: return await update.message.reply_text("❌ <b>Error:</b> Reply to a message.", parse_mode=ParseMode.HTML)
    msg = await update.message.reply_text("⏳ <b>Broadcasting...</b>", parse_mode=ParseMode.HTML)
    success, failed = 0, 0
    async for user in await db.get_all_users():
        try:
            await reply_msg.copy(user['id'], reply_markup=reply_msg.reply_markup)
            success += 1
            await asyncio.sleep(0.05) 
        except Exception: failed += 1
    await msg.edit_text(f"✅ <b>Broadcast Complete!</b>\n<blockquote>🟢 Success: <code>{success}</code>\n🔴 Failed: <code>{failed}</code></blockquote>", parse_mode=ParseMode.HTML)

async def add_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id): return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji("💎"), is_big=True)
    except: pass
    try:
        t_id, days = int(context.args[0]), int(context.args[1])
        await db.grant_premium(t_id, days)
        await update.message.reply_text(f"💎 Premium granted to <code>{t_id}</code> for {days} days!", parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))
    except: await update.message.reply_text("❌ /addpremium [ID] [Days]", parse_mode=ParseMode.HTML)

async def remove_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id): return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji("🚫"), is_big=True)
    except: pass
    try:
        t_id = int(context.args[0])
        await db.revoke_premium(t_id)
        await update.message.reply_text(f"🚫 Premium revoked from <code>{t_id}</code>.", parse_mode=ParseMode.HTML)
    except: await update.message.reply_text("❌ /removepremium [ID]", parse_mode=ParseMode.HTML)

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id): return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji("🔨"), is_big=True)
    except: pass
    try:
        t_id = int(context.args[0])
        await db.ban_user(t_id)
        await update.message.reply_text(f"🔨 Banned: <code>{t_id}</code>.", parse_mode=ParseMode.HTML)
    except: await update.message.reply_text("❌ /ban [ID]", parse_mode=ParseMode.HTML)

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update.effective_user.id): return
    try: await update.message.set_reaction(reaction=ReactionTypeEmoji("✅"), is_big=True)
    except: pass
    try:
        t_id = int(context.args[0])
        await db.unban_user(t_id)
        await update.message.reply_text(f"✅ Unbanned: <code>{t_id}</code>.", parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))
    except: await update.message.reply_text("❌ /unban [ID]", parse_mode=ParseMode.HTML)

# ================= NEW ADMIN MANAGEMENT =================
async def add_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Only the MAIN OWNER (from secret.py) can add new admins security check
    if update.effective_user.id != secret.ADMIN_ID:
        return await update.message.reply_text("🔒 <b>ACCESS DENIED:</b> Only the Main Owner can add new admins.", parse_mode=ParseMode.HTML)
    
    try:
        target_id = int(context.args[0])
        
        # 1. Update Database
        await db.col.update_one({'id': target_id}, {'$set': {'is_admin': True}})
        
        # 2. Confirm to Owner
        await update.message.reply_text(f"✅ <b>SUCCESS:</b>\nUser <code>{target_id}</code> is now an Admin.", parse_mode=ParseMode.HTML)
        
        # 3. Notify the New Admin (The "Power" UI)
        try:
            power_text = (
                "<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n"
                "⚡ <b>ACCESS LEVEL UPGRADED</b>\n\n"
                "<blockquote><b>Congratulations!</b>\n"
                "You have been granted <b>ADMINISTRATOR</b> privileges.\n"
                "You now have control over the system core. Use it wisely.</blockquote>"
            )
            markup = InlineKeyboardMarkup([[InlineKeyboardButton("🛡️ Open Admin Panel", callback_data="panel")]])
            
            await context.bot.send_photo(
                chat_id=target_id,
                photo=random.choice(secret.IMAGE_LINKS),
                caption=power_text,
                reply_markup=markup,
                parse_mode=ParseMode.HTML
            )
        except Exception:
            await update.message.reply_text("⚠️ Admin added, but could not DM them (they might have blocked the bot).")
            
    except IndexError:
        await update.message.reply_text("❌ <b>Usage:</b> <code>/addadmin [User_ID]</code>", parse_mode=ParseMode.HTML)

async def remove_admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != secret.ADMIN_ID:
        return await update.message.reply_text("🔒 <b>ACCESS DENIED:</b> Only the Main Owner can remove admins.", parse_mode=ParseMode.HTML)
    
    try:
        target_id = int(context.args[0])
        await db.col.update_one({'id': target_id}, {'$set': {'is_admin': False}})
        await update.message.reply_text(f"🤡 <b>REVOKED:</b>\nUser <code>{target_id}</code> is no longer an Admin.", parse_mode=ParseMode.HTML)
    except:
        await update.message.reply_text("❌ <b>Usage:</b> <code>/removeadmin [User_ID]</code>", parse_mode=ParseMode.HTML)

# ================= GRAPHICAL UI PANEL =================
def get_panel_markup():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 User List", callback_data="admin_list_0", api_kwargs={"style": "primary"}), InlineKeyboardButton("📊 DB Stats", callback_data="admin_stats", api_kwargs={"style": "success"})],
        [InlineKeyboardButton("🛠️ Admin Commands Directory", callback_data="admin_cmds", api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("🔒 Close Panel", callback_data="admin_close", api_kwargs={"style": "danger"})]
    ])

def get_cmds_markup():
    kb = []
    cmds = list(ADMIN_CMDS.keys())
    for i in range(0, len(cmds), 2):
        row = [InlineKeyboardButton(f"/{cmds[i]}", callback_data=f"cmd_help_{cmds[i]}", api_kwargs={"style": "primary"})]
        if i+1 < len(cmds): row.append(InlineKeyboardButton(f"/{cmds[i+1]}", callback_data=f"cmd_help_{cmds[i+1]}", api_kwargs={"style": "primary"}))
        kb.append(row)
    kb.append([InlineKeyboardButton("⬅️ Back to Panel", callback_data="admin_home", api_kwargs={"style": "danger"})])
    return InlineKeyboardMarkup(kb)

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This handler can be triggered via Command or Callback
    if not await check_admin(update.effective_user.id): return
    
    # Handle Callback Queries calling this function directly
    if update.callback_query:
        await update.callback_query.answer()
        # If it's a callback, we might need to send a new message or edit
        # For simplicity in this logic, we send a new one like the command does
        msg = update.callback_query.message
    else:
        msg = update.message

    if not msg: return

    try: await msg.set_reaction(reaction=ReactionTypeEmoji(random.choice(secret.EMOJIS)), is_big=True)
    except: pass
    
    sent_msg = await context.bot.send_photo(
        chat_id=msg.chat.id,
        photo=random.choice(secret.IMAGE_LINKS), 
        caption="<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n🛡️ <b>ADMIN CONTROL PANEL</b>\n\n<blockquote>Select an operation from the master console below.</blockquote>", 
        parse_mode=ParseMode.HTML, 
        reply_markup=get_panel_markup()
    )
    try: await sent_msg.set_reaction(reaction=ReactionTypeEmoji("🛡️"), is_big=True)
    except: pass

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await check_admin(update.effective_user.id): return await query.answer("❌ Unauthorized.", show_alert=True)
    data = query.data
    await query.answer()

    if data == "admin_close": await query.message.delete()
    
    elif data == "panel": # Handler for the "Open Admin Panel" button from DM
        await panel(update, context)

    elif data == "admin_home":
        try: await query.edit_message_caption(caption="<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n🛡️ <b>ADMIN CONTROL PANEL</b>\n\n<blockquote>Select an operation from the master console below.</blockquote>", parse_mode=ParseMode.HTML, reply_markup=get_panel_markup())
        except: pass
    elif data == "admin_cmds":
        try: await query.edit_message_caption(caption="<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n🛠️ <b>ADMIN COMMAND DIRECTORY</b>\n\n<blockquote>Click a command to view detailed documentation.</blockquote>", parse_mode=ParseMode.HTML, reply_markup=get_cmds_markup())
        except: pass
    elif data.startswith("cmd_help_"):
        cmd = data.split("_")[2]
        info = ADMIN_CMDS.get(cmd, "Info not found.")
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="admin_cmds", api_kwargs={"style": "primary"})]])
        try: await query.edit_message_caption(caption=f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n🛠️ <b>/{cmd} INFO</b>\n\n<blockquote>{info}</blockquote>", parse_mode=ParseMode.HTML, reply_markup=markup)
        except: pass
    elif data == "admin_stats":
        total = await db.total_users_count()
        db_size = await db.get_db_stats()
        stats = f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n📊 <b>SYSTEM STATS</b>\n<blockquote>├ 👥 Total Users: <code>{total}</code>\n╰ 🗄️ DB Size: <code>{db_size}</code></blockquote>"
        try: await query.edit_message_caption(caption=stats, parse_mode=ParseMode.HTML, reply_markup=get_panel_markup())
        except: pass
    elif data.startswith("admin_list_"):
        page = int(data.split("_")[2])
        skip, limit = page * 5, 5
        users = await db.get_users_page(skip, limit)
        text = f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n📜 <b>USER DATABASE (Page {page+1})</b>\n\n<blockquote>"
        for u in users:
            st = "💎 VIP" if u.get('is_premium') else ("🔨 BANNED" if u.get('is_banned') else "🆓 FREE")
            text += f"👤 <b>{u['name']}</b> [<code>{u['id']}</code>]\n├ <i>Tier:</i> {st}\n╰ <i>Files:</i> {u.get('files_processed', 0)}\n\n"
        text += "</blockquote>"
        buttons = []
        if page > 0: buttons.append(InlineKeyboardButton("⬅️ Back", callback_data=f"admin_list_{page-1}", api_kwargs={"style": "primary"}))
        if skip + limit < await db.total_users_count(): buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_list_{page+1}", api_kwargs={"style": "primary"}))
        try: await query.edit_message_caption(caption=text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup([buttons, [InlineKeyboardButton("🏠 Panel", callback_data="admin_home", api_kwargs={"style": "danger"})]]))
        except: pass
