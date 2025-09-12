from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from config import TOKEN, PORT, WEBHOOK_URL
from handlers import start, handle_button

def main():
    app = Application.builder().token(TOKEN).build()

    # الأوامر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))

    # تشغيل Webhook
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
