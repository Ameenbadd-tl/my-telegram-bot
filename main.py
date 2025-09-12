import json
import os
from typing import Dict, Any, Optional, List

from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ===== إعداداتك =====
TOKEN = "7793653598:AAFW5Nk1_DLAKW_eiiA8y3faet3OKD9ym_4"
ADMIN_ID = 6085506848
DATA_FILE = "data.json"
SECRET_CHAT_LOG = "secret_chat_log.json"

# ===== حالات المحادثات =====
(
    ADMIN_ADD_BTN_SELECT_PARENT,
    ADMIN_ADD_BTN_ENTER_NAME,
    ADMIN_ADD_BTN_CHOOSE_TYPE,
    ADMIN_ATTACH_FILES_WAIT,
    ADMIN_DELETE_BTN_SELECT,
    USER_SECRET_CHAT_WAIT,
    ADMIN_SECRET_CHAT_WAIT,
    ADMIN_MANAGE_WELCOME_WAIT,
    ADMIN_BROADCAST_WAIT,
    ADMIN_BAN_USER_WAIT,
) = range(10)

# ===== التحميل/الحفظ =====
def load_data() -> Dict[str, Any]:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "buttons": {},
        "user_data": {},
        "welcome_message": None,
        "banned_users": [],
        "bot_status": "online",
    }

def save_data(data: Dict[str, Any]) -> None:
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)

def load_secret_chat_log() -> Dict[str, Any]:
    if os.path.exists(SECRET_CHAT_LOG):
        with open(SECRET_CHAT_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"chats": {}}

def save_secret_chat_log(log: Dict[str, Any]) -> None:
    tmp = SECRET_CHAT_LOG + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SECRET_CHAT_LOG)

DATA = load_data()
SECRET_CHAT_DATA = load_secret_chat_log()

# ===== مساعدات عامة =====
def ensure_main_menu() -> None:
    if "main" not in DATA["buttons"]:
        DATA["buttons"]["main"] = {
            "type": "menu",
            "parent": None,
            "items": [],
            "files": [],
        }
        save_data(DATA)

def get_parent(name: str) -> Optional[str]:
    node = DATA["buttons"].get(name)
    return node.get("parent") if node else None

def build_user_keyboard(menu_name: str = "main") -> ReplyKeyboardMarkup:
    node = DATA["buttons"].get(menu_name)
    rows: List[List[KeyboardButton]] = []
    
    if node and node["type"] == "menu":
        for child in node.get("items", []):
            rows.append([KeyboardButton(child)])

    nav_row: List[KeyboardButton] = []
    parent = node.get("parent")
    if parent:
        nav_row.append(KeyboardButton("⬅️ رجوع"))
    if nav_row:
        rows.append(nav_row)

    main_buttons = [
        KeyboardButton("🏠 الرئيسية"),
        KeyboardButton("💬 دردشة سرية"),
    ]
    rows.append(main_buttons)
    
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)
    
def build_secret_chat_keyboard() -> ReplyKeyboardMarkup:
    """Creates a keyboard for secret chat, including a done button."""
    return ReplyKeyboardMarkup([
        [KeyboardButton("✅ إنهاء الدردشة")],
    ], resize_keyboard=True)

def build_admin_keyboard() -> InlineKeyboardMarkup:
    status_text = "🟢 البوت يعمل" if DATA.get("bot_status") == "online" else "🔴 البوت متوقف"
    rows = [
        [InlineKeyboardButton("➕ إضافة زر", callback_data="admin|add_btn"), InlineKeyboardButton("🗑️ حذف زر/ملف", callback_data="admin|delete_btn")],
        [InlineKeyboardButton("📎 إرفاق ملفات لزر", callback_data="admin|attach_existing"), InlineKeyboardButton("👀 معاينة البوت", callback_data="admin|preview")],
        [InlineKeyboardButton("🧾 عرض البنية", callback_data="admin|tree"), InlineKeyboardButton("📊 الإحصائيات", callback_data="admin|stats")],
        [InlineKeyboardButton("✉️ إدارة رسالة الترحيب", callback_data="admin|manage_welcome")],
        [InlineKeyboardButton("📢 بث رسالة للجميع", callback_data="admin|broadcast"), InlineKeyboardButton(status_text, callback_data="admin|toggle_status")],
        [InlineKeyboardButton("🚫 إدارة المستخدمين المحظورين", callback_data="admin|ban_user")],
        [InlineKeyboardButton("🔄 تحديث اللوحة", callback_data="admin|refresh")],
    ]
    return InlineKeyboardMarkup(rows)

def render_path(name: str) -> str:
    path = []
    cur = name
    while cur:
        path.append(cur)
        cur = get_parent(cur)
    return " / ".join(reversed(path))

