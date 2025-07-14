import asyncio
import logging
import sqlite3
from datetime import datetime, date
from typing import Dict, Optional

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from dotenv import load_dotenv
import os

from database import Database
from openai_service import OpenAIService
from scheduler import ReportScheduler
from reminder_system import start_habit_reminders, stop_habit_reminders, start_daily_reminder_check, active_reminders

# Загружаем переменные окружения
load_dotenv()

# Константы
CORRECT_BOT_USERNAME = "Alteria_8_bot"

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("BOT_TOKEN not found in environment variables")
    raise ValueError("BOT_TOKEN is required")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Инициализация базы данных
db = Database()

# Глобальный планировщик
scheduler = None

# Состояния для FSM
class OnboardingStates(StatesGroup):
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_bio = State()
    waiting_for_product = State()
    waiting_for_cases = State()
    waiting_for_motivation = State()
    waiting_for_values = State()
    waiting_for_goals = State()
    waiting_for_lifestyle = State()
    waiting_for_social = State()

class GoalStates(StatesGroup):
    waiting_for_goals_input = State()
    waiting_for_goal_type = State()
    waiting_for_goal_update = State()

class EditStates(StatesGroup):
    waiting_for_manual_edit = State()

class AdminStates(StatesGroup):
    waiting_for_broadcast_message = State()

class HabitStates(StatesGroup):
    waiting_for_habit_name = State()
    waiting_for_habit_description = State()
    waiting_for_habit_type = State()
    waiting_for_habit_frequency = State()
    waiting_for_habit_reminder = State()
    waiting_for_habit_notes = State()

class CalendarStates(StatesGroup):
    waiting_for_event_title = State()
    waiting_for_event_description = State()
    waiting_for_event_date = State()
    waiting_for_event_time = State()
    waiting_for_event_type = State()
    waiting_for_reminder_time = State()

# Клавиатуры
def get_main_menu_keyboard():
    """Главное меню бота"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🤝 Партнёры"), KeyboardButton(text="📅 Привычки")],
            [KeyboardButton(text="📁 Меню")],
            [KeyboardButton(text="🎯 Цели"), KeyboardButton(text="🚀 Развитие")]
        ],
        resize_keyboard=True,
        persistent=True
    )
    return keyboard

def get_full_menu_keyboard():
    """Полное меню со всеми функциями"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🆔 Визитка", callback_data="profile")],
            [InlineKeyboardButton(text="🌐 Нетворкинг", callback_data="networking")],
            [InlineKeyboardButton(text="📋 Органайзер", callback_data="organizer")],
            [InlineKeyboardButton(text="📆 Календарь", callback_data="calendar")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings")]
        ]
    )
    return keyboard

def get_yes_no_keyboard():
    """Клавиатура Да/Нет"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data="no")
            ]
        ]
    )
    return keyboard

def get_card_management_keyboard():
    """Клавиатура управления визиткой"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💾 Сохранить", callback_data="save_card")],
            [InlineKeyboardButton(text="🔄 Перегенерировать", callback_data="regenerate_card")],
            [InlineKeyboardButton(text="✏️ Изменить описание", callback_data="edit_card")],
            [InlineKeyboardButton(text="🔙 Меню", callback_data="main_menu")]
        ]
    )
    return keyboard

def get_categories_keyboard():
    """Клавиатура выбора категории"""
    categories = db.get_categories()
    keyboard_buttons = []
    
    for category in categories:
        button = InlineKeyboardButton(
            text=f"{category['category_emoji']} {category['category_name']}",
            callback_data=f"category_{category['category_id']}"
        )
        keyboard_buttons.append([button])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard

def get_goal_type_keyboard():
    """Клавиатура выбора типа цели"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Ежедневные", callback_data="goal_type_daily")],
            [InlineKeyboardButton(text="📆 Ежемесячные", callback_data="goal_type_monthly")]
        ]
    )
    return keyboard

def get_goals_keyboard(goals, goal_type):
    """Клавиатура для выбора цели для обновления"""
    keyboard_buttons = []
    
    for i, goal in enumerate(goals):
        emoji = "✅" if goal['status'] == 'completed' else "⚡️"
        text = f"{emoji} {goal['goal_text'][:30]}..."
        button = InlineKeyboardButton(
            text=text,
            callback_data=f"update_goal_{goal['goal_id']}"
        )
        keyboard_buttons.append([button])
    
    # Добавляем кнопку "Назад"
    keyboard_buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="goals_menu")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard

def get_goal_status_keyboard(goal_id):
    """Клавиатура для изменения статуса цели"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"goal_complete_{goal_id}")],
            [InlineKeyboardButton(text="⚡️ В процессе", callback_data=f"goal_progress_{goal_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="goals_menu")]
        ]
    )
    return keyboard

def get_habits_menu_keyboard():
    """Главное меню привычек"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить привычку", callback_data="add_habit")],
            [InlineKeyboardButton(text="📋 Мои привычки", callback_data="my_habits")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="habits_stats")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ]
    )
    return keyboard

def get_habit_type_keyboard():
    """Клавиатура выбора типа привычки"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Ежедневная", callback_data="habit_type_daily")],
            [InlineKeyboardButton(text="📆 Еженедельная", callback_data="habit_type_weekly")],
            [InlineKeyboardButton(text="🔧 Настраиваемая", callback_data="habit_type_custom")]
        ]
    )
    return keyboard

def get_habits_list_keyboard(habits):
    """Клавиатура со списком привычек пользователя"""
    keyboard_buttons = []
    
    for habit in habits:
        # Получаем статистику за сегодня
        from datetime import date
        today = date.today()
        
        # Получаем количество выполнений за сегодня из базы данных
        habit_stats = db.get_habit_stats(habit['user_id'], habit['habit_id'], days=1)
        completed_today = habit_stats.get('completed_count', 0) or 0  # Защита от None
        target_frequency = habit.get('target_frequency', 1) or 1  # Защита от None
        
        # Формируем отображение с молнией и галочкой в разные стороны
        if habit['is_active']:
            # Симметричное форматирование с пробелами
            text = f"{target_frequency} ⚡ {habit['habit_name']} ✅ {completed_today}"
            status_emoji = "🟢" if completed_today >= target_frequency else "🟡"
        else:
            text = f"⏸️ {habit['habit_name']}"
            status_emoji = "⏸️"
        button = InlineKeyboardButton(
            text=text,
            callback_data=f"habit_detail_{habit['habit_id']}"
        )
        keyboard_buttons.append([button])
    
    # Добавляем кнопки управления
    keyboard_buttons.append([
        InlineKeyboardButton(text="➕ Добавить", callback_data="add_habit"),
        InlineKeyboardButton(text="📊 Все привычки", callback_data="habits_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard

def get_habit_detail_keyboard(habit_id, is_active=True):
    """Клавиатура для детального просмотра привычки"""
    keyboard_buttons = []
    
    # Кнопка отметки выполнения
    keyboard_buttons.append([
        InlineKeyboardButton(text="✅ Выполнено", callback_data=f"habit_complete_{habit_id}"),
        InlineKeyboardButton(text="❌ Не выполнено", callback_data=f"habit_skip_{habit_id}")
    ])
    
    # Кнопка паузы/возобновления
    if is_active:
        keyboard_buttons.append([InlineKeyboardButton(text="⏸️ Приостановить", callback_data=f"habit_pause_{habit_id}")])
    else:
        keyboard_buttons.append([InlineKeyboardButton(text="▶️ Возобновить", callback_data=f"habit_resume_{habit_id}")])
    
    # Кнопки навигации
    keyboard_buttons.append([
        InlineKeyboardButton(text="📊 Статистика", callback_data=f"habit_stats_{habit_id}"),
        InlineKeyboardButton(text="🔙 К списку", callback_data="my_habits")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard

def get_habit_frequency_keyboard():
    """Клавиатура выбора частоты привычки"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 раз в день", callback_data="freq_1")],
            [InlineKeyboardButton(text="2 раза в день", callback_data="freq_2")],
            [InlineKeyboardButton(text="3 раза в день", callback_data="freq_3")],
            [InlineKeyboardButton(text="Другое", callback_data="freq_custom")]
        ]
    )
    return keyboard

def get_calendar_menu_keyboard():
    """Главное меню календаря"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить событие", callback_data="add_event")],
            [InlineKeyboardButton(text="📅 События сегодня", callback_data="events_today")],
            [InlineKeyboardButton(text="📆 События на неделю", callback_data="events_week")],
            [InlineKeyboardButton(text="📋 Все события", callback_data="all_events")],
            [InlineKeyboardButton(text="🔙 Главное меню", callback_data="main_menu")]
        ]
    )
    return keyboard

def get_event_type_keyboard():
    """Клавиатура выбора типа события"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📋 Задача", callback_data="event_type_task")],
            [InlineKeyboardButton(text="📅 Привычка", callback_data="event_type_habit")],
            [InlineKeyboardButton(text="💪 Тренировка", callback_data="event_type_workout")],
            [InlineKeyboardButton(text="🍽️ Прием пищи", callback_data="event_type_meal")],
            [InlineKeyboardButton(text="🤝 Встреча", callback_data="event_type_meeting")],
            [InlineKeyboardButton(text="⏰ Напоминание", callback_data="event_type_reminder")],
            [InlineKeyboardButton(text="📝 Другое", callback_data="event_type_custom")]
        ]
    )
    return keyboard

def get_reminder_time_keyboard():
    """Клавиатура выбора времени напоминания"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="За 5 минут", callback_data="reminder_5")],
            [InlineKeyboardButton(text="За 15 минут", callback_data="reminder_15")],
            [InlineKeyboardButton(text="За 30 минут", callback_data="reminder_30")],
            [InlineKeyboardButton(text="За 1 час", callback_data="reminder_60")],
            [InlineKeyboardButton(text="За 1 день", callback_data="reminder_1440")],
            [InlineKeyboardButton(text="Без напоминания", callback_data="reminder_none")]
        ]
    )
    return keyboard

