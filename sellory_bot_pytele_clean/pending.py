# pending.py
# Pending so'rovlar bilan ishlash: ro'yxatni ko'rsatish + yangi so'rovda adminni ogohlantirish

from telebot import TeleBot

from config import ADMIN_IDS, SERVICES
from database import get_pending_requests, get_user, get_referral_stats


def _format_single_request_plain(req: dict) -> str:
    """
    Bitta pending service_request ni juda oddiy TEXT qilib formatlaymiz.
    Hech qanday Markdown, HTML YO'Q.
    """
    user_id = req["user_id"]
    user = get_user(user_id)
    stats = get_referral_stats(user_id)

    username = user.get("username") or "—"
    first_name = user.get("first_name") or ""
    last_name = user.get("last_name") or ""

    svc_key = req["service_key"]
    svc = SERVICES.get(
        svc_key,
        {"name": svc_key, "emoji": "🎁", "cost": req.get("cost", 0)},
    )

    cost = int(req.get("cost") or svc.get("cost") or 0)

    lines = []
    lines.append(f"ID: {req['id']}")
    lines.append(f"User: @{username} (ID: {user_id})")
    if first_name or last_name:
        lines.append(f"Ism: {first_name} {last_name}".strip())
    lines.append(f"Xizmat: {svc.get('emoji', '🎁')} {svc['name']} — {cost} ball")
    lines.append(
        f"Ballar: jami {stats['total_points']} ta, mavjud {stats['available_points']} ta"
    )
    lines.append(f"Holat: {req['status']}")
    # MUHIM: komandada pastki chiziq yo'q, bo'shliq bilan:
    # /approve <user_id>
    lines.append(f"Tasdiqlash komandasi: /approve {user_id}")

    return "\n".join(lines)


def send_pending_list_to_admin(bot: TeleBot, chat_id: int):
    """
    Admin paneldagi 📋 Pending tugmasi bosilganda chaqiriladi.
    Har bir so'rovni alohida xabar qilib yuboramiz.
    Shunda matn juda oddiy bo'ladi va Markdown/HTML bilan muammo bo'lmaydi.
    """
    pending = get_pending_requests()
    if not pending:
        bot.send_message(chat_id, "Pending so'rovlar yo'q ✅")
        return

    header = "📋 PENDING SO'ROVLAR:\n"
    bot.send_message(chat_id, header)

    for req in pending[:20]:
        text = _format_single_request_plain(req)
        # parse_mode bermaymiz, oddiy text bo'lib ketadi
        bot.send_message(chat_id, text)


def notify_admins_new_request(bot: TeleBot, user_id: int, service_key: str):
    """
    Foydalanuvchi xizmatga ariza yuborgan zahoti barcha ADMINlarga DM qilib xabar yuborish.
    Buni service tanlash joyidan chaqiramiz.
    """
    user = get_user(user_id)
    stats = get_referral_stats(user_id)

    username = user.get("username") or "—"
    first_name = user.get("first_name") or ""
    last_name = user.get("last_name") or ""

    svc = SERVICES.get(service_key, {"name": service_key, "emoji": "🎁", "cost": 0})
    cost = int(svc.get("cost", 0))

    lines = []
    lines.append("🔔 YANGI SO'ROV!")
    lines.append("")
    lines.append(f"User: @{username} (ID: {user_id})")
    if first_name or last_name:
        lines.append(f"Ism: {first_name} {last_name}".strip())
    lines.append(f"Xizmat: {svc.get('emoji', '🎁')} {svc['name']} — {cost} ball")
    lines.append(
        f"Ballar: jami {stats['total_points']} ta, mavjud {stats['available_points']} ta"
    )
    lines.append("")
    # YANA: /approve <user_id>, pastki chiziq yo'q
    lines.append(f"Tasdiqlash uchun: /approve {user_id}")

    text = "\n".join(lines)

    for aid in ADMIN_IDS:
        try:
            bot.send_message(aid, text)
        except Exception:
            continue
