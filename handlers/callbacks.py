# handlers/callbacks.py
from telebot import TeleBot, types

from config import ADMIN_IDS, SERVICES
from database import get_referral_stats, create_service_request, get_user_services
from keyboards import subscription_keyboard
from utils import is_user_subscribed
from .text_handlers import send_main_menu
from pending import notify_admins_new_request


def register_callback_handlers(bot: TeleBot):
    @bot.callback_query_handler(func=lambda c: c.data == "check_channel")
    def callback_check_channel(call: types.CallbackQuery):
        user_id = call.from_user.id
        chat_id = call.message.chat.id

        if not is_user_subscribed(bot, user_id):
            bot.answer_callback_query(call.id, "Obuna bo'lmaganga o'xshaysiz.", show_alert=True)
            try:
                bot.edit_message_text(
                    "❌ Obuna bo'lmaganga o'xshaysiz. Iltimos, kanalga obuna bo'ling va qaytadan urining.",
                    chat_id,
                    call.message.message_id,
                    reply_markup=subscription_keyboard(),
                )
            except Exception:
                pass
            return

        bot.answer_callback_query(call.id, "Obuna tasdiqlandi!")
        try:
            bot.edit_message_text(
                "✅ Obuna tasdiqlandi! Endi botdan bemalol foydalanishingiz mumkin.",
                chat_id,
                call.message.message_id,
            )
        except Exception:
            pass

        send_main_menu(bot, chat_id, user_id)

    @bot.callback_query_handler(func=lambda c: c.data.startswith("service"))
    def callback_services(call: types.CallbackQuery):
        user = call.from_user
        chat_id = call.message.chat.id
        data = call.data

        if data == "service_locked":
            bot.answer_callback_query(call.id, "Bu xizmat uchun balans yetarli emas.", show_alert=True)
            return

        if data == "back_to_balance":
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
                "💎 *BALANS DASHBOARD*\n\n"
                f"👥 Level 1: {l1} ta ✅\n"
                f"🔥 Level 2: {l2} ta (25%) 🔥\n"
                "━━━━━━━━━━\n"
                f"💎 TOTAL: {total} ta\n"
                f"💎 Mavjud: {available} ta\n\n"
                "✅ *OLINGAN:*\n"
                f"{taken_text}\n\n"
                "⏳ *PENDING:*\n"
                f"{pending_text}\n\n"
                "🎯 *OLISH MUMKIN:*\n"
                f"{possible_text}"
            )

            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.row(types.KeyboardButton("🎁 Xizmat olish"))
            kb.row(types.KeyboardButton("🔙 Asosiy"))
            bot.send_message(chat_id, text, reply_markup=kb)
            bot.answer_callback_query(call.id)
            return

        if data.startswith("service:"):
            service_key = data.split(":", 1)[1]
            svc = SERVICES.get(service_key)
            if not svc:
                bot.answer_callback_query(call.id, "Xizmat topilmadi.", show_alert=True)
                return

            stats = get_referral_stats(user.id)
            available = stats["available_points"]
            cost = svc["cost"]

            if available < cost:
                bot.answer_callback_query(call.id, "Balansingiz yetarli emas.", show_alert=True)
                return

            create_service_request(user.id, service_key, cost)
            stats_after = get_referral_stats(user.id)
            available_after = stats_after["available_points"]

            text = (
                f"💎 *{svc['name']} TANLANDI!* 🌟\n\n"
                f"📊 Balansingiz: {available} → {available_after}\n\n"
                "Admin xizmatni berishi uchun so‘rov yuborildi.\n"
                "Iltimos kuting, 1–12 soat ichida javob keladi 🔥"
            )

            bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=None)
            bot.answer_callback_query(call.id)

            msg = (
                "🔔 *YANGI SO'ROV!*\n\n"
                f"👤 @{user.username or '—'} (ID: {user.id})\n"
                f"🎁 {svc['name']} ({cost} ta)\n"
                f"/approve_{user.id}"
            )
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, msg)
                except Exception:
                    continue
