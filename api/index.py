import os
import json
import logging
import asyncio
import socket
import time
from threading import Thread
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from supabase import create_client, Client

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = os.getenv("SPACE_URL") 

# Inisialisasi API
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

app_flask = Flask(__name__)
ptb_app = ApplicationBuilder().token(TOKEN).build()

# --- LOGIKA BOT (Tetap sama) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = os.getenv("WEBAPP_URL")
    kbd = [[InlineKeyboardButton("📊 Dashboard", web_app=WebAppInfo(url=url))]]
    await update.message.reply_text("Halo! Bot aktif. Kirim foto makanan untuk cek kalori.", reply_markup=InlineKeyboardMarkup(kbd))

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # (Logika Gemini & Supabase Anda di sini...)
    await update.message.reply_text("Foto diterima! Sedang diproses...")

ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# --- WEBHOOK ROUTE ---
@app_flask.route(f"/{TOKEN}", methods=['POST'])
async def webhook():
    update = Update.de_json(request.get_json(force=True), ptb_app.bot)
    await ptb_app.process_update(update)
    return "OK", 200

@app_flask.route('/')
def index():
    return "Bot is Waiting for Network...", 200

# --- FUNGSI TUNGGU JARINGAN (RETRY LOGIC) ---
async def start_bot_with_retry():
    max_retries = 10
    retry_delay = 10 # detik
    
    for i in range(max_retries):
        try:
            logger.info(f"Mencoba menyambung ke Telegram (Percobaan {i+1}/{max_retries})...")
            # Cek DNS secara manual dulu
            socket.gethostbyname('api.telegram.org')
            
            # Jika DNS ok, jalankan inisialisasi
            await ptb_app.initialize()
            webhook_url = f"{BASE_URL}/{TOKEN}"
            await ptb_app.bot.set_webhook(url=webhook_url)
            logger.info(f"✅ Webhook berhasil diset ke: {webhook_url}")
            return # Keluar dari loop jika berhasil
        except Exception as e:
            logger.error(f"❌ Koneksi gagal: {e}")
            if i < max_retries - 1:
                logger.info(f"Menunggu {retry_delay} detik sebelum mencoba lagi...")
                await asyncio.sleep(retry_delay)
            else:
                logger.error("Sistem menyerah. Periksa koneksi internet server.")

def run_bot_thread():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_bot_with_retry())

if __name__ == '__main__':
    # Jalankan Bot di thread berbeda agar Flask bisa start duluan
    # Ini supaya Space tidak dianggap 'Crashed' oleh Hugging Face
    bot_thread = Thread(target=run_bot_thread)
    bot_thread.start()
    
    # Jalankan Flask (HF butuh port 7860 segera aktif)
    app_flask.run(host='0.0.0.0', port=7860)