import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI
import base64
from io import BytesIO

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables (Render.com dashboardda o'rnatiladi)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
PORT = int(os.environ.get('PORT', 10000))

# DeepSeek client
client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

# System prompt
SYSTEM_PROMPT = """Siz foydali va do'stona yordamchisiz. O'zbek tilida javob bering."""

# Foydalanuvchi suhbatlari
user_sessions = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start komandasi"""
    welcome_text = """
🚀 **DeepSeek AI Bot ishga tushdi!**

Men **Render.com** da host qilinganman!

**Buyruqlar:**
/help - Yordam
/clear - Tarixni tozalash
/about - Bot haqida

Savollaringizni yozing!
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Yordam komandasi"""
    help_text = """
📚 **Yordam**

• Oddiy matn yozing - suhbatlashamiz
• /clear - Suhbat tarixini tozalaydi
• /about - Bot haqida ma'lumot

**Maslahat:** Aniq savollar bering!
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Bot haqida"""
    about_text = """
🤖 **Bot haqida**

• **Platforma:** Render.com
• **API:** DeepSeek (bepul)
• **Model:** deepseek-chat
• **Yaratilgan:** 2024

@username tomonidan yaratilgan
    """
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

async def health_check(request):
    """Render.com uchun health check"""
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
        # Bot yaratish
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Handlerlar
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("about", about_command))
        app.add_handler(CommandHandler("clear", clear_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        logger.info(f"✅ Bot ishga tushdi! Port: {PORT}")
        
        # Webhook bilan ishga tushirish (Render.com uchun)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TELEGRAM_TOKEN,
            webhook_url=f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/{TELEGRAM_TOKEN}"
        )
        
    except Exception as e:
        logger.error(f"Bot ishga tushmadi: {e}")

if __name__ == "__main__":
    main()