def dump_tree() -> str:
    if "main" not in DATA["buttons"]:
        return "لا توجد بيانات."
    lines: List[str] = []

    def dfs(name: str, depth: int = 0):
        node = DATA["buttons"][name]
        prefix = "  " * depth + ("- " if depth else "")
        if node["type"] == "menu":
            lines.append(f"{prefix}📂 {name} (menu) children={len(node['items'])}")
            for c in node["items"]:
                dfs(c, depth + 1)
        else:
            lines.append(f"{prefix}📁 {name} (files={len(node['files'])})")

    dfs("main")
    return "\n".join(lines)

# ===== واجهة المستخدم =====
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    
    if user_id in DATA.get("banned_users", []):
        await update.message.reply_text("❌ لقد تم حظرك من استخدام هذا البوت.")
        return
        
    if DATA.get("bot_status") != "online" and user_id != str(ADMIN_ID):
        await update.message.reply_text("🛠️ البوت في وضع الصيانة حاليًا. نعتذر على الإزعاج.")
        return

    first_time = user_id not in DATA.get("user_data", {})
    
    if first_time:
        if "user_data" not in DATA:
            DATA["user_data"] = {}
        
        # حفظ بيانات المستخدم الجديد
        DATA["user_data"][user_id] = {
            "first_name": user.first_name,
            "last_name": user.last_name,
            "username": user.username,
            "started": True,
        }
        save_data(DATA)
        
        # إرسال إشعار للمدير
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 مستخدم جديد انضم للبوت:\n\n- ID: {user_id}\n- الاسم: {user.first_name} {user.last_name or ''}\n- اليوزر: @{user.username or 'غير متاح'}"
        )
        
        # عرض رسالة الترحيب
        welcome_msg = DATA.get("welcome_message")
        if welcome_msg:
            ftype = welcome_msg.get("media_type")
            caption = welcome_msg.get("caption", "")
            
            try:
                if ftype == "photo":
                    await update.message.reply_photo(photo=welcome_msg["file_id"], caption=caption, reply_markup=build_user_keyboard("main"))
                elif ftype == "video":
                    await update.message.reply_video(video=welcome_msg["file_id"], caption=caption, reply_markup=build_user_keyboard("main"))
                elif ftype == "audio":
                    await update.message.reply_audio(audio=welcome_msg["file_id"], caption=caption, reply_markup=build_user_keyboard("main"))
                elif ftype == "document":
                    await update.message.reply_document(document=welcome_msg["file_id"], caption=caption, reply_markup=build_user_keyboard("main"))
                elif ftype == "text":
                    await update.message.reply_text(text=welcome_msg["text"], reply_markup=build_user_keyboard("main"))
            except Exception:
                await update.message.reply_text("📚 اختر من القائمة:", reply_markup=build_user_keyboard("main"))
        else:
            image_url = "https://i.ibb.co/6P0D6hP/photo-2025-09-12-05-42-30.jpg"
            caption = (
                "مرحباً بك في بوت طلاب السنة الرابعة كلية\n"
                "الطب البشري التابع لي\n"
                "قناة ⚕️ Human medicine Libya ⚕️\n"
                "powered by Ameen Badda©\n"
                "2024-2025"
            )
            await update.message.reply_photo(photo=image_url, caption=caption)
            
            welcome_text_2 = "ماذا يمكن لهذا البوت فعله؟"
            inline_keyboard = [[InlineKeyboardButton("النقر هنا لاستخدام هذا البوت", callback_data="preview_bot")]]
            reply_markup = InlineKeyboardMarkup(inline_keyboard)
            
            await update.message.reply_text(
                text=welcome_text_2,
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text("📚 اختر من القائمة:", reply_markup=build_user_keyboard("main"))
    
    ensure_main_menu()

async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in DATA.get("banned_users", []):
        return
    if DATA.get("bot_status") != "online" and user_id != str(ADMIN_ID):
        await update.message.reply_text("🛠️ البوت في وضع الصيانة حاليًا. نعتذر على الإزعاج.")
        return
    ensure_main_menu()
    await update.message.reply_text("📚 اختر من القائمة:", reply_markup=build_user_keyboard("main"))

async def msg_user_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id in DATA.get("banned_users", []):
        return
    if DATA.get("bot_status") != "online" and user_id != str(ADMIN_ID):
        await update.message.reply_text("🛠️ البوت في وضع الصيانة حاليًا. نعتذر على الإزعاج.")
        return
        
    text = update.message.text
    ensure_main_menu()
    
    if text == "🏠 الرئيسية":
        context.user_data.pop("current_menu", None)
        await update.message.reply_text("🏠 رجوع إلى القائمة الرئيسية.", reply_markup=build_user_keyboard("main"))
        return
    
    if text == "⬅️ رجوع":
        current_menu = context.user_data.get("current_menu", "main")
        parent = get_parent(current_menu)
        if parent:
            context.user_data["current_menu"] = parent
            await update.message.reply_text(f"⬅️ رجوع إلى {parent}", reply_markup=build_user_keyboard(parent))
        else:
            await update.message.reply_text("أنت في القائمة الرئيسية.", reply_markup=build_user_keyboard("main"))
        return
    
    if text == "💬 دردشة سرية":
        await update.message.reply_text("💬 يمكنك الآن بدء محادثة سرية. سيتم إرسال رسالتك للمدير دون الكشف عن هويتك. للخروج من الدردشة اضغط زر 'إنهاء الدردشة'.", reply_markup=build_secret_chat_keyboard())
        return USER_SECRET_CHAT_WAIT
        
    if text == "✅ إنهاء الدردشة":
        await update.message.reply_text("✅ تم إنهاء الدردشة السرية.", reply_markup=build_user_keyboard("main"))
        return ConversationHandler.END

    node = DATA["buttons"].get(text)
    if node and node["type"] == "menu":
        context.user_data["current_menu"] = text
        await update.message.reply_text(f"📂 القسم: {text}", reply_markup=build_user_keyboard(text))
        return

    if node and node["type"] == "files":
        files = node.get("files", [])
        if not files:
            await update.message.reply_text("ℹ️ لا توجد ملفات مرتبطة بعد.", reply_markup=build_user_keyboard(get_parent(text)))
            return
        
        await update.message.reply_text(f"📁 {text} - أرسل لك الملفات الآن:", reply_markup=build_user_keyboard(get_parent(text)))
        
        for entry in files:
            ftype = entry.get("media_type", "document")
            fid = entry.get("file_id")
            try:
                if ftype == "photo":
                    await context.bot.send_photo(chat_id=update.message.chat_id, photo=fid)
                elif ftype == "video":
                    await context.bot.send_video(chat_id=update.message.chat_id, video=fid)
                elif ftype == "audio":
                    await context.bot.send_audio(chat_id=update.message.chat_id, audio=fid)
                else:
                    await context.bot.send_document(chat_id=update.message.chat_id, document=fid)
            except Exception:
                await context.bot.send_document(chat_id=update.message.chat_id, document=fid)
        return
        
    await update.message.reply_text("❌ هذا العنصر غير موجود. اختر من القائمة:", reply_markup=build_user_keyboard(context.user_data.get("current_menu", "main")))

# ===== لوحة الإدارة =====
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("🚫 ليس لديك صلاحية.")
        return
    ensure_main_menu()
    await update.message.reply_text("🛠️ لوحة الإدارة:", reply_markup=build_admin_keyboard())

async def cmd_tree(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text(f"🧾 البنية:\n\n{dump_tree()}")

async def cb_admin_hub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("🚫 ليس لديك صلاحية.")
        return

    _, action = query.data.split("|", 1)

    if action == "add_btn":
        menus = [name for name, node in DATA["buttons"].items() if node["type"] == "menu"]
        if not menus:
            await query.edit_message_text("⚠️ لا توجد قوائم. سيتم إنشاء main تلقائياً.")
            ensure_main_menu()
            menus = ["main"]

        buttons = [[InlineKeyboardButton(m, callback_data=f"admin_add|parent|{m}")] for m in menus]
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin|refresh")])
        await query.edit_message_text("📂 اختر القائمة الأم:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if action == "delete_btn":
        all_nodes = list(DATA["buttons"].keys())
        buttons = [[InlineKeyboardButton(n, callback_data=f"admin_delete|select|{n}")] for n in all_nodes if n != "main"]
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin|refresh")])
        await query.edit_message_text("🗑️ اختر الزر للحذف:", reply_markup=InlineKeyboardMarkup(buttons))
        return ADMIN_DELETE_BTN_SELECT

    if action == "attach_existing":
        files_nodes = [n for n, v in DATA["buttons"].items() if v["type"] == "files"]
        if not files_nodes:
            await query.edit_message_text("ℹ️ لا توجد أزرار من نوع ملفات بعد.", reply_markup=build_admin_keyboard())
            return
        buttons = [[InlineKeyboardButton(n, callback_data=f"admin_attach|target|{n}")] for n in files_nodes]
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin|refresh")])
        await query.edit_message_text("📎 اختر زر ملفات لإرفاق ملفات:", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if action == "tree":
        tree = dump_tree()
        await query.edit_message_text(f"🧾 البنية الحالية:\n\n{tree}", reply_markup=build_admin_keyboard())
        return

    if action == "preview":
        await query.edit_message_text("👀 وضع المعاينة. سترى البوت كما يراه المستخدم العادي. اضغط /admin للعودة.", reply_markup=build_user_keyboard("main"))
        return ConversationHandler.END

    if action == "refresh":
        await query.edit_message_text("🛠️ لوحة الإدارة:", reply_markup=build_admin_keyboard())
        return
        
    if action == "manage_welcome":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ إضافة/تعديل رسالة الترحيب", callback_data="admin_welcome|add")],
            [InlineKeyboardButton("🗑️ حذف رسالة الترحيب", callback_data="admin_welcome|delete")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="admin|refresh")],
        ])
        await query.edit_message_text("✉️ إدارة رسالة الترحيب:", reply_markup=kb)
        return
        
    if action == "stats":
        total_users = len(DATA.get("user_data", {}))
        stats_text = f"📊 إحصائيات البوت:\n\n- إجمالي عدد المستخدمين: {total_users}\n- عدد الأزرار: {len(DATA['buttons'])}\n- عدد المستخدمين المحظورين: {len(DATA['banned_users'])}"
        await query.edit_message_text(stats_text, reply_markup=build_admin_keyboard())
        return

    if action == "broadcast":
        await query.edit_message_text("📢 أرسل الآن الرسالة التي تريد بثها لجميع المستخدمين. يمكن أن تكون نصًا، صورة، أو فيديو. اضغط /cancel للإلغاء.", 
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="admin|refresh")]]))
        return ADMIN_BROADCAST_WAIT

    if action == "toggle_status":
        current_status = DATA.get("bot_status", "online")
        if current_status == "online":
            DATA["bot_status"] = "maintenance"
            await query.edit_message_text("🔴 تم تفعيل وضع الصيانة بنجاح. لن يتمكن المستخدمون العاديون من استخدام البوت.", reply_markup=build_admin_keyboard())
        else:
            DATA["bot_status"] = "online"
            await query.edit_message_text("🟢 تم إعادة تشغيل البوت. أصبح متاحًا للاستخدام.", reply_markup=build_admin_keyboard())
        save_data(DATA)
        return

    if action == "ban_user":
        banned_users = DATA.get("banned_users", [])
        
        buttons = [[InlineKeyboardButton(f"✅ فك حظر: {DATA['user_data'][uid]['first_name']}", callback_data=f"admin_ban|unban|{uid}")] for uid in banned_users if uid in DATA["user_data"]]
        buttons.append([InlineKeyboardButton("🚫 حظر مستخدم جديد (عبر ID)", callback_data="admin_ban|add_ban")])
        buttons.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin|refresh")])

        text_message = "🚫 إدارة المستخدمين المحظورين:"
        if not banned_users:
            text_message += "\n(لا يوجد مستخدمون محظورون حاليًا)"

        await query.edit_message_text(text_message, reply_markup=InlineKeyboardMarkup(buttons))
        return

