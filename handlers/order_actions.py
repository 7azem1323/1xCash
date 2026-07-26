import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CallbackQueryHandler, ConversationHandler, MessageHandler, filters, CommandHandler

from database.db import (
    get_order, update_order, is_admin, is_owner,
    get_support_request, update_support_request,
    skip_order, has_admin_skipped,
    start_chat, end_chat, get_chat_by_user, get_chat_by_admin,
    get_all_admins, get_message, log_action, get_button_label
)
from handlers.keyboards import (
    main_menu_kb, order_accepted_kb, support_accepted_kb,
    order_admin_kb, support_admin_kb
)
from handlers.utils import make_mention, now_str, broadcast_to_admins, edit_admin_messages
from states.states import ADM_REJECT_REASON

# حفظ IDs رسائل الإدارة مؤقتاً (order_id -> {admin_id: msg_id})
_pending_admin_msgs: dict[str, dict] = {}


# ══════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════

def _accepted_text_for_admins(order, admin_mention: str) -> str:
    otype = "إيداع" if order[1] == "deposit" else "سحب"
    return (
        f"🔵 *طلب {otype} قيد التنفيذ*\n\n"
        f"👤 المستخدم: {order[6]}\n"
        f"🆔 Telegram ID: `{order[5]}`\n\n"
        f"✳️ الزر: {order[2]}\n"
        f"💶 المبلغ: {order[4]}\n\n"
        f"👨🏻‍💼 المشرف المسؤول: {admin_mention}"
    )


def _support_accepted_text(req, admin_mention: str) -> str:
    return (
        f"🔵 *طلب دعم قيد التنفيذ*\n\n"
        f"👤 المستخدم: {req[2]}\n"
        f"📃 السبب: {req[3]}\n\n"
        f"👨🏻‍💼 المشرف المسؤول: {admin_mention}"
    )


# ══════════════════════════════════════════════
# ACCEPT ORDER (DEPOSIT / WITHDRAW)
# ══════════════════════════════════════════════

async def order_accept(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin = query.from_user
    if not await is_admin(admin.id):
        await query.answer("⛔ غير مصرح.", show_alert=True)
        return

    await query.answer()
    parts = query.data.split(":")
    order_id = int(parts[1])

    order = await get_order(order_id)
    if not order:
        await query.edit_message_text("⚠️ الطلب غير موجود.")
        return

    if order[8] not in ("pending", "active"):
        await query.edit_message_text("⚠️ تم تنفيذ هذا الطلب بالفعل.")
        return

    admin_mention = make_mention(admin)
    await update_order(order_id, status="active", accepted_by=admin.id)

    # تحديث رسالة جميع الإدارة
    new_text = _accepted_text_for_admins(order, admin_mention)
    kb = order_accepted_kb(order_id, order[1])

    try:
        await query.edit_message_text(new_text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        pass

    # إبلاغ بقية المشرفين
    admins = await get_all_admins()
    for aid in admins:
        if aid == admin.id:
            continue
        try:
            await query.get_bot().send_message(
                aid, new_text, reply_markup=kb, parse_mode="Markdown"
            )
        except Exception:
            pass

    # فتح محادثة مع المستخدم
    user_id = order[5]
    await start_chat(user_id, admin.id, order_id, order[1])

    accepted_msg = await get_message("admin_accepted_user")
    await query.get_bot().send_message(
        user_id,
        accepted_msg.replace("{mention}", admin_mention),
        parse_mode="Markdown"
    )

    await log_action("order_accepted", admin.id, order_id)


# ══════════════════════════════════════════════
# SKIP ORDER
# ══════════════════════════════════════════════

async def order_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin = query.from_user
    if not await is_admin(admin.id):
        await query.answer("⛔ غير مصرح.", show_alert=True)
        return

    await query.answer("تم الاستغناء عن الطلب.", show_alert=True)
    parts = query.data.split(":")
    order_id = int(parts[1])

    order = await get_order(order_id)
    if not order or order[8] not in ("pending", "active"):
        return

    await skip_order(order_id, admin.id)

    # إخفاء الأزرار عند هذا المشرف فقط
    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 استغنيت عن هذا الطلب", callback_data="noop")]
        ]))
    except Exception:
        pass


# ══════════════════════════════════════════════
# COMPLETE ORDER
# ══════════════════════════════════════════════

