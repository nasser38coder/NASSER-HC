import os
import logging
from flask import Flask, request, jsonify
import telegram
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler, MessageHandler, Filters
import config
from database import Database
from account_creator import AccountCreator
from auto_reporter import AutoReporter

# ================= التوكن =================
BOT_TOKEN = "8854067469:AAECoNTDQlnV7V6FAhUnDwsdxbrDeLdYRso"
ADMIN_IDS = [5100562548]
# ========================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# قاعدة البيانات
db = Database()
creator = AccountCreator()
reporter = AutoReporter()

# البوت
bot = telegram.Bot(token=BOT_TOKEN)

# ================= دوال البوت =================

def generate_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 تقديم بلاغ", callback_data="submit_report")],
        [InlineKeyboardButton("🔧 إنشاء حسابات", callback_data="create_accounts")],
        [InlineKeyboardButton("📤 إرسال بلاغات جماعية", callback_data="mass_report")],
        [InlineKeyboardButton("❓ مساعدة", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def start(update, context):
    user = update.effective_user
    db.add_user({
        'user_id': user.id,
        'username': user.username or "N/A",
        'first_name': user.first_name or "N/A",
        'last_name': user.last_name or "N/A"
    })
    update.message.reply_text(
        "👋 مرحباً بك في بوت Nasser AI!\nاختر أحد الأزرار:",
        reply_markup=generate_main_menu()
    )

def help_command(update, context):
    update.message.reply_text("❓ للمساعدة، استخدم الأزرار.", reply_markup=generate_main_menu())

def submit_report(update, context):
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("👤 مستخدم", callback_data="report_type_user")],
        [InlineKeyboardButton("📄 محتوى", callback_data="report_type_content")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]
    query.edit_message_text("📝 اختر نوع البلاغ:", reply_markup=InlineKeyboardMarkup(keyboard))

def report_type_callback(update, context):
    query = update.callback_query
    query.answer()
    report_type = query.data.replace("report_type_", "")
    context.user_data['report_type'] = report_type
    context.user_data['step'] = 'username'
    query.edit_message_text(f"✅ النوع: {report_type}\n✏️ أرسل اسم المستخدم المستهدف:")

def handle_message(update, context):
    step = context.user_data.get('step')
    if not step:
        update.message.reply_text("استخدم الأزرار.", reply_markup=generate_main_menu())
        return
    if step == 'username':
        context.user_data['target_username'] = update.message.text.strip()
        context.user_data['step'] = 'description'
        update.message.reply_text("✏️ أرسل وصفاً تفصيلياً:")
    elif step == 'description':
        context.user_data['description'] = update.message.text
        user = update.effective_user
        report_data = {
            'user_id': user.id,
            'username': user.username or "N/A",
            'report_type': context.user_data.get('report_type', 'unknown'),
            'target_username': context.user_data.get('target_username', 'N/A'),
            'target_platform': context.user_data.get('target_platform', 'unknown'),
            'description': context.user_data.get('description', 'No description'),
            'media_url': ''
        }
        report_id = db.add_report(report_data)
        context.user_data.clear()
        update.message.reply_text(f"✅ تم استلام بلاغك! رقمه: #{report_id}", reply_markup=generate_main_menu())

def create_accounts(update, context):
    query = update.callback_query
    query.answer()
    keyboard = [
        [InlineKeyboardButton("5 حسابات", callback_data="create_5")],
        [InlineKeyboardButton("10 حسابات", callback_data="create_10")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]
    query.edit_message_text("🔧 كم حساب تريد إنشاءه؟", reply_markup=InlineKeyboardMarkup(keyboard))

def create_accounts_callback(update, context):
    query = update.callback_query
    query.answer()
    count = int(query.data.replace("create_", ""))
    query.edit_message_text(f"🔄 جاري إنشاء {count} حساب...")
    accounts = creator.create_bulk(count)
    if accounts:
        query.edit_message_text(f"✅ تم إنشاء {len(accounts)} حساب!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]]))

def mass_report(update, context):
    query = update.callback_query
    query.answer()
    accounts = creator.load_accounts()
    if not accounts:
        query.edit_message_text("❌ لا توجد حسابات!", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]]))
        return
    query.edit_message_text("📤 أرسل اسم المستخدم المستهدف:")
    context.user_data['action'] = 'mass_report_target'

def handle_mass_report(update, context):
    target = update.message.text.strip()
    update.message.reply_text(f"🔄 جاري الإرسال لـ @{target}...")
    results = reporter.mass_report(target)
    success = sum(1 for r in results if r.get('status') == 'success')
    update.message.reply_text(f"✅ اكتمل الإرسال! نجح: {success} من {len(results)}", reply_markup=generate_main_menu())

def back_handler(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text("🤖 القائمة الرئيسية:", reply_markup=generate_main_menu())

def callback_handler(update, context):
    query = update.callback_query
    data = query.data
    if data == "submit_report":
        submit_report(update, context)
    elif data.startswith("report_type_"):
        report_type_callback(update, context)
    elif data == "create_accounts":
        create_accounts(update, context)
    elif data.startswith("create_"):
        create_accounts_callback(update, context)
    elif data == "mass_report":
        mass_report(update, context)
    elif data == "help":
        help_command(update, context)
    elif data == "back":
        back_handler(update, context)

# ================= Webhook =================

@app.route('/')
def home():
    return "✅ Nasser AI Bot is running!"

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher = Dispatcher(bot, None, workers=0, use_context=True)
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("help", help_command))
        dispatcher.add_handler(CallbackQueryHandler(callback_handler))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_mass_report))
        dispatcher.process_update(update)
        return jsonify({"ok": True})
    except Exception as e:
        logger.error(f"❌ خطأ: {e}")
        return jsonify({"ok": False, "error": str(e)})

# ================= تشغيل =================

if __name__ == "__main__":
    try:
        webhook_url = "https://nasser-hc.onrender.com/webhook"
        bot.set_webhook(webhook_url)
        logger.info(f"✅ Webhook set to: {webhook_url}")
    except Exception as e:
        logger.error(f"❌ فشل تعيين Webhook: {e}")
    
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