# ===== محادثة: إضافة زر جديد =====
async def cb_admin_add_parent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("🚫 ليس لديك صلاحية.")
        return
    _, _, parent = query.data.split("|", 2)
    context.user_data["new_btn_parent"] = parent
    await query.edit_message_text(f"✍️ اكتب اسم الزر الجديد داخل: {parent}")
    return ADMIN_ADD_BTN_ENTER_NAME

async def admin_add_btn_enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    name = (update.message.text or "").strip()
    if not name:
        await update.message.reply_text("❌ الاسم فارغ. أرسل اسمًا صالحًا.")
        return ADMIN_ADD_BTN_ENTER_NAME
    if name in DATA["buttons"]:
        await update.message.reply_text("⚠️ الاسم موجود مسبقًا. اختر اسمًا آخر.")
        return ADMIN_ADD_BTN_ENTER_NAME
    context.user_data["new_btn_name"] = name

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 قائمة فرعية", callback_data="admin_add|type|menu")],
        [InlineKeyboardButton("📁 زر ملفات", callback_data="admin_add|type|files")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="admin|refresh")],
    ])
    await update.message.reply_text(f"✅ الاسم: {name}\nاختر نوع الزر:", reply_markup=kb)
    return ADMIN_ADD_BTN_CHOOSE_TYPE