async def order_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin = query.from_user
    if not await is_admin(admin.id):
        await query.answer("⛔ غير مصرح.", show_alert=True)
        return

    await query.answer()
    parts = query.data.split(":")
    prefix = parts[0]
    order_id = int(parts[1])
    admin_mention = make_mention(admin)

    order = await get_order(order_id)
    if not order:
        await query.edit_message_text("⚠️ الطلب غير موجود.")
        return

    # تحقق إن المشرف هو نفس اللي قبل الطلب
    if order[9] and order[9] != admin.id:
        await query.answer("🔒 هذا الطلب قيد المعالجة من قِبل مشرف آخر، لا يمكنك التدخل فيه.", show_alert=True)
        return

    await update_order(order_id, status="completed", accepted_by=admin.id)
    user_id = order[5]
    otype = "إيداع" if order[1] == "deposit" else "سحب"
    icon = "📥" if order[1] == "deposit" else "📤"

    date_str, time_str = now_str()
    result_text = (
        f"🟢 *عملية {otype} مكتملة*\n\n"
        f"✳️ الزر المختار: {order[2]}\n"
        f"👤 اللاعب: {order[6]}\n"
        f"🆔 Telegram ID: `{user_id}`\n"
        f"💶 المبلغ: {order[4]}\n"
        f"👨🏻‍💼 المشرف: {admin_mention}\n\n"
        f"🕒 {date_str} - {time_str}"
    )

    # إنهاء المحادثة
    chat = await get_chat_by_user(user_id)
    await end_chat(user_id)

    # إرسال لكلٍّ من المستخدم والمشرف
    for target in [user_id, admin.id]:
        try:
            await query.get_bot().send_message(target, result_text, parse_mode="Markdown")
        except Exception:
            pass

    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    await log_action("order_completed", admin.id, order_id)


# ══════════════════════════════════════════════
# REJECT ORDER — CONVERSATION
# ══════════════════════════════════════════════

async def order_reject_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin = query.from_user
    if not await is_admin(admin.id):
        await query.answer("⛔ غير مصرح.", show_alert=True)
        return

    parts = query.data.split(":")
    order_id = int(parts[1])
    rtype = parts[0].replace("_reject", "")

    # تحقق إن المشرف هو نفس اللي قبل الطلب
    if rtype != "sup":
        order = await get_order(order_id)
        if order and order[9] and order[9] != admin.id:
            await query.answer("🔒 هذا الطلب قيد المعالجة من قِبل مشرف آخر، لا يمكنك التدخل فيه.", show_alert=True)
            return
    else:
        req = await get_support_request(order_id)
        if req and req[5] and req[5] != admin.id:
            await query.answer("🔒 هذا الطلب قيد المعالجة من قِبل مشرف آخر، لا يمكنك التدخل فيه.", show_alert=True)
            return

    await query.answer()
    ctx.user_data["reject_order_id"] = order_id
    ctx.user_data["reject_type"] = rtype

    await query.get_bot().send_message(
        admin.id,
        "📝 يرجى كتابة سبب الرفض:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("الغاء 🚫", callback_data="reject_cancel")]
        ])
    )
    return ADM_REJECT_REASON


async def order_reject_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    reason = update.message.text.strip()
    admin = update.effective_user
    admin_mention = make_mention(admin)
    order_id = ctx.user_data.get("reject_order_id")
    rtype = ctx.user_data.get("reject_type", "dep")

    date_str, time_str = now_str()

    if rtype == "sup":
        req = await get_support_request(order_id)
        if req:
            await update_support_request(order_id, status="rejected", accepted_by=admin.id)
            user_id = req[1]
            result_text = (
                f"🔴 *طلب الدعم مرفوض*\n\n"
                f"👤 المستخدم: {req[2]}\n"
                f"📃 السبب المُدخل: {req[3]}\n"
                f"📃 سبب الرفض: {reason}\n"
                f"👨🏻‍💼 المشرف: {admin_mention}\n\n"
                f"🕒 {date_str} - {time_str}"
            )
            for target in [user_id, admin.id]:
                try:
                    await update.get_bot().send_message(target, result_text, parse_mode="Markdown")
                except Exception:
                    pass
    else:
        order = await get_order(order_id)
        if order:
            await update_order(order_id, status="rejected", reject_reason=reason, accepted_by=admin.id)
            user_id = order[5]
            otype = "إيداع" if order[1] == "deposit" else "سحب"
            result_text = (
                f"🔴 *عملية {otype} غير مكتملة*\n\n"
                f"✳️ الزر المختار: {order[2]}\n"
                f"👤 اللاعب: {order[6]}\n"
                f"🆔 Telegram ID: `{user_id}`\n"
                f"💶 المبلغ: {order[4]}\n"
                f"📃 السبب: {reason}\n"
                f"👨🏻‍💼 المشرف: {admin_mention}\n\n"
                f"🕒 {date_str} - {time_str}"
            )
            await end_chat(user_id)
            for target in [user_id, admin.id]:
                try:
                    await update.get_bot().send_message(target, result_text, parse_mode="Markdown")
                except Exception:
                    pass

    await update.message.reply_text("✅ تم إرسال رسالة الرفض.")
    await log_action("order_rejected", admin.id, order_id, reason)
    ctx.user_data.pop("reject_order_id", None)
    ctx.user_data.pop("reject_type", None)
    return ConversationHandler.END


async def reject_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("❌ تم إلغاء عملية الرفض.")
    ctx.user_data.pop("reject_order_id", None)
    return ConversationHandler.END