def get_events_list_keyboard(events):
    """Клавиатура со списком событий"""
    keyboard_buttons = []
    
    for event in events:
        # Форматируем дату и время
        start_time = event['start_datetime'][:16] if event['start_datetime'] else "Не указано"
        
        # Эмодзи в зависимости от типа события
        type_emoji = {
            'task': '📋',
            'habit': '📅', 
            'workout': '💪',
            'meal': '🍽️',
            'meeting': '🤝',
            'reminder': '⏰',
            'custom': '📝'
        }.get(event['event_type'], '📝')
        
        text = f"{type_emoji} {event['event_title']} ({start_time})"
        button = InlineKeyboardButton(
            text=text[:50] + "..." if len(text) > 50 else text,
            callback_data=f"event_detail_{event['event_id']}"
        )
        keyboard_buttons.append([button])
    
    # Добавляем кнопки управления
    keyboard_buttons.append([
        InlineKeyboardButton(text="➕ Добавить", callback_data="add_event"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="calendar_menu")
    ])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    return keyboard

def get_event_detail_keyboard(event_id):
    """Клавиатура для детального просмотра события"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отметить выполненным", callback_data=f"event_complete_{event_id}")],
            [InlineKeyboardButton(text="❌ Отменить событие", callback_data=f"event_cancel_{event_id}")],
            [InlineKeyboardButton(text="🔙 К списку", callback_data="all_events")]
        ]
    )
    return keyboard

# Обработчики команд
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    username = message.from_user.username
    
    # Отладочные логи
    logger.info(f"START command received: user_id={user_id}, text='{message.text}'")
    
    # Извлекаем реферальный код из команды /start
    referral_code = None
    if message.text and len(message.text.split()) > 1:
        start_param = message.text.split()[1]
        logger.info(f"Start parameter: '{start_param}'")
        if start_param.startswith('REF_'):
            referral_code = start_param
            logger.info(f"Referral code found: '{referral_code}'")
    
    # Проверяем, есть ли пользователь в базе
    user = db.get_user(user_id)
    logger.info(f"User exists in DB: {user is not None}")
    
    if not user:
        # Создаем нового пользователя
        referrer_id = None
        if referral_code:
            # Ищем пользователя по реферальному коду
            referrer = db.get_user_by_referral_code(referral_code)
            logger.info(f"Referrer found: {referrer}")
            if referrer:
                referrer_id = referrer['user_id']
                logger.info(f"Referrer ID: {referrer_id}")
        
        db.create_user(user_id, first_name, last_name, username, referrer_id)
        logger.info(f"New user created with referrer_id: {referrer_id}")
        
        # Уведомляем реферера (если есть)
        if referrer_id:
            try:
                await bot.send_message(
                    referrer_id, 
                    f"🎉 По вашей ссылке зарегистрировался новый пользователь: {first_name}!"
                )
            except:
                pass  # Если не удалось отправить уведомление
        
        # Отправляем приветственное сообщение
        welcome_text = f"Здравствуйте, {first_name}!\n\nДобро пожаловать в AlteriA пространство саморазвития! 🚀\n\nХочешь заполнить визитку?"
        
        await message.answer(
            welcome_text,
            reply_markup=get_yes_no_keyboard()
        )
    else:
        # Пользователь уже существует
        if user['onboarding_completed']:
            await message.answer(
                f"С возвращением, {first_name}! 👋",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await message.answer(
                "Давайте продолжим заполнение вашей визитки!",
                reply_markup=get_yes_no_keyboard()
            )

# Команда для администраторов
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Админ-панель (упрощенная версия)"""
    # Простая проверка на админа (в реальности нужно более надежную)
    admin_ids = [123456789]  # Замените на реальные ID администраторов
    
    if message.from_user.id not in admin_ids:
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="⚙️ Настройки", callback_data="admin_settings")]
        ]
    )
    
    await message.answer(
        "🔧 **Админ-панель**\n\nВыберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
    """Начало создания рассылки"""
    await callback.message.edit_text(
        "📢 **Создание рассылки**\n\nВведите текст сообщения для отправки всем пользователям:",
        reply_markup=None
    )
    await state.set_state(AdminStates.waiting_for_broadcast_message)
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_broadcast_message))
async def process_broadcast_message(message: types.Message, state: FSMContext):
    """Обработка сообщения для рассылки"""
    broadcast_text = message.text
    
    progress_msg = await message.answer("📤 Отправляю рассылку...")
    
    # Отправляем рассылку
    sent_count, failed_count = await scheduler.send_broadcast_message(broadcast_text)
    
    await progress_msg.edit_text(
        f"✅ **Рассылка завершена**\n\n"
        f"📤 Отправлено: {sent_count}\n"
        f"❌ Не удалось: {failed_count}"
    )
    
    await state.clear()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    """Показ статистики бота"""
    # Получаем статистику из базы данных
    all_users = db.get_all_active_users()
    total_users = len(all_users)
    
    # Можно добавить больше статистики
    stats_text = f"""📊 **Статистика бота**

👥 Всего пользователей: {total_users}
✅ Активных: {total_users}
🚫 Заблокировали: 0

📅 Сегодня: {datetime.now().strftime('%d.%m.%Y')}"""
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=None,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "yes")
async def start_onboarding(callback: types.CallbackQuery, state: FSMContext):
    """Начало процесса онбординга"""
    await callback.message.edit_text(
        "Отлично! Давайте создадим вашу визитку.\n\n1/10. Как к тебе обращаться?"
    )
    await state.set_state(OnboardingStates.waiting_for_first_name)
    await callback.answer()

@dp.callback_query(F.data == "no")
async def skip_onboarding(callback: types.CallbackQuery, state: FSMContext):
    """Пропуск онбординга"""
    await callback.message.edit_text(
        "Хорошо! Вы всегда можете создать визитку позже через меню.",
        reply_markup=None
    )
    await callback.message.answer(
        "Добро пожаловать в AlteriA! 🎉",
        reply_markup=get_main_menu_keyboard()
    )
    await callback.answer()

# Обработчики онбординга
@dp.message(StateFilter(OnboardingStates.waiting_for_first_name))
async def process_first_name(message: types.Message, state: FSMContext):
    """Обработка имени"""
    await state.update_data(first_name=message.text)
    await message.answer("2/10. Введи фамилию.")
    await state.set_state(OnboardingStates.waiting_for_last_name)

@dp.message(StateFilter(OnboardingStates.waiting_for_last_name))
async def process_last_name(message: types.Message, state: FSMContext):
    """Обработка фамилии"""
    await state.update_data(last_name=message.text)
    await message.answer("3/10. Расскажи о себе, чем занимаешься (позиционирование).")
    await state.set_state(OnboardingStates.waiting_for_bio)

@dp.message(StateFilter(OnboardingStates.waiting_for_bio))
async def process_bio(message: types.Message, state: FSMContext):
    """Обработка биографии"""
    await state.update_data(bio=message.text)
    await message.answer("4/10. Есть ли у тебя свой продукт? Если да – какой.")
    await state.set_state(OnboardingStates.waiting_for_product)

@dp.message(StateFilter(OnboardingStates.waiting_for_product))
async def process_product(message: types.Message, state: FSMContext):
    """Обработка информации о продукте"""
    await state.update_data(product_info=message.text)
    await message.answer("5/10. Опиши свои лучшие кейсы.")
    await state.set_state(OnboardingStates.waiting_for_cases)

@dp.message(StateFilter(OnboardingStates.waiting_for_cases))
async def process_cases(message: types.Message, state: FSMContext):
    """Обработка кейсов"""
    await state.update_data(case_studies=message.text)
    await message.answer("6/10. ЗАЧЕМ тебе нетворкинг?")
    await state.set_state(OnboardingStates.waiting_for_motivation)

@dp.message(StateFilter(OnboardingStates.waiting_for_motivation))
async def process_motivation(message: types.Message, state: FSMContext):
    """Обработка мотивации"""
    await state.update_data(networking_motive=message.text)
    await message.answer("7/10. Топ-3 твоих жизненных ценности.")
    await state.set_state(OnboardingStates.waiting_for_values)

@dp.message(StateFilter(OnboardingStates.waiting_for_values))
async def process_values(message: types.Message, state: FSMContext):
    """Обработка ценностей"""
    await state.update_data(life_values=message.text)
    await message.answer("8/10. Какие цели у тебя на ближайший год?")
    await state.set_state(OnboardingStates.waiting_for_goals)

@dp.message(StateFilter(OnboardingStates.waiting_for_goals))
async def process_goals(message: types.Message, state: FSMContext):
    """Обработка целей"""
    await state.update_data(goals=message.text)
    await message.answer("9/10. Какой образ жизни ты ведёшь? (спорт, йога, медитации…)")
    await state.set_state(OnboardingStates.waiting_for_lifestyle)

@dp.message(StateFilter(OnboardingStates.waiting_for_lifestyle))
async def process_lifestyle(message: types.Message, state: FSMContext):
    """Обработка образа жизни"""
    await state.update_data(lifestyle=message.text)
    await message.answer("10/10. Ссылка на Instagram (или другую соцсеть).")
    await state.set_state(OnboardingStates.waiting_for_social)

@dp.message(StateFilter(OnboardingStates.waiting_for_social))
async def process_social_and_generate_card(message: types.Message, state: FSMContext):
    """Обработка соцсетей и генерация визитки"""
    await state.update_data(social_link=message.text)
    
    # Получаем все данные
    data = await state.get_data()
    
    # Показываем приветственное сообщение с картинкой и меню
    with open('/home/ubuntu/gold/welcome_image.png', 'rb') as photo:
        await message.answer_photo(
            photo=photo,
            caption="🎉 **Добро пожаловать в AlteriA!**\n\n"
                   "Ваша визитка генерируется... Пока можете изучить возможности бота!",
            reply_markup=get_main_menu_keyboard(),
            parse_mode="Markdown"
        )
    
    # Показываем прогресс
    progress_msg = await message.answer("⏳ Генерирую вашу визитку...")
    
    try:
        # Временная заглушка вместо openai_service
        business_card = f"""📋 **Визитка {data.get('first_name', 'Пользователь')}**

👤 **Имя:** {data.get('first_name', '')} {data.get('last_name', '')}
🏢 **Компания:** {data.get('company', 'Не указана')}
💼 **Должность:** {data.get('position', 'Не указана')}
📧 **Email:** {data.get('email', 'Не указан')}
📱 **Телефон:** {data.get('phone', 'Не указан')}
🌐 **Соцсети:** {data.get('social_link', 'Не указаны')}

💡 **О себе:** {data.get('bio', 'Информация не указана')}
🎯 **Цели:** {data.get('goals', 'Не указаны')}
🤝 **Интересы:** {data.get('interests', 'Не указаны')}"""
        
        if business_card:
            await progress_msg.delete()
            await message.answer(
                "🎉 Ваша визитка готова!\n\n" + business_card,
                reply_markup=get_card_management_keyboard(),
                parse_mode="Markdown"
            )
    except Exception as e:
        await progress_msg.edit_text(
            "❌ Произошла ошибка при генерации визитки. Попробуйте позже."
        )
    
    # Сохраняем данные в состоянии для дальнейшего использования
    await state.update_data(generated_card=business_card)
    await state.clear()

