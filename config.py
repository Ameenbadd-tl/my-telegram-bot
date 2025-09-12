import os

# Telegram Bot Token (حطينا التوكن اللي أعطيتني إياه)
TOKEN = os.getenv("BOT_TOKEN", "7793653598:AAFW5Nk1_DLAKW_eiiA8y3faet3OKD9ym_4")

# إعدادات Webhook
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://اسم-مشروعك.onrender.com")
PORT = int(os.getenv("PORT", 8000))
