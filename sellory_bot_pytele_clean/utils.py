# utils.py
from telebot import TeleBot
from config import CHANNELS


def is_user_subscribed(bot: TeleBot, user_id: int) -> bool:
    """
    Bir nechta kanal bo'yicha obuna tekshirish.

    - Agar kanal uchun `username` berilgan bo'lsa (@kanal),
      get_chat_member orqali HAQIQIY tekshiruv qilinadi.
    - Agar faqat `url` (invite link) bo'lsa, tekshiruv SKIP qilinadi
      (Telegram API linkdan obuna tekshirishga ruxsat bermaydi).

    Natija:
      - Agar hech bo'lmaganda bitta `username`-li kanalga obuna bo'lmasa -> False.
      - Agar barcha `username`-li kanallar bo'yicha "member/admin/creator" bo'lsa -> True.
      - Agar umuman `username`-li kanal bo'lmasa, faqat linklar bo'lsa -> True
        (faqat "bosib kir" darajasida ishlaydi).
    """
    if not CHANNELS:
        # Kanallar configda bo'lmasa, tekshiruv yo'q
        return True

    # Hech bo'lmaganda bitta real check bo'ldimi yoki yo'q
    any_username_channel = False

    for ch in CHANNELS:
        username = ch.get("username")
        if not username:
            # faqat link berilgan (private kanal / invite link) -> tekshiruvni o'tkazib yuboramiz
            continue

        any_username_channel = True

        try:
            member = bot.get_chat_member(username, user_id)
            if member.status not in ["member", "administrator", "creator"]:
                # Shu kanalga obuna emas -> darrov False
                return False
        except Exception:
            # Chat topilmadi, bot admin emas, user yo'q va hokazo -> obuna emas deb hisoblaymiz
            return False

    # Agar birorta ham username kanal bo'lmasa, faqat linklar bo'lsa -> obuna tekshiruvini o'tdi deb hisoblaymiz
    if not any_username_channel:
        return True

    # Barcha username-kanallarda member bo'lsa
    return True
