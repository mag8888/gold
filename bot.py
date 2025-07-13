import os
import logging
from typing import Optional, Dict, List
from datetime import datetime
import requests
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, 
    CommandHandler, 
    CallbackQueryHandler, 
    CallbackContext,
    MessageHandler,
    Filters
)

# ===== CONFIGURATION =====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('gold_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration (should use environment variables in production)
CONFIG = {
    'TELEGRAM_TOKEN': os.getenv('TELEGRAM_TOKEN', 'YOUR_TELEGRAM_TOKEN'),
    'API_BASE_URL': os.getenv('API_BASE_URL', 'https://api.example.com/gold'),
    'API_KEY': os.getenv('GOLD_API_KEY', 'YOUR_API_KEY'),
    'CACHE_TTL': 300,  # 5 minutes cache
    'ADMIN_IDS': [12345678],  # List of admin user IDs
    'TIMEZONE': 'Europe/Moscow'
}

# ===== CACHE SYSTEM =====
class PriceCache:
    _instance = None
    last_price = None
    last_update = None
    history = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PriceCache, cls).__new__(cls)
        return cls._instance
    
    def update(self, price: float) -> None:
        self.last_price = price
        self.last_update = datetime.now(pytz.timezone(CONFIG['TIMEZONE']))
        self.history.append((price, self.last_update))
        if len(self.history) > 100:  # Keep last 100 records
            self.history.pop(0)
    
    def is_valid(self) -> bool:
        if not self.last_update:
            return False
        return (datetime.now(pytz.timezone(CONFIG['TIMEZONE'])) - self.last_update).seconds < CONFIG['CACHE_TTL']