async def cb_admin_add_choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("🚫 ليس لديك صلاحية.")
        return ConversationHandler.END

    parent = context.user_data.get("new_btn_parent")
    name = context.user_data.get("new_btn_name")
    if not parent or not name:
        await query.edit_message_text("⛔ انتهت الجلسة. حاول مجددًا.", reply_markup=build_admin_keyboard())
        return ConversationHandler.END

    _, _, typ = query.data.split("|", 2)
    if typ not in ("menu", "files"):
        await query.edit_message_text("❌ نوع غير صالح.", reply_markup=build_admin_keyboard())
        return ConversationHandler.END

    DATA["buttons"][name] = {
        "type": typ,
        "parent": parent,
        "items": [],
        "files": [],
    }
    DATA["buttons"][parent].setdefault("items", []).append(name)
    save_data(DATA)

    if typ == "menu":
        await query.edit_message_text(
            f"✅ تم إنشاء قائمة فرعية: {name}\nالمكان: {render_path(name)}",
            reply_markup=build_admin_keyboard()
        )
        context.user_data.pop("new_btn_parent", None)
        context.user_data.pop("new_btn_name", None)
        return ConversationHandler.END

    context.user_data["attach_target"] = name
    await query.edit_message_text(
        f"✅ تم إنشاء زر ملفات: {name}\n📎 أرسل الآن ملفات (PDF/صورة/فيديو/صوت). عند الانتهاء اضغط زر إنهاء الرفع.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ إنهاء الرفع", callback_data="admin_attach|done")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="admin|refresh")],
        ])
    )
    return ADMIN_ATTACH_FILES_WAIT

