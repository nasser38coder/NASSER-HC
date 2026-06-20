import logging
import re
import random
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackQueryHandler, CallbackContext
from telegram.ext import Filters
from telegram.constants import ParseMode
import config
from database import Database
from account_creator import AccountCreator
from auto_reporter import AutoReporter

# ================= توكن البوت =================
# 🟢 ضع توكن البوت هنا (من BotFather)
BOT_TOKEN = "8854067469:AAECoNTDQlnV7V6FAhUnDwsdxbrDeLdYRso"

# 🟢 ضع معرف المشرف هنا (من @userinfobot)
ADMIN_IDS = [5100562548]
# =============================================

# تسجيل
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# قاعدة البيانات
db = Database()
creator = AccountCreator()
reporter = AutoReporter()

# ================= دوال المساعدة =================

def is_admin(user_id):
    return user_id in ADMIN_IDS

def generate_main_menu():
    keyboard = [
        [InlineKeyboardButton("📝 تقديم بلاغ", callback_data="submit_report")],
        [InlineKeyboardButton("📊 بلاغاتي", callback_data="my_reports")],
        [InlineKeyboardButton("🔧 إنشاء حسابات", callback_data="create_accounts")],
        [InlineKeyboardButton("📤 إرسال بلاغات جماعية", callback_data="mass_report")],
        [InlineKeyboardButton("❓ مساعدة", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= أوامر البوت =================

def start(update, context):
    user = update.effective_user
    
    db.add_user({
        'user_id': user.id,
        'username': user.username or "N/A",
        'first_name': user.first_name or "N/A",
        'last_name': user.last_name or "N/A"
    })
    
    welcome_text = f"""
👋 *مرحباً بك في بوت Nasser AI!*

🤖 *ماذا يمكنني أن أفعل؟*
• 📝 تقديم بلاغات عن حسابات مخالفة
• 🔧 إنشاء حسابات إنستغرام تلقائياً
• 📤 إرسال بلاغات جماعية
• 📊 متابعة بلاغاتك

📌 *للاستخدام:*
اختر أحد الأزرار أدناه للبدء.
"""
    
    update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=generate_main_menu()
    )

def help_command(update, context):
    help_text = """
❓ *المساعدة*

📝 *تقديم بلاغ:*
• اختر نوع البلاغ
• أدخل اسم المستخدم المستهدف
• أضف وصفاً تفصيلياً

🔧 *إنشاء حسابات:*
• ينشئ حسابات إنستغرام تلقائياً
• يستخدم بريداً مؤقتاً للتفعيل

📤 *إرسال بلاغات جماعية:*
• يستخدم الحسابات المخزنة
• يرسل بلاغات متعددة تلقائياً

⚠️ *تنبيه:* للاستخدام الشخصي فقط!
"""
    update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# ================= دوال الإبلاغ =================

def submit_report(update, context):
    query = update.callback_query
    query.answer()
    
    keyboard = [
        [InlineKeyboardButton("👤 مستخدم", callback_data="report_type_user")],
        [InlineKeyboardButton("📄 محتوى", callback_data="report_type_content")],
        [InlineKeyboardButton("⚠️ احتيال", callback_data="report_type_scam")],
        [InlineKeyboardButton("📌 أخرى", callback_data="report_type_other")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]
    
    query.edit_message_text(
        "📝 *اختر نوع البلاغ:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def report_type_callback(update, context):
    query = update.callback_query
    query.answer()
    
    report_type = query.data.replace("report_type_", "")
    context.user_data['report_type'] = report_type
    context.user_data['step'] = 'platform'
    
    keyboard = [
        [InlineKeyboardButton("📸 Instagram", callback_data="platform_instagram")],
        [InlineKeyboardButton("📘 Facebook", callback_data="platform_facebook")],
        [InlineKeyboardButton("🐦 Twitter", callback_data="platform_twitter")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]
    
    query.edit_message_text(
        f"✅ النوع: *{report_type}*\n\n"
        f"📱 *اختر المنصة:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def platform_callback(update, context):
    query = update.callback_query
    query.answer()
    
    platform = query.data.replace("platform_", "")
    context.user_data['target_platform'] = platform
    context.user_data['step'] = 'username'
    
    query.edit_message_text(
        f"✅ المنصة: *{platform}*\n\n"
        f"✏️ *أرسل اسم المستخدم المستهدف:*\n"
        f"(بدون @)",
        parse_mode=ParseMode.MARKDOWN
    )

def handle_message(update, context):
    user_id = update.effective_user.id
    text = update.message.text
    step = context.user_data.get('step')
    
    if not step:
        update.message.reply_text(
            "استخدم الأزرار للتنقل.",
            reply_markup=generate_main_menu()
        )
        return
    
    if step == 'username':
        context.user_data['target_username'] = text.strip()
        context.user_data['step'] = 'description'
        
        update.message.reply_text(
            f"✅ المستهدف: @{text}\n\n"
            f"✏️ *أرسل وصفاً تفصيلياً:*\n"
            f"(اذكر التفاصيل كاملة)",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif step == 'description':
        context.user_data['description'] = text
        save_report(update, context)

def save_report(update, context):
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
    
    update.message.reply_text(
        f"✅ *تم استلام بلاغك!*\n\n"
        f"📋 رقم البلاغ: `#{report_id}`\n"
        f"📊 الحالة: قيد المراجعة\n\n"
        f"شكراً لك على الإبلاغ!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=generate_main_menu()
    )

# ================= دوال إنشاء الحسابات =================

def create_accounts(update, context):
    query = update.callback_query
    query.answer()
    
    keyboard = [
        [InlineKeyboardButton("5 حسابات", callback_data="create_5")],
        [InlineKeyboardButton("10 حسابات", callback_data="create_10")],
        [InlineKeyboardButton("20 حساب", callback_data="create_20")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]
    
    query.edit_message_text(
        "🔧 *كم حساب تريد إنشاءه؟*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def create_accounts_callback(update, context):
    query = update.callback_query
    query.answer()
    
    count = int(query.data.replace("create_", ""))
    
    query.edit_message_text(
        f"🔄 جاري إنشاء {count} حساب...\n⏳ قد يستغرق بضع دقائق",
        parse_mode=ParseMode.MARKDOWN
    )
    
    accounts = creator.create_bulk(count)
    
    if accounts:
        query.edit_message_text(
            f"✅ *تم إنشاء {len(accounts)} حساب!*\n\n"
            f"📁 تم حفظها في: `accounts.txt`\n"
            f"🔹 استخدمها للإبلاغ",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📤 إرسال بلاغات", callback_data="mass_report")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
            ])
        )
    else:
        query.edit_message_text(
            "❌ فشل إنشاء الحسابات. حاول مرة أخرى.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
            ])
        )

# ================= دوال الإبلاغ الجماعي =================

def mass_report(update, context):
    query = update.callback_query
    query.answer()
    
    accounts = creator.load_accounts()
    
    if not accounts:
        query.edit_message_text(
            "❌ *لا توجد حسابات!*\n\n"
            "أنشئ حسابات أولاً باستخدام 'إنشاء حسابات'",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔧 إنشاء حسابات", callback_data="create_accounts")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
            ])
        )
        return
    
    query.edit_message_text(
        f"📤 *إرسال بلاغات جماعية*\n\n"
        f"👥 الحسابات المتاحة: {len(accounts)}\n"
        f"✏️ *أرسل اسم المستخدم المستهدف:*",
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data['action'] = 'mass_report_target'

def handle_mass_report(update, context):
    target = update.message.text.strip()
    
    update.message.reply_text(
        f"🔄 جاري إرسال البلاغات لـ @{target}...\n⏳ قد يستغرق بضع دقائق",
        parse_mode=ParseMode.MARKDOWN
    )
    
    results = reporter.mass_report(target)
    
    success = sum(1 for r in results if r.get('status') == 'success')
    failed = len(results) - success
    
    update.message.reply_text(
        f"✅ *اكتمل الإرسال!*\n\n"
        f"📊 النتائج:\n"
        f"• ✅ نجح: {success}\n"
        f"• ❌ فشل: {failed}\n"
        f"• 📝 المجموع: {len(results)}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=generate_main_menu()
    )

# ================= دوال العودة =================

def back_handler(update, context):
    query = update.callback_query
    query.answer()
    
    query.edit_message_text(
        "🤖 *القائمة الرئيسية*\n\nاختر الإجراء المناسب:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=generate_main_menu()
    )

# ================= معالج الأزرار =================

def callback_handler(update, context):
    query = update.callback_query
    data = query.data
    
    if data == "submit_report":
        submit_report(update, context)
    elif data.startswith("report_type_"):
        report_type_callback(update, context)
    elif data.startswith("platform_"):
        platform_callback(update, context)
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
    else:
        query.answer("❌ خيار غير معروف")

# ================= التشغيل =================

def main():
    try:
        # الطريقة الجديدة (Python-telegram-bot v20+)
        from telegram.ext import Application
        app = Application.builder().token(BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CallbackQueryHandler(callback_handler))
        app.add_handler(MessageHandler(Filters.TEXT & ~Filters.COMMAND, handle_message))
        app.add_handler(MessageHandler(Filters.TEXT & ~Filters.COMMAND, handle_mass_report))
        
        logger.info("🚀 تشغيل البوت (v20)...")
        app.run_polling()
        
    except Exception as e:
        logger.warning(f"⚠️ الطريقة الأولى فشلت: {e}")
        logger.info("🔄 تجربة الطريقة القديمة...")
        
        # الطريقة القديمة (Python-telegram-bot v13)
        updater = Updater(BOT_TOKEN, use_context=True)
        dp = updater.dispatcher
        
        dp.add_handler(CommandHandler("start", start))
        dp.add_handler(CommandHandler("help", help_command))
        dp.add_handler(CallbackQueryHandler(callback_handler))
        dp.add_handler(MessageHandler(Filters.TEXT & ~Filters.COMMAND, handle_message))
        dp.add_handler(MessageHandler(Filters.TEXT & ~Filters.COMMAND, handle_mass_report))
        
        updater.start_polling()
        updater.idle()

if __name__ == "__main__":
    main()