# Обработчики управления визиткой
@dp.callback_query(F.data == "save_card")
async def save_business_card(callback: types.CallbackQuery, state: FSMContext):
    """Сохранение визитки"""
    data = await state.get_data()
    
    # Сохраняем профиль в базу данных
    profile_data = {
        'bio': data.get('bio'),
        'product_info': data.get('product_info'),
        'case_studies': data.get('case_studies'),
        'networking_motive': data.get('networking_motive'),
        'life_values': data.get('life_values'),
        'lifestyle': data.get('lifestyle'),
        'social_link': data.get('social_link'),
        'generated_card': data.get('generated_card')
    }
    
    if db.save_profile(callback.from_user.id, profile_data):
        # Отмечаем онбординг как завершенный
        db.complete_onboarding(callback.from_user.id)
        
        await callback.message.edit_text(
            "Теперь выберите категорию для вашего профиля:",
            reply_markup=get_categories_keyboard()
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при сохранении визитки. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("category_"))
async def select_category(callback: types.CallbackQuery, state: FSMContext):
    """Выбор категории профиля"""
    category_id = callback.data.split("_")[1]
    
    # Получаем информацию о категории
    categories = db.get_categories()
    selected_category = next((cat for cat in categories if str(cat['category_id']) == category_id), None)
    
    if selected_category:
        # Обновляем профиль с выбранной категорией
        user_profile = db.get_profile(callback.from_user.id)
        if user_profile:
            user_profile['category'] = selected_category['category_name']
            db.save_profile(callback.from_user.id, user_profile)
        
        await callback.message.edit_text(
            f"✅ Отлично! Ваш профиль сохранен в категории {selected_category['category_emoji']} {selected_category['category_name']}\n\n"
            "Добро пожаловать в AlteriA! 🎉",
            reply_markup=None
        )
        
        await callback.message.answer(
            "Используйте меню для навигации:",
            reply_markup=get_main_menu_keyboard()
        )
    
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "regenerate_card")
async def regenerate_business_card(callback: types.CallbackQuery, state: FSMContext):
    """Перегенерация визитки"""
    data = await state.get_data()
    
    progress_msg = await callback.message.edit_text("⏳ Создаю новую версию визитки...")
    
    # Перегенерируем визитку
    new_card = openai_service.regenerate_business_card(data, data.get('generated_card', ''))
    
    if new_card:
        await progress_msg.edit_text(
            "🎉 Новая версия визитки готова!\n\n" + new_card,
            reply_markup=get_card_management_keyboard(),
            parse_mode="Markdown"
        )
        
        # Обновляем данные
        await state.update_data(generated_card=new_card)
    else:
        await progress_msg.edit_text(
            "❌ Произошла ошибка при генерации новой визитки.",
            reply_markup=get_card_management_keyboard()
        )
    
    await callback.answer()

@dp.callback_query(F.data == "edit_card")
async def edit_business_card(callback: types.CallbackQuery, state: FSMContext):
    """Ручное редактирование визитки"""
    await callback.message.edit_text(
        "✏️ Отправьте новый текст для вашей визитки:",
        reply_markup=None
    )
    await state.set_state(EditStates.waiting_for_manual_edit)
    await callback.answer()

@dp.message(StateFilter(EditStates.waiting_for_manual_edit))
async def process_manual_edit(message: types.Message, state: FSMContext):
    """Обработка ручного редактирования"""
    new_card = message.text
    await state.update_data(generated_card=new_card)
    
    await message.answer(
        "✅ Визитка обновлена!\n\n" + new_card,
        reply_markup=get_card_management_keyboard(),
        parse_mode="Markdown"
    )
    
    await state.set_state(None)

@dp.callback_query(F.data == "main_menu")
async def show_main_menu(callback: types.CallbackQuery, state: FSMContext):
    """Показ главного меню"""
    await callback.message.edit_text(
        "Главное меню:",
        reply_markup=None
    )
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    await state.clear()
    await callback.answer()

# Обработчики главного меню
@dp.message(F.text == "📁 Меню")
async def main_menu_handler(message: types.Message):
    """Обработчик полного меню"""
    await message.answer(
        "📁 **Полное меню**\n\nВыберите нужный раздел:",
        reply_markup=get_full_menu_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "🆔 Визитка")
async def show_business_card(message: types.Message):
    """Показ визитки пользователя"""
    user_profile = db.get_profile(message.from_user.id)
    
    if user_profile and user_profile.get('generated_card'):
        await message.answer(
            "📋 Ваша визитка:\n\n" + user_profile['generated_card'],
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "❌ У вас пока нет визитки. Создайте её с помощью команды /start",
            reply_markup=get_yes_no_keyboard()
        )

@dp.message(F.text == "🎯 Цели")
async def show_goals_menu(message: types.Message):
    """Меню работы с целями"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить цели", callback_data="add_goals")],
            [InlineKeyboardButton(text="📅 Цели на сегодня", callback_data="show_daily_goals")],
            [InlineKeyboardButton(text="📆 Цели на месяц", callback_data="show_monthly_goals")],
            [InlineKeyboardButton(text="✏️ Обновить статус", callback_data="update_goals")]
        ]
    )
    
    await message.answer(
        "🎯 Управление целями:",
        reply_markup=keyboard
    )

@dp.message(F.text == "📅 Привычки")
async def show_habits_menu(message: types.Message):
    """Показ списка ежедневных привычек"""
    user_id = message.from_user.id
    
    # Получаем только ежедневные привычки
    habits = db.get_user_habits(user_id, active_only=True)
    daily_habits = [habit for habit in habits if habit.get('habit_type') == 'daily']
    
    if not daily_habits:
        await message.answer(
            "📅 **Ежедневные привычки**\n\n"
            "У вас пока нет ежедневных привычек.\n"
            "Добавьте первую привычку!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="➕ Добавить привычку", callback_data="add_habit")],
                    [InlineKeyboardButton(text="📊 Все привычки", callback_data="habits_menu")]
                ]
            ),
            parse_mode="Markdown"
        )
        return
    
    # Показываем список ежедневных привычек
    await message.answer(
        "📅 **Ежедневные привычки**",
        reply_markup=get_habits_list_keyboard(daily_habits),
        parse_mode="Markdown"
    )

@dp.message(F.text == "📆 Календарь")
async def show_calendar_menu(message: types.Message):
    """Главное меню календаря"""
    user_id = message.from_user.id
    
    # Получаем краткую статистику событий
    from datetime import date, timedelta
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    today_events = db.get_user_events(user_id, start_date=today.isoformat(), end_date=today.isoformat())
    upcoming_events = db.get_user_events(user_id, start_date=tomorrow.isoformat(), end_date=(today + timedelta(days=7)).isoformat())
    
    stats_text = f"📊 События на сегодня: {len(today_events)}\n"
    stats_text += f"📅 Предстоящие (7 дней): {len(upcoming_events)}"
    
    await message.answer(
        f"📆 **Календарь и планировщик**\n\n{stats_text}",
        reply_markup=get_calendar_menu_keyboard(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "goals_menu")
async def show_goals_menu_callback(callback: types.CallbackQuery):
    """Меню работы с целями (callback версия)"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить цели", callback_data="add_goals")],
            [InlineKeyboardButton(text="📅 Цели на сегодня", callback_data="show_daily_goals")],
            [InlineKeyboardButton(text="📆 Цели на месяц", callback_data="show_monthly_goals")],
            [InlineKeyboardButton(text="✏️ Обновить статус", callback_data="update_goals")]
        ]
    )
    
    await callback.message.edit_text(
        "🎯 Управление целями:",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "add_goals")
async def add_goals_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало добавления целей"""
    await callback.message.edit_text(
        "📝 Введите ваши цели списком (каждая цель с новой строки):",
        reply_markup=None
    )
    await state.set_state(GoalStates.waiting_for_goals_input)
    await callback.answer()

@dp.message(StateFilter(GoalStates.waiting_for_goals_input))
async def process_goals_input(message: types.Message, state: FSMContext):
    """Обработка ввода целей"""
    goals_text = message.text.strip()
    goals_list = [goal.strip() for goal in goals_text.split('\n') if goal.strip()]
    
    if not goals_list:
        await message.answer("❌ Пожалуйста, введите хотя бы одну цель.")
        return
    
    await state.update_data(goals_list=goals_list)
    await message.answer(
        f"📋 Получено целей: {len(goals_list)}\n\nВыберите тип целей:",
        reply_markup=get_goal_type_keyboard()
    )
    await state.set_state(GoalStates.waiting_for_goal_type)

@dp.callback_query(F.data.startswith("goal_type_"))
async def process_goal_type(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора типа цели"""
    goal_type = callback.data.split("_")[2]  # daily или monthly
    data = await state.get_data()
    goals_list = data.get('goals_list', [])
    
    # Сохраняем цели в базу данных
    saved_count = 0
    for goal_text in goals_list:
        goal_id = db.add_goal(
            user_id=callback.from_user.id,
            goal_text=goal_text,
            goal_type=goal_type,
            due_date=date.today() if goal_type == 'daily' else None
        )
        if goal_id:
            saved_count += 1
    
    type_text = "ежедневные" if goal_type == "daily" else "ежемесячные"
    await callback.message.edit_text(
        f"✅ Сохранено {saved_count} {type_text} целей!",
        reply_markup=None
    )
    
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "show_daily_goals")
async def show_daily_goals(callback: types.CallbackQuery):
    """Показ ежедневных целей"""
    goals = db.get_user_goals(
        user_id=callback.from_user.id,
        goal_type='daily',
        date_filter=date.today()
    )
    
    if not goals:
        await callback.message.edit_text(
            "📅 У вас пока нет целей на сегодня.\n\nДобавьте их через кнопку '➕ Добавить цели'",
            reply_markup=None
        )
    else:
        goals_text = "📅 **Мои цели на сегодня:**\n\n"
        for goal in goals:
            emoji = "✅" if goal['status'] == 'completed' else "⚡️"
            goals_text += f"{emoji} {goal['goal_text']}\n"
        
        await callback.message.edit_text(
            goals_text,
            parse_mode="Markdown",
            reply_markup=None
        )
    
    await callback.answer()

