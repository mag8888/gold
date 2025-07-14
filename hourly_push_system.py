#!/usr/bin/env python3
"""
Система почасовых push-уведомлений по незавершенным привычкам
"""

import asyncio
import logging
from datetime import datetime, time
from typing import List, Dict, Any
import pytz
from aiogram import Bot
from database import Database

logger = logging.getLogger(__name__)

class HourlyPushSystem:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = Database()
        self.is_running = False
        self.push_task = None
    
    def start(self):
        """Запуск системы почасовых push-уведомлений"""
        if self.is_running:
            return
        
        self.is_running = True
        self.push_task = asyncio.create_task(self._hourly_push_loop())
        logger.info("Hourly push system started")
    
    def stop(self):
        """Остановка системы"""
        self.is_running = False
        if self.push_task:
            self.push_task.cancel()
        logger.info("Hourly push system stopped")
    
    def _get_user_local_time(self, timezone_str: str) -> datetime:
        """Получение локального времени пользователя"""
        try:
            user_tz = pytz.timezone(timezone_str)
            utc_now = datetime.now(pytz.UTC)
            return utc_now.astimezone(user_tz)
        except:
            # Если часовой пояс некорректный, используем UTC
            return datetime.now(pytz.UTC)
    
    def _is_in_push_time(self, user_settings: Dict) -> bool:
        """Проверка, находится ли пользователь в своем дневном времени"""
        if not user_settings['push_enabled']:
            return False
        
        local_time = self._get_user_local_time(user_settings['timezone'])
        current_hour = local_time.hour
        
        start_hour = user_settings['push_start_hour']
        end_hour = user_settings['push_end_hour']
        
        # Обработка случая когда время переходит через полночь
        if start_hour <= end_hour:
            return start_hour <= current_hour < end_hour
        else:
            return current_hour >= start_hour or current_hour < end_hour
    
    async def _hourly_push_loop(self):
        """Основной цикл почасовых уведомлений"""
        while self.is_running:
            try:
                await self._send_hourly_push_notifications()
                
                # Ждем до следующего часа
                await self._wait_until_next_hour()
                
            except Exception as e:
                logger.error(f"Error in hourly push loop: {e}")
                await asyncio.sleep(300)  # Ждем 5 минут при ошибке
    
    async def _wait_until_next_hour(self):
        """Ожидание до начала следующего часа"""
        now = datetime.now()
        next_hour = now.replace(minute=0, second=0, microsecond=0)
        next_hour = next_hour.replace(hour=next_hour.hour + 1)
        
        wait_seconds = (next_hour - now).total_seconds()
        await asyncio.sleep(wait_seconds)
    
    async def _send_hourly_push_notifications(self):
        """Отправка почасовых push-уведомлений"""
        logger.info("Starting hourly push notifications")
        
        # Получаем всех пользователей с их настройками часового пояса
        users_with_settings = self.db.get_all_users_with_timezone_settings()
        
        sent_count = 0
        for user_data in users_with_settings:
            try:
                user_id = user_data['user_id']
                
                # Проверяем, находится ли пользователь в своем дневном времени
                if not self._is_in_push_time(user_data):
                    continue
                
                # Проверяем, есть ли у пользователя активные привычки
                if not self.db.get_user_habits(user_id):
                    continue
                
                # Проверяем статус пользователя на сегодня
                if self._is_user_goals_completed(user_id):
                    logger.info(f"User {user_id} has completed all goals, skipping")
                    continue
                
                # Получаем незавершенные привычки
                incomplete_habits = self._get_incomplete_habits(user_id)
                
                if incomplete_habits:
                    await self._send_push_notification(user_id, incomplete_habits)
                    sent_count += 1
                    
                    # Небольшая задержка между отправками
                    await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error sending push to user {user_id}: {e}")
        
        logger.info(f"Sent {sent_count} hourly push notifications")
    
    def _is_user_goals_completed(self, user_id: int) -> bool:
        """Проверка, выполнил ли пользователь все цели на сегодня"""
        try:
            today = datetime.now().date()
            
            # Получаем все привычки пользователя
            habits = self.db.get_user_habits(user_id)
            if not habits:
                return True  # Нет привычек = цели выполнены
            
            # Проверяем каждую привычку
            for habit in habits:
                habit_id = habit['habit_id']
                target_count = habit.get('target_frequency', 1)
                
                # Получаем текущий прогресс
                current_count = self.db.get_habit_progress_today(user_id, habit_id)
                
                # Если хотя бы одна привычка не выполнена
                if current_count < target_count:
                    return False
            
            # Все привычки выполнены
            return True
            
        except Exception as e:
            logger.error(f"Error checking user goals completion: {e}")
            return False
    
    def _get_incomplete_habits(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение списка незавершенных привычек"""
        try:
            today = datetime.now().date()
            incomplete_habits = []
            
            habits = self.db.get_user_habits(user_id)
            
            for habit in habits:
                habit_id = habit['habit_id']
                habit_name = habit['habit_name']
                target_count = habit.get('target_frequency', 1)
                
                # Получаем текущий прогресс
                current_count = self.db.get_habit_progress_today(user_id, habit_id)
                
                # Если привычка не выполнена полностью
                if current_count < target_count:
                    incomplete_habits.append({
                        'id': habit_id,
                        'name': habit_name,
                        'current': current_count,
                        'target': target_count,
                        'remaining': target_count - current_count
                    })
            
            return incomplete_habits
            
        except Exception as e:
            logger.error(f"Error getting incomplete habits: {e}")
            return []
    
    async def _send_push_notification(self, user_id: int, incomplete_habits: List[Dict[str, Any]]):
        """Отправка push-уведомления о незавершенных привычках с кнопками"""
        try:
            from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
            
            # Формируем сообщение
            message = "⏰ **Напоминание о привычках**\n\n"
            message += "Незавершенные цели на сегодня:\n\n"
            
            # Создаем кнопки для каждой привычки
            keyboard_buttons = []
            
            for habit in incomplete_habits:
                remaining = habit['remaining']
                name = habit['name']
                current = habit['current']
                target = habit['target']
                habit_id = habit['id']
                
                message += f"🔴 **{name}**\n"
                message += f"   Осталось: {remaining} из {target}\n"
                message += f"   Выполнено: {current}/{target}\n\n"
                
                # Добавляем кнопку для быстрого отмечания
                button_text = f"✅ {name}"
                callback_data = f"quick_habit_{habit_id}"
                
                keyboard_buttons.append([
                    InlineKeyboardButton(text=button_text, callback_data=callback_data)
                ])
            
            message += "💪 Продолжайте! Каждый шаг приближает к цели!\n\n"
            message += "*Нажмите кнопку для быстрого отмечания выполнения*"
            
            # Создаем клавиатуру
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            
            # Отправляем уведомление с кнопками
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            logger.info(f"Sent push notification with buttons to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending push notification to user {user_id}: {e}")

# Глобальный экземпляр системы (будет инициализирован в main)
hourly_push_system = None