# ===== API FUNCTIONS =====
def fetch_gold_price() -> Optional[float]:
    """Fetch current gold price from API"""
    try:
        headers = {"Authorization": f"Bearer {CONFIG['API_KEY']}"}
        params = {"currency": "USD"}
        response = requests.get(
            f"{CONFIG['API_BASE_URL']}/price",
            headers=headers,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return float(data.get('price'))
    except (requests.exceptions.RequestException, ValueError) as e:
        logger.error(f"API request failed: {e}")
        return None

def get_gold_price() -> Optional[float]:
    """Get gold price with cache support"""
    cache = PriceCache()
    
    if cache.is_valid():
        logger.debug("Returning cached price")
        return cache.last_price
    
    current_price = fetch_gold_price()
    if current_price is not None:
        cache.update(current_price)
    
    return current_price

# ===== BOT COMMANDS =====
def start(update: Update, context: CallbackContext) -> None:
    """Handle /start command"""
    try:
        user = update.effective_user
        welcome_msg = (
            f"🛠 Привет, {user.first_name}!\n\n"
            "🔹 Я бот для отслеживания цен на золото.\n"
            "🔹 Доступные команды:\n"
            "/price - текущая цена\n"
            "/history - история цен\n"
            "/subscribe - подписаться на обновления\n"
            "/help - справка"
        )
        
        keyboard = [
            [InlineKeyboardButton("Текущая цена", callback_data='quick_price')],
            [InlineKeyboardButton("История цен", callback_data='price_history')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        update.message.reply_text(welcome_msg, reply_markup=reply_markup)
        logger.info(f"User {user.id} started the bot")
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        send_error_message(update)

def price(update: Update, context: CallbackContext) -> None:
    """Handle /price command"""
    try:
        current_price = get_gold_price()
        cache = PriceCache()
        
        if current_price is not None:
            last_update = cache.last_update.strftime('%d.%m.%Y %H:%M') if cache.last_update else "неизвестно"
            
            message = (
                f"💰 Текущая цена на золото: {current_price:.2f} USD/унция\n"
                f"🕒 Последнее обновление: {last_update}"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data='refresh_price')],
                [InlineKeyboardButton("📈 История", callback_data='price_history'),
                 InlineKeyboardButton("🔔 Подписаться", callback_data='subscribe')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            update.message.reply_text(message, reply_markup=reply_markup)
        else:
            update.message.reply_text("⚠️ Не удалось получить текущую цену. Попробуйте позже.")
            
    except Exception as e:
        logger.error(f"Error in price command: {e}")
        send_error_message(update)

def history(update: Update, context: CallbackContext) -> None:
    """Handle /history command"""
    try:
        cache = PriceCache()
        
        if not cache.history:
            update.message.reply_text("История цен пока недоступна.")
            return
            
        # Get last 7 days history
        recent_history = cache.history[-7:]
        history_text = "📈 История цен за последние 7 дней:\n\n"
        
        for price, date in recent_history:
            history_text += f"{date.strftime('%d.%m.%Y')}: {price:.2f} USD\n"
        
        update.message.reply_text(history_text)
        
    except Exception as e:
        logger.error(f"Error in history command: {e}")
        send_error_message(update)

# ===== HELPER FUNCTIONS =====
def send_error_message(update: Update) -> None:
    """Send user-friendly error message"""
    if update and update.effective_message:
        update.effective_message.reply_text(
            "⚠️ Произошла ошибка. Пожалуйста, попробуйте позже.\n"
            "Если проблема сохраняется, сообщите администратору."
        )

def format_price_message(price: float, timestamp: datetime) -> str:
    """Format price message with emoji"""
    trend_emoji = "➡️"
    if len(PriceCache().history) > 1:
        prev_price = PriceCache().history[-2][0]
        trend_emoji = "📈" if price > prev_price else "📉" if price < prev_price else "➡️"
    
    return (
        f"{trend_emoji} Новая цена на золото: {price:.2f} USD/унция\n"
        f"🕒 Обновлено: {timestamp.strftime('%d.%m.%Y %H:%M')}"
    )

# ===== BUTTON HANDLERS =====
def button_handler(update: Update, context: CallbackContext) -> None:
    """Handle inline button presses"""
    query = update.callback_query
    query.answer()
    
    try:
        if query.data == 'refresh_price':
            current_price = get_gold_price()
            cache = PriceCache()
            
            if current_price:
                new_text = format_price_message(current_price, cache.last_update)
                query.edit_message_text(text=new_text)
            else:
                query.edit_message_text(text="⚠️ Не удалось обновить цену")
                
        elif query.data == 'price_history':
            history(update, context)
            
        elif query.data == 'quick_price':
            current_price = get_gold_price()
            if current_price:
                query.edit_message_text(text=f"💰 Текущая цена: {current_price:.2f} USD")
            else:
                query.edit_message_text(text="⚠️ Цена недоступна")
                
        elif query.data == 'subscribe':
            query.edit_message_text(
                text="🔔 Функция подписки в разработке. Используйте /subscribe"
            )
            
    except Exception as e:
        logger.error(f"Error in button handler: {e}")
        query.edit_message_text(text="⚠️ Ошибка обработки запроса")

# ===== ADMIN COMMANDS =====
def stats(update: Update, context: CallbackContext) -> None:
    """Admin command: show bot statistics"""
    try:
        user = update.effective_user
        if user.id not in CONFIG['ADMIN_IDS']:
            update.message.reply_text("⛔ Доступ запрещен")
            return
            
        cache = PriceCache()
        stats_msg = (
            "📊 Статистика бота:\n\n"
            f"👥 Пользователей: {len(context.bot_data.get('users', []))}\n"
            f"💰 Последняя цена: {cache.last_price if cache.last_price else 'N/A'}\n"
            f"🕒 Последнее обновление: {cache.last_update if cache.last_update else 'N/A'}\n"
            f"📝 Записей в истории: {len(cache.history)}"
        )
        
        update.message.reply_text(stats_msg)
        
    except Exception as e:
        logger.error(f"Error in stats command: {e}")
        send_error_message(update)

# ===== MAIN SETUP =====
def main() -> None:
    """Start the bot"""
    try:
        if not CONFIG['TELEGRAM_TOKEN']:
            raise ValueError("Telegram token is not configured")
            
        updater = Updater(CONFIG['TELEGRAM_TOKEN'])
        dispatcher = updater.dispatcher

        # Register handlers
        dispatcher.add_handler(CommandHandler("start", start))
        dispatcher.add_handler(CommandHandler("price", price))
        dispatcher.add_handler(CommandHandler("history", history))
        dispatcher.add_handler(CommandHandler("stats", stats))
        dispatcher.add_handler(CommandHandler("help", start))  # Reuse start as help
        
        dispatcher.add_handler(CallbackQueryHandler(button_handler))
        dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text_message))
        
        dispatcher.add_error_handler(error_handler)

        logger.info("Starting bot...")
        updater.start_polling()
        logger.info("Bot is now running")
        updater.idle()
        
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}")
        raise

def handle_text_message(update: Update, context: CallbackContext) -> None:
    """Handle regular text messages"""
    text = update.message.text.lower()
    
    if any(word in text for word in ['цена', 'gold', 'золот']):
        price(update, context)
    else:
        update.message.reply_text(
            "Не понял вашего сообщения. Используйте команды:\n"
            "/start - начало работы\n"
            "/price - текущая цена\n"
            "/help - справка"
        )

def error_handler(update: Update, context: CallbackContext) -> None:
    """Handle errors"""
    logger.error(msg="Exception while handling update:", exc_info=context.error)
    
    # Notify admins about critical errors
    if isinstance(context.error, Exception):
        for admin_id in CONFIG['ADMIN_IDS']:
            context.bot.send_message(
                admin_id,
                f"⚠️ Ошибка в боте:\n{context.error}\n\n"
                f"Update: {update.to_dict() if update else 'None'}"
            )
    
    if update and update.effective_message:
        send_error_message(update)

if __name__ == '__main__':
    main()