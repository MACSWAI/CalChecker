import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

# Inisialisasi API
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY"))
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

async def analyze_food(image_bytes):
    prompt = """Analyze this food image. Return ONLY a raw JSON object:
    {"food_name": "name", "calories": 100, "protein": 5.0, "carbs": 10.0, "fat": 2.0}
    Do not include markdown tags or other text."""
    
    response = model.generate_content([{"mime_type": "image/jpeg", "data": image_bytes}, prompt])
    # Membersihkan karakter ```json ... ``` jika ada
    clean_text = response.text.strip().replace("```json", "").replace("```", "")
    return json.loads(clean_text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = os.getenv("WEBAPP_URL")
    kbd = [[InlineKeyboardButton("📊 Buka Dashboard Kalori", web_app=WebAppInfo(url=url))]]
    await update.message.reply_text(
        "Halo! Saya asisten kalori AI.\n\n"
        "1. Kirim foto makanan untuk cek kalori.\n"
        "2. Ketik `/bmi [berat_kg] [tinggi_cm]` untuk profil.",
        reply_markup=InlineKeyboardMarkup(kbd)
    )

async def handle_bmi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        w, h = float(context.args[0]), float(context.args[1])
        bmi = round(w / ((h/100)**2), 1)
        cat = "Normal"
        if bmi < 18.5: cat = "Underweight"
        elif bmi >= 25: cat = "Overweight"
        
        supabase.table("profiles").upsert({
            "id": update.effective_user.id,
            "username": update.effective_user.username,
            "weight": w, "height": h, "bmi": bmi, "bmi_category": cat
        }).execute()
        await update.message.reply_text(f"BMI Anda: {bmi} ({cat}) ✅")
    except:
        await update.message.reply_text("Gunakan format: /bmi 70 170")

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
        
        res = (f"✅ {data['food_name']}\n🔥 {data['calories']} kcal\n"
               f"P: {data['protein']}g | C: {data['carbs']}g | L: {data['fat']}g")
        await status.edit_text(res)
    except Exception as e:
        await status.edit_text(f"Gagal mendeteksi makanan. Pastikan foto jelas.")

if __name__ == '__main__':
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("bmi", handle_bmi))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()