@dp.callback_query(F.data == "show_monthly_goals")
async def show_monthly_goals(callback: types.CallbackQuery):
    """Показ ежемесячных целей"""
    goals = db.get_user_goals(
        user_id=callback.from_user.id,
        goal_type='monthly'
    )
    
    if not goals:
        await callback.message.edit_text(
            "📆 У вас пока нет целей на месяц.\n\nДобавьте их через кнопку '➕ Добавить цели'",
            reply_markup=None
        )
    else:
        goals_text = "📆 **Мои цели на месяц:**\n\n"
        for goal in goals:
            emoji = "✅" if goal['status'] == 'completed' else "⚡️"
            goals_text += f"{emoji} {goal['goal_text']}\n"
        
        await callback.message.edit_text(
            goals_text,
            parse_mode="Markdown",
            reply_markup=None
        )
    
    await callback.answer()

@dp.callback_query(F.data == "update_goals")
async def update_goals_menu(callback: types.CallbackQuery):
    """Меню обновления целей"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📅 Обновить ежедневные", callback_data="update_daily_goals")],
            [InlineKeyboardButton(text="📆 Обновить ежемесячные", callback_data="update_monthly_goals")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="goals_menu")]
        ]
    )
    
    await callback.message.edit_text(
        "✏️ Выберите тип целей для обновления:",
        reply_markup=keyboard
    )
    await callback.answer()

@dp.callback_query(F.data == "update_daily_goals")
async def update_daily_goals(callback: types.CallbackQuery):
    """Обновление ежедневных целей"""
    goals = db.get_user_goals(
        user_id=callback.from_user.id,
        goal_type='daily',
        date_filter=date.today()
    )
    
    if not goals:
        await callback.message.edit_text(
            "📅 У вас пока нет целей на сегодня.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="goals_menu")]]
            )
        )
    else:
        await callback.message.edit_text(
            "📅 Выберите цель для обновления статуса:",
            reply_markup=get_goals_keyboard(goals, 'daily')
        )
    
    await callback.answer()

@dp.callback_query(F.data == "update_monthly_goals")
async def update_monthly_goals(callback: types.CallbackQuery):
    """Обновление ежемесячных целей"""
    goals = db.get_user_goals(
        user_id=callback.from_user.id,
        goal_type='monthly'
    )
    
    if not goals:
        await callback.message.edit_text(
            "📆 У вас пока нет целей на месяц.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="goals_menu")]]
            )
        )
    else:
        await callback.message.edit_text(
            "📆 Выберите цель для обновления статуса:",
            reply_markup=get_goals_keyboard(goals, 'monthly')
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("update_goal_"))
async def select_goal_for_update(callback: types.CallbackQuery):
    """Выбор цели для обновления"""
    goal_id = int(callback.data.split("_")[2])
    
    await callback.message.edit_text(
        "✏️ Выберите новый статус для цели:",
        reply_markup=get_goal_status_keyboard(goal_id)
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("goal_complete_"))
async def complete_goal(callback: types.CallbackQuery):
    """Отметка цели как выполненной"""
    goal_id = int(callback.data.split("_")[2])
    
    if db.update_goal_status(goal_id, 'completed'):
        await callback.message.edit_text(
            "✅ Цель отмечена как выполненная!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 К целям", callback_data="goals_menu")]]
            )
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при обновлении цели.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 К целям", callback_data="goals_menu")]]
            )
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("goal_progress_"))
async def set_goal_in_progress(callback: types.CallbackQuery):
    """Отметка цели как в процессе"""
    goal_id = int(callback.data.split("_")[2])
    
    if db.update_goal_status(goal_id, 'in_progress'):
        await callback.message.edit_text(
            "⚡️ Цель отмечена как в процессе выполнения!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 К целям", callback_data="goals_menu")]]
            )
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при обновлении цели.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🔙 К целям", callback_data="goals_menu")]]
            )
        )
    
    await callback.answer()

# Команда для получения правильной реферальной ссылки
@dp.message(Command("mylink"))
async def get_correct_referral_link(message: types.Message):
    """Получение правильной реферальной ссылки"""
    user_id = message.from_user.id
    
    # Жестко прописанная правильная ссылка для вашего аккаунта
    if user_id == 6840451873:  # Ваш ID
        correct_link = "https://t.me/Alteria_8_bot?start=REF_6840451873_20250713"
        await message.answer(
            f"✅ **Ваша ПРАВИЛЬНАЯ реферальная ссылка:**\n{correct_link}\n\n"
            f"🎯 Эта ссылка гарантированно работает!\n"
            f"📋 Скопируйте и используйте её для приглашения друзей.",
            parse_mode="Markdown"
        )
    else:
        # Для других пользователей генерируем ссылку обычным способом
        referral_stats = db.get_referral_stats(user_id)
        referral_link = f"https://t.me/Alteria_8_bot?start={referral_stats['referral_code']}"
        await message.answer(
            f"🔗 **Ваша реферальная ссылка:**\n{referral_link}",
            parse_mode="Markdown"
        )

# Команда для получения реферальной ссылки (для тестирования)
@dp.message(Command("referral"))
async def get_referral_link(message: types.Message):
    """Получение реферальной ссылки"""
    user_id = message.from_user.id
    referral_stats = db.get_referral_stats(user_id)
    
    # Создаем кнопку для копирования ссылки
    referral_link = f"https://t.me/{CORRECT_BOT_USERNAME}?start={referral_stats['referral_code']}"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📋 Копировать ссылку", 
                url=f"https://t.me/share/url?url={referral_link}&text=Присоединяйся к AlteriA!"
            )]
        ]
    )
    
    await message.answer(
        f"🔗 **Ваша реферальная ссылка:**\n`{referral_link}`\n\n"
        f"👥 Приглашено: {referral_stats['referral_count']} человек\n"
        f"💰 Заработано: {referral_stats['total_earnings']:.2f} ₽\n\n"
        f"⏰ Создано: {datetime.now().strftime('%H:%M:%S')}",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

# Заглушки для остальных разделов меню
@dp.message(F.text == "🤝 Партнёры")
async def partners_handler_new(message: types.Message):
    """НОВЫЙ обработчик раздела Партнёры"""
    user_id = message.from_user.id
    referral_stats = db.get_referral_stats(user_id)
    
    # Создаем кнопку для копирования ссылки
    referral_link = f"https://t.me/{CORRECT_BOT_USERNAME}?start={referral_stats['referral_code']}"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📋 Копировать ссылку", 
                url=f"https://t.me/share/url?url={referral_link}&text=Присоединяйся к AlteriA!"
            )],
            [InlineKeyboardButton(
                text="👥 Мои рефералы", 
                callback_data="show_my_referrals"
            )]
        ]
    )
    
    text = f"""🤝 **Партнёры**

📊 **Ваша статистика:**
👥 Приглашено: {referral_stats['referral_count']} человек
💰 Заработано: {referral_stats['total_earnings']:.2f} ₽
🔗 **Ваша реферальная ссылка:**
`{referral_link}`

🏪 **Каталог наставников** - в разработке
📈 **Реферальная программа** - активна

⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}"""
    
    await message.answer(text, parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(F.data == "show_my_referrals")
async def show_my_referrals(callback: types.CallbackQuery):
    """Показать список рефералов пользователя"""
    user_id = callback.from_user.id
    
    try:
        referrals = db.get_user_referrals(user_id)
        
        if not referrals:
            await callback.message.edit_text(
                "👥 **Мои рефералы**\n\n"
                "У вас пока нет рефералов.\n"
                "Поделитесь своей реферальной ссылкой, чтобы пригласить друзей!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_partners")]
                    ]
                )
            )
            await callback.answer()
            return
        
        text = f"👥 **Мои рефералы ({len(referrals)})**\n\n"
        
        for i, referral in enumerate(referrals[:10], 1):  # Показываем первые 10
            name = referral['first_name'] or "Пользователь"
            if referral['last_name']:
                name += f" {referral['last_name']}"
            
            username = f"@{referral['username']}" if referral['username'] else "без username"
            
            # Форматируем дату
            from datetime import datetime
            timestamp = datetime.fromisoformat(referral['timestamp'].replace('Z', '+00:00'))
            date_str = timestamp.strftime('%d.%m.%Y')
            
            # Экранируем специальные символы для Markdown
            name_escaped = name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
            username_escaped = username.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
            
            text += f"{i}. **{name_escaped}** ({username_escaped})\n"
            text += f"   📅 Присоединился: {date_str}\n"
            if referral['bio']:
                bio_short = referral['bio'][:50] + "..." if len(referral['bio']) > 50 else referral['bio']
                bio_escaped = bio_short.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]')
                text += f"   📝 {bio_escaped}\n"
            text += f"   💰 Заработано: {referral['earnings']:.2f} ₽\n\n"
        
        if len(referrals) > 10:
            text += f"... и еще {len(referrals) - 10} рефералов"
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_partners")]
            ]
        )
        
        await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        import traceback
        logger.error(f"Error showing referrals: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Отправляем сообщение об ошибке пользователю
        try:
            await callback.message.edit_text(
                f"❌ **Ошибка при загрузке рефералов**\n\n"
                f"Детали ошибки: {str(e)}\n\n"
                f"Попробуйте позже или обратитесь к администратору.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_partners")]
                    ]
                )
            )
        except:
            pass
        
        await callback.answer("❌ Ошибка при загрузке рефералов")

@dp.callback_query(F.data == "back_to_partners")
async def back_to_partners(callback: types.CallbackQuery):
    """Вернуться к разделу партнеры"""
    user_id = callback.from_user.id
    referral_stats = db.get_referral_stats(user_id)
    
    referral_link = f"https://t.me/{CORRECT_BOT_USERNAME}?start={referral_stats['referral_code']}"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="📋 Копировать ссылку", 
                url=f"https://t.me/share/url?url={referral_link}&text=Присоединяйся к AlteriA!"
            )],
            [InlineKeyboardButton(
                text="👥 Мои рефералы", 
                callback_data="show_my_referrals"
            )]
        ]
    )
    
    text = f"""🤝 **Партнёры**

