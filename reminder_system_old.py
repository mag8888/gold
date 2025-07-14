import asyncio
import logging
from datetime import datetime, time
from aiogram import types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter
from aiogram import F

logger = logging.getLogger(__name__)

# Глобальный словарь для хранения активных напоминаний
active_reminders = {}

class ReminderStates(StatesGroup):
    waiting_for_interval = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()

async def start_habit_reminders(bot, db, user_id: int, habit_id: int):
    """Запуск напоминаний для привычки с учетом настроек пользователя"""
    reminder_key = f"{user_id}_{habit_id}"
    
    # Если уже есть активное напоминание для этой привычки, останавливаем его
    if reminder_key in active_reminders:
        active_reminders[reminder_key].cancel()
    
    # Создаем новую задачу напоминания
    task = asyncio.create_task(habit_reminder_loop(bot, db, user_id, habit_id))
    active_reminders[reminder_key] = task
    
    logger.info(f"Started reminders for user {user_id}, habit {habit_id}")

async def stop_habit_reminders(user_id: int, habit_id: int):
    """Остановка напоминаний для привычки"""
    reminder_key = f"{user_id}_{habit_id}"
    
    if reminder_key in active_reminders:
        active_reminders[reminder_key].cancel()
        del active_reminders[reminder_key]
        logger.info(f"Stopped reminders for user {user_id}, habit {habit_id}")

def is_within_reminder_time(start_time_str: str, end_time_str: str) -> bool:
    """Проверка, находится ли текущее время в диапазоне напоминаний"""
    try:
        current_time = datetime.now().time()
        start_time = datetime.strptime(start_time_str, "%H:%M").time()
        end_time = datetime.strptime(end_time_str, "%H:%M").time()
        
        if start_time <= end_time:
            # Обычный случай: 07:00 - 22:00
            return start_time <= current_time <= end_time
        else:
            # Переход через полночь: 22:00 - 07:00
            return current_time >= start_time or current_time <= end_time
    except:
        return True  # В случае ошибки разрешаем напоминания

async def habit_reminder_loop(bot, db, user_id: int, habit_id: int):
    """Цикл отправки напоминаний с учетом настроек пользователя"""
    try:
        while True:
            # Получаем настройки напоминаний пользователя
            settings = db.get_reminder_settings(user_id)
            
            if not settings['is_enabled']:
                # Напоминания отключены
                await stop_habit_reminders(user_id, habit_id)
                break
            
            # Проверяем, находимся ли в разрешенном времени
            if not is_within_reminder_time(settings['start_time'], settings['end_time']):
                # Ждем до следующей проверки (1 минута)
                await asyncio.sleep(60)
                continue
            
            # Проверяем, выполнена ли привычка сегодня
            habit_stats = db.get_habit_stats(user_id, habit_id, days=1)
            completed_today = habit_stats.get('completed_count', 0) or 0
            
            if completed_today > 0:
                # Привычка выполнена, останавливаем напоминания
                await stop_habit_reminders(user_id, habit_id)
                break
            
            # Получаем информацию о привычке
            habits = db.get_user_habits(user_id)
            habit = next((h for h in habits if h['habit_id'] == habit_id), None)
            
            if not habit or not habit['is_active']:
                # Привычка не найдена или неактивна, останавливаем напоминания
                await stop_habit_reminders(user_id, habit_id)
                break
            
            # Отправляем напоминание
            habit_name = habit['habit_name']
            target_frequency = habit.get('target_frequency', 1)
            
            # Определяем текст интервала для отображения
            # Получаем все привычки пользователя
            habits = db.get_user_habits(user_id)
            
            if not habits:
                return
            
            # Формируем список привычек с выделением невыполненных
            habits_text = "📅 **Ваши привычки на сегодня:**\n\n"
            
            for habit in habits:
                habit_id = habit['habit_id']
                habit_name = habit['habit_name']
                target_freq = habit['target_frequency']
                
                # Получаем количество выполненных сегодня
                completed_today = db.get_habit_completion_count(user_id, habit_id, datetime.now().date())
                if completed_today is None:
                    completed_today = 0
                
                # Проверяем, выполнена ли привычка
                is_completed = completed_today >= target_freq
                
                if is_completed:
                    # Выполненная привычка - зеленый текст
                    habits_text += f"✅ {target_freq} ⚡ {habit_name} ✅ {completed_today}\n"
                else:
                    # Невыполненная привычка - красный текст с эмодзи внимания
                    habits_text += f"🔴 {target_freq} ⚡ {habit_name} ✅ {completed_today} ⚠️\n"
            
            habits_text += "\n💡 Красным выделены невыполненные привычки"
            
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=habits_text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(
                                text="📅 Открыть привычки", 
                                callback_data="show_habits_menu"
                            )],
                            [InlineKeyboardButton(
                                text="⏸️ Остановить напоминания", 
                                callback_data=f"stop_reminders_{habit_id}"
                            )]
                        ]
                    )
                )
                logger.info(f"Sent habits list reminder for user {user_id}")
            except Exception as e:
                logger.error(f"Failed to send habits list reminder: {e}")
            
            # Ждем до следующего напоминания согласно настройкам
            await asyncio.sleep(settings['interval'])
            
    except asyncio.CancelledError:
        logger.info(f"Reminder loop cancelled for user {user_id}, habit {habit_id}")
    except Exception as e:
        logger.error(f"Error in reminder loop: {e}")

async def start_daily_reminder_check(bot, db):
    """Ежедневная проверка и запуск напоминаний для невыполненных привычек"""
    try:
        # Получаем всех пользователей с активными привычками
        cursor = db.conn.cursor()
        cursor.execute('''
            SELECT DISTINCT user_id FROM habits WHERE is_active = 1
        ''')
        users = cursor.fetchall()
        
        for (user_id,) in users:
            # Получаем активные привычки пользователя
            habits = db.get_user_habits(user_id, active_only=True)
            
            for habit in habits:
                habit_id = habit['habit_id']
                
                # Проверяем, выполнена ли привычка сегодня
                habit_stats = db.get_habit_stats(user_id, habit_id, days=1)
                completed_today = habit_stats.get('completed_count', 0) or 0
                
                if completed_today == 0:
                    # Привычка не выполнена, запускаем напоминания
                    await start_habit_reminders(bot, db, user_id, habit_id)
        
        logger.info("Daily reminder check completed")
    except Exception as e:
        logger.error(f"Error in daily reminder check: {e}")

