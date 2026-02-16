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

def get_uptime():
    d = datetime.timedelta(seconds=time.time() - BOT_START_TIME)
    return str(d).split('.')[0]

def is_admin(user_id):
    return user_id == secret.ADMIN_ID

ADMIN_CMDS = {
    "speedtest": "⚡ <b>/speedtest</b>\nRuns a network diagnostic test on the cloud server and returns a generated photo of the upload/download speeds.",
    "broadcast": "📢 <b>/broadcast</b>\nReply to any message (photo/video/text) with this command to instantly forward it to all users.",
    "ban": "🔨 <b>/ban [User_ID]</b>\nPermanently block a user from using the bot.",
    "unban": "✅ <b>/unban [User_ID]</b>\nRestore access for a banned user.",
    "users": "👥 <b>/users</b>\nQuickly retrieve the total number of users in the database.",
    "logs": "📄 <b>/logs</b>\nDownloads the bot's internal 'bot.log' text file for debugging.",
    "restart": "🔄 <b>/restart</b>\nForce-restarts the Python engine instantly.",
    "update": "⬇️ <b>/update</b>\nPulls the latest code from GitHub and triggers a restart.",
    "maintenance": "🚧 <b>/maintenance</b>\nToggles Maintenance Mode. When ON, regular users cannot use the bot.",
    "addpremium": "💎 <b>/addpremium [User_ID] [Days]</b>\nGrant premium status to a user.",
    "removepremium": "🚫 <b>/removepremium [User_ID]</b>\nRevoke a user's premium status."
}

# ================= SERVER & MAINTENANCE COMMANDS =================
def run_speedtest_sync():
    st = speedtest.Speedtest()
    st.get_best_server()
    st.download()
    st.upload()
    return st.results.share()

async def speedtest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    msg = await update.message.reply_text("⏳ <b>Initializing Server Speedtest...</b>\n<i>This takes about 15 seconds.</i>", parse_mode=ParseMode.HTML)
    loop = asyncio.get_running_loop()
    try:
        img_url = await loop.run_in_executor(None, run_speedtest_sync)
        await msg.delete()
        await update.message.reply_photo(photo=img_url, caption="🚀 <b>SERVER SPEEDTEST COMPLETE</b>", parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))
    except Exception as e:
        await msg.edit_text(f"❌ Speedtest Failed: {str(e)}")

async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if os.path.exists("bot.log"): await update.message.reply_document(document=open("bot.log", "rb"), caption="📄 System Logs")
    else: await update.message.reply_text("❌ No bot.log file found.")

async def restart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("🔄 <b>Restarting Engine...</b>", parse_mode=ParseMode.HTML)
    os.execl(sys.executable, sys.executable, *sys.argv)

async def update_bot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    await update.message.reply_text("⬇️ <b>Pulling from GitHub...</b>", parse_mode=ParseMode.HTML)
    os.system("git pull")
    await update.message.reply_text("🔄 <b>Restarting to apply updates...</b>", parse_mode=ParseMode.HTML)
    os.execl(sys.executable, sys.executable, *sys.argv)

async def maintenance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    new_state = await db.toggle_maintenance()
    status = "🔴 ENABLED (Bot is locked)" if new_state else "🟢 DISABLED (Bot is open)"
    await update.message.reply_text(f"🚧 <b>MAINTENANCE MODE:</b> {status}", parse_mode=ParseMode.HTML)

async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    total = await db.total_users_count()
    await update.message.reply_text(f"👥 <b>Total Registered Users:</b> <code>{total}</code>", parse_mode=ParseMode.HTML)

# ================= CORE ADMIN COMMANDS =================
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    total_users = await db.total_users_count()
    db_storage = await db.get_db_stats()
    stats_text = f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n📊 <b>SYSTEM TELEMETRY</b>\n\n<blockquote>🤖 <b>Status:</b> 🟢 <i>Operational</i>\n⏱ <b>Uptime:</b> <code>{get_uptime()}</code>\n👥 <b>Users:</b> <code>{total_users}</code>\n🗄️ <b>DB Storage:</b> <code>{db_storage}</code></blockquote>"
    await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML, message_effect_id=random.choice(secret.MESSAGE_EFFECTS))

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
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
    if not is_admin(update.effective_user.id): return
    try:
        t_id, days = int(context.args[0]), int(context.args[1])
        await db.grant_premium(t_id, days)
        await update.message.reply_text(f"💎 Premium granted to <code>{t_id}</code> for {days} days!", parse_mode=ParseMode.HTML)
    except: await update.message.reply_text("❌ /addpremium [ID] [Days]", parse_mode=ParseMode.HTML)

