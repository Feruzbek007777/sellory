# config.py

# Bot token
BOT_TOKEN = "7321407043:AAGqrJYfqWZO8wIkNNTnfMhikmDArvWQuF4"

# Adminlar ro'yxati
ADMIN_IDS = [
    6587587517,
    1702195778,
]

# Kanallar ro'yxati (bitta yoki bir nechta)
# title  - tugmada chiqadigan nom
# username - agar public bo'lsa: "@kanal_nomi" (ixtiyoriy, private + faqat link bo'lsa None qoldir)
# url    - kanalga invite/link (private bo'lsa ham bo'ladi)
CHANNELS = [
    {
        "title": "Selloriy kanal",
        "username": None,  # public bo'lsa masalan "@selloriy_official", hozir private bo'lgani uchun None qoldiramiz
        "url": "https://t.me/+kHb0wbA7oIwxZTAy",
    },
    # xohlasang keyin shu yerga yana kanal qo'shasan:
    # {
    #     "title": "Yana bir kanal",
    #     "username": "@yana_bir_kanal",
    #     "url": "https://t.me/yana_bir_kanal",
    # },
]

# SQLite fayl nomi
DB_PATH = "sellory.db"

# Level2 bonus foizi (0.25 = 25%)
REFERRAL_BONUS_LEVEL2 = 0.25

# Retention tekshirish kunlari
RETENTION_DAYS = 30

# Xizmatlar ro'yxati
SERVICES = {
    "gift": {
        "key": "gift",
        "emoji": "🎁",
        "name": "Telegram Gift",
        "cost": 7,
    },
    "canva": {
        "key": "canva",
        "emoji": "🎨",
        "name": "Canva Pro",
        "cost": 10,
    },
    "capcut": {
        "key": "capcut",
        "emoji": "🎬",
        "name": "CapCut Pro",
        "cost": 15,
    },
    "perplexity": {
        "key": "perplexity",
        "emoji": "🔍",
        "name": "Perplexity",
        "cost": 15,
    },
    "gemini": {
        "key": "gemini",
        "emoji": "✨",
        "name": "Gemini Advanced",
        "cost": 18,
    },
    "chatgpt": {
        "key": "chatgpt",
        "emoji": "🤖",
        "name": "ChatGPT Plus",
        "cost": 20,
    },
    "tpremium": {
        "key": "tpremium",
        "emoji": "📱",
        "name": "Telegram Premium",
        "cost": 29,
    },
    "supergrok": {
        "key": "supergrok",
        "emoji": "👑",
        "name": "SuperGrok",
        "cost": 55,
    },
}
