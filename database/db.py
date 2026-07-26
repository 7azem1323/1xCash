import aiosqlite
import os
import json

DB_PATH = "data/bot.db"
os.makedirs("data", exist_ok=True)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                full_name   TEXT,
                joined_at   TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS admins (
                user_id     INTEGER PRIMARY KEY,
                username    TEXT,
                added_at    TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS orders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                type            TEXT NOT NULL,
                platform        TEXT,
                account_id      TEXT,
                amount          TEXT,
                user_id         INTEGER NOT NULL,
                user_mention    TEXT,
                user_full_name  TEXT,
                status          TEXT DEFAULT 'pending',
                accepted_by     INTEGER,
                reject_reason   TEXT,
                cancel_msg_ids  TEXT,
                created_at      TEXT DEFAULT (datetime('now')),
                updated_at      TEXT
            );

            CREATE TABLE IF NOT EXISTS support_requests (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id         INTEGER NOT NULL,
                user_mention    TEXT,
                reason          TEXT,
                status          TEXT DEFAULT 'pending',
                accepted_by     INTEGER,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS admin_order_skipped (
                order_id    INTEGER,
                admin_id    INTEGER,
                PRIMARY KEY (order_id, admin_id)
            );

            CREATE TABLE IF NOT EXISTS active_chats (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER UNIQUE,
                admin_id    INTEGER,
                order_id    INTEGER,
                order_type  TEXT,
                started_at  TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS settings (
                key     TEXT PRIMARY KEY,
                value   TEXT
            );

            CREATE TABLE IF NOT EXISTS messages (
                key     TEXT PRIMARY KEY,
                value   TEXT
            );

            CREATE TABLE IF NOT EXISTS button_labels (
                key     TEXT PRIMARY KEY,
                value   TEXT
            );

            CREATE TABLE IF NOT EXISTS custom_buttons (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                label       TEXT,
                url         TEXT,
                position    INTEGER DEFAULT 0,
                visible     INTEGER DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS counters (
                name    TEXT PRIMARY KEY,
                value   INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS logs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                action      TEXT,
                admin_id    INTEGER,
                target_id   INTEGER,
                details     TEXT,
                created_at  TEXT DEFAULT (datetime('now'))
            );
        """)
        await db.commit()
    await _insert_defaults()


async def _insert_defaults():
    async with aiosqlite.connect(DB_PATH) as db:
        # Counters
        for name in ("deposit", "withdraw", "support"):
            await db.execute("INSERT OR IGNORE INTO counters (name,value) VALUES (?,0)", (name,))

        # Settings
        for k, v in {
            "maintenance_mode": "0",
            "deposit_enabled": "1",
            "withdraw_enabled": "1",
            "support_enabled": "1",
            "proofs_url": "https://t.me/theproofs",
        }.items():
            await db.execute("INSERT OR IGNORE INTO settings (key,value) VALUES (?,?)", (k, v))

        # Messages
        for k, v in {
            "welcome": (
                "👋 أهلاً بك في البوت\n\n"
                "استخدم الأزرار أدناه للبدء."
            ),
            "deposit_intro": (
                "خدمة الايداع 📥\n\n"
                "💠 اهلا بك يا {mention}\n\n"
                "شكراً لاستخدامك خدماتنا\n\n"
                "ونتمنى لك تجربة آمنة وسلسة\n\n"
                "✳️ يرجى اختيار الزر:"
            ),
            "withdraw_intro": (
                "خدمة السحب 📤\n\n"
                "💠 اهلا بك يا {mention}\n\n"
                "شكراً لاستخدامك خدماتنا\n\n"
                "ونتمنى لك تجربة آمنة وسلسة\n\n"
                "✳️ يرجى اختيار الزر:"
            ),
            "deposit_ask_id": "💠 ادخل الـ ID الخاص بك في {platform}:",
            "deposit_ask_amount": "💶 ادخل المبلغ المراد إيداعه:",
            "deposit_sent": (
                "⏳ تم إرسال طلب الإيداع بنجاح!\n\n"
                "سيتم الرد عليك من قبل الإدارة في أقرب وقت."
            ),
            "withdraw_ask_amount": "💶 ادخل المبلغ المراد سحبه:",
            "withdraw_sent": (
                "⏳ تم إرسال طلب السحب بنجاح!\n\n"
                "سيتم الرد عليك من قبل الإدارة في أقرب وقت."
            ),
            "support_ask_reason": "🎧 يرجى إدخال سبب طلب الدعم:",
            "support_sent": "⏳ تم إرسال طلب الدعم الفني للمشرفين وسيتم الرد عليك في أقرب وقت ⏳",
            "tote": "🔔 تابعنا للمزيد من العروض والأخبار.",
            "order_cancelled_user": "✅ تم إلغاء طلبك بنجاح.",
            "admin_accepted_user": "🟢 أنت الآن متصل مع المشرف {mention}",
            "chat_ended_user": "✅ تم إنهاء المحادثة.",
        }.items():
            await db.execute("INSERT OR IGNORE INTO messages (key,value) VALUES (?,?)", (k, v))

        # Button labels
        for k, v in {
            "deposit":  "ايداع - Deposit 📥",
            "withdraw": "سحب - Withdraw 📤",
            "tote":     "tote",
            "proofs":   "جروب الاثباتات 🧾",
            "myops":    "عملياتي - transaction 📋",
            "support":  "الدعم - Support 🎧",
            "platform1": "زار 1",
            "platform2": "زار 2",
        }.items():
            await db.execute("INSERT OR IGNORE INTO button_labels (key,value) VALUES (?,?)", (k, v))

        await db.commit()


# ══════════════════════════════════════════════
# COUNTERS
# ══════════════════════════════════════════════

async def next_counter(name: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE counters SET value=value+1 WHERE name=?", (name,))
        await db.commit()
        async with db.execute("SELECT value FROM counters WHERE name=?", (name,)) as cur:
            r = await cur.fetchone()
            return r[0] if r else 1


# ══════════════════════════════════════════════
# USERS
# ══════════════════════════════════════════════

async def register_user(user_id, username, full_name):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id,username,full_name) VALUES (?,?,?)",
            (user_id, username or "", full_name or "")
        )
        await db.commit()


async def get_all_users():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM users") as cur:
            return [r[0] for r in await cur.fetchall()]


# ══════════════════════════════════════════════
# ADMINS
# ══════════════════════════════════════════════

def get_owner_id() -> int:
    return int(os.getenv("ADMIN_ID", "0"))


async def is_owner(user_id: int) -> bool:
    return user_id == get_owner_id()


async def is_admin(user_id: int) -> bool:
    if user_id == get_owner_id():
        return True
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone() is not None


async def get_all_admins() -> list[int]:
    owner = get_owner_id()
    result = [owner]
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id FROM admins") as cur:
            for r in await cur.fetchall():
                if r[0] not in result:
                    result.append(r[0])
    return result


async def add_admin(user_id: int, username: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO admins (user_id,username) VALUES (?,?)",
            (user_id, username)
        )
        await db.commit()


async def remove_admin(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM admins WHERE user_id=?", (user_id,))
        await db.commit()


async def get_admin_list():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT user_id,username,added_at FROM admins") as cur:
            return await cur.fetchall()


# ══════════════════════════════════════════════
# SETTINGS & MESSAGES & BUTTONS
# ══════════════════════════════════════════════

async def get_setting(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            r = await cur.fetchone()
            return r[0] if r else ""


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, value))
        await db.commit()


async def get_message(key: str) -> str:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM messages WHERE key=?", (key,)) as cur:
            r = await cur.fetchone()
            return r[0] if r else f"[{key}]"


async def set_message(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO messages (key,value) VALUES (?,?)", (key, value))
        await db.commit()


async def get_button_label(key: str) -> str:
    defaults = {
        "deposit": "ايداع - Deposit 📥",
        "withdraw": "سحب - Withdraw 📤",
        "tote": "tote",
        "proofs": "جروب الاثباتات 🧾",
        "myops": "عملياتي - transaction 📋",
        "support": "الدعم - Support 🎧",
        "platform1": "زار 1",
        "platform2": "زار 2",
    }
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM button_labels WHERE key=?", (key,)) as cur:
            r = await cur.fetchone()
            return r[0] if r else defaults.get(key, key)


async def set_button_label(key: str, value: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO button_labels (key,value) VALUES (?,?)", (key, value))
        await db.commit()


async def get_all_button_labels() -> dict:
    keys = ["deposit", "withdraw", "tote", "proofs", "myops", "support", "platform1", "platform2"]
    result = {}
    for k in keys:
        result[k] = await get_button_label(k)
    return result


async def get_custom_buttons():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id,label,url,position FROM custom_buttons WHERE visible=1 ORDER BY position"
        ) as cur:
            return await cur.fetchall()


async def add_custom_button(label, url, position=0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO custom_buttons (label,url,position) VALUES (?,?,?)",
            (label, url, position)
        )
        await db.commit()


async def delete_custom_button(btn_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM custom_buttons WHERE id=?", (btn_id,))
        await db.commit()


# ══════════════════════════════════════════════
# ORDERS
# ══════════════════════════════════════════════

async def create_order(
    order_type, platform, account_id, amount,
    user_id, user_mention, user_full_name
) -> tuple[int, int]:
    seq = await next_counter(order_type)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            """INSERT INTO orders
               (type,platform,account_id,amount,user_id,user_mention,user_full_name)
               VALUES (?,?,?,?,?,?,?)""",
            (order_type, platform, account_id, amount, user_id, user_mention, user_full_name)
        )
        await db.commit()
        return cur.lastrowid, seq


async def get_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM orders WHERE id=?", (order_id,)) as cur:
            return await cur.fetchone()


async def update_order(order_id: int, **kwargs):
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [order_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE orders SET {fields}, updated_at=datetime('now') WHERE id=?",
            values
        )
        await db.commit()


async def skip_order(order_id: int, admin_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO admin_order_skipped (order_id,admin_id) VALUES (?,?)",
            (order_id, admin_id)
        )
        await db.commit()


async def has_admin_skipped(order_id: int, admin_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM admin_order_skipped WHERE order_id=? AND admin_id=?",
            (order_id, admin_id)
        ) as cur:
            return await cur.fetchone() is not None


async def get_orders_list(order_type: str = None, status: str = None, limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        q = "SELECT id,type,platform,amount,user_mention,status,created_at FROM orders WHERE 1=1"
        p = []
        if order_type:
            q += " AND type=?"; p.append(order_type)
        if status:
            q += " AND status=?"; p.append(status)
        q += " ORDER BY id DESC LIMIT ?"
        p.append(limit)
        async with db.execute(q, p) as cur:
            return await cur.fetchall()


async def get_user_orders(user_id: int, page: int = 0, per_page: int = 5):
    offset = page * per_page
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id,type,platform,amount,status,created_at FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ? OFFSET ?",
            (user_id, per_page, offset)
        ) as cur:
            rows = await cur.fetchall()
        async with db.execute(
            "SELECT COUNT(*) FROM orders WHERE user_id=?", (user_id,)
        ) as cur:
            total = (await cur.fetchone())[0]
    return rows, total


async def get_stats():
    async with aiosqlite.connect(DB_PATH) as db:
        users = (await (await db.execute("SELECT COUNT(*) FROM users")).fetchone())[0]
        dep_p = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE type='deposit' AND status='pending'")).fetchone())[0]
        dep_c = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE type='deposit' AND status='completed'")).fetchone())[0]
        dep_r = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE type='deposit' AND status='rejected'")).fetchone())[0]
        wit_p = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE type='withdraw' AND status='pending'")).fetchone())[0]
        wit_c = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE type='withdraw' AND status='completed'")).fetchone())[0]
        wit_r = (await (await db.execute("SELECT COUNT(*) FROM orders WHERE type='withdraw' AND status='rejected'")).fetchone())[0]
        sup_p = (await (await db.execute("SELECT COUNT(*) FROM support_requests WHERE status='pending'")).fetchone())[0]
    return dict(
        users=users,
        dep_p=dep_p, dep_c=dep_c, dep_r=dep_r,
        wit_p=wit_p, wit_c=wit_c, wit_r=wit_r,
        sup_p=sup_p,
    )


# ══════════════════════════════════════════════
# SUPPORT REQUESTS
# ══════════════════════════════════════════════

async def create_support_request(user_id, user_mention, reason) -> tuple[int, int]:
    seq = await next_counter("support")
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO support_requests (user_id,user_mention,reason) VALUES (?,?,?)",
            (user_id, user_mention, reason)
        )
        await db.commit()
        return cur.lastrowid, seq


async def get_support_request(req_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM support_requests WHERE id=?", (req_id,)) as cur:
            return await cur.fetchone()


async def update_support_request(req_id: int, **kwargs):
    fields = ", ".join(f"{k}=?" for k in kwargs)
    values = list(kwargs.values()) + [req_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE support_requests SET {fields} WHERE id=?", values)
        await db.commit()


# ══════════════════════════════════════════════
# ACTIVE CHATS
# ══════════════════════════════════════════════

async def start_chat(user_id, admin_id, order_id, order_type):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM active_chats WHERE user_id=?", (user_id,))
        await db.execute(
            "INSERT INTO active_chats (user_id,admin_id,order_id,order_type) VALUES (?,?,?,?)",
            (user_id, admin_id, order_id, order_type)
        )
        await db.commit()


async def get_chat_by_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM active_chats WHERE user_id=?", (user_id,)
        ) as cur:
            return await cur.fetchone()


async def get_chat_by_admin(admin_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM active_chats WHERE admin_id=?", (admin_id,)
        ) as cur:
            return await cur.fetchone()


async def end_chat(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM active_chats WHERE user_id=?", (user_id,))
        await db.commit()


# ══════════════════════════════════════════════
# LOGS
# ══════════════════════════════════════════════

async def log_action(action, admin_id=None, target_id=None, details=""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO logs (action,admin_id,target_id,details) VALUES (?,?,?,?)",
            (action, admin_id, target_id, details)
        )
        await db.commit()


async def get_logs(limit: int = 20):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT action,admin_id,target_id,details,created_at FROM logs ORDER BY id DESC LIMIT ?",
            (limit,)
        ) as cur:
            return await cur.fetchall()
