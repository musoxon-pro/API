import logging
import os
import sys
from typing import Dict, List
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI
import asyncio
import base64
from io import BytesIO

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Environment variables (PythonAnywhere dashboardda o'rnatiladi)
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
PYTHONANYWHERE_DOMAIN = os.environ.get('PYTHONANYWHERE_DOMAIN', 'yourusername.pythonanywhere.com')

# DeepSeek client
client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

# Models
DEFAULT_MODEL = "deepseek-chat"
CODE_MODEL = "deepseek-coder"
VISION_MODEL = "deepseek-vl"

# System prompt
SYSTEM_PROMPT = """Siz foydali va do'stona yordamchisiz. Quyidagi qoidalarga amal qiling:
1. O'zbek tilida (kirill yoki lotin) javob bering
2. Aniq va tushunarli javoblar bering
3. Kod so'ralsa, tushuntirish bilan bering
4. Uzun javoblarni qismlarga bo'lib yozing
5. Har doim xushmuomala bo'ling"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    welcome_text = """
🤖 **DeepSeek AI Bot - PythonAnywhere da!**

Assalomu alaykum! Men bepul DeepSeek API orqali ishlayman.

**Imkoniyatlar:**
• 💬 Matnli suhbat
• 👨‍💻 Kod yozish (deepseek-coder)
• 🖼 Rasm tahlili (deepseek-vl)
• 📚 Uzun matnlar (1M token)

**Buyruqlar:**
/help - Yordam
/clear - Tarixni tozalash
/stats - Statistika
/about - Bot haqida

Menga istalgan savolingizni yozing!
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command handler"""
    help_text = """
📚 **Yordam**

**Qanday ishlatish:**
• Oddiy matn yozing - suhbatlashamiz
• Rasm yuboring + izoh - tahlil qilaman
• Kod so'rang - masalan: "Python da kalkulyator yoz"

**Maslahatlar:**
• Aniq savollar bering
• Rasm yuborsangiz, nima qilishni yozing
• Uzun matnlarni qismlarga bo'lib yuboring

**Cheklovlar:**
• 60 so'rov/daqiqa
• 2048 token/javob
• Rasm hajmi < 20MB
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history"""
    if 'messages' in context.user_data:
        context.user_data['messages'] = []
    await update.message.reply_text("✅ Suhbat tarixi tozalandi!")

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics"""
    msg_count = len(context.user_data.get('messages', [])) // 2
    
    stats = f"""
📊 **Statistika**

• Xabarlar soni: {msg_count}
• Platforma: PythonAnywhere
• Model: DeepSeek Chat
• API holati: Bepul
• Ishlab turibdi: ✅
    """
    await update.message.reply_text(stats, parse_mode='Markdown')

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """About command"""
    about = """
🤖 **Bot haqida**

• **Yaratuvchi:** @username
• **Platforma:** PythonAnywhere
• **API:** DeepSeek (bepul)
• **Model:** deepseek-chat
• **Versiya:** 1.0.0

**Manba kod:** GitHub da ochiq
    """
    await update.message.reply_text(about, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    
    # Send typing action
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    user_message = update.message.text
    
    try:
        # Initialize conversation history
        if 'messages' not in context.user_data:
            context.user_data['messages'] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
        
        # Add user message
        context.user_data['messages'].append(
            {"role": "user", "content": user_message}
        )
        
        # Keep only last 15 messages (to save memory)
        if len(context.user_data['messages']) > 16:
            context.user_data['messages'] = [
                context.user_data['messages'][0]  # system prompt
            ] + context.user_data['messages'][-15:]  # last 15
        
        # Check if it's a coding question
        model = CODE_MODEL if any(word in user_message.lower() 
                                 for word in ['kod', 'dastur', 'function', 'class']) \
                else DEFAULT_MODEL
        
        # Get response from DeepSeek
        response = await client.chat.completions.create(
            model=model,
            messages=context.user_data['messages'],
            temperature=0.7,
            max_tokens=1000,
            timeout=30
        )
        
        reply_text = response.choices[0].message.content
        
        # Add response to history
        context.user_data['messages'].append(
            {"role": "assistant", "content": reply_text}
        )
        
        # Send response
        await update.message.reply_text(reply_text)
        
    except asyncio.TimeoutError:
        await update.message.reply_text("⏱ So'rov juda uzoq davom etdi. Qayta urinib ko'ring.")
    except Exception as e:
        logger.error(f"Error: {e}")
        error_msg = f"❌ Xatolik: {str(e)[:100]}"
        await update.message.reply_text(error_msg)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages"""
    
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    try:
        # Get photo
        photo_file = await update.message.photo[-1].get_file()
        photo_bytes = await photo_file.download_as_bytearray()
        
        # Convert to base64
        base64_image = base64.b64encode(photo_bytes).decode('utf-8')
        
        # Get caption
        prompt = update.message.caption or "Bu rasmda nima tasvirlangan? O'zbek tilida tushuntir."
        
        # Vision model
        response = await client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        reply = f"🖼 **Rasm tahlili:**\n\n{response.choices[0].message.content}"
        await update.message.reply_text(reply, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Photo error: {e}")
        await update.message.reply_text("❌ Rasmni tahlil qilishda xatolik.")

def main():
    """Main function"""
    if not TELEGRAM_TOKEN or not DEEPSEEK_API_KEY:
        logger.error("Tokens not set!")
        sys.exit(1)
    
    try:
        # Create application
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("clear", clear_command))
        app.add_handler(CommandHandler("stats", stats_command))
        app.add_handler(CommandHandler("about", about_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
        
        logger.info("Bot started successfully on PythonAnywhere!")
        
        # Start polling (for PythonAnywhere)
        app.run_polling()
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