📊 **Ваша статистика:**
👥 Приглашено: {referral_stats['referral_count']} человек
💰 Заработано: {referral_stats['total_earnings']:.2f} ₽
🔗 **Ваша реферальная ссылка:**
`{referral_link}`

🏪 **Каталог наставников** - в разработке
📈 **Реферальная программа** - активна

⏰ Обновлено: {datetime.now().strftime('%H:%M:%S')}"""
    
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=keyboard)
    await callback.answer()

@dp.message(F.text == "🚀 Развитие")
async def development_handler(message: types.Message):
    """Обработчик раздела Развитие"""
    await message.answer(
        "🚀 **Развитие**\n\n"
        "📚 Материалы по нетворкингу\n"
        "💡 Советы по продуктивности\n"
        "🚀 Личностный рост\n\n"
        "_Раздел находится в разработке_",
        parse_mode="Markdown"
    )

@dp.message(F.text == "🌐 Нетворкинг")
async def networking_handler(message: types.Message):
    """Обработчик раздела Нетворкинг"""
    await message.answer(
        "🌐 **Нетворкинг**\n\n"
        "🔍 Поиск единомышленников\n"
        "💬 Общение с участниками\n"
        "🤝 Создание связей\n\n"
        "_Раздел находится в разработке_",
        parse_mode="Markdown"
    )

# Обработчики callback-запросов для модуля привычек
@dp.callback_query(F.data == "habits_menu")
async def habits_menu_callback(callback: types.CallbackQuery):
    """Главное меню привычек (callback версия)"""
    user_id = callback.from_user.id
    
    # Получаем краткую статистику
    habits = db.get_user_habits(user_id, active_only=True)
    total_habits = len(habits)
    
    # Получаем статистику выполнения за сегодня
    today_completed = 0
    for habit in habits:
        today_logs = db.get_habit_stats(user_id, habit['habit_id'], days=1)
        if today_logs.get('completed_count', 0) > 0:
            today_completed += 1
    
    stats_text = f"📊 У вас {total_habits} активных привычек\n"
    if total_habits > 0:
        stats_text += f"✅ Сегодня выполнено: {today_completed}/{total_habits}"
    
    await callback.message.edit_text(
        f"📅 **Полезные привычки**\n\n{stats_text}",
        reply_markup=get_habits_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "add_habit")
async def add_habit_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало добавления новой привычки"""
    await callback.message.edit_text(
        "➕ **Добавление новой привычки**\n\n"
        "Введите название привычки (например: 'Выпить стакан воды', 'Прочитать 10 страниц'):",
        reply_markup=None,
        parse_mode="Markdown"
    )
    await state.set_state(HabitStates.waiting_for_habit_name)
    await callback.answer()

@dp.message(StateFilter(HabitStates.waiting_for_habit_name))
async def process_habit_name(message: types.Message, state: FSMContext):
    """Обработка названия привычки"""
    habit_name = message.text.strip()
    
    if len(habit_name) > 100:
        await message.answer("❌ Название слишком длинное. Максимум 100 символов.")
        return
    
    await state.update_data(habit_name=habit_name)
    
    await message.answer(
        f"✅ Название: {habit_name}\n\n"
        "Добавьте описание привычки (необязательно) или отправьте '-' чтобы пропустить:",
        reply_markup=None
    )
    await state.set_state(HabitStates.waiting_for_habit_description)

@dp.message(StateFilter(HabitStates.waiting_for_habit_description))
async def process_habit_description(message: types.Message, state: FSMContext):
    """Обработка описания привычки"""
    description = message.text.strip() if message.text.strip() != '-' else None
    await state.update_data(habit_description=description)
    
    await message.answer(
        "📅 Выберите тип привычки:",
        reply_markup=get_habit_type_keyboard()
    )
    await state.set_state(HabitStates.waiting_for_habit_type)

@dp.callback_query(StateFilter(HabitStates.waiting_for_habit_type))
async def process_habit_type(callback: types.CallbackQuery, state: FSMContext):
    """Обработка типа привычки"""
    habit_type_map = {
        "habit_type_daily": "daily",
        "habit_type_weekly": "weekly", 
        "habit_type_custom": "custom"
    }
    
    habit_type = habit_type_map.get(callback.data)
    await state.update_data(habit_type=habit_type)
    
    if habit_type == "custom":
        await callback.message.edit_text(
            "🔧 Введите желаемую частоту (например: '3 раза в неделю', '2 раза в день'):",
            reply_markup=None
        )
        await state.set_state(HabitStates.waiting_for_habit_frequency)
    else:
        # Для ежедневных и еженедельных привычек показываем выбор частоты
        await callback.message.edit_text(
            "🔢 Выберите частоту выполнения:",
            reply_markup=get_habit_frequency_keyboard()
        )
        await state.set_state(HabitStates.waiting_for_habit_frequency)
    
    await callback.answer()

@dp.callback_query(StateFilter(HabitStates.waiting_for_habit_frequency))
async def process_habit_frequency_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка частоты привычки (callback)"""
    frequency_map = {
        "freq_1": 1,
        "freq_2": 2,
        "freq_3": 3
    }
    
    if callback.data == "freq_custom":
        # Получаем тип привычки из состояния
        data = await state.get_data()
        habit_type = data.get('habit_type', 'daily')
        
        if habit_type == 'daily':
            frequency_text = "🔧 Введите желаемую частоту числом (сколько раз в день):"
        elif habit_type == 'weekly':
            frequency_text = "🔧 Введите желаемую частоту числом (сколько раз в неделю):"
        else:
            frequency_text = "🔧 Введите желаемую частоту числом (сколько раз в день/неделю):"
        
        await callback.message.edit_text(
            frequency_text,
            reply_markup=None
        )
        await callback.answer()
        return
    
    frequency = frequency_map.get(callback.data, 1)
    await state.update_data(target_frequency=frequency)
    
    # Завершаем создание привычки
    await finish_habit_creation(callback.message, state, callback.from_user.id)
    await callback.answer()

@dp.message(StateFilter(HabitStates.waiting_for_habit_frequency))
async def process_habit_frequency_text(message: types.Message, state: FSMContext):
    """Обработка частоты привычки (текст)"""
    try:
        frequency = int(message.text.strip())
        if frequency <= 0 or frequency > 10:
            await message.answer("❌ Частота должна быть от 1 до 10.")
            return
    except ValueError:
        await message.answer("❌ Введите число от 1 до 10.")
        return
    
    await state.update_data(target_frequency=frequency)
    
    # Завершаем создание привычки
    await finish_habit_creation(message, state, message.from_user.id)

async def finish_habit_creation(message, state: FSMContext, user_id: int):
    """Завершение создания привычки"""
    data = await state.get_data()
    
    # Создаем привычку в базе данных
    success = db.create_habit(
        user_id=user_id,
        habit_name=data['habit_name'],
        habit_description=data.get('habit_description'),
        habit_type=data.get('habit_type', 'daily'),
        target_frequency=data.get('target_frequency', 1)
    )
    
    if success:
        await message.answer(
            f"✅ **Привычка создана!**\n\n"
            f"📝 Название: {data['habit_name']}\n"
            f"📅 Тип: {data.get('habit_type', 'daily')}\n"
            f"🔢 Частота: {data.get('target_frequency', 1)} раз\n\n"
            f"Теперь вы можете отмечать выполнение в разделе 'Мои привычки'.",
            reply_markup=get_habits_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "❌ Ошибка при создании привычки. Попробуйте еще раз.",
            reply_markup=get_habits_menu_keyboard()
        )
    
    await state.clear()

@dp.callback_query(F.data == "my_habits")
async def show_my_habits(callback: types.CallbackQuery):
    """Показ списка привычек пользователя"""
    user_id = callback.from_user.id
    habits = db.get_user_habits(user_id, active_only=False)
    
    if not habits:
        await callback.message.edit_text(
            "📅 **Мои привычки**\n\n"
            "У вас пока нет привычек.\n"
            "Создайте первую привычку, чтобы начать отслеживание!",
            reply_markup=get_habits_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            f"📅 **Мои привычки** ({len(habits)})\n\n"
            "Выберите привычку для просмотра деталей:",
            reply_markup=get_habits_list_keyboard(habits),
            parse_mode="Markdown"
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("habit_detail_"))
async def show_habit_detail(callback: types.CallbackQuery):
    """Показ детальной информации о привычке"""
    habit_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # Получаем информацию о привычке
    habits = db.get_user_habits(user_id, active_only=False)
    habit = next((h for h in habits if h['habit_id'] == habit_id), None)
    
    if not habit:
        await callback.answer("❌ Привычка не найдена")
        return
    
    # Получаем статистику
    stats = db.get_habit_stats(user_id, habit_id, days=30)
    
    status_emoji = "✅" if habit['is_active'] else "⏸️"
    status_text = "Активна" if habit['is_active'] else "Приостановлена"
    
    detail_text = f"""📅 **{habit['habit_name']}**

{status_emoji} Статус: {status_text}
📝 Описание: {habit['habit_description'] or 'Не указано'}
🔢 Частота: {habit['target_frequency']} раз в {habit['habit_type']}

