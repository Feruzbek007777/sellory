# keyboards.py
from telebot import types
from config import SERVICES, CHANNELS


def main_menu_keyboard(is_admin: bool = False):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    row1 = [types.KeyboardButton("🚀 Boshlash"), types.KeyboardButton("📱 Share")]
    row2 = [types.KeyboardButton("📊 Balans"), types.KeyboardButton("🏆 Top")]
    row3 = [types.KeyboardButton("❓ Yordam")]
    if is_admin:
        row3.append(types.KeyboardButton("👨‍💼 Admin panel"))
    kb.row(*row1)
    kb.row(*row2)
    kb.row(*row3)
    return kb


def help_menu_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(
        types.KeyboardButton("📖 Qanday ishlaydi?"),
        types.KeyboardButton("🔥 2-Level bonus?"),
    )
    kb.row(
        types.KeyboardButton("💎 Mukofot olish?"),
        types.KeyboardButton("⏰ Retention check?"),
    )
    kb.row(
        types.KeyboardButton("👥 Do'stlar faol?"),
        types.KeyboardButton("🔙 Asosiy"),
    )
    return kb


def subscription_keyboard():
    kb = types.InlineKeyboardMarkup()

    # Har bir kanal uchun alohida tugma
    for ch in CHANNELS:
        title = ch.get("title") or "Kanal"
        url = ch.get("url")
        if not url:
            continue
        btn = types.InlineKeyboardButton(f"📱 {title}", url=url)
        kb.add(btn)

    # Oxirida umumiy "Tekshirish" tugmasi
    btn_check = types.InlineKeyboardButton("✅ Tekshirish", callback_data="check_channel")
    kb.add(btn_check)

    return kb


def services_inline_keyboard(available_points: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)

    buttons = []
    for key, svc in SERVICES.items():
        cost = svc["cost"]
        emoji = svc["emoji"]
        name = svc["name"]
        text = f"{emoji} {name} ({cost})"
        # shu yer MUHIM:
        callback_data = f"service:{key}"
        btn = types.InlineKeyboardButton(text, callback_data=callback_data)
        buttons.append(btn)

    kb.add(*buttons)
    return kb


def admin_menu_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(types.KeyboardButton("📊 Stats"), types.KeyboardButton("📋 Pending"))
    kb.row(types.KeyboardButton("👥 Top"), types.KeyboardButton("📥 Excel"))
    kb.row(types.KeyboardButton("📢 Broadcast"), types.KeyboardButton("🔍 Users"))
    kb.row(types.KeyboardButton("🔙 Asosiy"))
    return kb
