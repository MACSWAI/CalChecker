import os
import json
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
import google.generativeai as genai
from supabase import create_client

app = Flask(__name__)

# Konfigurasi API (diambil dari Vercel Env Vars)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

# Setup Bot
ptb_app = ApplicationBuilder().token(TOKEN).build()

# --- LOGIKA BOT ---
async def start(update, context):
    url = os.getenv("WEBAPP_URL")
    kbd = [[InlineKeyboardButton("📊 Buka Dashboard", web_app=WebAppInfo(url=url))]]
    await update.message.reply_text("Halo! Bot aktif di Vercel.", reply_markup=InlineKeyboardMarkup(kbd))

async def handle_photo(update, context):
    msg = await update.message.reply_text("Menganalisis makanan... ⏳")
    photo = await update.message.photo[-1].get_file()
    img_bytes = await photo.download_as_bytearray()
    
    try:
        # Prompt Gemini
        prompt = "Analyze this food image. Return ONLY raw JSON: {\"food_name\": str, \"calories\": int, \"protein\": float, \"carbs\": float, \"fat\": float}"
        response = model.generate_content([{"mime_type": "image/jpeg", "data": img_bytes}, prompt])
        data = json.loads(response.text.strip().replace("```json", "").replace("```", ""))
        
        # Simpan Supabase
        supabase.table("calorie_logs").insert({"user_id": update.effective_user.id, **data}).execute()
        await msg.edit_text(f"✅ {data['food_name']} - {data['calories']} kcal")
    except:
        await msg.edit_text("Gagal menganalisis foto.")

# Register Handlers
ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

@app.route('/')
def home():
    return "Bot is alive!"

@app.route('/webhook', methods=['POST'])
async def webhook():
    update = Update.de_json(request.get_json(force=True), ptb_app.bot)
    async with ptb_app:
        await ptb_app.process_update(update)
    return "OK", 200