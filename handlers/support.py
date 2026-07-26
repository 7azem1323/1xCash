from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ChatAction
from telegram.ext import (
    ContextTypes, ConversationHandler,
    MessageHandler, CallbackQueryHandler, filters, CommandHandler
)
from database.db import (
    get_message, get_setting, get_button_label, is_admin,
    create_support_request
)
from handlers.keyboards import main_menu_kb, support_admin_kb, cancel_inline
from handlers.utils import make_mention, now_str, broadcast_to_admins
from states.states import SUP_REASON


async def sup_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if await get_setting("maintenance_mode") == "1" and not await is_admin(user.id):
        await update.message.reply_text("🔧 البوت في وضع الصيانة.")
        return ConversationHandler.END
    if await get_setting("support_enabled") == "0":
        await update.message.reply_text("⚠️ خدمة الدعم غير متاحة حالياً.")
        return ConversationHandler.END

    await update.message.chat.send_action(ChatAction.TYPING)
    ask = await get_message("support_ask_reason")
    await update.message.reply_text(ask, reply_markup=cancel_inline("الغاء 🚫", "sup_cancel"))
    return SUP_REASON


async def sup_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.chat.send_action(ChatAction.TYPING)
    mention = make_mention(user)
    reason = update.message.text.strip()

    req_id, seq = await create_support_request(user.id, mention, reason)

    sent = await get_message("support_sent")
    await update.message.reply_text(sent)

    date_str, time_str = now_str()
    admin_text = (
        f"🎧 *طلب دعم*\n\n"
        f"Order #{seq}\n\n"
        f"👤 المستخدم: {mention}\n"
        f"🆔 Telegram ID: `{user.id}`\n"
        f"📃 السبب: {reason}\n\n"
        f"🕒 الوقت: {date_str} - {time_str}"
    )
    kb = support_admin_kb(req_id)
    await broadcast_to_admins(update.get_bot(), admin_text, reply_markup=kb)
    return ConversationHandler.END


async def sup_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.delete_message()
    except Exception:
        pass
    kb = await main_menu_kb()
    await query.get_bot().send_message(query.from_user.id, "🏠 تم الإلغاء.", reply_markup=kb)
    return ConversationHandler.END


def get_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(sup_start, pattern=r"^sup_start$")],
        states={
            SUP_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, sup_reason),
                CallbackQueryHandler(sup_cancel, pattern=r"^sup_cancel$"),
            ],
        },
        fallbacks=[
            CommandHandler("start", lambda u, c: ConversationHandler.END),
        ],
        per_user=True,
        allow_reentry=True,
        name="support_conv",
    )
