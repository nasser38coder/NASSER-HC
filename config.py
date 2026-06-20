import os

# ================= إعدادات البوت =================
# ضع توكن البوت هنا (من BotFather)
BOT_TOKEN = "8854067469:AAECoNTDQlnV7V6FAhUnDwsdxbrDeLdYRso"

# ضع معرفك الرقمي هنا (من @userinfobot)
ADMIN_IDS = [5100562548]

# ================= إعدادات قاعدة البيانات =================
DATABASE_FILE = "data/reports.db"

# ================= إعدادات أخرى =================
HEADLESS_MODE = True  # True = يعمل في الخلفية
AUTO_REPORT_ENABLED = True
MAX_REPORTS_PER_DAY = 100
REPORTS_PER_ACCOUNT = 2

# ================= إعدادات الملفات =================
ACCOUNTS_FILE = "data/accounts.txt"
ACCOUNTS_JSON = "data/accounts.json"

# ================= إنشاء المجلدات =================
os.makedirs("data", exist_ok=True)
os.makedirs("templates", exist_ok=True)
