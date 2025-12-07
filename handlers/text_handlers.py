# handlers/text_handlers.py
from typing import Optional

from telebot import TeleBot, types

from config import ADMIN_IDS, SERVICES, RETENTION_DAYS
from database import (
    add_or_update_user,
    touch_user_activity,
    get_referral_stats,
    get_level1_users_with_stats,
    get_active_referral_stats,
    get_leaderboard,
    get_user_services,
)
from keyboards import (
    main_menu_keyboard,
    help_menu_keyboard,
    subscription_keyboard,
    services_inline_keyboard,
)
from utils import is_user_subscribed


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def build_ref_link(bot: TeleBot, user_id: int) -> str:
    """
    User uchun referal link: https://t.me/YourBot?start=ref_USERID
    """
    me = bot.get_me()
    return f"https://t.me/{me.username}?start=ref_{user_id}"


def parse_ref_token(args: str) -> Optional[int]:
    if not args:
        return None
    if args.startswith("ref_"):
        ref = args[4:]
        if ref.isdigit():
            return int(ref)
    return None


def send_main_menu(bot: TeleBot, chat_id: int, user_id: int):
    text = (
        "💎 Premium xizmatlar BEPUL!\n\n"
        "Do'stlarni taklif qiling va referal orqali ball to'plang:\n\n"
        "🎁 7 ta = Telegram Gift\n"
        "🤖 20 ta = ChatGPT Plus\n"
        "👑 55 ta = SuperGrok"
    )
    kb = main_menu_keyboard(is_admin=is_admin(user_id))
    bot.send_message(chat_id, text, reply_markup=kb, parse_mode=None)


