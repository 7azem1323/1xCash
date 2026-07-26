from telegram import Update
from telegram.constants import ChatAction, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from database.db import (
    register_user, get_message, get_setting, is_admin,
    get_button_label, get_custom_buttons
)
from handlers.keyboards import main_menu_kb, admin_menu_kb, proofs_inline_kb


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await register_user(user.id, user.username, user.full_name)
    await update.message.chat.send_action(ChatAction.TYPING)

    if await get_setting("maintenance_mode") == "1" and not await is_admin(user.id):
        await update.message.reply_text("🔧 البوت في وضع الصيانة حالياً.")
        return

    if await is_admin(user.id):
        await update.message.reply_text("👑 مرحبًا بك في لوحة الإدارة!", reply_markup=admin_menu_kb())
        return

    welcome = await get_message("welcome")
    kb = await main_menu_kb()
    await update.message.reply_text(welcome, reply_markup=kb)


async def handle_deposit_btn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """يعرض شاشة الإيداع مع اختيار المنصة"""
    user = update.effective_user
    if await get_setting("maintenance_mode") == "1" and not await is_admin(user.id):
        await update.message.reply_text("🔧 البوت في وضع الصيانة.")
        return
    if await get_setting("deposit_enabled") == "0":
        await update.message.reply_text("⚠️ خدمة الإيداع غير متاحة حالياً.")
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    from handlers.keyboards import deposit_platform_kb
    mention = f"@{user.username}" if user.username else user.full_name
    template = await get_message("deposit_intro")
    text = template.replace("{mention}", mention)
    kb = await deposit_platform_kb()
    await update.message.reply_text(text, reply_markup=kb)


async def handle_withdraw_btn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """يعرض شاشة السحب مع اختيار المنصة"""
    user = update.effective_user
    if await get_setting("maintenance_mode") == "1" and not await is_admin(user.id):
        await update.message.reply_text("🔧 البوت في وضع الصيانة.")
        return
    if await get_setting("withdraw_enabled") == "0":
        await update.message.reply_text("⚠️ خدمة السحب غير متاحة حالياً.")
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    from handlers.keyboards import withdraw_platform_kb
    mention = f"@{user.username}" if user.username else user.full_name
    template = await get_message("withdraw_intro")
    text = template.replace("{mention}", mention)
    kb = await withdraw_platform_kb()
    await update.message.reply_text(text, reply_markup=kb)


async def handle_support_btn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """زرار الدعم — يعرض inline keyboard للبدء"""
    user = update.effective_user
    if await get_setting("maintenance_mode") == "1" and not await is_admin(user.id):
        await update.message.reply_text("🔧 البوت في وضع الصيانة.")
        return
    if await get_setting("support_enabled") == "0":
        await update.message.reply_text("⚠️ خدمة الدعم غير متاحة حالياً.")
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    ask = await get_message("support_ask_reason")
    await update.message.reply_text(
        ask,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("الغاء 🚫", callback_data="sup_cancel")]
        ])
    )
    # نبدأ محادثة الدعم مباشرة — نحفظ الـ state يدوياً
    ctx.user_data["in_support"] = True


async def handle_proofs_btn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(ChatAction.TYPING)
    kb = await proofs_inline_kb()
    await update.message.reply_text("📋 جروب الإثباتات:", reply_markup=kb)


async def handle_tote_btn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(ChatAction.TYPING)
    msg = await get_message("tote")
    back_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ])
    await update.message.reply_text(msg, reply_markup=back_kb)


async def handle_myops_btn(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.chat.send_action(ChatAction.TYPING)
    from handlers.myops import _show_myops
    await _show_myops(update.effective_user.id, 0, update, ctx)


async def back_main_cb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        await query.delete_message()
    except Exception:
        pass
    kb = await main_menu_kb()
    welcome = await get_message("welcome")
    await query.get_bot().send_message(query.from_user.id, welcome, reply_markup=kb)


async def handle_custom_buttons(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    custom = await get_custom_buttons()
    for btn in custom:
        if text == btn[1]:
            await update.message.reply_text(
                f"🔗 {btn[1]}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(btn[1], url=btn[2])]
                ])
            )
            return


async def handle_support_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """يستقبل نص الدعم لو المستخدم في وضع الدعم"""
    if not ctx.user_data.get("in_support"):
        return
    from handlers.support import sup_reason
    ctx.user_data.pop("in_support", None)
    await sup_reason(update, ctx)


async def _text_router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """يوزّع الرسائل النصية على الزراير الصح"""
    user = update.effective_user
    text = update.message.text

    # تحقق من وضع الصيانة أولاً
    if await get_setting("maintenance_mode") == "1" and not await is_admin(user.id):
        await update.message.reply_text("🔧 البوت في وضع الصيانة حالياً، يرجى المحاولة لاحقًا.")
        return

    dep_label   = await get_button_label("deposit")
    wit_label   = await get_button_label("withdraw")
    proof_label = await get_button_label("proofs")
    tote_label  = await get_button_label("tote")
    myops_label = await get_button_label("myops")

    if text == dep_label:
        return await handle_deposit_btn(update, ctx)
    if text == wit_label:
        return await handle_withdraw_btn(update, ctx)
    if text == proof_label:
        return await handle_proofs_btn(update, ctx)
    if text == tote_label:
        return await handle_tote_btn(update, ctx)
    if text == myops_label:
        return await handle_myops_btn(update, ctx)

    # لو كان المستخدم في وضع الدعم
    if ctx.user_data.get("in_support"):
        return await handle_support_text(update, ctx)

    # أزرار مخصصة
    await handle_custom_buttons(update, ctx)


def get_handlers():
    return [
        CommandHandler("start", cmd_start),
        CallbackQueryHandler(back_main_cb, pattern=r"^back_main$"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, _text_router),
    ]
