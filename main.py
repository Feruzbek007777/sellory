# main.py
import logging

from telebot import TeleBot

from config import BOT_TOKEN
from database import init_db
from handlers.text_handlers import register_text_handlers
from handlers.callbacks import register_callback_handlers
from handlers.admin_handlers import register_admin_handlers
from points import register_points_handlers
from handlers.service_callbacks import register_service_callbacks


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = TeleBot(BOT_TOKEN)   # hech qanday parse_mode bermaymiz
bot.parse_mode = None


def main():
    # DB yaratish / migrate
    init_db()

    # Handlers ro'yxatdan o'tkazish
    register_text_handlers(bot)
    register_callback_handlers(bot)
    register_admin_handlers(bot)
    register_points_handlers(bot)
    register_service_callbacks(bot)


    logger.info("Selloriy bot (pyTelegramBotAPI, modular, clean) ishga tushdi...")
    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    main()
