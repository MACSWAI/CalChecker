import os
from dotenv import load_dotenv

# Ambil path folder tempat script berada
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
WEBAPP_URL = os.getenv("WEBAPP_URL")
# Inisialisasi API
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Inisialisasi Bot Telegram (Tanpa start_polling)
ptb_app = ApplicationBuilder().token(TOKEN).build()

async def analyze_food(image_bytes):
    prompt = "Analyze this food image. Return ONLY raw JSON: {\"food_name\": str, \"calories\": int, \"protein\": float, \"carbs\": float, \"fat\": float}"
    response = model.generate_content([{"mime_type": "image/jpeg", "data": image_bytes}, prompt])
    # Bersihkan response jika ada markdown ```json
    clean_text = response.text.strip().replace("```json", "").replace("```", "")
    return json.loads(clean_text)

async def start(update, context):
    kbd = [[InlineKeyboardButton("📊 Buka Dashboard", web_app=WebAppInfo(url=WEBAPP_URL))]]
    await update.message.reply_text(
        "Halo! Saya asisten kalori AI kamu. Kirim foto makanan ya!",
        reply_markup=InlineKeyboardMarkup(kbd)
    )

async def handle_photo(update, context):
    msg = await update.message.reply_text("Menganalisis makanan... ⏳")
    photo_file = await update.message.photo[-1].get_file()
    img_bytes = await photo_file.download_as_bytearray()
    
    try:
        data = await analyze_food(img_bytes)
        supabase.table("calorie_logs").insert({"user_id": update.effective_user.id, **data}).execute()
        
        res = (f"✅ {data['food_name']}\n"
               f"🔥 {data['calories']} kcal\n"
               f"P: {data['protein']}g | C: {data['carbs']}g | L: {data['fat']}g")
        await msg.edit_text(res)
    except Exception as e:
        await msg.edit_text("Gagal menganalisis foto. Pastikan gambar jelas.")

# Tambahkan handler
ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# Endpoint Webhook untuk Telegram
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == "POST":
        update = Update.de_json(request.get_json(force=True), ptb_app.bot)
        # Menjalankan PTB secara asinkron
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ptb_app.initialize())
        loop.run_until_complete(ptb_app.process_update(update))
        loop.close()
        return "OK", 200

@app.route('/')
def index():
    return "Bot is running on PythonAnywhere!"

# Bagian ini sangat penting untuk PythonAnywhere
if __name__ == "__main__":
    app.run(debug=True)