📊 **Статистика за 30 дней:**
✅ Выполнено: {stats.get('completed_count', 0)} раз
📈 Процент выполнения: {stats.get('completion_rate', 0):.1f}%
📅 Последнее выполнение: {stats.get('last_completion', 'Никогда')}"""
    
    await callback.message.edit_text(
        detail_text,
        reply_markup=get_habit_detail_keyboard(habit_id, habit['is_active']),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("habit_complete_"))
async def complete_habit(callback: types.CallbackQuery):
    """Отметка выполнения привычки"""
    habit_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    success = db.log_habit_completion(habit_id, user_id, completed=True)
    
    if success:
        # Останавливаем напоминания для этой привычки
        await stop_habit_reminders(user_id, habit_id)
        
        await callback.answer("✅ Привычка отмечена как выполненная!")
        # Обновляем информацию о привычке
        await show_habit_detail(callback)
    else:
        await callback.answer("❌ Ошибка при сохранении")

@dp.callback_query(F.data.startswith("habit_skip_"))
async def skip_habit(callback: types.CallbackQuery):
    """Отметка пропуска привычки"""
    habit_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    success = db.log_habit_completion(habit_id, user_id, completed=False)
    
    if success:
        await callback.answer("❌ Привычка отмечена как пропущенная")
        # Обновляем информацию о привычке
        await show_habit_detail(callback)
    else:
        await callback.answer("❌ Ошибка при сохранении")

@dp.callback_query(F.data.startswith("habit_pause_"))
async def pause_habit(callback: types.CallbackQuery):
    """Приостановка привычки"""
    habit_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    success = db.toggle_habit_status(habit_id, user_id)
    
    if success:
        await callback.answer("⏸️ Привычка приостановлена")
        await show_habit_detail(callback)
    else:
        await callback.answer("❌ Ошибка при изменении статуса")

@dp.callback_query(F.data.startswith("habit_resume_"))
async def resume_habit(callback: types.CallbackQuery):
    """Возобновление привычки"""
    habit_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    success = db.toggle_habit_status(habit_id, user_id)
    
    if success:
        await callback.answer("▶️ Привычка возобновлена")
        await show_habit_detail(callback)
    else:
        await callback.answer("❌ Ошибка при изменении статуса")

@dp.callback_query(F.data == "habits_stats")
async def show_habits_stats(callback: types.CallbackQuery):
    """Показ общей статистики по привычкам"""
    try:
        user_id = callback.from_user.id
        habits = db.get_user_habits(user_id, active_only=True)
        
        if not habits:
            await callback.message.edit_text(
                "📊 **Статистика привычек**\n\n"
                "У вас пока нет активных привычек для отображения статистики.",
                reply_markup=get_habits_menu_keyboard(),
                parse_mode="Markdown"
            )
            await callback.answer()
            return
        
        stats_text = "📊 **Статистика привычек**\n\n"
        
        total_completion_rate = 0
        for habit in habits:
            try:
                stats = db.get_habit_stats(user_id, habit['habit_id'], days=7)
                completion_rate = stats.get('completion_rate', 0)
                total_completion_rate += completion_rate
                
                stats_text += f"📅 {habit['habit_name']}\n"
                stats_text += f"   ✅ За неделю: {completion_rate:.1f}%\n\n"
            except Exception as e:
                logger.error(f"Error getting stats for habit {habit['habit_id']}: {e}")
                stats_text += f"📅 {habit['habit_name']}\n"
                stats_text += f"   ❌ Ошибка получения данных\n\n"
        
        avg_completion = total_completion_rate / len(habits) if habits else 0
        stats_text += f"📈 **Средний процент выполнения: {avg_completion:.1f}%**"
        
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_habits_menu_keyboard(),
            parse_mode="Markdown"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in show_habits_stats: {e}")
        await callback.answer("❌ Ошибка при получении статистики")
        try:
            await callback.message.edit_text(
                "❌ **Ошибка**\n\nНе удалось получить статистику привычек.",
                reply_markup=get_habits_menu_keyboard(),
                parse_mode="Markdown"
            )
        except:
            pass

# Обработчики callback-запросов для модуля календаря
@dp.callback_query(F.data == "calendar_menu")
async def calendar_menu_callback(callback: types.CallbackQuery):
    """Главное меню календаря (callback версия)"""
    user_id = callback.from_user.id
    
    # Получаем краткую статистику событий
    from datetime import date, timedelta
    today = date.today()
    tomorrow = today + timedelta(days=1)
    
    today_events = db.get_user_events(user_id, start_date=today.isoformat(), end_date=today.isoformat())
    upcoming_events = db.get_user_events(user_id, start_date=tomorrow.isoformat(), end_date=(today + timedelta(days=7)).isoformat())
    
    stats_text = f"📊 События на сегодня: {len(today_events)}\n"
    stats_text += f"📅 Предстоящие (7 дней): {len(upcoming_events)}"
    
    await callback.message.edit_text(
        f"📆 **Календарь и планировщик**\n\n{stats_text}",
        reply_markup=get_calendar_menu_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "add_event")
async def add_event_start(callback: types.CallbackQuery, state: FSMContext):
    """Начало добавления нового события"""
    await callback.message.edit_text(
        "➕ **Добавление нового события**\n\n"
        "Введите название события:",
        reply_markup=None,
        parse_mode="Markdown"
    )
    await state.set_state(CalendarStates.waiting_for_event_title)
    await callback.answer()

@dp.message(StateFilter(CalendarStates.waiting_for_event_title))
async def process_event_title(message: types.Message, state: FSMContext):
    """Обработка названия события"""
    event_title = message.text.strip()
    
    if len(event_title) > 100:
        await message.answer("❌ Название слишком длинное. Максимум 100 символов.")
        return
    
    await state.update_data(event_title=event_title)
    
    await message.answer(
        f"✅ Название: {event_title}\n\n"
        "Добавьте описание события (необязательно) или отправьте '-' чтобы пропустить:",
        reply_markup=None
    )
    await state.set_state(CalendarStates.waiting_for_event_description)

@dp.message(StateFilter(CalendarStates.waiting_for_event_description))
async def process_event_description(message: types.Message, state: FSMContext):
    """Обработка описания события"""
    description = message.text.strip() if message.text.strip() != '-' else None
    await state.update_data(event_description=description)
    
    await message.answer(
        "📅 Введите дату события в формате ДД.ММ.ГГГГ (например: 15.07.2025):",
        reply_markup=None
    )
    await state.set_state(CalendarStates.waiting_for_event_date)

@dp.message(StateFilter(CalendarStates.waiting_for_event_date))
async def process_event_date(message: types.Message, state: FSMContext):
    """Обработка даты события"""
    date_text = message.text.strip()
    
    try:
        from datetime import datetime
        event_date = datetime.strptime(date_text, "%d.%m.%Y").date()
        await state.update_data(event_date=event_date.isoformat())
        
        await message.answer(
            f"✅ Дата: {event_date.strftime('%d.%m.%Y')}\n\n"
            "Введите время события в формате ЧЧ:ММ (например: 14:30) или отправьте '-' если время не важно:",
            reply_markup=None
        )
        await state.set_state(CalendarStates.waiting_for_event_time)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ (например: 15.07.2025)")

@dp.message(StateFilter(CalendarStates.waiting_for_event_time))
async def process_event_time(message: types.Message, state: FSMContext):
    """Обработка времени события"""
    time_text = message.text.strip()
    
    if time_text == '-':
        await state.update_data(event_time=None)
    else:
        try:
            from datetime import datetime
            event_time = datetime.strptime(time_text, "%H:%M").time()
            await state.update_data(event_time=event_time.isoformat())
        except ValueError:
            await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ (например: 14:30)")
            return
    
    await message.answer(
        "📝 Выберите тип события:",
        reply_markup=get_event_type_keyboard()
    )
    await state.set_state(CalendarStates.waiting_for_event_type)

@dp.callback_query(StateFilter(CalendarStates.waiting_for_event_type))
async def process_event_type(callback: types.CallbackQuery, state: FSMContext):
    """Обработка типа события"""
    event_type_map = {
        "event_type_task": "task",
        "event_type_habit": "habit",
        "event_type_workout": "workout",
        "event_type_meal": "meal",
        "event_type_meeting": "meeting",
        "event_type_reminder": "reminder",
        "event_type_custom": "custom"
    }
    
    event_type = event_type_map.get(callback.data, "custom")
    await state.update_data(event_type=event_type)
    
    await callback.message.edit_text(
        "⏰ Настроить напоминание?",
        reply_markup=get_reminder_time_keyboard()
    )
    await state.set_state(CalendarStates.waiting_for_reminder_time)
    await callback.answer()

@dp.callback_query(StateFilter(CalendarStates.waiting_for_reminder_time))
async def process_reminder_time(callback: types.CallbackQuery, state: FSMContext):
    """Обработка времени напоминания"""
    reminder_map = {
        "reminder_5": 5,
        "reminder_15": 15,
        "reminder_30": 30,
        "reminder_60": 60,
        "reminder_1440": 1440,
        "reminder_none": None
    }
    
    reminder_minutes = reminder_map.get(callback.data)
    await state.update_data(reminder_minutes=reminder_minutes)
    
    # Завершаем создание события
    await finish_event_creation(callback.message, state, callback.from_user.id)
    await callback.answer()

async def finish_event_creation(message, state: FSMContext, user_id: int):
    """Завершение создания события"""
    data = await state.get_data()
    
    # Формируем datetime для события
    event_datetime = None
    if data.get('event_date'):
        if data.get('event_time'):
            event_datetime = f"{data['event_date']} {data['event_time']}"
        else:
            event_datetime = f"{data['event_date']} 00:00"
    
    # Создаем событие в базе данных
    success = db.create_event(
        user_id=user_id,
        event_title=data['event_title'],
        event_description=data.get('event_description'),
        event_type=data.get('event_type', 'custom'),
        start_datetime=event_datetime,
        reminder_minutes=data.get('reminder_minutes')
    )
    
    if success:
        # Форматируем информацию о событии
        type_names = {
            'task': 'Задача',
            'habit': 'Привычка',
            'workout': 'Тренировка',
            'meal': 'Прием пищи',
            'meeting': 'Встреча',
            'reminder': 'Напоминание',
            'custom': 'Другое'
        }
        
        reminder_text = ""
        if data.get('reminder_minutes'):
            if data['reminder_minutes'] >= 1440:
                reminder_text = f"\n⏰ Напоминание: за {data['reminder_minutes'] // 1440} дн."
            elif data['reminder_minutes'] >= 60:
                reminder_text = f"\n⏰ Напоминание: за {data['reminder_minutes'] // 60} ч."
            else:
                reminder_text = f"\n⏰ Напоминание: за {data['reminder_minutes']} мин."
        
        await message.answer(
            f"✅ **Событие создано!**\n\n"
            f"📝 Название: {data['event_title']}\n"
            f"📅 Дата: {data.get('event_date', 'Не указана')}\n"
            f"⏰ Время: {data.get('event_time', 'Не указано')}\n"
            f"📋 Тип: {type_names.get(data.get('event_type'), 'Другое')}"
            f"{reminder_text}",
            reply_markup=get_calendar_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            "❌ Ошибка при создании события. Попробуйте еще раз.",
            reply_markup=get_calendar_menu_keyboard()
        )
    
    await state.clear()

@dp.callback_query(F.data == "events_today")
async def show_events_today(callback: types.CallbackQuery):
    """Показ событий на сегодня"""
    user_id = callback.from_user.id
    from datetime import date
    today = date.today()
    
    events = db.get_user_events(user_id, start_date=today.isoformat(), end_date=today.isoformat())
    
    if not events:
        await callback.message.edit_text(
            f"📅 **События на сегодня ({today.strftime('%d.%m.%Y')})**\n\n"
            "На сегодня событий не запланировано.",
            reply_markup=get_calendar_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            f"📅 **События на сегодня ({today.strftime('%d.%m.%Y')})** ({len(events)})\n\n"
            "Выберите событие для просмотра деталей:",
            reply_markup=get_events_list_keyboard(events),
            parse_mode="Markdown"
        )
    
    await callback.answer()

@dp.callback_query(F.data == "events_week")
async def show_events_week(callback: types.CallbackQuery):
    """Показ событий на неделю"""
    user_id = callback.from_user.id
    from datetime import date, timedelta
    today = date.today()
    week_end = today + timedelta(days=7)
    
    events = db.get_user_events(user_id, start_date=today.isoformat(), end_date=week_end.isoformat())
    
    if not events:
        await callback.message.edit_text(
            f"📆 **События на неделю**\n\n"
            "На ближайшую неделю событий не запланировано.",
            reply_markup=get_calendar_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            f"📆 **События на неделю** ({len(events)})\n\n"
            "Выберите событие для просмотра деталей:",
            reply_markup=get_events_list_keyboard(events),
            parse_mode="Markdown"
        )
    
    await callback.answer()

@dp.callback_query(F.data == "all_events")
async def show_all_events(callback: types.CallbackQuery):
    """Показ всех событий"""
    user_id = callback.from_user.id
    events = db.get_user_events(user_id)
    
    if not events:
        await callback.message.edit_text(
            "📋 **Все события**\n\n"
            "У вас пока нет запланированных событий.",
            reply_markup=get_calendar_menu_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            f"📋 **Все события** ({len(events)})\n\n"
            "Выберите событие для просмотра деталей:",
            reply_markup=get_events_list_keyboard(events),
            parse_mode="Markdown"
        )
    
    await callback.answer()

@dp.callback_query(F.data.startswith("event_detail_"))
async def show_event_detail(callback: types.CallbackQuery):
    """Показ детальной информации о событии"""
    event_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # Получаем информацию о событии
    events = db.get_user_events(user_id)
    event = next((e for e in events if e['event_id'] == event_id), None)
    
    if not event:
        await callback.answer("❌ Событие не найдено")
        return
    
    # Форматируем информацию
    type_names = {
        'task': '📋 Задача',
        'habit': '📅 Привычка',
        'workout': '💪 Тренировка',
        'meal': '🍽️ Прием пищи',
        'meeting': '🤝 Встреча',
        'reminder': '⏰ Напоминание',
        'custom': '📝 Другое'
    }
    
    status_emoji = "✅" if event['status'] == 'completed' else "⏳"
    status_text = "Выполнено" if event['status'] == 'completed' else "Запланировано"
    
    detail_text = f"""📅 **{event['event_title']}**