# ══════════════════════════════════════════════
# SUPPORT ACCEPT / SKIP / DONE / REJECT
# ══════════════════════════════════════════════

async def sup_accept(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin = query.from_user
    if not await is_admin(admin.id):
        await query.answer("⛔ غير مصرح.", show_alert=True)
        return

    await query.answer()
    req_id = int(query.data.split(":")[1])
    req = await get_support_request(req_id)
    if not req or req[4] != "pending":
        await query.edit_message_text("⚠️ الطلب غير موجود أو تم قبوله مسبقاً.")
        return

    admin_mention = make_mention(admin)
    await update_support_request(req_id, status="active", accepted_by=admin.id)

    new_text = _support_accepted_text(req, admin_mention)
    kb = support_accepted_kb(req_id)
    try:
        await query.edit_message_text(new_text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        pass

    admins = await get_all_admins()
    for aid in admins:
        if aid == admin.id:
            continue
        try:
            await query.get_bot().send_message(aid, new_text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            pass

    user_id = req[1]
    await start_chat(user_id, admin.id, req_id, "support")
    accepted_msg = await get_message("admin_accepted_user")
    await query.get_bot().send_message(
        user_id,
        accepted_msg.replace("{mention}", admin_mention),
        parse_mode="Markdown"
    )
    await log_action("support_accepted", admin.id, req_id)


async def sup_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await is_admin(query.from_user.id):
        await query.answer("⛔ غير مصرح.", show_alert=True)
        return
    await query.answer("تم الاستغناء.", show_alert=True)
    try:
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 استغنيت عن هذا الطلب", callback_data="noop")]
        ]))
    except Exception:
        pass


async def sup_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    admin = query.from_user
    if not await is_admin(admin.id):
        await query.answer("⛔ غير مصرح.", show_alert=True)
        return
    await query.answer()
    req_id = int(query.data.split(":")[1])
    req = await get_support_request(req_id)
    if not req:
        return

    # تحقق إن المشرف هو نفس اللي قبل الطلب
    if req[5] and req[5] != admin.id:
        await query.answer("🔒 هذا الطلب قيد المعالجة من قِبل مشرف آخر، لا يمكنك التدخل فيه.", show_alert=True)
        return

    await update_support_request(req_id, status="completed")
    admin_mention = make_mention(admin)
    date_str, time_str = now_str()
    result_text = (
        f"🟢 *طلب الدعم مكتمل*\n\n"
        f"👤 المستخدم: {req[2]}\n"
        f"📃 السبب: {req[3]}\n"
        f"👨🏻‍💼 المشرف: {admin_mention}\n\n"
        f"🕒 {date_str} - {time_str}"
    )
    user_id = req[1]
    await end_chat(user_id)
    for target in [user_id, admin.id]:
        try:
            await query.get_bot().send_message(target, result_text, parse_mode="Markdown")
        except Exception:
            pass
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass
    await log_action("support_completed", admin.id, req_id)


# ══════════════════════════════════════════════
# RELAY CHAT
# ══════════════════════════════════════════════

async def relay_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    msg = update.message

    # المستخدم يرسل للمشرف
    chat = await get_chat_by_user(user.id)
    if chat:
        admin_id = chat[2]
        try:
            await msg.copy(admin_id)
        except Exception:
            pass
        return

    # المشرف يرسل للمستخدم
    if await is_admin(user.id):
        chat = await get_chat_by_admin(user.id)
        if chat:
            target_user = chat[1]
            try:
                await msg.copy(target_user)
            except Exception:
                pass


def get_handlers():
    reject_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(order_reject_start, pattern=r"^(dep|wit|sup)_reject:\d+$"),
        ],
        states={
            ADM_REJECT_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, order_reject_reason),
                CallbackQueryHandler(reject_cancel, pattern=r"^reject_cancel$"),
            ],
        },
        fallbacks=[CommandHandler("start", lambda u, c: ConversationHandler.END)],
        per_user=True,
        allow_reentry=True,
        name="reject_conv",
    )

    return [
        reject_conv,
        CallbackQueryHandler(order_accept, pattern=r"^(dep|wit)_accept:\d+$"),
        CallbackQueryHandler(order_skip,   pattern=r"^(dep|wit)_skip:\d+$"),
        CallbackQueryHandler(order_done,   pattern=r"^(dep|wit)_done:\d+$"),
        CallbackQueryHandler(sup_accept,   pattern=r"^sup_accept:\d+$"),
        CallbackQueryHandler(sup_skip,     pattern=r"^sup_skip:\d+$"),
        CallbackQueryHandler(sup_done,     pattern=r"^sup_done:\d+$"),
        CallbackQueryHandler(lambda u, c: u.callback_query.answer(), pattern=r"^noop$"),
    ]


def get_relay_handler():
    return MessageHandler(filters.ALL & ~filters.COMMAND, relay_message)
