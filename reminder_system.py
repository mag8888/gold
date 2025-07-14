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
            return start_time <= current_time <= end_time
        else:
            # Случай, когда диапазон переходит через полночь
            return current_time >= start_time or current_time <= end_time
    except Exception as e:
        logger.error(f"Error checking reminder time: {e}")
        return True  # По умолчанию разрешаем напоминания

async def habit_reminder_loop(bot, db, user_id: int, habit_id: int):
    """Основной цикл напоминаний для привычки"""
    try:
        while True:
            # Получаем настройки напоминаний пользователя
            settings = db.get_reminder_settings(user_id)
            
            # Проверяем, находится ли текущее время в диапазоне напоминаний
            if not is_within_reminder_time(settings['start_time'], settings['end_time']):
                await asyncio.sleep(300)  # Проверяем каждые 5 минут
                continue
            
            # Получаем все привычки пользователя
            habits = db.get_user_habits(user_id)
            
            if not habits:
                return
            
            # Проверяем, есть ли невыполненные привычки
            has_incomplete = False
            for habit in habits:
                habit_stats = db.get_habit_stats(user_id, habit['habit_id'], days=1)
                completed_today = habit_stats.get('completed_count', 0) or 0
                if completed_today < habit['target_frequency']:
                    has_incomplete = True
                    break
            
            # Если все привычки выполнены, останавливаем напоминания
            if not has_incomplete:
                await stop_habit_reminders(user_id, habit_id)
                break
            
            # Формируем список привычек как на скриншоте
            habits_text = "📅 **Ежедневные привычки**\n\n"
            
            for habit in habits:
                habit_id_current = habit['habit_id']
                habit_name = habit['habit_name']
                target_freq = habit['target_frequency']
                
                # Получаем количество выполненных сегодня
                habit_stats = db.get_habit_stats(user_id, habit_id_current, days=1)
                completed_today = habit_stats.get('completed_count', 0) or 0
                
                # Форматируем как на скриншоте: "6 ⚡ Отжаться ✅ 6"
                habits_text += f"{target_freq} ⚡ {habit_name} ✅ {completed_today}\n"
            
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=habits_text,
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(
                        inline_keyboard=[
                            [InlineKeyboardButton(
                                text="Добавить", 
                                callback_data="add_habit"
                            ),
                            InlineKeyboardButton(
                                text="🎯 Все привычки", 
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
        users = db.get_all_users_with_habits()
        
        for user_id in users:
            habits = db.get_user_habits(user_id)
            
            for habit in habits:
                if habit['is_active']:
                    # Проверяем, выполнена ли привычка сегодня
                    habit_stats = db.get_habit_stats(user_id, habit['habit_id'], days=1)
                    completed_today = habit_stats.get('completed_count', 0) or 0
                    
                    # Если привычка не выполнена, запускаем напоминания
                    if completed_today < habit['target_frequency']:
                        await start_habit_reminders(bot, db, user_id, habit['habit_id'])
                        
    except Exception as e:
        logger.error(f"Error in daily reminder check: {e}")

