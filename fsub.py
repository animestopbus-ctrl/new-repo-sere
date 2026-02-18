import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import secret

async def is_user_subscribed(bot, user_id):
    """
    Strictly checks if a user is inside the mandatory channel.
    """
    if not secret.FSUB_CHANNEL_ID:
        return True
        
    try:
        member = await bot.get_chat_member(chat_id=secret.FSUB_CHANNEL_ID, user_id=user_id)
        if member.status in ['left', 'kicked', 'banned']:
            return False
        return True
    except Exception as e:
        # 🔥 THE BUG FIX: If Telegram throws an error (User Not Found), they are NOT in the channel!
        logging.warning(f"FSUB Check Blocked User {user_id} (Not in channel)")
        return False

def get_fsub_markup():
    """Returns the colorful buttons for F-Sub."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 JOIN OFFICIAL CHANNEL", url=secret.FSUB_CHANNEL_LINK, api_kwargs={"style": "primary"})],
        [InlineKeyboardButton("🔄 I Have Joined", callback_data="check_fsub", api_kwargs={"style": "success"})]
    ])

def get_fsub_text(first_name):
    """Returns the perfectly formatted F-Sub message."""
    return (
        f"<b><u><blockquote>THE UPDATED GUYS 😎</blockquote></u></b>\n\n"
        f"<b>🛑 ACCESS DENIED, {first_name}!</b>\n\n"
        f"<blockquote>You must join our official channel to unlock the engine. "
        f"Click the button below to join, then click 'I Have Joined' to verify your access.</blockquote>"
    )
