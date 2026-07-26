import json
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, ConversationHandler,
    MessageHandler, CallbackQueryHandler, filters, CommandHandler
)
from database.db import (
    is_admin, is_owner, get_owner_id,
    get_all_admins, add_admin, remove_admin, get_admin_list,
    get_message, set_message, get_setting, set_setting,
    get_button_label, set_button_label, get_all_button_labels,
    get_custom_buttons, add_custom_button, delete_custom_button,
    get_orders_list, get_stats, get_logs, log_action, get_all_users
)
from handlers.keyboards import admin_menu_kb, main_menu_kb
from handlers.utils import status_icon, order_type_ar
from states.states import (
    ADM_BROADCAST, ADM_EDIT_MSG_KEY, ADM_EDIT_MSG_VAL,
    ADM_EDIT_BTN_KEY, ADM_EDIT_BTN_VAL,
    ADM_ADD_ADMIN, ADM_REMOVE_ADMIN,
    ADM_ADD_CUSTOM_LABEL, ADM_ADD_CUSTOM_URL,
    ADM_EDIT_SETTING_KEY, ADM_EDIT_SETTING_VAL,
)

CANCEL_TEXT = "/cancel"

async def _cancel_conv(update, ctx):
    if update.message:
        await update.message.reply_text("❌ تم الإلغاء.", reply_markup=admin_menu_kb())
    return ConversationHandler.END




# ══════════════════════════════════════════════
# /admin COMMAND
# ══════════════════════════════════════════════

async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    await update.message.reply_text("👑 لوحة الإدارة:", reply_markup=admin_menu_kb())


# ══════════════════════════════════════════════
# ORDERS LISTS
# ══════════════════════════════════════════════

