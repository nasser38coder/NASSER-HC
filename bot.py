import logging
import re
import random
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.constants import ParseMode
import config
from database import Database
from account_creator import AccountCreator
from auto_reporter import AutoReporter

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
    return user_id in config.ADMIN_IDS

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=generate_main_menu()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

# ================= دوال الإبلاغ =================

async def submit_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("👤 مستخدم", callback_data="report_type_user")],
        [InlineKeyboardButton("📄 محتوى", callback_data="report_type_content")],
        [InlineKeyboardButton("⚠️ احتيال", callback_data="report_type_scam")],
        [InlineKeyboardButton("📌 أخرى", callback_data="report_type_other")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]
    
    await query.edit_message_text(
        "📝 *اختر نوع البلاغ:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def report_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    report_type = query.data.replace("report_type_", "")
    context.user_data['report_type'] = report_type
    context.user_data['step'] = 'platform'
    
    keyboard = [
        [InlineKeyboardButton("📸 Instagram", callback_data="platform_instagram")],
        [InlineKeyboardButton("📘 Facebook", callback_data="platform_facebook")],
        [InlineKeyboardButton("🐦 Twitter", callback_data="platform_twitter")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]
    
    await query.edit_message_text(
        f"✅ النوع: *{report_type}*\n\n"
        f"📱 *اختر المنصة:*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def platform_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    platform = query.data.replace("platform_", "")
    context.user_data['target_platform'] = platform
    context.user_data['step'] = 'username'
    
    await query.edit_message_text(
        f"✅ المنصة: *{platform}*\n\n"
        f"✏️ *أرسل اسم المستخدم المستهدف:*\n"
        f"(بدون @)",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    step = context.user_data.get('step')
    
    if not step:
        await update.message.reply_text(
            "استخدم الأزرار للتنقل.",
            reply_markup=generate_main_menu()
        )
        return
    
    if step == 'username':
        context.user_data['target_username'] = text.strip()
        context.user_data['step'] = 'description'
        
        await update.message.reply_text(
            f"✅ المستهدف: @{text}\n\n"
            f"✏️ *أرسل وصفاً تفصيلياً:*\n"
            f"(اذكر التفاصيل كاملة)",
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif step == 'description':
        context.user_data['description'] = text
        await save_report(update, context)

async def save_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    await update.message.reply_text(
        f"✅ *تم استلام بلاغك!*\n\n"
        f"📋 رقم البلاغ: `#{report_id}`\n"
        f"📊 الحالة: قيد المراجعة\n\n"
        f"شكراً لك على الإبلاغ!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=generate_main_menu()
    )

# ================= دوال إنشاء الحسابات =================

async def create_accounts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("5 حسابات", callback_data="create_5")],
        [InlineKeyboardButton("10 حسابات", callback_data="create_10")],
        [InlineKeyboardButton("20 حساب", callback_data="create_20")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]
    
    await query.edit_message_text(
        "🔧 *كم حساب تريد إنشاءه؟*",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def create_accounts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    count = int(query.data.replace("create_", ""))
    
    await query.edit_message_text(
        f"🔄 جاري إنشاء {count} حساب...\n⏳ قد يستغرق بضع دقائق",
        parse_mode=ParseMode.MARKDOWN
    )
    
    accounts = creator.create_bulk(count)
    
    if accounts:
        await query.edit_message_text(
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
        await query.edit_message_text(
            "❌ فشل إنشاء الحسابات. حاول مرة أخرى.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
            ])
        )

# ================= دوال الإبلاغ الجماعي =================

async def mass_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    accounts = creator.load_accounts()
    
    if not accounts:
        await query.edit_message_text(
            "❌ *لا توجد حسابات!*\n\n"
            "أنشئ حسابات أولاً باستخدام 'إنشاء حسابات'",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔧 إنشاء حسابات", callback_data="create_accounts")],
                [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
            ])
        )
        return
    
    await query.edit_message_text(
        f"📤 *إرسال بلاغات جماعية*\n\n"
        f"👥 الحسابات المتاحة: {len(accounts)}\n"
        f"✏️ *أرسل اسم المستخدم المستهدف:*",
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data['action'] = 'mass_report_target'

async def handle_mass_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target = update.message.text.strip()
    
    await update.message.reply_text(
        f"🔄 جاري إرسال البلاغات لـ @{target}...\n⏳ قد يستغرق بضع دقائق",
        parse_mode=ParseMode.MARKDOWN
    )
    
    results = reporter.mass_report(target)
    
    success = sum(1 for r in results if r.get('status') == 'success')
    failed = len(results) - success
    
    await update.message.reply_text(
        f"✅ *اكتمل الإرسال!*\n\n"
        f"📊 النتائج:\n"
        f"• ✅ نجح: {success}\n"
        f"• ❌ فشل: {failed}\n"
        f"• 📝 المجموع: {len(results)}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=generate_main_menu()
    )

# ================= دوال العودة =================

async def back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🤖 *القائمة الرئيسية*\n\nاختر الإجراء المناسب:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=generate_main_menu()
    )

# ================= معالج الأزرار =================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "submit_report":
        await submit_report(update, context)
    elif data.startswith("report_type_"):
        await report_type_callback(update, context)
    elif data.startswith("platform_"):
        await platform_callback(update, context)
    elif data == "create_accounts":
        await create_accounts(update, context)
    elif data.startswith("create_"):
        await create_accounts_callback(update, context)
    elif data == "mass_report":
        await mass_report(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data == "back":
        await back_handler(update, context)
    else:
        await query.answer("❌ خيار غير معروف")

# ================= التشغيل =================

def main():
    try:
        # محاولة تشغيل بالإصدار الجديد
        app = Application.builder().token(config.BOT_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CallbackQueryHandler(callback_handler))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mass_report))
        
        logger.info("🚀 تشغيل البوت...")
        app.run_polling()
        
    except Exception as e:
        logger.error(f"❌ خطأ في التشغيل: {e}")
        # محاولة بديلة
        try:
            from telegram.ext import Updater
            import telegram.ext as tg_ext
            
            # طريقة قديمة
            updater = Updater(config.BOT_TOKEN, use_context=True)
            dp = updater.dispatcher
            
            dp.add_handler(CommandHandler("start", start))
            dp.add_handler(CommandHandler("help", help_command))
            dp.add_handler(CallbackQueryHandler(callback_handler))
            dp.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
            dp.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mass_report))
            
            logger.info("🚀 تشغيل البوت (طريقة بديلة)...")
            updater.start_polling()
            updater.idle()
            
        except Exception as e2:
            logger.error(f"❌ فشل التشغيل تماماً: {e2}")

if __name__ == "__main__":
    main()