# ===== محادثة: حذف زر/ملف =====
async def cb_admin_delete_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("🚫 ليس لديك صلاحية.")
        return ConversationHandler.END

    _, _, target = query.data.split("|", 2)
    node = DATA["buttons"].get(target)
    if not node:
        await query.edit_message_text("❌ الزر غير موجود.", reply_markup=build_admin_keyboard())
        return ConversationHandler.END

    if node["type"] == "menu":
        confirm_text = f"هل أنت متأكد من حذف القائمة '{target}'؟ سيتم حذف كل ما بداخلها!"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تأكيد الحذف", callback_data=f"admin_delete|confirm_menu|{target}")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="admin|refresh")],
        ])
    else:
        confirm_text = f"هل تريد حذف زر الملفات '{target}' أم ملف معين بداخله؟"
        files_buttons = [[InlineKeyboardButton(f"🗑️ حذف ملف: {f.get('file_name', 'غير معروف')}", callback_data=f"admin_delete|file|{target}|{i}")] for i, f in enumerate(node.get("files", []))]
        full_delete_button = [InlineKeyboardButton(f"❌ حذف الزر بالكامل: {target}", callback_data=f"admin_delete|confirm_btn|{target}")]
        
        kb = InlineKeyboardMarkup(files_buttons + [full_delete_button] + [[InlineKeyboardButton("🔙 رجوع", callback_data="admin|refresh")]])

    await query.edit_message_text(confirm_text, reply_markup=kb)
    return ADMIN_DELETE_BTN_SELECT

async def cb_admin_delete_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("🚫 ليس لديك صلاحية.")
        return ConversationHandler.END

    parts = query.data.split("|")
    action_type = parts[1]
    target_name = parts[2]
    
    if action_type == "file":
        file_index = int(parts[3])
        node = DATA["buttons"].get(target_name)
        if node and node["type"] == "files" and 0 <= file_index < len(node.get("files", [])):
            del node["files"][file_index]
            save_data(DATA)
            await query.edit_message_text("✅ تم حذف الملف بنجاح.", reply_markup=build_admin_keyboard())
        else:
            await query.edit_message_text("❌ فشل حذف الملف.", reply_markup=build_admin_keyboard())
        return ConversationHandler.END

    def recursive_delete(name):
        node = DATA["buttons"].pop(name, None)
        if node and node["type"] == "menu":
            for child in node.get("items", []):
                recursive_delete(child)

    if action_type == "confirm_menu" or action_type == "confirm_btn":
        parent_name = get_parent(target_name)
        if parent_name and target_name in DATA["buttons"].get(parent_name, {}).get("items", []):
            DATA["buttons"][parent_name]["items"].remove(target_name)

        recursive_delete(target_name)
        save_data(DATA)
        await query.edit_message_text(f"✅ تم حذف '{target_name}' وكل ما يتعلق بها بنجاح.", reply_markup=build_admin_keyboard())
        return ConversationHandler.END

# ===== محادثة: إرفاق ملفات لزر موجود =====
async def cb_admin_attach_existing_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("🚫 ليس لديك صلاحية.")
        return ConversationHandler.END

    _, action, maybe_name = query.data.split("|", 2)
    if action == "done":
        context.user_data.pop("attach_target", None)
        await query.edit_message_text("✅ تم إنهاء عملية الرفع.", reply_markup=build_admin_keyboard())
        return ConversationHandler.END

    target = maybe_name
    node = DATA["buttons"].get(target)
    if not node or node["type"] != "files":
        await query.edit_message_text("❌ زر غير صالح للملفات.", reply_markup=build_admin_keyboard())
        return ConversationHandler.END

    context.user_data["attach_target"] = target
    await query.edit_message_text(
        f"📎 إرفاق لزر: {target}\nأرسل الآن الملفات. عند الانتهاء اضغط:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ إنهاء الرفع", callback_data="admin_attach|done")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="admin|refresh")],
        ])
    )
    return ADMIN_ATTACH_FILES_WAIT

