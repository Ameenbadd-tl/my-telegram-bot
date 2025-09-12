from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from storage import load_data

# تحميل البيانات
DATA = load_data()

# بناء القائمة الرئيسية
def build_main_menu():
    buttons = []
    for key in DATA["buttons"].keys():
        buttons.append([InlineKeyboardButton(key, callback_data=f"menu_{key}")])
    return InlineKeyboardMarkup(buttons)

# التعامل مع /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلا بيك 👋\nاختار من القائمة:", reply_markup=build_main_menu())

# التعامل مع الضغط على زر
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("menu_"):
        key = data.replace("menu_", "")
        # هنا ممكن نضيف فتح القوائم الفرعية أو إرسال ملفات
        await query.edit_message_text(f"إنت اخترت: {key}")
