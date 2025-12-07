# points.py
# /givepoint komandasi: admin userga qo'lda ball berishi uchun modul

import sqlite3
from typing import Optional

from telebot import TeleBot, types

from config import ADMIN_IDS, DB_PATH
from database import get_referral_stats


# =========================
# DB HELPER FUNKSIYALAR
# =========================

def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_manual_points_table(cur: sqlite3.Cursor):
    """
    manual_points jadvali borligini kafolatlaymiz.
    STRUKTURA:
      id, user_id, points, reason, created_at
    """
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS manual_points (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            points      INTEGER NOT NULL,
            reason      TEXT,
            created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def find_user_by_username_or_id(identifier: str) -> Optional[dict]:
    """
    identifier: '@username', 'username' yoki '123456789' (ID) bo'lishi mumkin.
    users jadvalidan userni olib kelamiz.
    """
    if not identifier:
        return None

    text = identifier.strip()
    if not text:
        return None

    # boshidagi @ ni olib tashlaymiz (bo'lsa)
    if text.startswith("@"):
        text = text[1:].strip()

    conn = _get_connection()
    cur = conn.cursor()

    user_row = None

    if text.isdigit():
        uid = int(text)
        cur.execute(
            "SELECT * FROM users WHERE user_id = ? LIMIT 1",
            (uid,),
        )
        user_row = cur.fetchone()
    else:
        cur.execute(
            "SELECT * FROM users WHERE username = ? COLLATE NOCASE LIMIT 1",
            (text,),
        )
        user_row = cur.fetchone()

    conn.close()

    if user_row is None:
        return None
    return dict(user_row)


def add_manual_points(user_id: int, points: int, reason: str):
    """
    userga qo'lda ball qo'shamiz:
      1) manual_points log jadvaliga yozamiz
      2) users jadvalidagi extra_points ustuniga qo'shamiz (agar bo'lmasa, ustunni yaratamiz)
    """
    conn = _get_connection()
    cur = conn.cursor()

    # 1) log jadvali (yo'q bo'lsa — yaratamiz)
    _ensure_manual_points_table(cur)

    cur.execute(
        "INSERT INTO manual_points (user_id, points, reason) VALUES (?, ?, ?)",
        (user_id, points, reason),
    )

    # 2) users jadvalida extra_points ustuni bo'lmasa – qo'shamiz
    try:
        cur.execute("ALTER TABLE users ADD COLUMN extra_points INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        # ustun allaqachon mavjud bo'lsa, xato chiqadi – e'tibor bermaymiz
        pass

    cur.execute(
        "UPDATE users SET extra_points = COALESCE(extra_points, 0) + ? WHERE user_id = ?",
        (points, user_id),
    )

    conn.commit()
    conn.close()


def get_manual_points_sum(user_id: int) -> int:
    """
    manual_points jadvalidan user uchun jami berilgan qo'shimcha ballni qaytaradi.
    Jadval bo'lmasa – avval yaratib olamiz.
    """
    conn = _get_connection()
    cur = conn.cursor()

    _ensure_manual_points_table(cur)

    cur.execute(
        "SELECT COALESCE(SUM(points), 0) AS total FROM manual_points WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()

    if row is None:
        return 0
    return int(row["total"])


# =========================
# TELEGRAM HANDLERLAR
# =========================

def register_points_handlers(bot: TeleBot):
    """
    main.py ichidan chaqirasan:
        from points import register_points_handlers
        ...
        register_points_handlers(bot)
    """

    # 1-QADAM: /givepoint komandasi
    @bot.message_handler(commands=["givepoint"])
    def givepoint_start(message: types.Message):
        admin = message.from_user
        chat_id = message.chat.id

        if admin.id not in ADMIN_IDS:
            bot.reply_to(message, "Bu komanda faqat adminlar uchun.")
            return

        msg = bot.send_message(
            chat_id,
            "Kimga ball yuborasiz?\n"
            "Username yoki ID ni kiriting (masalan: @username yoki 123456789).",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, givepoint_get_user)

    # 2-QADAM: Userni tanlash
    def givepoint_get_user(message: types.Message):
        admin = message.from_user
        chat_id = message.chat.id
        text = (message.text or "").strip()

        if admin.id not in ADMIN_IDS:
            bot.reply_to(message, "Siz admin emassiz.")
            return

        if not text:
            msg = bot.send_message(
                chat_id,
                "Matn topilmadi. Qaytadan kiriting: @username yoki ID.",
                parse_mode="HTML",
            )
            bot.register_next_step_handler(msg, givepoint_get_user)
            return

        user_data = find_user_by_username_or_id(text)
        if not user_data:
            bot.send_message(
                chat_id,
                "Bunday foydalanuvchi topilmadi.\n"
                "/givepoint ni qaytadan yozib, boshqa user kiriting.",
                parse_mode="HTML",
            )
            return

        target_id = user_data["user_id"]
        username = user_data.get("username") or "-"
        first_name = user_data.get("first_name") or ""
        last_name = user_data.get("last_name") or ""

        stats = get_referral_stats(target_id)
        total_ref = stats.get("total_points", 0)
        manual_sum = get_manual_points_sum(target_id)
        total_all = total_ref + manual_sum

        text_info = (
            "FOYDALANUVCHI TOPILDI:\n\n"
            f"ID: {target_id}\n"
            f"Username: @{username}\n"
            f"Ism: {first_name} {last_name}\n\n"
            f"Referral ballari: {total_ref}\n"
            f"Qo'shimcha (manual): {manual_sum}\n"
            f"Jami (taxminiy): {total_all}\n\n"
            "Necha ball yubormoqchisiz? (faqat son yozing, masalan: 7)"
        )

        msg = bot.send_message(
            chat_id,
            text_info,
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, givepoint_get_points, user_data)

    # 3-QADAM: Ball miqdori
    def givepoint_get_points(message: types.Message, user_data: dict):
        admin = message.from_user
        chat_id = message.chat.id
        text = (message.text or "").strip()

        if admin.id not in ADMIN_IDS:
            bot.reply_to(message, "Siz admin emassiz.")
            return

        if not text.lstrip("-").isdigit():
            msg = bot.send_message(
                chat_id,
                "Noto'g'ri format. Faqat butun son kiriting (masalan: 7).\n"
                "Qaytadan miqdor kiriting:",
                parse_mode="HTML",
            )
            bot.register_next_step_handler(msg, givepoint_get_points, user_data)
            return

        points = int(text)
        if points == 0:
            msg = bot.send_message(
                chat_id,
                "Ball miqdori 0 bo'lishi mumkin emas.\n"
                "Qaytadan miqdor kiriting:",
                parse_mode="HTML",
            )
            bot.register_next_step_handler(msg, givepoint_get_points, user_data)
            return

        msg = bot.send_message(
            chat_id,
            "Izoh yozing (masalan: \"Konkurs g'olibi\" yoki \"Faol ishtirokchi\").",
            parse_mode="HTML",
        )
        bot.register_next_step_handler(msg, givepoint_get_reason, user_data, points)

    # 4-QADAM: Izoh + DBga yozish
    def givepoint_get_reason(message: types.Message, user_data: dict, points: int):
        admin = message.from_user
        chat_id = message.chat.id
        reason = (message.text or "").strip()

        if admin.id not in ADMIN_IDS:
            bot.reply_to(message, "Siz admin emassiz.")
            return

        if not reason:
            reason = "Admin bonus ball"

        target_id = user_data["user_id"]
        username = user_data.get("username") or "-"

        add_manual_points(target_id, points, reason)

        manual_sum = get_manual_points_sum(target_id)
        stats = get_referral_stats(target_id)
        total_ref = stats.get("total_points", 0)
        total_all = total_ref + manual_sum

        admin_text = (
            "Ball muvaffaqiyatli yuborildi!\n\n"
            f"Foydalanuvchi: @{username} (ID: {target_id})\n"
            f"Berilgan ball: {points}\n"
            f"Izoh: {reason}\n\n"
            f"Referral ballari: {total_ref}\n"
            f"Qo'shimcha (manual): {manual_sum}\n"
            f"Jami (taxminiy): {total_all}"
        )
        bot.send_message(
            chat_id,
            admin_text,
            parse_mode="HTML",
        )

        try:
            user_text = (
                "SIZGA BALL BERILDI! 🎁\n\n"
                f"Ballar: {points}\n"
                f"Sabab: {reason}\n\n"
                "Ballaringiz mukofotlarga yaqinlashtiradi, faol bo'lib turing! 💎"
            )
            bot.send_message(
                target_id,
                user_text,
                parse_mode="HTML",
            )
        except Exception:
            pass

        bot.send_message(
            chat_id,
            "Yana /givepoint ni ishlatishingiz yoki /admin menyuga qaytishingiz mumkin.",
            parse_mode="HTML",
        )
