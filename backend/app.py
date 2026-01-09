import os
import json
import logging
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import google.generativeai as genai
from supabase import create_client, Client

# --- SERVER FLASK (PENTING: Port 7860 untuk Hugging Face) ---
server = Flask(__name__)

@server.route('/')
def health_check():
    return "Bot status: ACTIVE", 200

def run_web_server():
    # Hugging Face secara default membaca port 7860
    server.run(host='0.0.0.0', port=7860)

# --- KONFIGURASI SUPABASE & GEMINI ---
# Variabel diambil dari Secrets di Hugging Face Settings
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"), 
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

async def analyze_food(image_bytes):
    prompt = """Analyze this food image. Return ONLY a raw JSON object:
    {"food_name": "name", "calories": 100, "protein": 5.0, "carbs": 10.0, "fat": 2.0}
    Do not include markdown tags like ```json."""
    
    response = model.generate_content([{"mime_type": "image/jpeg", "data": image_bytes}, prompt])
    clean_text = response.text.strip().replace("```json", "").replace("```", "")
    return json.loads(clean_text)

# --- HANDLERS BOT ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # WEBAPP_URL diambil dari Secrets (URL Netlify Anda)
    url = os.getenv("WEBAPP_URL")
    kbd = [[InlineKeyboardButton("📊 Buka Dashboard Kalori", web_app=WebAppInfo(url=url))]]
    await update.message.reply_text(
        f"Halo {update.effective_user.first_name}! 🍎\nKirim foto makanan untuk cek kalori.",
        reply_markup=InlineKeyboardMarkup(kbd)
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = await update.message.reply_text("Sedang menganalisis makanan... ⏳")
    photo = await update.message.photo[-1].get_file()
    img_bytes = await photo.download_as_bytearray()
    
    try:
        data = await analyze_food(img_bytes)
        supabase.table("calorie_logs").insert({
            "user_id": update.effective_user.id,
            **data
        }).execute()
        
        res = (f"✅ *{data['food_name']}*\n🔥 {data['calories']} kcal\n"
               f"P: {data['protein']}g | C: {data['carbs']}g | L: {data['fat']}g")
        await status.edit_text(res, parse_mode="Markdown")
    except Exception as e:
        await status.edit_text("Gagal menganalisis makanan. Pastikan foto makanan terlihat jelas.")

# --- RUNNER ---
if __name__ == '__main__':
    # 1. Jalankan Flask di Thread berbeda agar UptimeRobot bisa nge-ping
    Thread(target=run_web_server).start()
    
    # 2. Jalankan Bot
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("Bot is starting...")
    app.run_polling()