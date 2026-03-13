import logging
import os
import asyncio
from typing import Dict, List
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import AsyncOpenAI
import base64
from io import BytesIO
from PIL import Image

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment variables
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY')
PORT = int(os.environ.get('PORT', 8080))

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
4. Uzun javoblarni qismlarga bo'lib yozing"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    await update.message.reply_text(
        "🚀 **DeepSeek AI Bot ishga tushdi!**\n\n"
        "Men Fly.io da host qilinganman!\n"
        "Savollaringizni yozing.",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messages"""
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, 
        action="typing"
    )
    
    try:
        # Initialize history
        if 'messages' not in context.user_data:
            context.user_data['messages'] = [
                {"role": "system", "content": SYSTEM_PROMPT}
            ]
        
        # Add user message
        context.user_data['messages'].append({
            "role": "user", 
            "content": update.message.text
        })
        
        # Keep last 20 messages
        if len(context.user_data['messages']) > 21:
            context.user_data['messages'] = [
                context.user_data['messages'][0]
            ] + context.user_data['messages'][-20:]
        
        # Get response
        response = await client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=context.user_data['messages'],
            temperature=0.7,
            max_tokens=2000
        )
        
        reply = response.choices[0].message.content
        
        # Add to history
        context.user_data['messages'].append({
            "role": "assistant", 
            "content": reply
        })
        
        # Send response
        await update.message.reply_text(reply)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Xatolik: {str(e)[:100]}")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photos"""
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, 
        action="typing"
    )
    
    try:
        # Get photo
        photo = await update.message.photo[-1].get_file()
        photo_bytes = await photo.download_as_bytearray()
        
        # Convert to base64
        base64_image = base64.b64encode(photo_bytes).decode('utf-8')
        
        # Get caption
        prompt = update.message.caption or "Bu rasmda nima bor?"
        
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
                        {"type": "text", "text": prompt}
                    ]
                }
            ],
            max_tokens=500
        )
        
        await update.message.reply_text(
            f"🖼 **Rasm tahlili:**\n\n{response.choices[0].message.content}",
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Photo error: {e}")
        await update.message.reply_text("❌ Rasmni tahlil qilishda xatolik.")

async def health_check(request):
    """Health check for Fly.io"""
    return "OK"

def main():
    """Start bot"""
    if not TELEGRAM_TOKEN or not DEEPSEEK_API_KEY:
        logger.error("Tokens not set!")
        return
    
    # Create application
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    # Start webhook for Fly.io
    logger.info(f"Starting bot on port {PORT}...")
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_TOKEN,
        webhook_url=f"https://your-app-name.fly.dev/{TELEGRAM_TOKEN}"
    )

if __name__ == "__main__":
    main()
