from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters

from database.db import get_button_label, get_user_orders
from handlers.keyboards import myops_pagination_kb
from handlers.utils import status_icon, order_type_ar

PER_PAGE = 5


async def myops_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    label = await get_button_label("myops")
    if update.message.text != label:
        return
    await _show_myops(update.effective_user.id, 0, update, ctx)


async def myops_page(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    page = int(query.data.split(":")[1])
    await _show_myops(query.from_user.id, page, update, ctx, edit=True)


async def _show_myops(user_id, page, update, ctx, edit=False):
    rows, total = await get_user_orders(user_id, page, PER_PAGE)

    if not rows:
        text = "📋 لا توجد عمليات بعد."
        kb = None
    else:
        lines = [f"📋 *عملياتي* — الصفحة {page+1}\n"]
        for r in rows:
            order_id, otype, platform, amount, status, created_at = r
            lines.append(
                f"• `#{order_id}` {order_type_ar(otype)} | {platform or ''} | {amount} | {status_icon(status)}\n"
                f"  🕒 {created_at[:16]}"
            )
        text = "\n".join(lines)
        kb = myops_pagination_kb(page, total, PER_PAGE)

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=kb, parse_mode="Markdown")


def get_handlers():
    return [
        CallbackQueryHandler(myops_page, pattern=r"^myops_page:\d+$"),
    ]
