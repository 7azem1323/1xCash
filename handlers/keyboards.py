from telegram import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton,
)
from database.db import (
    get_button_label, get_setting, get_custom_buttons
)


# ══════════════════════════════════════════════
# MAIN MENU
# ══════════════════════════════════════════════

async def main_menu_kb() -> ReplyKeyboardMarkup:
    dep     = await get_button_label("deposit")
    wit     = await get_button_label("withdraw")
    tote    = await get_button_label("tote")
    proofs  = await get_button_label("proofs")
    myops   = await get_button_label("myops")
    support = await get_button_label("support")

    # الأزرار المخصصة مرتبة بالـ position
    custom = await get_custom_buttons()

    def custom_at(pos):
        return [KeyboardButton(b[1]) for b in custom if b[3] == pos]

    rows = []

    # position 0 = قبل كل شيء
    if custom_at(0):
        rows.append(custom_at(0))

    rows.append([KeyboardButton(dep), KeyboardButton(wit)])

    # position 1 = بعد الإيداع والسحب
    if custom_at(1):
        rows.append(custom_at(1))

    rows.append([KeyboardButton(tote)])

    # position 2 = بعد tote
    if custom_at(2):
        rows.append(custom_at(2))

    rows.append([KeyboardButton(proofs), KeyboardButton(myops)])

    # position 3 = بعد الإثباتات وعملياتي
    if custom_at(3):
        rows.append(custom_at(3))

    rows.append([KeyboardButton(support)])

    # position 4 = في الآخر (الافتراضي)
    if custom_at(4) or [b for b in custom if b[3] not in (0,1,2,3,4)]:
        remaining = [KeyboardButton(b[1]) for b in custom if b[3] not in (0,1,2,3)]
        if remaining:
            rows.append(remaining)

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def admin_menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([
        ["📥 طلبات الإيداع",    "📤 طلبات السحب"],
        ["💬 المحادثات",         "📣 إذاعة"],
        ["📝 تعديل الرسائل",    "⚙️ الإعدادات"],
        ["🔘 إدارة الأزرار",    "📊 الإحصائيات"],
        ["📜 السجلات",           "👤 تعيين مشرف"],
        ["❌ إزالة مشرف",        "🚪 خروج"],
    ], resize_keyboard=True)


def cancel_inline(text="الغاء 🚫", cb="cancel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=cb)]])


def back_inline(cb="back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("رجوع 🔙", callback_data=cb)]])


# ══════════════════════════════════════════════
# DEPOSIT
# ══════════════════════════════════════════════

async def deposit_platform_kb() -> InlineKeyboardMarkup:
    p1 = await get_button_label("platform1")
    p2 = await get_button_label("platform2")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(p1, callback_data="dep_plat:platform1")],
        [InlineKeyboardButton(p2, callback_data="dep_plat:platform2")],
        [InlineKeyboardButton("الغاء 🚫", callback_data="cancel")],
    ])


async def withdraw_platform_kb() -> InlineKeyboardMarkup:
    p1 = await get_button_label("platform1")
    p2 = await get_button_label("platform2")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(p1, callback_data="wit_plat:platform1")],
        [InlineKeyboardButton(p2, callback_data="wit_plat:platform2")],
        [InlineKeyboardButton("الغاء 🚫", callback_data="cancel")],
    ])


def dep_cancel_order_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("الغاء الطلب 🚫", callback_data=f"dep_cancel:{order_id}")]
    ])


def wit_cancel_order_kb(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("الغاء الطلب 🚫", callback_data=f"wit_cancel:{order_id}")]
    ])


# ══════════════════════════════════════════════
# ADMIN ORDER ACTIONS
# ══════════════════════════════════════════════

def order_admin_kb(order_id: int, order_type: str) -> InlineKeyboardMarkup:
    prefix = "dep" if order_type == "deposit" else "wit"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("قبول الطلب ☑️",        callback_data=f"{prefix}_accept:{order_id}")],
        [InlineKeyboardButton("الاستغناء عن الطلب 🚫", callback_data=f"{prefix}_skip:{order_id}")],
    ])


def support_admin_kb(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("قبول الطلب ☑️",        callback_data=f"sup_accept:{req_id}")],
        [InlineKeyboardButton("الاستغناء عن الطلب 🚫", callback_data=f"sup_skip:{req_id}")],
    ])


def order_accepted_kb(order_id: int, order_type: str) -> InlineKeyboardMarkup:
    prefix = "dep" if order_type == "deposit" else ("wit" if order_type == "withdraw" else "sup")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("طلب مكتمل 🟢",  callback_data=f"{prefix}_done:{order_id}")],
        [InlineKeyboardButton("طلب مرفوض 🔴",  callback_data=f"{prefix}_reject:{order_id}")],
    ])


def support_accepted_kb(req_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("طلب مكتمل 🟢",  callback_data=f"sup_done:{req_id}")],
        [InlineKeyboardButton("طلب مرفوض 🔴",  callback_data=f"sup_reject:{req_id}")],
    ])


def order_completed_view_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تم", callback_data="noop")]
    ])


# ══════════════════════════════════════════════
# MY OPERATIONS PAGINATION
# ══════════════════════════════════════════════

def myops_pagination_kb(page: int, total: int, per_page: int = 5) -> InlineKeyboardMarkup:
    btns = []
    row = []
    if page > 0:
        row.append(InlineKeyboardButton("◀️ السابق", callback_data=f"myops_page:{page-1}"))
    if (page + 1) * per_page < total:
        row.append(InlineKeyboardButton("التالي ▶️", callback_data=f"myops_page:{page+1}"))
    if row:
        btns.append(row)
    return InlineKeyboardMarkup(btns)


# ══════════════════════════════════════════════
# PROOFS
# ══════════════════════════════════════════════

async def proofs_inline_kb() -> InlineKeyboardMarkup:
    url = await get_setting("proofs_url") or "https://t.me/theproofs"
    label = await get_button_label("proofs")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, url=url)]
    ])
