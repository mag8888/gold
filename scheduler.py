import asyncio
import schedule
import threading
import time
from datetime import datetime, date
from typing import List
import logging

from aiogram import Bot
from database import Database
from google_sheets import sheets_manager

logger = logging.getLogger(__name__)

class ReportScheduler:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = Database()  # Создаем экземпляр базы данных
        self.is_running = False
        self.scheduler_thread = None
    
    def start(self):
        """Запуск планировщика"""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Настраиваем расписание
        self._setup_schedule()
        
        # Запускаем планировщик в отдельном потоке
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        
        logger.info("Report scheduler started")
    
    def stop(self):
        """Остановка планировщика"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5)
        logger.info("Report scheduler stopped")
    
    def _setup_schedule(self):
        """Настройка расписания задач"""
        # Получаем время из настроек (по умолчанию 21:00 для отчетов, 20:00 для напоминаний)
        report_time = self._get_setting_with_fallback('report_time', '21:00')
        reminder_time = self._get_setting_with_fallback('reminder_time', '20:00')
        
        # Планируем ежедневные отчеты
        schedule.every().day.at(report_time).do(self._schedule_daily_reports)
        
        # Планируем напоминания о невыполненных целях
        schedule.every().day.at(reminder_time).do(self._schedule_goal_reminders)
        
        # Планируем ежедневный отчет по привычкам в 00:00
        schedule.every().day.at("00:00").do(self._schedule_habits_daily_report)
        
        # Планируем сброс счетчиков привычек в 00:01
        schedule.every().day.at("00:01").do(self._schedule_habits_reset)
        
        logger.info(f"Scheduled daily reports at {report_time}")
        logger.info(f"Scheduled goal reminders at {reminder_time}")
        logger.info("Scheduled habits daily report at 00:00")
        logger.info("Scheduled habits reset at 00:01")
    
    def _get_setting_with_fallback(self, key: str, default: str) -> str:
        """Получение настройки с fallback на базу данных"""
        # Сначала пытаемся получить из Google Sheets
        if sheets_manager.is_connected():
            value = sheets_manager.get_setting(key)
            if value:
                return value
        
        # Если не получилось, берем из локальной базы
        value = self.db.get_setting(key)
        return value if value else default
    
    def _run_scheduler(self):
        """Основной цикл планировщика"""
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Проверяем каждую минуту
    
    def _schedule_daily_reports(self):
        """Планирование отправки ежедневных отчетов"""
        asyncio.create_task(self._send_daily_reports())
    
    def _schedule_goal_reminders(self):
        """Планирование отправки напоминаний о целях"""
        asyncio.create_task(self._send_goal_reminders())
    
    def _schedule_habits_daily_report(self):
        """Планирование отправки ежедневного отчета по привычкам"""
        asyncio.create_task(self._send_habits_daily_report())
    
    def _schedule_habits_reset(self):
        """Планирование сброса счетчиков привычек"""
        asyncio.create_task(self._reset_habits_counters())
    
    async def _send_daily_reports(self):
        """Отправка ежедневных отчетов пользователям"""
        try:
            logger.info("Starting daily reports sending")
            
            # Получаем всех пользователей с целями на сегодня
            users_with_goals = self._get_users_with_daily_goals()
            
            sent_count = 0
            for user_id in users_with_goals:
                try:
                    report = await self._generate_daily_report(user_id)
                    if report:
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=report,
                            parse_mode="Markdown"
                        )
                        sent_count += 1
                        
                        # Небольшая задержка между отправками
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"Failed to send daily report to user {user_id}: {e}")
                    # Если пользователь заблокировал бота, помечаем его как неактивного
                    if "bot was blocked" in str(e).lower():
                        self.db.update_user_status(user_id, 'blocked')
            
            logger.info(f"Daily reports sent to {sent_count} users")
            
        except Exception as e:
            logger.error(f"Error in daily reports sending: {e}")
    
    async def _send_goal_reminders(self):
        """Отправка напоминаний о невыполненных целях"""
        try:
            logger.info("Starting goal reminders sending")
            
            # Получаем пользователей с невыполненными целями на сегодня
            users_with_incomplete_goals = self.db.get_users_with_incomplete_goals(date.today())
            
            sent_count = 0
            for user_id in users_with_incomplete_goals:
                try:
                    reminder = await self._generate_goal_reminder(user_id)
                    if reminder:
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=reminder,
                            parse_mode="Markdown"
                        )
                        sent_count += 1
                        
                        # Небольшая задержка между отправками
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"Failed to send goal reminder to user {user_id}: {e}")
                    # Если пользователь заблокировал бота, помечаем его как неактивного
                    if "bot was blocked" in str(e).lower():
                        self.db.update_user_status(user_id, 'blocked')
            
            logger.info(f"Goal reminders sent to {sent_count} users")
            
        except Exception as e:
            logger.error(f"Error in goal reminders sending: {e}")
    
    def _get_users_with_daily_goals(self) -> List[int]:
        """Получение пользователей с ежедневными целями"""
        # Это упрощенная версия - в реальности нужно более сложный запрос
        return self.db.get_all_active_users()
    
    async def _generate_daily_report(self, user_id: int) -> str:
        """Генерация ежедневного отчета для пользователя"""
        try:
            # Получаем цели пользователя на сегодня
            daily_goals = self.db.get_user_goals(
                user_id=user_id,
                goal_type='daily',
                date_filter=date.today()
            )
            
            monthly_goals = self.db.get_user_goals(
                user_id=user_id,
                goal_type='monthly'
            )
            
            if not daily_goals and not monthly_goals:
                return None
            
            # Формируем отчет
            report = "📊 **Ваш ежедневный отчет**\n\n"
            
            if daily_goals:
                report += "📅 **Цели на сегодня:**\n"
                completed_daily = 0
                for goal in daily_goals:
                    emoji = "✅" if goal['status'] == 'completed' else "⚡️"
                    report += f"{emoji} {goal['goal_text']}\n"
                    if goal['status'] == 'completed':
                        completed_daily += 1
                
                # Статистика по ежедневным целям
                if daily_goals:
                    completion_rate = (completed_daily / len(daily_goals)) * 100
                    report += f"\n📈 Выполнено: {completed_daily}/{len(daily_goals)} ({completion_rate:.0f}%)\n"
            
            if monthly_goals:
                report += "\n📆 **Цели на месяц:**\n"
                completed_monthly = 0
                for goal in monthly_goals:
                    emoji = "✅" if goal['status'] == 'completed' else "⚡️"
                    progress_info = ""
                    if goal.get('progress_data'):
                        progress_info = f" ({goal['progress_data']})"
                    report += f"{emoji} {goal['goal_text']}{progress_info}\n"
                    if goal['status'] == 'completed':
                        completed_monthly += 1
                
                # Статистика по месячным целям
                if monthly_goals:
                    completion_rate = (completed_monthly / len(monthly_goals)) * 100
                    report += f"\n📈 Выполнено: {completed_monthly}/{len(monthly_goals)} ({completion_rate:.0f}%)\n"
            
            # Мотивационное сообщение
            if daily_goals and all(goal['status'] == 'completed' for goal in daily_goals):
                report += "\n🎉 **Поздравляем! Все цели на сегодня выполнены!**"
            elif daily_goals:
                incomplete_count = len([g for g in daily_goals if g['status'] != 'completed'])
                report += f"\n💪 **Осталось выполнить: {incomplete_count} целей. Вы можете это сделать!**"
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating daily report for user {user_id}: {e}")
            return None
    
    async def _generate_goal_reminder(self, user_id: int) -> str:
        """Генерация напоминания о невыполненных целях"""
        try:
            # Получаем невыполненные цели на сегодня
            incomplete_goals = [
                goal for goal in self.db.get_user_goals(
                    user_id=user_id,
                    goal_type='daily',
                    date_filter=date.today()
                )
                if goal['status'] != 'completed'
            ]
            
            if not incomplete_goals:
                return None
            
            user = self.db.get_user(user_id)
            first_name = user['first_name'] if user else "Друг"
            
            reminder = f"⏰ **Напоминание, {first_name}!**\n\n"
            reminder += f"У вас есть {len(incomplete_goals)} невыполненных целей на сегодня:\n\n"
            
            for goal in incomplete_goals:
                reminder += f"⚡️ {goal['goal_text']}\n"
            
            reminder += "\n💪 **Время действовать! Каждый шаг приближает вас к успеху!**"
            
            return reminder
            
        except Exception as e:
            logger.error(f"Error generating goal reminder for user {user_id}: {e}")
            return None
    
    async def send_broadcast_message(self, message: str, parse_mode: str = "Markdown"):
        """Отправка сообщения всем активным пользователям"""
        try:
            active_users = self.db.get_all_active_users()
            sent_count = 0
            failed_count = 0
            
            for user_id in active_users:
                try:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=message,
                        parse_mode=parse_mode
                    )
                    sent_count += 1
                    
                    # Небольшая задержка между отправками
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Failed to send broadcast to user {user_id}: {e}")
                    
                    # Если пользователь заблокировал бота, помечаем его как неактивного
                    if "bot was blocked" in str(e).lower():
                        self.db.update_user_status(user_id, 'blocked')
            
            logger.info(f"Broadcast sent to {sent_count} users, {failed_count} failed")
            return sent_count, failed_count
            
        except Exception as e:
            logger.error(f"Error in broadcast sending: {e}")
            return 0, 0

    async def _send_habits_daily_report(self):
        """Отправка ежедневного отчета по привычкам в 00:00"""
        try:
            logger.info("Starting habits daily report sending")
            
            # Получаем всех пользователей с активными привычками
            users_with_habits = self.db.get_all_users_with_habits()
            
            sent_count = 0
            for user_id in users_with_habits:
                try:
                    report = await self._generate_habits_daily_report(user_id)
                    if report:
                        await self.bot.send_message(
                            chat_id=user_id,
                            text=report,
                            parse_mode="Markdown"
                        )
                        sent_count += 1
                        
                        # Небольшая задержка между отправками
                        await asyncio.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"Failed to send habits daily report to user {user_id}: {e}")
                    # Если пользователь заблокировал бота, помечаем его как неактивного
                    if "bot was blocked" in str(e).lower():
                        self.db.update_user_status(user_id, 'blocked')
            
            logger.info(f"Habits daily reports sent to {sent_count} users")
            
        except Exception as e:
            logger.error(f"Error in habits daily reports sending: {e}")
    
    async def _reset_habits_counters(self):
        """Сброс счетчиков привычек в новый день (00:01)"""
        try:
            logger.info("Starting habits counters reset")
            
            # Получаем всех пользователей с активными привычками
            users_with_habits = self.db.get_all_users_with_habits()
            
            reset_count = 0
            for user_id in users_with_habits:
                try:
                    # Сбрасываем счетчики привычек для пользователя
                    success = self.db.reset_daily_habits_counters(user_id)
                    if success:
                        reset_count += 1
                        
                except Exception as e:
                    logger.error(f"Failed to reset habits counters for user {user_id}: {e}")
            
            logger.info(f"Habits counters reset for {reset_count} users")
            
        except Exception as e:
            logger.error(f"Error in habits counters reset: {e}")
    
    async def _generate_habits_daily_report(self, user_id: int) -> str:
        """Генерация ежедневного отчета по привычкам для пользователя"""
        try:
            from datetime import datetime, timedelta
            
            # Получаем привычки пользователя
            habits = self.db.get_user_habits(user_id, active_only=True)
            
            if not habits:
                return None
            
            # Получаем вчерашнюю дату для отчета
            yesterday = (datetime.now() - timedelta(days=1)).date()
            
            user = self.db.get_user(user_id)
            first_name = user['first_name'] if user else "Друг"
            
            report = f"📊 **Отчет по привычкам за {yesterday.strftime('%d.%m.%Y')}, {first_name}!**\n\n"
            report += "📅 **Ежедневные привычки**\n\n"
            
            total_habits = 0
            completed_habits = 0
            
            for habit in habits:
                if habit.get('habit_type') == 'daily':
                    total_habits += 1
                    
                    # Получаем статистику выполнения за вчера
                    stats = self.db.get_habit_stats(user_id, habit['habit_id'], days=1)
                    
                    target = habit.get('target_frequency', 1)
                    completed = stats.get('completed_count', 0)
                    
                    if completed >= target:
                        completed_habits += 1
                        emoji = "✅"
                    else:
                        emoji = "🔴"
                    
                    report += f"{target} ⚡ {habit['habit_name']} {emoji} {completed}\n"
            
            # Добавляем процент выполнения
            if total_habits > 0:
                completion_percentage = (completed_habits / total_habits) * 100
                report += f"\n📈 **Выполнено: {completed_habits}/{total_habits} ({completion_percentage:.1f}%)**\n"
                
                # Мотивационное сообщение
                if completion_percentage == 100:
                    report += "\n🎉 **Отлично! Все привычки выполнены!**"
                elif completion_percentage >= 80:
                    report += "\n💪 **Хороший результат! Продолжайте в том же духе!**"
                elif completion_percentage >= 50:
                    report += "\n⚡ **Неплохо! Есть к чему стремиться!**"
                else:
                    report += "\n🔥 **Новый день - новые возможности! Вперед!**"
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating habits daily report for user {user_id}: {e}")
            return None


# Глобальный экземпляр планировщика (будет инициализирован в main)
scheduler = None