async def admin_attach_receive_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    target = context.user_data.get("attach_target")
    if not target:
        return
    
    node = DATA["buttons"].get(target)
    if not node or node["type"] != "files":
        await update.message.reply_text("❌ الهدف ليس زر ملفات.")
        return

    entry = None
    msg = update.message

    if msg.document:
        entry = {"media_type": "document", "file_id": msg.document.file_id, "file_name": msg.document.file_name}
    elif msg.photo:
        entry = {"media_type": "photo", "file_id": msg.photo[-1].file_id}
    elif msg.video:
        entry = {"media_type": "video", "file_id": msg.video.file_id}
    elif msg.audio:
        entry = {"media_type": "audio", "file_id": msg.audio.file_id}
    else:
        await update.message.reply_text("⚠️ نوع الملف غير مدعوم هنا. أرسل مستند/صورة/فيديو/صوت.")
        return

    node.setdefault("files", []).append(entry)
    save_data(DATA)
    await update.message.reply_text(f"✅ تم إرفاق ({entry['media_type']}) لزر: {target}")

async def admin_attach_done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    context.user_data.pop("attach_target", None)
    await update.message.reply_text("✅ تم إنهاء عملية الرفع.")
    return ConversationHandler.END

async def admin_cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END
    context.user_data.clear()
    await update.message.reply_text("✖️ تم إلغاء العملية.")
    return ConversationHandler.END

# ===== محادثة: الدردشة السرية =====
async def user_start_secret_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("💬 أرسل رسالتك الآن. يمكنك إرسال نصوص وصور وملفات. للخروج من الدردشة اضغط زر 'إنهاء الدردشة'.", reply_markup=build_secret_chat_keyboard())
    return USER_SECRET_CHAT_WAIT

async def user_send_secret_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "✅ إنهاء الدردشة":
        await update.message.reply_text("✅ تم إنهاء الدردشة السرية.", reply_markup=build_user_keyboard("main"))
        return ConversationHandler.END

    chat_id = update.effective_chat.id
    user_id_hash = str(hash(chat_id))
    SECRET_CHAT_DATA["chats"][user_id_hash] = chat_id
    save_secret_chat_log(SECRET_CHAT_DATA)
    
    message_text = update.message.text or ""
    
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"✉️ رسالة جديدة في الدردشة السرية:\n\nالدردشة: {user_id_hash}\n\n{message_text}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("➡️ الرد", callback_data=f"admin_reply|{user_id_hash}")]])
        )
    except Exception as e:
        await update.message.reply_text(f"❌ فشل إرسال الرسالة إلى المدير: {e}")
        return
    
    await update.message.reply_text("✅ تم إرسال رسالتك. سيتم إعلامك عند الرد.", reply_markup=build_secret_chat_keyboard())
    return USER_SECRET_CHAT_WAIT

async def admin_start_secret_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, user_hash = query.data.split("|")
    user_chat_id = SECRET_CHAT_DATA["chats"].get(user_hash)
    
    context.user_data["admin_reply_target"] = user_chat_id
    await query.edit_message_text(f"➡️ يمكنك الآن الرد على المستخدم صاحب الدردشة: {user_hash}. اضغط /done للانتهاء.")
    
    return ADMIN_SECRET_CHAT_WAIT

async def admin_send_secret_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_chat_id = context.user_data.get("admin_reply_target")
    if not target_chat_id:
        await update.message.reply_text("❌ لم يتم تحديد دردشة للرد عليها. ابدأ من جديد.")
        return ConversationHandler.END
    
    if update.message.text == "/done":
        context.user_data.pop("admin_reply_target", None)
        await update.message.reply_text("✅ تم إنهاء الرد.", reply_markup=build_admin_keyboard())
        return ConversationHandler.END
    
    try:
        await context.bot.send_message(chat_id=target_chat_id, text=f"💬 رد من المدير:\n\n{update.message.text}")
        await update.message.reply_text("✅ تم إرسال الرد بنجاح.")
    except Exception as e:
        await update.message.reply_text(f"❌ فشل إرسال الرد: {e}")
    
    return ADMIN_SECRET_CHAT_WAIT

# ===== محادثة: إدارة رسالة الترحيب =====
async def cb_admin_welcome_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    _, action = query.data.split("|", 1)

    if action == "add":
        await query.edit_message_text(
            "✉️ أرسل رسالة الترحيب الجديدة الآن. يمكن أن تكون نصًا، صورة، فيديو، أو أي ملف آخر. يمكنك أيضًا إرسال وسائط مع تعليق.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ إلغاء", callback_data="admin|refresh")]
            ])
        )
        return ADMIN_MANAGE_WELCOME_WAIT
    
    if action == "delete":
        if DATA.get("welcome_message"):
            DATA["welcome_message"] = None
            save_data(DATA)
            await query.edit_message_text("🗑️ تم حذف رسالة الترحيب بنجاح.", reply_markup=build_admin_keyboard())
        else:
            await query.edit_message_text("⚠️ لا توجد رسالة ترحيب لحذفها.", reply_markup=build_admin_keyboard())
        return ConversationHandler.END

