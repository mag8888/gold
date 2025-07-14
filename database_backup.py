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
            [KeyboardButton(text="🤝 Партнёры"), KeyboardButton(text="🎯 Мои цели")],
            [KeyboardButton(text="🆔 Визитка"), KeyboardButton(text="🎓 Обучение")],
            [KeyboardButton(text="🌐 Нетворкинг"), KeyboardButton(text="📅 Привычки")],
            [KeyboardButton(text="📋 Органайзер"), KeyboardButton(text="📆 Календарь")],
            [KeyboardButton(text="📁 Меню")]
        ],
        resize_keyboard=True,
        persistent=True
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
        "Отлично! Давайте создадим вашу визитку.\n\n1/10. Как тебя зовут?"
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
    
    # Показываем прогресс
    progress_msg = await message.answer("⏳ Генерирую вашу визитку...")
    
    # Генерируем визитку через OpenAI
    business_card = openai_service.generate_business_card(data)
    
    if business_card:
        await progress_msg.delete()
        await message.answer(
            "🎉 Ваша визитка готова!\n\n" + business_card,
            reply_markup=get_card_management_keyboard(),
            parse_mode="Markdown"
        )
        
        # Сохраняем данные в состоянии для дальнейшего использования
        await state.update_data(generated_card=business_card)
    else:
        await progress_msg.delete()
        await message.answer(
            "❌ Произошла ошибка при генерации визитки. Попробуйте позже.",
            reply_markup=get_main_menu_keyboard()
        )
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
    """Обработчик главного меню"""
    await message.answer(
        "Главное меню:",
        reply_markup=get_main_menu_keyboard()
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

@dp.message(F.text == "🎯 Мои цели")
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
