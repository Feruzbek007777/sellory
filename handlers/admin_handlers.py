# handlers/admin_handlers.py

from telebot import TeleBot, types

from config import ADMIN_IDS, SERVICES
from database import (
    get_stats,
    get_leaderboard,
    export_users_to_excel,
    get_user,
    get_referral_stats,
    get_user_by_username,
    approve_latest_request_for_user,
)
from keyboards import admin_menu_keyboard, main_menu_keyboard
from pending import send_pending_list_to_admin


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def register_admin_handlers(bot: TeleBot):
    # =========================
    #  ADMIN PANELGA KIRISH
    # =========================
    @bot.message_handler(commands=["admin"])
    def admin_panel_entry(message: types.Message):
        user_id = message.from_user.id
        if not is_admin(user_id):
            return

        stats = get_stats()
        text = (
            "👨‍💼 ADMIN PANEL\n\n"
            f"📋 Pending: {stats['pending']} ta\n"
            f"👥 Users: {stats['users']}\n"
            f"🎁 Berilgan: {stats['approved']} ta"
        )
        kb = admin_menu_keyboard()
        bot.send_message(message.chat.id, text, reply_markup=kb, parse_mode=None)

    # =========================
    #  📊 STATS tugmasi
    # =========================
    @bot.message_handler(func=lambda m: m.text == "📊 Stats")
    def admin_stats(message: types.Message):
        if not is_admin(message.from_user.id):
            return

        stats = get_stats()
        text = (
            "📊 Umumiy statistika\n\n"
            f"👥 Foydalanuvchilar: {stats['users']}\n"
            f"📋 Pending so'rovlar: {stats['pending']}\n"
            f"🎁 Tasdiqlangan so'rovlar: {stats['approved']}"
        )
        bot.send_message(message.chat.id, text, parse_mode=None)

    # =========================
    #  📋 PENDING tugmasi
    # =========================
    @bot.message_handler(func=lambda m: m.text == "📋 Pending")
    def admin_pending(message: types.Message):
        if not is_admin(message.from_user.id):
            return

        send_pending_list_to_admin(bot, message.chat.id)

    # =========================
    #  👥 TOP tugmasi
    # =========================
    @bot.message_handler(func=lambda m: m.from_user.id in ADMIN_IDS and m.text == "👥 Top")
    def admin_top(message: types.Message):
        if not is_admin(message.from_user.id):
            return

        chat_id = message.chat.id
        leaders = get_leaderboard(50)

        if not leaders:
            bot.send_message(
                chat_id,
                "Hozircha hech kimda ball yo'q. Foydalanuvchilar hali taklif qilmagan shekilli 🙂",
                parse_mode=None,
            )
            return

        lines = ["TOP foydalanuvchilar:\n"]
        for idx, user in enumerate(leaders, start=1):
            uid = user.get("user_id")
            username = user.get("username") or "-"
            total = user.get("total_points", 0)

            if username != "-":
                display = f"@{username}"
            else:
                display = f"ID: {uid}"

            line = f"{idx}. {display} — {total} ball"
            lines.append(line)

        text = "\n".join(lines)

        bot.send_message(
            chat_id,
            text,
            parse_mode=None,
        )

    # =========================
    #  📥 EXCEL tugmasi
    # =========================
    @bot.message_handler(func=lambda m: m.text == "📥 Excel")
    def admin_export_excel_handler(message: types.Message):
        if not is_admin(message.from_user.id):
            return

        path = "sellory_users.xlsx"
        ok = export_users_to_excel(path)
        if not ok:
            bot.send_message(
                message.chat.id,
                "Excel faylini yaratishda xatolik yuz berdi (openpyxl o'rnatilganligini tekshiring).",
                parse_mode=None,
            )
            return

        try:
            with open(path, "rb") as f:
                bot.send_document(
                    message.chat.id,
                    f,
                    visible_file_name="sellory_users.xlsx",
                    caption="📥 Excel export",
                )
        except FileNotFoundError:
            bot.send_message(message.chat.id, "Excel faylini topib bo'lmadi.", parse_mode=None)

    # =====================================================
    #  📢 BROADCAST – TUGMA ORQALI (2 bosqichli)
    # =====================================================
    @bot.message_handler(func=lambda m: m.text == "📢 Broadcast")
    def admin_broadcast_start_from_button(message: types.Message):
        """Admin menyudagi '📢 Broadcast' tugmasi."""
        if not is_admin(message.from_user.id):
            return

        msg = bot.send_message(
            message.chat.id,
            "Broadcast xabar matnini yuboring.\n"
            "Bu xabar barcha foydalanuvchilarga jo'natiladi.",
            parse_mode=None,
        )
        bot.register_next_step_handler(msg, admin_broadcast_process)

    def admin_broadcast_process(message: types.Message):
        if not is_admin(message.from_user.id):
            return

        text_to_send = (message.text or "").strip()
        if not text_to_send:
            bot.send_message(message.chat.id, "Bo'sh xabar. Bekor qilindi.", parse_mode=None)
            return

        users = get_leaderboard(limit=1000000)
        ids = [u["user_id"] for u in users]

        sent = 0
        for uid in ids:
            try:
                bot.send_message(uid, text_to_send, parse_mode=None)
                sent += 1
            except Exception:
                continue

        bot.send_message(
            message.chat.id,
            f"Broadcast yuborildi: {sent} ta foydalanuvchiga ✅",
            parse_mode=None,
        )

    # (xohlasang ishlatadigan) /broadcast komandasi ham qoladi
    @bot.message_handler(commands=["broadcast"])
    def admin_broadcast_cmd(message: types.Message):
        if not is_admin(message.from_user.id):
            return

        parts = (message.text or "").split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            bot.send_message(
                message.chat.id,
                "Broadcast yuborish uchun:\n"
                "/broadcast Sizning matningiz...",
                parse_mode=None,
            )
            return

        text_to_send = parts[1].strip()
        users = get_leaderboard(limit=1000000)
        ids = [u["user_id"] for u in users]

        sent = 0
        for uid in ids:
            try:
                bot.send_message(uid, text_to_send, parse_mode=None)
                sent += 1
            except Exception:
                continue

        bot.send_message(
            message.chat.id,
            f"Broadcast yuborildi: {sent} ta foydalanuvchiga ✅",
            parse_mode=None,
        )

    # =====================================================
    #  🔍 USERS tugmasi – foydalanuvchi qidirish
    # =====================================================
    @bot.message_handler(func=lambda m: m.text in ("🔍 Users", "👤 Users"))
    def admin_users_search_start(message: types.Message):
        if not is_admin(message.from_user.id):
            return

        msg = bot.send_message(
            message.chat.id,
            "Foydalanuvchini qidirish uchun ID yoki @username yuboring.\n\n"
            "Misollar:\n"
            "123456789\n"
            "@username",
            parse_mode=None,
        )
        bot.register_next_step_handler(msg, admin_users_search_process)

    def admin_users_search_process(message: types.Message):
        if not is_admin(message.from_user.id):
            return

        query = (message.text or "").strip()
        if not query:
            bot.send_message(message.chat.id, "Bo'sh xabar. Qayta urinib ko'ring.", parse_mode=None)
            return

        target = None
        if query.startswith("@"):
            username = query[1:]
            target = get_user_by_username(username)
        elif query.isdigit():
            target = get_user(int(query))

        if not target:
            bot.send_message(message.chat.id, "Foydalanuvchi topilmadi.", parse_mode=None)
            return

        stats = get_referral_stats(target["user_id"])

        lines = []
        lines.append("👤 FOYDALANUVCHI:")
        lines.append("")
        lines.append(f"ID: {target['user_id']}")
        if target.get("username"):
            lines.append(f"Username: @{target['username']}")
        else:
            lines.append("Username: —")

        full_name = (
            f"{target.get('first_name') or ''} {target.get('last_name') or ''}".strip()
        )
        if full_name:
            lines.append(f"Ism: {full_name}")

        lines.append("")
        lines.append(f"Level 1: {stats['level1_count']} ta")
        lines.append(f"Level 2 bonus: {stats['level2_bonus']} ta")
        lines.append(f"Jami ball: {stats['total_points']} ta")

        text = "\n".join(lines)
        bot.send_message(message.chat.id, text, parse_mode=None)

    # =====================================================
    #  🔙 ASOSIY tugmasi – admin menyudan user menyuga
    # =====================================================
    @bot.message_handler(func=lambda m: m.text == "🔙 Asosiy")
    def admin_back_to_main(message: types.Message):
        user = message.from_user
        if not is_admin(user.id):
            return

        kb = main_menu_keyboard(is_admin=True)
        bot.send_message(message.chat.id, "Asosiy menyu.", reply_markup=kb, parse_mode=None)

    # =====================================================
    #  /approve + izoh bosqichi
    # =====================================================
    @bot.message_handler(func=lambda m: (m.text or "").startswith("/approve"))
    def admin_approve(message: types.Message):
        if not is_admin(message.from_user.id):
            return

        parts = (message.text or "").split()
        if len(parts) < 2 or not parts[1].isdigit():
            bot.send_message(
                message.chat.id,
                "Noto'g'ri format.\nTo'g'ri format: /approve 123456",
                parse_mode=None,
            )
            return

        target_id = int(parts[1])

        result = approve_latest_request_for_user(target_id, admin_id=message.from_user.id)
        if not result:
            bot.send_message(
                message.chat.id,
                "Bu foydalanuvchi uchun pending so'rov topilmadi.",
                parse_mode=None,
            )
            return

        svc_key = result["service_key"]
        svc = SERVICES.get(svc_key, {"name": svc_key})
        service_name = svc["name"]

        stats_after = get_referral_stats(target_id)
        total = stats_after["total_points"]
        available = stats_after["available_points"]

        lines = []
        lines.append(f"'{service_name}' so'rovi tasdiqlandi ✅")
        lines.append(f"User ID: {target_id}")
        lines.append(f"Jami ball: {total} ta, mavjud: {available} ta")
        lines.append("")
        lines.append("Endi foydalanuvchiga yuboriladigan izohni yozing.")
        lines.append("Misollar:")
        lines.append("- Shu lichkaga yozib sovg'angizni oling")
        lines.append("- Login: ...  Parol: ...")
        lines.append("")
        lines.append("Bekor qilish uchun /cancel yuboring.")
        prompt = "\n".join(lines)

        msg = bot.send_message(message.chat.id, prompt, parse_mode=None)
        bot.register_next_step_handler(
            msg,
            admin_approve_comment_step,
            target_id,
            service_name,
            total,
            available,
        )

    def admin_approve_comment_step(
        message: types.Message,
        target_id: int,
        service_name: str,
        total: int,
        available: int,
    ):
        if not is_admin(message.from_user.id):
            return

        text = (message.text or "").strip()

        # Admin bekor qilsa – default xabar bilan yuboramiz
        if text.lower() == "/cancel":
            base_lines = []
            base_lines.append("✅ MUKOFOT TAYYOR!")
            base_lines.append("")
            base_lines.append(f"Xizmat: {service_name}")
            base_lines.append(f"Jami ball: {total} ta")
            base_lines.append(f"Mavjud ball: {available} ta")
            user_text = "\n".join(base_lines)

            try:
                bot.send_message(target_id, user_text, parse_mode=None)
            except Exception:
                pass

            bot.send_message(
                message.chat.id,
                "Tasdiq yakunlandi. Izoh yuborilmadi (standart xabar jo'natildi).",
                parse_mode=None,
            )
            return

        # Aks holda – izoh bilan birga
        comment = text

        user_lines = []
        user_lines.append("✅ MUKOFOT TAYYOR!")
        user_lines.append("")
        user_lines.append(f"Xizmat: {service_name}")
        user_lines.append(f"Jami ball: {total} ta")
        user_lines.append(f"Mavjud ball: {available} ta")
        user_lines.append("")
        user_lines.append("Admin izohi:")
        user_lines.append(comment)
        user_text = "\n".join(user_lines)

        try:
            bot.send_message(target_id, user_text, parse_mode=None)
        except Exception:
            pass

        bot.send_message(
            message.chat.id,
            "Tasdiq va izoh foydalanuvchiga yuborildi ✅",
            parse_mode=None,
        )