async def show_deposit_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    rows = await get_orders_list(order_type="deposit")
    if not rows:
        await update.message.reply_text("📭 لا توجد طلبات إيداع.")
        return
    lines = ["📥 *طلبات الإيداع:*\n"]
    for r in rows:
        lines.append(f"• `#{r[0]}` {r[2]} | {r[3]} | {status_icon(r[5])} | {r[6][:16]}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def show_withdraw_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    rows = await get_orders_list(order_type="withdraw")
    if not rows:
        await update.message.reply_text("📭 لا توجد طلبات سحب.")
        return
    lines = ["📤 *طلبات السحب:*\n"]
    for r in rows:
        lines.append(f"• `#{r[0]}` {r[2]} | {r[3]} | {status_icon(r[5])} | {r[6][:16]}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ══════════════════════════════════════════════
# STATS
# ══════════════════════════════════════════════

async def show_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    s = await get_stats()
    text = (
        f"📊 *الإحصائيات*\n\n"
        f"👥 المستخدمين: {s['users']}\n\n"
        f"📥 *الإيداع*\n"
        f"  🟡 قيد الانتظار: {s['dep_p']}\n"
        f"  🟢 مكتمل: {s['dep_c']}\n"
        f"  🔴 مرفوض: {s['dep_r']}\n\n"
        f"📤 *السحب*\n"
        f"  🟡 قيد الانتظار: {s['wit_p']}\n"
        f"  🟢 مكتمل: {s['wit_c']}\n"
        f"  🔴 مرفوض: {s['wit_r']}\n\n"
        f"🎧 دعم قيد الانتظار: {s['sup_p']}"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ══════════════════════════════════════════════
# LOGS
# ══════════════════════════════════════════════

async def show_logs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    rows = await get_logs(15)
    if not rows:
        await update.message.reply_text("📭 لا توجد سجلات.")
        return
    lines = ["📜 *السجلات:*\n"]
    for r in rows:
        lines.append(f"• `{r[0]}` | admin:{r[1]} | {r[3]} | {r[4][:16]}")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ══════════════════════════════════════════════
# BROADCAST
# ══════════════════════════════════════════════

async def broadcast_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update.effective_user.id):
        return
    await update.message.reply_text(
        "📣 أرسل الرسالة التي تريد إذاعتها:\n"
        "سيتم إضافة *📢 إشعار من 1xCash:* تلقائياً في البداية.\n"
        "(اكتب /cancel للإلغاء)",
        parse_mode="Markdown"
    )
    return ADM_BROADCAST


async def broadcast_send(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text and update.message.text.strip() == CANCEL_TEXT:
        await update.message.reply_text("❌ تم إلغاء الإذاعة.", reply_markup=admin_menu_kb())
        return ConversationHandler.END

    users = await get_all_users()
    bot = update.get_bot()
    success = 0
    broadcast_text = f"📢 إشعار من 1xCash:\n\n{update.message.text or ''}"
    for uid in users:
        try:
            await bot.send_message(uid, broadcast_text, parse_mode="Markdown")
            success += 1
        except Exception:
            pass
    await update.message.reply_text(
        f"✅ تم الإرسال لـ {success} من أصل {len(users)} مستخدم.",
        reply_markup=admin_menu_kb()
    )
    await log_action("broadcast", update.effective_user.id, details=f"sent to {success}")
    return ConversationHandler.END


# ══════════════════════════════════════════════
# EDIT MESSAGES
# ══════════════════════════════════════════════

MESSAGE_KEYS = [
    ("welcome", "رسالة الترحيب"),
    ("deposit_intro", "مقدمة الإيداع"),
    ("withdraw_intro", "مقدمة السحب"),
    ("deposit_ask_id", "سؤال ID الإيداع"),
    ("deposit_ask_amount", "سؤال المبلغ (إيداع)"),
    ("withdraw_ask_amount", "سؤال المبلغ (سحب)"),
    ("deposit_sent", "رسالة إرسال الإيداع"),
    ("withdraw_sent", "رسالة إرسال السحب"),
    ("support_ask_reason", "سؤال الدعم"),
    ("support_sent", "رسالة إرسال الدعم"),
    ("tote", "رسالة tote"),
    ("order_cancelled_user", "رسالة إلغاء الطلب"),
    ("admin_accepted_user", "رسالة قبول الطلب للمستخدم"),
    ("chat_ended_user", "رسالة إنهاء المحادثة"),
]


async def edit_messages_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ هذه الميزة للمالك فقط.")
        return
    btns = []
    for key, label in MESSAGE_KEYS:
        btns.append([InlineKeyboardButton(label, callback_data=f"editm:{key}")])
    await update.message.reply_text(
        "📝 اختر الرسالة التي تريد تعديلها:",
        reply_markup=InlineKeyboardMarkup(btns)
    )
    return ADM_EDIT_MSG_KEY


async def edit_msg_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.split(":")[1]
    ctx.user_data["edit_msg_key"] = key
    current = await get_message(key)
    await query.edit_message_text(
        f"📝 الرسالة الحالية:\n\n{current}\n\nأرسل النص الجديد:\n(اكتب /cancel للإلغاء)"
    )
    return ADM_EDIT_MSG_VAL


async def edit_msg_save(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_TEXT:
        await update.message.reply_text("تم الإلغاء.", reply_markup=admin_menu_kb())
        return ConversationHandler.END
    key = ctx.user_data.get("edit_msg_key")
    await set_message(key, update.message.text)
    await update.message.reply_text("✅ تم تحديث الرسالة!", reply_markup=admin_menu_kb())
    await log_action("edit_message", update.effective_user.id, details=key)
    return ConversationHandler.END


# ══════════════════════════════════════════════
# MANAGE BUTTONS
# ══════════════════════════════════════════════

BUTTON_KEYS = [
    ("deposit",   "زرار الإيداع"),
    ("withdraw",  "زرار السحب"),
    ("tote",      "زرار tote"),
    ("proofs",    "زرار الإثباتات"),
    ("myops",     "زرار عملياتي"),
    ("support",   "زرار الدعم"),
    ("platform1", "اسم زار 1"),
    ("platform2", "اسم زار 2"),
]


async def manage_buttons_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ هذه الميزة للمالك فقط.")
        return
    labels = await get_all_button_labels()
    custom = await get_custom_buttons()

    lines = ["🔘 *إدارة الأزرار*\n\nالأزرار الحالية:"]
    for k, label in BUTTON_KEYS:
        lines.append(f"• {label}: `{labels.get(k, k)}`")
    if custom:
        lines.append("\nأزرار مخصصة:")
        for b in custom:
            lines.append(f"  • `{b[1]}` → {b[2]}")

    btns = []
    for key, label in BUTTON_KEYS:
        btns.append([InlineKeyboardButton(f"✏️ {label}", callback_data=f"editb:{key}")])
    btns.append([InlineKeyboardButton("➕ إضافة زرار مخصص", callback_data="btn_add_custom")])
    if custom:
        btns.append([InlineKeyboardButton("🗑 حذف زرار مخصص", callback_data="btn_del_custom")])

    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(btns),
        parse_mode="Markdown"
    )
    return ADM_EDIT_BTN_KEY


async def edit_btn_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.split(":")[1]
    ctx.user_data["edit_btn_key"] = key
    current = await get_button_label(key)
    await query.edit_message_text(
        f"✏️ القيمة الحالية: *{current}*\n\nأرسل الاسم الجديد:\n(/cancel للإلغاء)",
        parse_mode="Markdown"
    )
    return ADM_EDIT_BTN_VAL


async def edit_btn_save(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_TEXT:
        await update.message.reply_text("تم الإلغاء.", reply_markup=admin_menu_kb())
        return ConversationHandler.END
    key = ctx.user_data.get("edit_btn_key")
    await set_button_label(key, update.message.text.strip())
    await update.message.reply_text("✅ تم تحديث الزرار!", reply_markup=admin_menu_kb())
    await log_action("edit_button", update.effective_user.id, details=key)
    return ConversationHandler.END


async def btn_add_custom_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("➕ أرسل اسم الزرار الجديد:\n(/cancel للإلغاء)")
    return ADM_ADD_CUSTOM_LABEL


async def btn_add_custom_label(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_TEXT:
        await update.message.reply_text("تم الإلغاء.", reply_markup=admin_menu_kb())
        return ConversationHandler.END
    ctx.user_data["new_btn_label"] = update.message.text.strip()
    await update.message.reply_text("🔗 الآن أرسل رابط الزرار:")
    return ADM_ADD_CUSTOM_URL


async def btn_add_custom_url(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_TEXT:
        await update.message.reply_text("تم الإلغاء.", reply_markup=admin_menu_kb())
        return ConversationHandler.END
    label = ctx.user_data.get("new_btn_label", "زرار")
    await add_custom_button(label, update.message.text.strip())
    await update.message.reply_text(f"✅ تم إضافة الزرار: {label}", reply_markup=admin_menu_kb())
    return ConversationHandler.END


async def btn_del_custom(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    custom = await get_custom_buttons()
    if not custom:
        await query.edit_message_text("لا توجد أزرار مخصصة.")
        return ConversationHandler.END
    btns = [[InlineKeyboardButton(f"🗑 {b[1]}", callback_data=f"delbtn:{b[0]}")] for b in custom]
    await query.edit_message_text("اختر الزرار للحذف:", reply_markup=InlineKeyboardMarkup(btns))
    return ADM_EDIT_BTN_KEY


async def btn_del_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    btn_id = int(query.data.split(":")[1])
    await delete_custom_button(btn_id)
    await query.edit_message_text("✅ تم حذف الزرار.")
    return ConversationHandler.END


# ══════════════════════════════════════════════
# SETTINGS
# ══════════════════════════════════════════════

SETTING_KEYS = [
    ("maintenance_mode", "وضع الصيانة (0=إيقاف / 1=تشغيل)"),
    ("deposit_enabled",  "الإيداع (1=مفعّل / 0=موقوف)"),
    ("withdraw_enabled", "السحب (1=مفعّل / 0=موقوف)"),
    ("support_enabled",  "الدعم (1=مفعّل / 0=موقوف)"),
    ("proofs_url",       "رابط جروب الإثباتات"),
]


async def show_settings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ هذه الميزة للمالك فقط.")
        return
    lines = ["⚙️ *الإعدادات الحالية:*\n"]
    for k, label in SETTING_KEYS:
        val = await get_setting(k)
        lines.append(f"• {label}: `{val}`")
    btns = [[InlineKeyboardButton(f"✏️ {l}", callback_data=f"sets:{k}")] for k, l in SETTING_KEYS]
    await update.message.reply_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(btns),
        parse_mode="Markdown"
    )
    return ADM_EDIT_SETTING_KEY


async def setting_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.split(":")[1]
    ctx.user_data["edit_setting_key"] = key
    current = await get_setting(key)
    await query.edit_message_text(
        f"⚙️ القيمة الحالية: `{current}`\n\nأرسل القيمة الجديدة:\n(/cancel للإلغاء)",
        parse_mode="Markdown"
    )
    return ADM_EDIT_SETTING_VAL


async def setting_save(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_TEXT:
        await update.message.reply_text("تم الإلغاء.", reply_markup=admin_menu_kb())
        return ConversationHandler.END
    key = ctx.user_data.get("edit_setting_key")
    await set_setting(key, update.message.text.strip())
    await update.message.reply_text("✅ تم تحديث الإعداد!", reply_markup=admin_menu_kb())
    await log_action("edit_setting", update.effective_user.id, details=key)
    return ConversationHandler.END


# ══════════════════════════════════════════════
# ADD / REMOVE ADMIN (OWNER ONLY)
# ══════════════════════════════════════════════

async def add_admin_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ هذه الميزة للمالك فقط.")
        return
    await update.message.reply_text("👤 أرسل الـ Telegram ID للمشرف الجديد:\n(/cancel للإلغاء)")
    return ADM_ADD_ADMIN


async def add_admin_save(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message.text == CANCEL_TEXT:
        await update.message.reply_text("تم الإلغاء.", reply_markup=admin_menu_kb())
        return ConversationHandler.END
    if not update.message.text.strip().isdigit():
        await update.message.reply_text("⚠️ يرجى إدخال ID صحيح (أرقام فقط).")
        return ADM_ADD_ADMIN
    new_id = int(update.message.text.strip())
    if new_id == get_owner_id():
        await update.message.reply_text("⚠️ هذا المستخدم هو المالك بالفعل.")
        return ConversationHandler.END
    await add_admin(new_id)
    await update.message.reply_text(f"✅ تم تعيين `{new_id}` مشرفًا.", parse_mode="Markdown", reply_markup=admin_menu_kb())
    await log_action("add_admin", update.effective_user.id, new_id)
    return ConversationHandler.END


async def remove_admin_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await is_owner(update.effective_user.id):
        await update.message.reply_text("⛔ هذه الميزة للمالك فقط.")
        return
    admins = await get_admin_list()
    if not admins:
        await update.message.reply_text("لا يوجد مشرفون مضافون.")
        return
    btns = [[InlineKeyboardButton(f"❌ {a[1] or a[0]}", callback_data=f"rmadm:{a[0]}")] for a in admins]
    await update.message.reply_text("اختر المشرف للإزالة:", reply_markup=InlineKeyboardMarkup(btns))
    return ADM_REMOVE_ADMIN


async def remove_admin_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not await is_owner(query.from_user.id):
        await query.answer("⛔ غير مصرح.", show_alert=True)
        return ConversationHandler.END
    await query.answer()
    target_id = int(query.data.split(":")[1])
    await remove_admin(target_id)
    await query.edit_message_text(f"✅ تم إزالة المشرف `{target_id}`.", parse_mode="Markdown")
    await log_action("remove_admin", query.from_user.id, target_id)
    return ConversationHandler.END


# ══════════════════════════════════════════════
# EXIT ADMIN
# ══════════════════════════════════════════════

async def exit_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = await main_menu_kb()
    await update.message.reply_text("👋 خرجت من لوحة الإدارة.", reply_markup=kb)


# ══════════════════════════════════════════════
# CONVERSATIONS BUILDER
# ══════════════════════════════════════════════

def get_handlers():
    broadcast_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📣 إذاعة$"), broadcast_start)],
        states={ADM_BROADCAST: [MessageHandler(filters.ALL, broadcast_send)]},
        fallbacks=[CommandHandler("cancel", _cancel_conv)],
        per_user=True, allow_reentry=True, name="broadcast_conv",
    )

    edit_msg_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📝 تعديل الرسائل$"), edit_messages_menu)],
        states={
            ADM_EDIT_MSG_KEY: [CallbackQueryHandler(edit_msg_select, pattern=r"^editm:")],
            ADM_EDIT_MSG_VAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_msg_save)],
        },
        fallbacks=[CommandHandler("cancel", _cancel_conv)],
        per_user=True, allow_reentry=True, name="edit_msg_conv",
    )

    edit_btn_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🔘 إدارة الأزرار$"), manage_buttons_menu)],
        states={
            ADM_EDIT_BTN_KEY: [
                CallbackQueryHandler(edit_btn_select, pattern=r"^editb:"),
                CallbackQueryHandler(btn_add_custom_start, pattern=r"^btn_add_custom$"),
                CallbackQueryHandler(btn_del_custom, pattern=r"^btn_del_custom$"),
                CallbackQueryHandler(btn_del_confirm, pattern=r"^delbtn:\d+$"),
            ],
            ADM_EDIT_BTN_VAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_btn_save)],
            ADM_ADD_CUSTOM_LABEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, btn_add_custom_label)],
            ADM_ADD_CUSTOM_URL: [MessageHandler(filters.TEXT & ~filters.COMMAND, btn_add_custom_url)],
        },
        fallbacks=[CommandHandler("cancel", _cancel_conv)],
        per_user=True, allow_reentry=True, name="edit_btn_conv",
    )

    settings_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^⚙️ الإعدادات$"), show_settings)],
        states={
            ADM_EDIT_SETTING_KEY: [CallbackQueryHandler(setting_select, pattern=r"^sets:")],
            ADM_EDIT_SETTING_VAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, setting_save)],
        },
        fallbacks=[CommandHandler("cancel", _cancel_conv)],
        per_user=True, allow_reentry=True, name="settings_conv",
    )

    add_admin_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^👤 تعيين مشرف$"), add_admin_start)],
        states={ADM_ADD_ADMIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_admin_save)]},
        fallbacks=[CommandHandler("cancel", _cancel_conv)],
        per_user=True, allow_reentry=True, name="add_admin_conv",
    )

    remove_admin_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^❌ إزالة مشرف$"), remove_admin_start)],
        states={ADM_REMOVE_ADMIN: [CallbackQueryHandler(remove_admin_confirm, pattern=r"^rmadm:\d+$")]},
        fallbacks=[CommandHandler("cancel", _cancel_conv)],
        per_user=True, allow_reentry=True, name="remove_admin_conv",
    )

    return [
        CommandHandler("admin", cmd_admin),
        broadcast_conv,
        edit_msg_conv,
        edit_btn_conv,
        settings_conv,
        add_admin_conv,
        remove_admin_conv,
        MessageHandler(filters.Regex("^📥 طلبات الإيداع$"), show_deposit_orders),
        MessageHandler(filters.Regex("^📤 طلبات السحب$"), show_withdraw_orders),
        MessageHandler(filters.Regex("^📊 الإحصائيات$"), show_stats),
        MessageHandler(filters.Regex("^📜 السجلات$"), show_logs),
        MessageHandler(filters.Regex("^🚪 خروج$"), exit_admin),
    ]