async def admin_receive_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    entry = None

    if msg.document:
        entry = {"media_type": "document", "file_id": msg.document.file_id, "file_name": msg.document.file_name, "caption": msg.caption or ""}
    elif msg.photo:
        entry = {"media_type": "photo", "file_id": msg.photo[-1].file_id, "caption": msg.caption or ""}
    elif msg.video:
        entry = {"media_type": "video", "file_id": msg.video.file_id, "caption": msg.caption or ""}
    elif msg.audio:
        entry = {"media_type": "audio", "file_id": msg.audio.file_id, "caption": msg.caption or ""}
    elif msg.text:
        entry = {"media_type": "text", "text": msg.text}
    
    if entry:
        DATA["welcome_message"] = entry
        save_data(DATA)
        await update.message.reply_text("✅ تم حفظ رسالة الترحيب بنجاح.", reply_markup=build_admin_keyboard())
        return ConversationHandler.END
    else:
        await update.message.reply_text("❌ لم يتم التعرف على نوع الرسالة. حاول مرة أخرى.", reply_markup=build_admin_keyboard())
        return ADMIN_MANAGE_WELCOME_WAIT
        
async def cb_preview_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("👀 وضع المعاينة. سترى البوت كما يراه المستخدم العادي. اضغط /admin للعودة.", reply_markup=build_user_keyboard("main"))
    return ConversationHandler.END

# ===== محادثة: البث الجماعي (Broadcast) =====
async def admin_broadcast_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    broadcast_message = update.message

    for user_id in DATA.get("user_data", {}).keys():
        if user_id != str(ADMIN_ID) and user_id not in DATA.get("banned_users", []):
            try:
                if broadcast_message.document:
                    await context.bot.send_document(chat_id=user_id, document=broadcast_message.document.file_id, caption=broadcast_message.caption)
                elif broadcast_message.photo:
                    await context.bot.send_photo(chat_id=user_id, photo=broadcast_message.photo[-1].file_id, caption=broadcast_message.caption)
                elif broadcast_message.video:
                    await context.bot.send_video(chat_id=user_id, video=broadcast_message.video.file_id, caption=broadcast_message.caption)
                elif broadcast_message.audio:
                    await context.bot.send_audio(chat_id=user_id, audio=broadcast_message.audio.file_id, caption=broadcast_message.caption)
                elif broadcast_message.text:
                    await context.bot.send_message(chat_id=user_id, text=broadcast_message.text)
            except Exception as e:
                print(f"Failed to send broadcast to {user_id}: {e}")
                
    await update.message.reply_text("✅ تم إرسال رسالة البث بنجاح.", reply_markup=build_admin_keyboard())
    return ConversationHandler.END

