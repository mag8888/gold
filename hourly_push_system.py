#!/usr/bin/env python3
"""
Система почасовых push-уведомлений по незавершенным привычкам
"""

import asyncio
import logging
from datetime import datetime, time
from typing import List, Dict, Any
from aiogram import Bot
from database import Database

logger = logging.getLogger(__name__)

class HourlyPushSystem:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = Database()
        self.is_running = False
        self.push_task = None
        
        # Настройки дневного времени (можно настроить)
        self.day_start_hour = 8   # 08:00
        self.day_end_hour = 22    # 22:00
    
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
    
    async def _hourly_push_loop(self):
        """Основной цикл почасовых уведомлений"""
        while self.is_running:
            try:
                current_hour = datetime.now().hour
                
                # Проверяем, находимся ли в дневном времени
                if self.day_start_hour <= current_hour < self.day_end_hour:
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
        
        # Получаем всех пользователей с активными привычками
        users_with_habits = self.db.get_users_with_active_habits()
        
        sent_count = 0
        for user_id in users_with_habits:
            try:
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
        """Отправка push-уведомления о незавершенных привычках"""
        try:
            # Формируем сообщение
            message = "⏰ **Напоминание о привычках**\n\n"
            message += "Незавершенные цели на сегодня:\n\n"
            
            for habit in incomplete_habits:
                remaining = habit['remaining']
                name = habit['name']
                current = habit['current']
                target = habit['target']
                
                message += f"🔴 **{name}**\n"
                message += f"   Осталось: {remaining} из {target}\n"
                message += f"   Выполнено: {current}/{target}\n\n"
            
            message += "💪 Продолжайте! Каждый шаг приближает к цели!"
            
            # Отправляем уведомление
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode="Markdown"
            )
            
            logger.info(f"Sent push notification to user {user_id}")
            
        except Exception as e:
            logger.error(f"Error sending push notification to user {user_id}: {e}")

# Глобальный экземпляр системы (будет инициализирован в main)
hourly_push_system = None