def register_text_handlers(bot: TeleBot):

    # /start
    @bot.message_handler(commands=["start"])
    def handle_start(message: types.Message):
        user = message.from_user
        chat_id = message.chat.id

        args = ""
        if " " in (message.text or ""):
            args = message.text.split(" ", 1)[1].strip()
        ref_id = parse_ref_token(args)

        # True qaytadi agar user yangi bo'lsa
        is_new = add_or_update_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            referrer_id=ref_id,
        )
        touch_user_activity(user.id)

        # Agar referal orqali birinchi marta kirgan bo'lsa – taklif qilgan odamga xabar
        if is_new and ref_id:
            try:
                inviter_text = (
                    "🎉 Siz yangi foydalanuvchini taklif qildingiz!\n\n"
                    f"👤 Yangi foydalanuvchi: {user.first_name or ''} "
                    f"{'@' + user.username if user.username else ''}\n"
                    "✅ Sizga +1 ball qo'shildi.\n\n"
                    "🔥 Do'stingiz ham odam taklif qilsa, sizga ham bonus ball keladi!"
                )
                bot.send_message(ref_id, inviter_text, parse_mode=None)
            except Exception:
                # agar DM ochilmagan bo'lsa yoki blok bo'lsa – jim o'tib ketamiz
                pass

        # Kanalga obuna tekshirish
        if not is_user_subscribed(bot, user.id):
            text = (
                "✅ Botni ishlatish uchun Selloriy kanaliga obuna bo'ling!\n\n"
                "📢 Kanalga o'ting va obuna bo'ling, so'ngra '✅ Tekshirish' tugmasini bosing."
            )
            kb = subscription_keyboard()
            bot.send_message(chat_id, text, reply_markup=kb, parse_mode=None)
            return

        send_main_menu(bot, chat_id, user.id)

    # 🚀 Boshlash – referal dashboard
    @bot.message_handler(func=lambda m: m.text == "🚀 Boshlash")
    def handle_boshlash(message: types.Message):
        user = message.from_user
        chat_id = message.chat.id
        touch_user_activity(user.id)

        stats = get_referral_stats(user.id)
        ref_link = build_ref_link(bot, user.id)

        l1 = stats["level1_count"]
        l2 = stats["level2_bonus"]
        total = stats["total_points"]

        costs_sorted = sorted(SERVICES.values(), key=lambda s: s["cost"])
        next_service_text = "Mukofotlarga yaqinlashish uchun do'stlarni taklif qiling!"
        for svc in costs_sorted:
            if total < svc["cost"]:
                next_service_text = (
                    f"🎯 Eng yaqin sovg'a: {svc['emoji']} {svc['name']} "
                    f"({svc['cost']} ball)"
                )
                break
        else:
            if costs_sorted:
                next_service_text = (
                    "🎯 Eng qimmat mukofotga ham yetdingiz yoki juda yaqin turibsiz!"
                )

        text = (
            "🔗 Sizning maxsus linkingiz:\n\n"
            f"{ref_link}\n\n"
            "📊 Hozirgi balans:\n"
            f"👥 Level 1: {l1} ta\n"
            f"🔥 Level 2: {l2} ta (25%)\n"
            "━━━━━━━━━━\n"
            f"💎 JAMI: {total} ta\n\n"
            f"{next_service_text}"
        )

        kb = main_menu_keyboard(is_admin=is_admin(user.id))
        bot.send_message(chat_id, text, reply_markup=kb, parse_mode=None)

    # 📱 Share
    @bot.message_handler(func=lambda m: m.text == "📱 Share")
    def handle_share(message: types.Message):
        user = message.from_user
        chat_id = message.chat.id
        touch_user_activity(user.id)

        ref_link = build_ref_link(bot, user.id)

        text = (
            "🔥 Share qiling:\n\n"
            "📱 Instagram Story\n"
            "📱 WhatsApp Status\n"
            "📱 Copy Link\n\n"
            f"{ref_link}\n\n"
            "Taklif matni:\n"
            "💎 ChatGPT Plus BEPUL!\n"
            "15 ta do'st = 1 oy TEKIN! ⚡\n"
            f"{ref_link}"
        )

        kb = main_menu_keyboard(is_admin=is_admin(user.id))
        bot.send_message(chat_id, text, reply_markup=kb, parse_mode=None)

    # 📊 Balans
    @bot.message_handler(func=lambda m: m.text == "📊 Balans")
    def handle_balance(message: types.Message):
        user = message.from_user
        chat_id = message.chat.id
        touch_user_activity(user.id)

        stats = get_referral_stats(user.id)
        services = get_user_services(user.id)

        approved = [s for s in services if s["status"] == "approved"]
        pending = [s for s in services if s["status"] == "pending"]

        l1 = stats["level1_count"]
        l2 = stats["level2_bonus"]
        total = stats["total_points"]
        available = stats["available_points"]

        if approved:
            taken_lines = []
            for s in approved:
                key = s["service_key"]
                svc = SERVICES.get(key)
                name = svc["name"] if svc else key
                taken_lines.append(f"• {name}")
            taken_text = "\n".join(taken_lines)
        else:
            taken_text = "—"

        possible_lines = []
        for key, svc in SERVICES.items():
            emoji = svc["emoji"]
            name = svc["name"]
            cost = svc["cost"]
            mark = "✅" if available >= cost else "❌"
            possible_lines.append(f"{emoji} {name} ({cost}) {mark}")
        possible_text = "\n".join(possible_lines)

        if pending:
            pending_lines = []
            for s in pending:
                key = s["service_key"]
                svc = SERVICES.get(key)
                name = svc["name"] if svc else key
                pending_lines.append(f"• {name} — ⏳ pending")
            pending_text = "\n".join(pending_lines)
        else:
            pending_text = "—"

        text = (
            "💎 BALANS DASHBOARD\n\n"
            f"👥 Level 1: {l1} ta ✅\n"
            f"🔥 Level 2: {l2} ta (25%) 🔥\n"
            "━━━━━━━━━━\n"
            f"💎 JAMI: {total} ta\n"
            f"💎 Mavjud: {available} ta\n\n"
            "✅ Olingan sovg'alar:\n"
            f"{taken_text}\n\n"
            "⏳ PENDING:\n"
            f"{pending_text}\n\n"
            "🎯 Olish mumkin bo'lganlar:\n"
            f"{possible_text}"
        )

        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row(types.KeyboardButton("🎁 Xizmat olish"))
        kb.row(types.KeyboardButton("🔙 Asosiy"))

        bot.send_message(chat_id, text, reply_markup=kb, parse_mode=None)

    # 🎁 Xizmat olish
    @bot.message_handler(func=lambda m: m.text == "🎁 Xizmat olish")
    def handle_services_entry(message: types.Message):
        user = message.from_user
        chat_id = message.chat.id
        touch_user_activity(user.id)

        stats = get_referral_stats(user.id)
        available = stats["available_points"]

        text = (
            "🎁 XIZMAT TANLANG\n\n"
            f"Balans: {available} ta 💎\n"
            "Quyidagi xizmatlardan birini tanlang:"
        )

        kb_inline = services_inline_keyboard(available)
        bot.send_message(chat_id, text, reply_markup=kb_inline, parse_mode=None)

    # 🌐 Network
    @bot.message_handler(func=lambda m: m.text == "🌐 Network")
    def handle_network(message: types.Message):
        user = message.from_user
        chat_id = message.chat.id
        touch_user_activity(user.id)

        stats = get_referral_stats(user.id)
        level1_users = get_level1_users_with_stats(user.id)

        l1 = stats["level1_count"]
        l2_raw = stats["level2_raw"]
        l2_bonus = stats["level2_bonus"]

        lines = ["🌐 SIZNING NETWORK\n"]
        lines.append("👤 Siz")
        if level1_users:
            lines.append(f"├─ 👥 Level 1 ({l1} ta):")
            for child in level1_users[:10]:
                uname = child["username"]
                display = f"@{uname}" if uname else f"ID: {child['user_id']}"
                bonus = int(child["level1_count"] * 0.25)
                lines.append(
                    f"│  ├─ {display} → {child['level1_count']} ta (+{bonus} bonus)"
                )
        else:
            lines.append("├─ 👥 Level 1: 0 ta")

        lines.append(f"└─ 🔥 Level 2: {l2_raw} ta → {l2_bonus} ta bonus\n")

        text = "\n".join(lines)
        kb = main_menu_keyboard(is_admin=is_admin(user.id))
        bot.send_message(chat_id, text, reply_markup=kb, parse_mode=None)

    # 🏆 Top
    @bot.message_handler(func=lambda m: m.text == "🏆 Top")
    def handle_top(message: types.Message):
        user = message.from_user
        chat_id = message.chat.id
        touch_user_activity(user.id)

        leaderboard = get_leaderboard()

        legend_lines = []
        master_lines = []
        user_rank = None
        user_points = 0

        for idx, u in enumerate(leaderboard, start=1):
            total = u["total_points"]
            uname = u["username"]
            display = f"@{uname}" if uname else f"ID: {u['user_id']}"

            if u["user_id"] == user.id:
                user_rank = idx
                user_points = total

            if total >= 50:
                legend_lines.append(f"{idx}. {display} — {total} ta 👑")
            elif total >= 30:
                master_lines.append(f"{idx}. {display} — {total} ta 💎")

        if not legend_lines:
            legend_lines.append("—")
        if not master_lines:
            master_lines.append("—")

        if user_rank is None:
            user_line = "📍 Siz hali reytingga kira olmadingiz."
        else:
            user_line = f"📍 Siz: #{user_rank} — {user_points} ta"

        text = (
            "🏆 TOP USERS\n\n"
            "👑 LEGENDS (50+):\n"
            f"{chr(10).join(legend_lines)}\n\n"
            "💎 MASTERS (30+):\n"
            f"{chr(10).join(master_lines)}\n\n"
            f"{user_line}"
        )

        kb = main_menu_keyboard(is_admin=is_admin(user.id))
        bot.send_message(chat_id, text, reply_markup=kb, parse_mode=None)

    # ❓ Yordam menyu
    @bot.message_handler(func=lambda m: m.text == "❓ Yordam")
    def handle_help(message: types.Message):
        user = message.from_user
        chat_id = message.chat.id
        touch_user_activity(user.id)

        text = (
            "❓ YORDAM / FAQ\n\n"
            "Savollardan birini tanlang yoki to'g'ridan-to'g'ri admin bilan bog'laning."
        )
        kb = help_menu_keyboard()
        bot.send_message(chat_id, text, reply_markup=kb, parse_mode=None)

    @bot.message_handler(func=lambda m: m.text == "📖 Qanday ishlaydi?")
    def help_how(message: types.Message):
        user = message.from_user
        touch_user_activity(user.id)
        text = (
            "📖 QANDAY ISHLAYDI?\n\n"
            "1. /start ni bosing va kanalga obuna bo'ling.\n"
            "2. \"🚀 Boshlash\" orqali o'zingizning referal linkingizni oling.\n"
            "3. Linkni do'stlaringizga ulashing. Ular botga kirsa — sizga ball qo'shiladi.\n"
            "4. Ballarni to'plab, \"🎁 Xizmat olish\" orqali mukofot tanlaysiz."
        )
        bot.send_message(message.chat.id, text, parse_mode=None)

    @bot.message_handler(func=lambda m: m.text == "🔥 2-Level bonus?")
    def help_bonus(message: types.Message):
        user = message.from_user
        touch_user_activity(user.id)
        text = (
            "🔥 2-LEVEL BONUS\n\n"
            "👥 Level 1 — siz bevosita taklif qilgan foydalanuvchilar.\n"
            "🔥 Level 2 — sizning Level 1 foydalanuvchilaringiz taklif qilganlar.\n\n"
            "Har bir Level 2 foydalanuvchi sizga 25% bonus ball beradi (to'planib boradi)."
        )
        bot.send_message(message.chat.id, text, parse_mode=None)

    @bot.message_handler(func=lambda m: m.text == "💎 Mukofot olish?")
    def help_rewards(message: types.Message):
        user = message.from_user
        touch_user_activity(user.id)
        lines = ["💎 MUKOFOTLAR"]
        for svc in SERVICES.values():
            lines.append(f"{svc['emoji']} {svc['name']} — {svc['cost']} ball")
        text = "\n".join(lines)
        bot.send_message(message.chat.id, text, parse_mode=None)

    @bot.message_handler(func=lambda m: m.text == "⏰ Retention check?")
    def help_retention(message: types.Message):
        user = message.from_user
        touch_user_activity(user.id)

        total_stats = get_referral_stats(user.id)
        active_stats = get_active_referral_stats(user.id, days=RETENTION_DAYS)

        old_total = total_stats["total_points"]
        new_total = active_stats["total_points"]
        diff = old_total - new_total

        text = (
            "⏰ RETENTION CHECK\n\n"
            f"Oldingi (umumiy) ballar: {old_total} ta\n"
            f"So'nggi {RETENTION_DAYS} kunda faol: {new_total} ta\n"
            f"Minus (noaktivlar): {diff if diff > 0 else 0} ta"
        )
        bot.send_message(message.chat.id, text, parse_mode=None)

    @bot.message_handler(func=lambda m: m.text == "👥 Do'stlar faol?")
    def help_friends(message: types.Message):
        user = message.from_user
        touch_user_activity(user.id)
        text = (
            "👥 DO'STLAR FAOLLIGI\n\n"
            "Retention tekshiruvi sizning referallaringiz botdan qay darajada foydalanayotganini ko'rsatadi.\n"
            "Do'stlaringiz qancha ko'p faol bo'lsa, shuncha yaxshiroq statistikaga ega bo'lasiz."
        )
        bot.send_message(message.chat.id, text, parse_mode=None)

    # 🔙 Asosiy
    @bot.message_handler(func=lambda m: m.text == "🔙 Asosiy")
    def handle_back_to_main(message: types.Message):
        user = message.from_user
        touch_user_activity(user.id)
        send_main_menu(bot, message.chat.id, user.id)

    # E'TIBOR BER: BU YERDA HECH QANDAY FALLBACK YO'Q.
    # Hech qanday "Men sizni tushunmadim" avtomatik handler yo'q endi.