{status_emoji} Статус: {status_text}
{type_names.get(event['event_type'], '📝 Другое')}
📝 Описание: {event['event_description'] or 'Не указано'}
📅 Дата: {event['start_datetime'][:10] if event['start_datetime'] else 'Не указана'}
⏰ Время: {event['start_datetime'][11:16] if event['start_datetime'] and len(event['start_datetime']) > 10 else 'Не указано'}"""
    
    if event['reminder_minutes']:
        if event['reminder_minutes'] >= 1440:
            detail_text += f"\n🔔 Напоминание: за {event['reminder_minutes'] // 1440} дн."
        elif event['reminder_minutes'] >= 60:
            detail_text += f"\n🔔 Напоминание: за {event['reminder_minutes'] // 60} ч."
        else:
            detail_text += f"\n🔔 Напоминание: за {event['reminder_minutes']} мин."
    
    await callback.message.edit_text(
        detail_text,
        reply_markup=get_event_detail_keyboard(event_id),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("event_complete_"))
async def complete_event(callback: types.CallbackQuery):
    """Отметка события как выполненного"""
    event_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    success = db.complete_event(event_id, user_id)
    
    if success:
        await callback.answer("✅ Событие отмечено как выполненное!")
        # Обновляем информацию о событии
        await show_event_detail(callback)
    else:
        await callback.answer("❌ Ошибка при сохранении")

@dp.callback_query(F.data.startswith("event_cancel_"))
async def cancel_event(callback: types.CallbackQuery):
    """Отмена события"""
    event_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    success = db.delete_event(event_id, user_id)
    
    if success:
        await callback.answer("❌ Событие отменено")
        # Возвращаемся к списку событий
        await show_all_events(callback)
    else:
        await callback.answer("❌ Ошибка при удалении")

# Запуск бота
async def main():
    """Главная функция запуска бота"""
    global scheduler
    
    logger.info("Starting AlteriA bot...")
    
    # Инициализируем базу данных
    db.init_database()
    
    # Инициализируем планировщик
    scheduler = ReportScheduler(bot)
    scheduler.start()
    

# Импорт системы напоминаний
from reminder_system import (
    start_habit_reminders, stop_habit_reminders, start_daily_reminder_check,
    ReminderStates, active_reminders
)

# Обработчик для остановки напоминаний
@dp.callback_query(F.data.startswith("stop_reminders_"))
async def stop_reminders_handler(callback: types.CallbackQuery):
    """Остановка напоминаний по запросу пользователя"""
    habit_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    await stop_habit_reminders(user_id, habit_id)
    
    await callback.message.edit_text(
        "⏸️ Напоминания для этой привычки остановлены.",
        reply_markup=None
    )
    await callback.answer("Напоминания остановлены")

# Обработчик настроек напоминаний
@dp.callback_query(F.data == "reminder_settings")
async def show_reminder_settings(callback: types.CallbackQuery):
    """Показ настроек напоминаний"""
    user_id = callback.from_user.id
    settings = db.get_reminder_settings(user_id)
    
    interval_text = {
        300: "5 минут",
        1200: "20 минут",
        3600: "1 час"
    }.get(settings['interval'], f"{settings['interval']//60} минут")
    
    status_text = "✅ Включены" if settings['is_enabled'] else "❌ Отключены"
    
    text = f"⚙️ **Настройки напоминаний**\n\n" \
           f"📊 Статус: {status_text}\n" \
           f"⏱️ Интервал: каждые {interval_text}\n" \
           f"🕐 Время работы: {settings['start_time']} - {settings['end_time']}\n\n" \
           f"Выберите, что хотите изменить:"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="⏱️ Изменить интервал", 
                callback_data="change_interval"
            )],
            [InlineKeyboardButton(
                text="🕐 Изменить время работы", 
                callback_data="change_time_range"
            )],
            [InlineKeyboardButton(
                text="✅ Включить" if not settings['is_enabled'] else "❌ Отключить", 
                callback_data="toggle_reminders"
            )],
            [InlineKeyboardButton(
                text="🔙 Назад", 
                callback_data="close_settings"
            )]
        ]
    )
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "change_interval")
async def change_reminder_interval(callback: types.CallbackQuery):
    """Изменение интервала напоминаний"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Каждые 5 минут", callback_data="set_interval_300")],
            [InlineKeyboardButton(text="🕐 Каждые 20 минут", callback_data="set_interval_1200")],
            [InlineKeyboardButton(text="⏰ Каждый час", callback_data="set_interval_3600")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="reminder_settings")]
        ]
    )
    
    await callback.message.edit_text(
        "⏱️ **Выберите интервал напоминаний:**",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("set_interval_"))
async def set_reminder_interval(callback: types.CallbackQuery):
    """Установка интервала напоминаний"""
    interval = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    success = db.update_reminder_settings(user_id, interval=interval)
    
    if success:
        interval_text = {
            300: "5 минут",
            1200: "20 минут",
            3600: "1 час"
        }.get(interval, f"{interval//60} минут")
        
        await callback.answer(f"✅ Интервал изменен на: каждые {interval_text}")
        await show_reminder_settings(callback)
    else:
        await callback.answer("❌ Ошибка при сохранении настроек")

@dp.callback_query(F.data == "change_time_range")
async def change_time_range(callback: types.CallbackQuery, state: FSMContext):
    """Изменение времени работы напоминаний"""
    await callback.message.edit_text(
        "🕐 **Настройка времени работы напоминаний**\n\n"
        "Введите время начала в формате ЧЧ:ММ (например: 07:00):",
        reply_markup=None,
        parse_mode="Markdown"
    )
    await state.set_state(ReminderStates.waiting_for_start_time)
    await callback.answer()

@dp.message(StateFilter(ReminderStates.waiting_for_start_time))
async def process_start_time(message: types.Message, state: FSMContext):
    """Обработка времени начала"""
    try:
        # Проверяем формат времени
        datetime.strptime(message.text.strip(), "%H:%M")
        await state.update_data(start_time=message.text.strip())
        
        await message.answer(
            "✅ Время начала сохранено.\n\n"
            "Теперь введите время окончания в формате ЧЧ:ММ (например: 22:00):"
        )
        await state.set_state(ReminderStates.waiting_for_end_time)
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ (например: 07:00)")

