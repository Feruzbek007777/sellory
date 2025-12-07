# handlers/service_callbacks.py
from telebot import TeleBot, types

from config import SERVICES
from database import get_referral_stats, create_service_request
from pending import notify_admins_new_request


def register_service_callbacks(bot: TeleBot):
    """
    Xizmat tanlash uchun callback handlerlar.
    services_inline_keyboard() dagi tugmalar callback_data: 'service:<key>' bo'lishi kerak.
    """

    @bot.callback_query_handler(func=lambda c: c.data.startswith("service:"))
    def handle_service_choice(call: types.CallbackQuery):
        user = call.from_user
        chat_id = call.message.chat.id

        # callback_data: 'service:chatgpt' yoki 'service:gift' kabi
        data = call.data or ""
        try:
            service_key = data.split(":", 1)[1]
        except IndexError:
            bot.answer_callback_query(call.id, "Xizmat topilmadi.", show_alert=True)
            return

        svc = SERVICES.get(service_key)
        if not svc:
            bot.answer_callback_query(call.id, "Xizmat topilmadi.", show_alert=True)
            return

        # User statistikasi va balans
        stats = get_referral_stats(user.id)
        available = stats["available_points"]
        total = stats["total_points"]
        cost = int(svc["cost"])

        if available < cost:
            bot.answer_callback_query(
                call.id,
                f"Balansingiz yetarli emas. Kerak: {cost}, sizda: {available}.",
                show_alert=True,
            )
            return

        # DB ga pending so'rov qo'shamiz
        create_service_request(user.id, service_key, cost)

        # Adminlarga DM qilib xabar beramiz
        notify_admins_new_request(bot, user.id, service_key)

        # Callbackga qisqa javob (alert yoq)
        bot.answer_callback_query(call.id, "So'rovingiz adminga yuborildi ✅", show_alert=False)

        # Foydalanuvchiga xabar (eski xabarni o'zgartiramiz)
        text = (
            "💎 Xizmat so'rovi qabul qilindi!\n\n"
            f"Siz tanlagan xizmat: {svc['name']} ({cost} ball)\n"
            f"Jami ballaringiz: {total} ta, mavjud: {available - cost} ta.\n\n"
            "Admin so'rovingizni ko'rib chiqadi va 1–12 soat ichida javob beradi."
        )

        try:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=call.message.message_id,
                text=text,
            )
        except Exception:
            # Agar edit xato bersa (masalan, o'chib ketgan bo'lsa) – alohida xabar yuboramiz
            bot.send_message(chat_id, text)
