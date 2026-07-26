import logging
import os
from telegram import BotCommand
from telegram.ext import Application

from database.db import init_db
from handlers import deposit, withdraw, support, order_actions, admin_panel, myops, user_menu

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def post_init(app):
    await init_db()
    await app.bot.set_my_commands([
        BotCommand("start", "بدء البوت"),
        BotCommand("cancel", "إلغاء العملية الحالية"),
    ])
    logger.info("✅ قاعدة البيانات جاهزة")


def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN غير موجود في متغيرات البيئة!")

    app = (
        Application.builder()
        .token(token)
        .post_init(post_init)
        .build()
    )

    # group=0 : Relay chat (أعلى أولوية)
    app.add_handler(order_actions.get_relay_handler(), group=0)

    # group=1 : Admin panel
    for h in admin_panel.get_handlers():
        app.add_handler(h, group=1)

    # group=2 : Conversations (deposit / withdraw / support)
    app.add_handler(deposit.get_handler(), group=2)
    app.add_handler(withdraw.get_handler(), group=2)
    app.add_handler(support.get_handler(), group=2)

    # group=3 : Order actions callbacks
    for h in order_actions.get_handlers():
        app.add_handler(h, group=3)

    # group=4 : My operations pagination
    for h in myops.get_handlers():
        app.add_handler(h, group=4)

    # group=5 : User menu
    for h in user_menu.get_handlers():
        app.add_handler(h, group=5)

    logger.info("✅ البوت شغال...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