async def remove_premium(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        t_id = int(context.args[0])
        await db.revoke_premium(t_id)
        await update.message.reply_text(f"🚫 Premium revoked from <code>{t_id}</code>.", parse_mode=ParseMode.HTML)
    except: await update.message.reply_text("❌ /removepremium [ID]", parse_mode=ParseMode.HTML)

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        t_id = int(context.args[0])
        await db.ban_user(t_id)
        await update.message.reply_text(f"🔨 Banned: <code>{t_id}</code>.", parse_mode=ParseMode.HTML)
    except: await update.message.reply_text("❌ /ban [ID]", parse_mode=ParseMode.HTML)

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    try:
        t_id = int(context.args[0])
        await db.unban_user(t_id)
        await update.message.reply_text(f"✅ Unbanned: <code>{t_id}</code>.", parse_mode=ParseMode.HTML)
    except: await update.message.reply_text("❌ /unban [ID]", parse_mode=ParseMode.HTML)

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
        row = [InlineKeyboardButton(f"/{cmds[i]}", callback_data=f"cmd_help_{cmds[i]}", api_kwargs={"style": "secondary"})]
        if i+1 < len(cmds): row.append(InlineKeyboardButton(f"/{cmds[i+1]}", callback_data=f"cmd_help_{cmds[i+1]}", api_kwargs={"style": "secondary"}))
        kb.append(row)
    kb.append([InlineKeyboardButton("⬅️ Back to Panel", callback_data="admin_home", api_kwargs={"style": "danger"})])
    return InlineKeyboardMarkup(kb)

async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    
    # 🔥 SMOOTH ANIMATION: Send Sticker -> Sip -> Delete -> Send Panel
    try:
        sticker_msg = await update.message.reply_sticker(sticker=random.choice(secret.LOADING_STICKERS))
        await asyncio.sleep(1.2) # Take a sip
        await sticker_msg.delete()
    except: pass

    await update.message.reply_photo(
        photo=random.choice(secret.IMAGE_LINKS), 
        caption="<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n🛡️ <b>ADMIN CONTROL PANEL</b>\n\n<blockquote>Select an option below to manage the engine.</blockquote>", 
        parse_mode=ParseMode.HTML, 
        reply_markup=get_panel_markup(),
        message_effect_id=random.choice(secret.MESSAGE_EFFECTS)
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(update.effective_user.id): return await query.answer("❌ Unauthorized.", show_alert=True)
    data = query.data
    await query.answer()

    if data == "admin_close": await query.message.delete()
    elif data == "admin_home":
        try: await query.edit_message_caption(caption="<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n🛡️ <b>ADMIN CONTROL PANEL</b>\n\n<blockquote>Select an option below to manage the engine.</blockquote>", parse_mode=ParseMode.HTML, reply_markup=get_panel_markup())
        except: pass
    elif data == "admin_cmds":
        try: await query.edit_message_caption(caption="<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n🛠️ <b>ADMIN COMMAND DIRECTORY</b>\n\n<blockquote>Click a command below to view its details and usage.</blockquote>", parse_mode=ParseMode.HTML, reply_markup=get_cmds_markup())
        except: pass
    elif data.startswith("cmd_help_"):
        cmd = data.split("_")[2]
        info = ADMIN_CMDS.get(cmd, "Info not found.")
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Commands", callback_data="admin_cmds", api_kwargs={"style": "primary"})]])
        try: await query.edit_message_caption(caption=f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n🛠️ <b>COMMAND INFO</b>\n\n<blockquote>{info}</blockquote>", parse_mode=ParseMode.HTML, reply_markup=markup)
        except: pass
    elif data == "admin_stats":
        stats = f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n📊 <b>SYSTEM STATS</b>\n<blockquote>├ 👥 Total Users: <code>{await db.total_users_count()}</code>\n╰ 🗄️ DB Size: <code>{await db.get_db_stats()}</code></blockquote>"
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