# ===== محادثة: حظر/فك حظر المستخدمين =====
async def cb_admin_ban_manager(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("🚫 ليس لديك صلاحية.")
        return

    parts = query.data.split("|")
    action = parts[1]

    if action == "unban":
        user_id_to_unban = parts[2]
        if user_id_to_unban in DATA["banned_users"]:
            DATA["banned_users"].remove(user_id_to_unban)
            save_data(DATA)
            await query.edit_message_text(f"✅ تم فك حظر المستخدم بنجاح: {user_id_to_unban}", reply_markup=build_admin_keyboard())
        else:
            await query.edit_message_text("❌ المستخدم غير محظور.", reply_markup=build_admin_keyboard())
        return ConversationHandler.END
        
    elif action == "add_ban":
        await query.edit_message_text("🚫 أرسل الـ ID الخاص بالمستخدم الذي تريد حظره. (يمكنك الحصول عليه من إشعارات المستخدمين الجدد).\nاضغط /cancel للإلغاء.", 
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ إلغاء", callback_data="admin|refresh")]]))
        return ADMIN_BAN_USER_WAIT
        
async def admin_ban_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id_to_ban = update.message.text.strip()
    if not user_id_to_ban.isdigit():
        await update.message.reply_text("❌ الـ ID يجب أن يكون رقمًا. حاول مرة أخرى.")
        return ADMIN_BAN_USER_WAIT

    if user_id_to_ban not in DATA["banned_users"]:
        DATA["banned_users"].append(user_id_to_ban)
        save_data(DATA)
        await update.message.reply_text(f"✅ تم حظر المستخدم بنجاح: {user_id_to_ban}", reply_markup=build_admin_keyboard())
    else:
        await update.message.reply_text("⚠️ هذا المستخدم محظور بالفعل.", reply_markup=build_admin_keyboard())

    return ConversationHandler.END

# ===== تطبيق البوت =====
def main():
    ensure_main_menu()

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("admin", cmd_admin))
    app.add_handler(CommandHandler("tree", cmd_tree))
    app.add_handler(CallbackQueryHandler(cb_preview_bot, pattern=r"^preview_bot$"))

    conv_add_btn = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_admin_add_parent, pattern=r"^admin_add\|parent\|")],
        states={
            ADMIN_ADD_BTN_ENTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(ADMIN_ID), admin_add_btn_enter_name)],
            ADMIN_ADD_BTN_CHOOSE_TYPE: [CallbackQueryHandler(cb_admin_add_choose_type, pattern=r"^admin_add\|type\|")],
            ADMIN_ATTACH_FILES_WAIT: [
                MessageHandler(filters.User(ADMIN_ID) & (filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO), admin_attach_receive_media),
                CallbackQueryHandler(cb_admin_attach_existing_select, pattern=r"^admin_attach\|done$"),
            ],
        },
        fallbacks=[
            CommandHandler("done", admin_attach_done_cmd),
            CommandHandler("cancel", admin_cancel_cmd),
        ],
        allow_reentry=True,
    )
    app.add_handler(conv_add_btn)

    conv_delete_btn = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_admin_delete_select, pattern=r"^admin_delete\|select\|")],
        states={
            ADMIN_DELETE_BTN_SELECT: [CallbackQueryHandler(cb_admin_delete_confirm, pattern=r"^admin_delete\|confirm_menu\||^admin_delete\|confirm_btn\||^admin_delete\|file\|")],
        },
        fallbacks=[
            CallbackQueryHandler(cb_admin_hub, pattern=r"^admin\|refresh$"),
        ],
        allow_reentry=True,
    )
    app.add_handler(conv_delete_btn)
   
    conv_secret_chat_user = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & filters.Regex("💬 دردشة سرية") & ~filters.User(ADMIN_ID), user_start_secret_chat)],
        states={
            USER_SECRET_CHAT_WAIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, user_send_secret_message),
                MessageHandler(filters.TEXT & filters.Regex("✅ إنهاء الدردشة"), msg_user_nav),
            ],
        },
        fallbacks=[], 
        allow_reentry=True,
    )
    app.add_handler(conv_secret_chat_user)
    
    conv_secret_chat_admin = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_start_secret_reply, pattern=r"^admin_reply\|")],
        states={
            ADMIN_SECRET_CHAT_WAIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_send_secret_reply),
                CommandHandler("done", admin_send_secret_reply),
            ],
        },
        fallbacks=[CommandHandler("done", admin_send_secret_reply)],
        allow_reentry=True,
    )
    app.add_handler(conv_secret_chat_admin)
    
    # محادثة إدارة رسالة الترحيب
    conv_welcome_manager = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_admin_welcome_manager, pattern=r"^admin_welcome\|")],
        states={
            ADMIN_MANAGE_WELCOME_WAIT: [
                MessageHandler(filters.User(ADMIN_ID) & (filters.TEXT | filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO), admin_receive_welcome_message),
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cb_admin_hub, pattern=r"^admin\|refresh$"),
        ],
        allow_reentry=True,
    )
    app.add_handler(conv_welcome_manager)
    
    # محادثة البث الجماعي
    conv_broadcast = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_admin_hub, pattern=r"^admin\|broadcast$")],
        states={
            ADMIN_BROADCAST_WAIT: [
                MessageHandler(filters.User(ADMIN_ID) & (filters.TEXT | filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO), admin_broadcast_receive),
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cb_admin_hub, pattern=r"^admin\|refresh$"),
            CommandHandler("cancel", admin_cancel_cmd),
        ],
        allow_reentry=True,
    )
    app.add_handler(conv_broadcast)
    
    # محادثة حظر المستخدمين
    conv_ban_user = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_admin_ban_manager, pattern=r"^admin\|ban_user$|^admin_ban\|")],
        states={
            ADMIN_BAN_USER_WAIT: [
                MessageHandler(filters.User(ADMIN_ID) & filters.TEXT & ~filters.COMMAND, admin_ban_user_id),
            ]
        },
        fallbacks=[
            CallbackQueryHandler(cb_admin_hub, pattern=r"^admin\|refresh$"),
            CommandHandler("cancel", admin_cancel_cmd),
        ],
        allow_reentry=True,
    )
    app.add_handler(conv_ban_user)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.User(ADMIN_ID), msg_user_nav))
    app.add_handler(CallbackQueryHandler(cb_admin_hub, pattern=r"^admin\|"))
    app.add_handler(CallbackQueryHandler(cb_admin_add_choose_type, pattern=r"^admin_add\|type\|"))
    app.add_handler(CallbackQueryHandler(cb_admin_attach_existing_select, pattern=r"^admin_attach\|"))
    app.add_handler(CallbackQueryHandler(cb_admin_ban_manager, pattern=r"^admin_ban\|"))

    print("✅ Bot is running...")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()