@dp.message(StateFilter(ReminderStates.waiting_for_end_time))
async def process_end_time(message: types.Message, state: FSMContext):
    """Обработка времени окончания"""
    try:
        # Проверяем формат времени
        datetime.strptime(message.text.strip(), "%H:%M")
        
        data = await state.get_data()
        start_time = data['start_time']
        end_time = message.text.strip()
        
        user_id = message.from_user.id
        success = db.update_reminder_settings(user_id, start_time=start_time, end_time=end_time)
        
        if success:
            await message.answer(
                f"✅ **Время работы напоминаний обновлено!**\n\n"
                f"🕐 С {start_time} до {end_time}\n\n"
                f"Напоминания будут приходить только в указанное время.",
                parse_mode="Markdown"
            )
        else:
            await message.answer("❌ Ошибка при сохранении настроек")
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ (например: 22:00)")

@dp.callback_query(F.data == "toggle_reminders")
async def toggle_reminders(callback: types.CallbackQuery):
    """Включение/отключение напоминаний"""
    user_id = callback.from_user.id
    settings = db.get_reminder_settings(user_id)
    
    new_status = not settings['is_enabled']
    success = db.update_reminder_settings(user_id, is_enabled=new_status)
    
    if success:
        if new_status:
            await callback.answer("✅ Напоминания включены")
        else:
            # Останавливаем все активные напоминания пользователя
            keys_to_remove = []
            for key in active_reminders.keys():
                if key.startswith(f"{user_id}_"):
                    active_reminders[key].cancel()
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del active_reminders[key]
            
            await callback.answer("❌ Напоминания отключены")
        
        await show_reminder_settings(callback)
    else:
        await callback.answer("❌ Ошибка при сохранении настроек")

@dp.callback_query(F.data == "close_settings")
async def close_settings(callback: types.CallbackQuery):
    """Закрытие настроек"""
    await callback.message.delete()
    await callback.answer()

# Команда для тестирования напоминаний
@dp.message(Command("test_reminders"))
async def test_reminders_command(message: types.Message):
    """Команда для тестирования системы напоминаний"""
    user_id = message.from_user.id
    
    # Получаем первую активную привычку пользователя
    habits = db.get_user_habits(user_id, active_only=True)
    
    if not habits:
        await message.answer("❌ У вас нет активных привычек для тестирования напоминаний.")
        return
    
    # Берем первую привычку для теста
    test_habit = habits[0]
    habit_id = test_habit['habit_id']
    habit_name = test_habit['habit_name']
    
    # Запускаем напоминания
    await start_habit_reminders(bot, db, user_id, habit_id)
    
    await message.answer(
        f"🔔 **Тестирование напоминаний запущено!**\n\n"
        f"📅 Привычка: {habit_name}\n"
        f"⏰ Напоминания согласно вашим настройкам\n"
        f"✅ Остановятся после выполнения привычки\n\n"
        f"Используйте /stop_test_reminders для остановки.",
        parse_mode="Markdown"
    )

@dp.message(Command("stop_test_reminders"))
async def stop_test_reminders_command(message: types.Message):
    """Команда для остановки тестовых напоминаний"""
    user_id = message.from_user.id
    
    # Останавливаем все напоминания пользователя
    keys_to_remove = []
    for key in active_reminders.keys():
        if key.startswith(f"{user_id}_"):
            active_reminders[key].cancel()
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del active_reminders[key]
    
    await message.answer("⏸️ Все тестовые напоминания остановлены.")

@dp.message(Command("test_daily_report"))
async def test_daily_report_command(message: types.Message):
    """Команда для тестирования ежедневного отчета по привычкам"""
    user_id = message.from_user.id
    
    try:
        from datetime import date, timedelta
        
        # Получаем привычки пользователя
        habits = db.get_user_habits(user_id, active_only=True)
        
        if not habits:
            await message.answer("❌ У вас нет активных привычек для отчета.")
            return
        
        user = db.get_user(user_id)
        first_name = user['first_name'] if user else "Друг"
        
        yesterday = date.today() - timedelta(days=1)
        
        report = f"📊 **Тестовый отчет по привычкам за {yesterday.strftime('%d.%m.%Y')}, {first_name}!**\n\n"
        
        total_expected = 0
        total_completed = 0
        
        for habit in habits:
            habit_id = habit['habit_id']
            habit_name = habit['habit_name']
            target_freq = habit['target_frequency']
            
            # Получаем статистику за вчера
            stats = db.get_habit_stats(user_id, habit_id, days=1, end_date=yesterday)
            completed = stats.get('completed_count', 0)
            
            total_expected += target_freq
            total_completed += completed
            
            # Рассчитываем процент выполнения
            completion_rate = (completed / target_freq * 100) if target_freq > 0 else 0
            
            # Эмодзи в зависимости от выполнения
            if completion_rate >= 100:
                emoji = "✅"
            elif completion_rate >= 50:
                emoji = "🟡"
            else:
                emoji = "🔴"
            
            report += f"{emoji} **{habit_name}**: {completed}/{target_freq} ({completion_rate:.0f}%)\n"
        
        # Общая статистика
        overall_rate = (total_completed / total_expected * 100) if total_expected > 0 else 0
        
        report += f"\n📈 **Общий результат**: {total_completed}/{total_expected} ({overall_rate:.0f}%)\n\n"
        
        # Мотивационное сообщение
        if overall_rate >= 100:
            report += "🎉 **Отличная работа! Все привычки выполнены!**"
        elif overall_rate >= 80:
            report += "👏 **Хороший результат! Продолжайте в том же духе!**"
        elif overall_rate >= 50:
            report += "💪 **Неплохо! Есть к чему стремиться!**"
        else:
            report += "🔥 **Новый день - новые возможности! Вы можете лучше!**"
        
        await message.answer(report, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in test_daily_report: {e}")
        await message.answer("❌ Ошибка при генерации отчета.")

# Команда для настройки напоминаний
@dp.message(Command("reminder_settings"))
async def reminder_settings_command(message: types.Message):
    """Команда для настройки напоминаний"""
    user_id = message.from_user.id
    settings = db.get_reminder_settings(user_id)
    
    interval_text = {
        300: "5 минут",
        1200: "20 минут",
        3600: "1 час"
    }.get(settings['interval'], f"{settings['interval']//60} минут")
    
    status_text = "✅ Включены" if settings['is_enabled'] else "❌ Отключены"
    
    text = f"⚙️ **Настройки напоминаний**\n\n" \
           f"📊 Статус: {status_text}\n" \
           f"⏱️ Интервал: каждые {interval_text}\n" \
           f"🕐 Время работы: {settings['start_time']} - {settings['end_time']}\n\n" \
           f"Выберите, что хотите изменить:"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text="⏱️ Изменить интервал", 
                callback_data="change_interval"
            )],
            [InlineKeyboardButton(
                text="🕐 Изменить время работы", 
                callback_data="change_time_range"
            )],
            [InlineKeyboardButton(
                text="✅ Включить" if not settings['is_enabled'] else "❌ Отключить", 
                callback_data="toggle_reminders"
            )]
        ]
    )
    
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

async def main():
    """Главная функция запуска бота"""
    try:
        # Создаем таблицу настроек напоминаний
        db.create_reminder_settings_table()
        
        # Запускаем ежедневную проверку напоминаний
        asyncio.create_task(start_daily_reminder_check(bot, db))
        
        logger.info("Starting bot...")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())


# Обработчики кнопок из полного меню
@dp.callback_query(F.data == "profile")
async def profile_callback(callback: types.CallbackQuery):
    """Обработчик кнопки Визитка из меню"""
    user_profile = db.get_profile(callback.from_user.id)
    
    if user_profile and user_profile.get('generated_card'):
        await callback.message.edit_text(
            "📋 **Ваша визитка:**\n\n" + user_profile['generated_card'],
            parse_mode="Markdown"
        )
    else:
        await callback.message.edit_text(
            "❌ У вас пока нет визитки. Создайте её с помощью команды /start"
        )
    await callback.answer()

@dp.callback_query(F.data == "networking")
async def networking_callback(callback: types.CallbackQuery):
    """Обработчик кнопки Нетворкинг из меню"""
    await callback.message.edit_text(
        "🌐 **Нетворкинг**\n\n"
        "🤝 Поиск контактов\n"
        "📱 Обмен контактами\n"
        "🎯 Деловые встречи\n\n"
        "Раздел в разработке..."
    )
    await callback.answer()

@dp.callback_query(F.data == "organizer")
async def organizer_callback(callback: types.CallbackQuery):
    """Обработчик кнопки Органайзер из меню"""
    await callback.message.edit_text(
        "📋 **Органайзер**\n\n"
        "📝 Заметки\n"
        "📋 Списки дел\n"
        "📊 Планирование\n\n"
        "Раздел в разработке..."
    )
    await callback.answer()

@dp.callback_query(F.data == "calendar")
async def calendar_callback(callback: types.CallbackQuery):
    """Обработчик кнопки Календарь из меню"""
    await callback.message.edit_text(
        "📆 **Календарь**\n\n"
        "📅 События\n"
        "⏰ Напоминания\n"
        "🗓️ Планирование\n\n"
        "Раздел в разработке..."
    )
    await callback.answer()

@dp.callback_query(F.data == "settings")
async def settings_callback(callback: types.CallbackQuery):
    """Обработчик кнопки Настройки из меню"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Настройки напоминаний", callback_data="reminder_settings")],
            [InlineKeyboardButton(text="🔔 Уведомления", callback_data="notification_settings")],
            [InlineKeyboardButton(text="🌍 Язык", callback_data="language_settings")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="close_settings")]
        ]
    )
    
    await callback.message.edit_text(
        "⚙️ **Настройки**\n\nВыберите раздел для настройки:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data == "notification_settings")
async def notification_settings_callback(callback: types.CallbackQuery):
    """Настройки уведомлений"""
    await callback.message.edit_text(
        "🔔 **Настройки уведомлений**\n\n"
        "Раздел в разработке...",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="settings")]
            ]
        )
    )
    await callback.answer()

@dp.callback_query(F.data == "language_settings")
async def language_settings_callback(callback: types.CallbackQuery):
    """Настройки языка"""
    await callback.message.edit_text(
        "🌍 **Настройки языка**\n\n"
        "🇷🇺 Русский (текущий)\n"
        "🇺🇸 English\n\n"
        "Раздел в разработке...",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="settings")]
            ]
        )
    )
    await callback.answer()

