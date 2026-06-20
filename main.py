import os
import sys
import logging
import threading
from flask import Flask, jsonify
import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Nasser AI Bot is running on Render!"

@app.route('/health')
def health():
    return "OK", 200

@app.route('/status')
def status():
    return jsonify({
        'status': 'running',
        'bot': 'Nasser AI',
        'version': '2.0'
    })

def run_bot():
    """تشغيل البوت في خلفية"""
    try:
        from bot import main as bot_main
        bot_main()
    except Exception as e:
        logger.error(f"❌ خطأ في البوت: {e}")

def start_bot_thread():
    thread = threading.Thread(target=run_bot, daemon=True)
    thread.start()
    logger.info("✅ تم تشغيل البوت في الخلفية")

if __name__ == "__main__":
    # بدء البوت
    start_bot_thread()
    
    # بدء الخادم
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
