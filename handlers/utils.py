from datetime import datetime
from telegram import Update, Message, Bot
from database.db import get_all_admins


def now_str() -> tuple[str, str]:
    now = datetime.now()
    return now.strftime("%Y/%m/%d"), now.strftime("%I:%M %p")


def make_mention(user) -> str:
    if user.username:
        return f"@{user.username}"
    return f"[{user.full_name}](tg://user?id={user.id})"


def status_icon(status: str) -> str:
    return {
        "pending":   "🟡 قيد الانتظار",
        "completed": "🟢 مكتمل",
        "rejected":  "🔴 مرفوض",
        "cancelled": "⚫ ملغي",
        "active":    "🔵 جاري",
    }.get(status, status)


def order_type_ar(order_type: str) -> str:
    return {"deposit": "إيداع", "withdraw": "سحب", "support": "دعم"}.get(order_type, order_type)


async def broadcast_to_admins(bot: Bot, text: str, reply_markup=None, exclude: int = None, parse_mode="Markdown"):
    admins = await get_all_admins()
    sent = {}
    for admin_id in admins:
        if admin_id == exclude:
            continue
        try:
            msg = await bot.send_message(
                chat_id=admin_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            sent[admin_id] = msg.message_id
        except Exception:
            pass
    return sent


async def edit_admin_messages(bot: Bot, admin_msg_ids: dict, text: str, reply_markup=None, parse_mode="Markdown"):
    for admin_id, msg_id in admin_msg_ids.items():
        try:
            await bot.edit_message_text(
                chat_id=int(admin_id),
                message_id=msg_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
        except Exception:
            pass
