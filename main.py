import os
import logging
import asyncio
from flask import Flask, request
import threading
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI
import base64

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
PORT = int(os.environ.get('PORT', 10000))

# Flask app (Render.com web service uchun)
app = Flask(__name__)

# DeepSeek client
client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

# System prompt
SYSTEM_PROMPT = """Siz foydali va do'stona yordamchisiz. O'zbek tilida javob bering."""

# Foydalanuvchi suhbatlari
user_sessions = {}

# Bot application (global)
telegram_app = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi"""
    welcome_text = (
        "🚀 **DeepSeek AI Bot ishga tushdi!**\n\n"
        "Men **Render.com** da host qilinganman!\n\n"
        "**Buyruqlar:**\n"
        "/help - Yordam\n"
        "/clear - Tarixni tozalash\n"
        "/about - Bot haqida\n\n"
        "Savollaringizni yozing!"
    )
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam komandasi"""
    help_text = (
        "📚 **Yordam**\n\n"
        "• Oddiy matn yozing - suhbatlashamiz\n"
        "• /clear - Suhbat tarixini tozalaydi\n"
        "• /about - Bot haqida ma'lumot\n\n"
        "**Maslahat:** Aniq savollar bering!"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot haqida"""
    about_text = (
        "🤖 **Bot haqida**\n\n"
        "• **Platforma:** Render.com\n"
        "• **API:** DeepSeek (bepul)\n"
        "• **Model:** deepseek-chat\n"
        "• **Yaratilgan:** 2025\n\n"
        "@username tomonidan yaratilgan"
    )
    await update.message.reply_text(about_text, parse_mode='Markdown')

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tarixni tozalash"""
    user_id = update.effective_user.id
    if user_id in user_sessions:
        del user_sessions[user_id]
    await update.message.reply_text("✅ Suhbat tarixi tozalandi!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xabarlarni qabul qilish"""
    
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Typing indicator
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    try:
        # Yangi suhbat boshlash
        if user_id not in user_sessions:
            user_sessions[user_id] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
        
        # Foydalanuvchi xabarini qo'shish
        user_sessions[user_id].append({
            "role": "user",
            "content": user_message
        })
        
        # Oxirgi 10 ta xabarni saqlash
        if len(user_sessions[user_id]) > 11:
            user_sessions[user_id] = [
                user_sessions[user_id][0]
            ] + user_sessions[user_id][-10:]
        
        # DeepSeek API ga so'rov
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=user_sessions[user_id],
            temperature=0.7,
            max_tokens=1000,
            timeout=30
        )
        
        reply_text = response.choices[0].message.content
        
        # Javobni saqlash
        user_sessions[user_id].append({
            "role": "assistant",
            "content": reply_text
        })
        
        # Javobni yuborish
        await update.message.reply_text(reply_text)
        
    except Exception as e:
        logger.error(f"Xatolik: {e}")
        await update.message.reply_text(
            f"❌ Xatolik yuz berdi. Iltimos, keyinroq urinib ko'ring."
        )

def run_bot():
    """Botni alohida threadda ishga tushirish"""
    global telegram_app
    
    try:
        # Bot yaratish
        telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Handlerlar
        telegram_app.add_handler(CommandHandler("start", start))
        telegram_app.add_handler(CommandHandler("help", help_command))
        telegram_app.add_handler(CommandHandler("about", about_command))
        telegram_app.add_handler(CommandHandler("clear", clear_command))
        telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info("✅ Bot ishga tushmoqda...")
        
        # Polling bilan ishga tushirish (webhook o'rniga)
        telegram_app.run_polling(drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"Bot ishga tushmadi: {e}")

@app.route('/')
def home():
    """Home page"""
    return "🤖 DeepSeek AI Bot ishlayapti!"

@app.route('/health')
def health():
    """Health check"""
    return "OK", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook endpoint (ixtiyoriy)"""
    if telegram_app:
        # Webhook logikasi
        pass
    return "OK", 200

def main():
    """Asosiy funksiya"""
    
    # Tokenlarni tekshirish
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN topilmadi!")
        return
    
    if not DEEPSEEK_API_KEY:
        logger.error("DEEPSEEK_API_KEY topilmadi!")
        return
    
    try:
        # Botni alohida threadda ishga tushirish
        bot_thread = threading.Thread(target=run_bot, daemon=True)
        bot_thread.start()
        
        logger.info(f"🌐 Flask server ishga tushdi: Port {PORT}")
        
        # Flask serverini ishga tushirish (Render.com uchun)
        app.run(host='0.0.0.0', port=PORT)
        
    except Exception as e:
        logger.error(f"Xatolik: {e}")

if __name__ == "__main__":
    main()
