import sqlite3
import json
from datetime import datetime, date
from typing import Optional, List, Dict, Any

class Database:
    def __init__(self, db_path: str = "bot_database.db"):
    self.db_path = db_path
    self.init_database()
    
    def init_database(self):
    """Инициализация базы данных и создание таблиц"""
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                status TEXT DEFAULT 'active',
                join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                onboarding_completed BOOLEAN DEFAULT FALSE,
                referrer_id INTEGER,
                referral_code TEXT UNIQUE
            )
        ''')
        
        # Таблица профилей (визиток)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS profiles (
                user_id INTEGER PRIMARY KEY,
                bio TEXT,
                product_info TEXT,
                case_studies TEXT,
                networking_motive TEXT,
                life_values TEXT,
                lifestyle TEXT,
                social_link TEXT,
                category TEXT,
                generated_card TEXT,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица целей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS goals (
                goal_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                goal_text TEXT NOT NULL,
                goal_type TEXT CHECK(goal_type IN ('daily', 'monthly')) NOT NULL,
                status TEXT CHECK(status IN ('in_progress', 'completed')) DEFAULT 'in_progress',
                progress_data TEXT,
                created_date DATE DEFAULT CURRENT_DATE,
                due_date DATE,
                completed_date DATE,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица рефералов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                referral_id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_user_id INTEGER,
                referred_user_id INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                earnings REAL DEFAULT 0.0,
                FOREIGN KEY (referrer_user_id) REFERENCES users (user_id),
                FOREIGN KEY (referred_user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица настроек
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица категорий партнеров
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS partner_categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT UNIQUE NOT NULL,
                category_emoji TEXT,
                is_active BOOLEAN DEFAULT TRUE
            )
        ''')
        
        # Таблица привычек
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS habits (
                habit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                habit_name TEXT NOT NULL,
                habit_description TEXT,
                habit_type TEXT CHECK(habit_type IN ('daily', 'weekly', 'custom')) DEFAULT 'daily',
                target_frequency INTEGER DEFAULT 1,
                reminder_time TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица логов привычек
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS habit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                habit_id INTEGER,
                user_id INTEGER,
                completion_date DATE DEFAULT CURRENT_DATE,
                completed BOOLEAN DEFAULT TRUE,
                notes TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (habit_id) REFERENCES habits (habit_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица программ тренировок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workout_programs (
                program_id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_name TEXT NOT NULL,
                program_description TEXT,
                program_type TEXT CHECK(program_type IN ('energy', 'strength', 'cardio', 'flexibility')) DEFAULT 'energy',
                duration_weeks INTEGER DEFAULT 4,
                difficulty_level TEXT CHECK(difficulty_level IN ('beginner', 'intermediate', 'advanced')) DEFAULT 'beginner',
                exercises_data TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица пользовательских тренировок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_workouts (
                user_workout_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                program_id INTEGER,
                start_date DATE DEFAULT CURRENT_DATE,
                current_week INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (program_id) REFERENCES workout_programs (program_id)
            )
        ''')
        
        # Таблица логов тренировок
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS workout_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_workout_id INTEGER,
                user_id INTEGER,
                workout_date DATE DEFAULT CURRENT_DATE,
                exercises_completed TEXT,
                duration_minutes INTEGER,
                notes TEXT,
                completed BOOLEAN DEFAULT TRUE,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_workout_id) REFERENCES user_workouts (user_workout_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица задач органайзера
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                task_title TEXT NOT NULL,
                task_description TEXT,
                task_category TEXT,
                priority TEXT CHECK(priority IN ('low', 'medium', 'high', 'urgent')) DEFAULT 'medium',
                status TEXT CHECK(status IN ('pending', 'in_progress', 'completed', 'cancelled')) DEFAULT 'pending',
                due_date DATE,
                reminder_time TIMESTAMP,
                parent_task_id INTEGER,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_date TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (parent_task_id) REFERENCES tasks (task_id)
            )
        ''')
        
        # Таблица шаблонов распорядка дня
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS schedule_templates (
                template_id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_name TEXT NOT NULL,
                template_description TEXT,
                template_type TEXT CHECK(template_type IN ('morning', 'workday', 'weekend', 'full_day')) DEFAULT 'full_day',
                time_blocks TEXT,
                is_public BOOLEAN DEFAULT FALSE,
                created_by INTEGER,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица ежедневных планов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_schedules (
                schedule_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                schedule_date DATE DEFAULT CURRENT_DATE,
                template_id INTEGER,
                time_blocks TEXT,
                completion_status TEXT,
                notes TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (template_id) REFERENCES schedule_templates (template_id)
            )
        ''')
        
        # Таблица планов питания
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nutrition_plans (
                plan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_name TEXT NOT NULL,
                plan_description TEXT,
                plan_type TEXT CHECK(plan_type IN ('weight_loss', 'muscle_gain', 'maintenance', 'detox')) DEFAULT 'maintenance',
                duration_days INTEGER DEFAULT 30,
                meals_data TEXT,
                calories_target INTEGER,
                is_active BOOLEAN DEFAULT TRUE,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица пользовательского питания
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_nutrition (
                user_nutrition_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_id INTEGER,
                start_date DATE DEFAULT CURRENT_DATE,
                current_day INTEGER DEFAULT 1,
                is_active BOOLEAN DEFAULT TRUE,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (plan_id) REFERENCES nutrition_plans (plan_id)
            )
        ''')
        
        # Таблица логов питания
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nutrition_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_nutrition_id INTEGER,
                user_id INTEGER,
                meal_date DATE DEFAULT CURRENT_DATE,
                meal_type TEXT CHECK(meal_type IN ('breakfast', 'lunch', 'dinner', 'snack')) NOT NULL,
                meal_description TEXT,
                calories INTEGER,
                completed BOOLEAN DEFAULT TRUE,
                notes TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_nutrition_id) REFERENCES user_nutrition (user_nutrition_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица биохакинг метрик
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS biohacking_metrics (
                metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                metric_type TEXT CHECK(metric_type IN ('sleep', 'hrv', 'weight', 'energy', 'mood', 'stress', 'custom')) NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL,
                metric_unit TEXT,
                measurement_date DATE DEFAULT CURRENT_DATE,
                notes TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица чек-листа матерманайда
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mastermind_checklist (
                checklist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                checklist_date DATE DEFAULT CURRENT_DATE,
                morning_routine BOOLEAN DEFAULT FALSE,
                goal_review BOOLEAN DEFAULT FALSE,
                learning_session BOOLEAN DEFAULT FALSE,
                networking_activity BOOLEAN DEFAULT FALSE,
                reflection_time BOOLEAN DEFAULT FALSE,
                gratitude_practice BOOLEAN DEFAULT FALSE,
                skill_development BOOLEAN DEFAULT FALSE,
                creative_thinking BOOLEAN DEFAULT FALSE,
                physical_activity BOOLEAN DEFAULT FALSE,
                mindfulness_practice BOOLEAN DEFAULT FALSE,
                notes TEXT,
                completion_percentage INTEGER DEFAULT 0,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Таблица календарных событий
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS calendar_events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                event_title TEXT NOT NULL,
                event_description TEXT,
                event_type TEXT CHECK(event_type IN ('task', 'habit', 'workout', 'meal', 'meeting', 'reminder', 'custom')) DEFAULT 'custom',
                start_datetime TIMESTAMP NOT NULL,
                end_datetime TIMESTAMP,
                is_all_day BOOLEAN DEFAULT FALSE,
                reminder_minutes INTEGER DEFAULT 15,
                recurrence_rule TEXT,
                status TEXT CHECK(status IN ('scheduled', 'completed', 'cancelled')) DEFAULT 'scheduled',
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        
        # Вставляем базовые категории
        cursor.execute('''
            INSERT OR IGNORE INTO partner_categories (category_name, category_emoji) 
            VALUES 
            ('Коуч', '👤'),
            ('Энергопрактик', '⚡'),
            ('Психолог', '🧠')
        ''')
        
        # Вставляем базовые настройки
        cursor.execute('''
            INSERT OR IGNORE INTO settings (setting_key, setting_value) 
            VALUES 
            ('report_time', '21:00'),
            ('reminder_time', '20:00'),
            ('admin_chat_id', ''),
            ('welcome_message', 'Добро пожаловать в SynergyNet!')
        ''')
        
        conn.commit()
    
    # Методы для работы с пользователями
    def create_user(self, user_id: int, first_name: str, last_name: str = None, 
               username: str = None, referrer_id: int = None) -> bool:
    """Создание нового пользователя"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Генерируем уникальный реферальный код в правильном формате
            referral_code = f"REF_{user_id}_{datetime.now().strftime('%Y%m%d%H')}"
            
            cursor.execute('''
                INSERT INTO users (user_id, first_name, last_name, username, referrer_id, referral_code)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, first_name, last_name, username, referrer_id, referral_code))
            
            # Если есть реферер, добавляем запись в таблицу рефералов
            if referrer_id:
                cursor.execute('''
                    INSERT INTO referrals (referrer_user_id, referred_user_id)
                    VALUES (?, ?)
                ''', (referrer_id, user_id))
            
            conn.commit()
            return True
    except sqlite3.IntegrityError:
        return False
    
    def get_user(self, user_id: int) -> Optional[Dict]:
    """Получение информации о пользователе"""
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_user_status(self, user_id: int, status: str) -> bool:
    """Обновление статуса пользователя"""
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET status = ? WHERE user_id = ?', (status, user_id))
        conn.commit()
        return cursor.rowcount > 0
    
    def complete_onboarding(self, user_id: int) -> bool:
    """Отметка о завершении онбординга"""
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET onboarding_completed = TRUE WHERE user_id = ?', (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    
    # Методы для работы с профилями
    def save_profile(self, user_id: int, profile_data: Dict) -> bool:
    """Сохранение профиля пользователя"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO profiles 
                (user_id, bio, product_info, case_studies, networking_motive, 
                 life_values, lifestyle, social_link, category, generated_card)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id,
                profile_data.get('bio'),
                profile_data.get('product_info'),
                profile_data.get('case_studies'),
                profile_data.get('networking_motive'),
                profile_data.get('life_values'),
                profile_data.get('lifestyle'),
                profile_data.get('social_link'),
                profile_data.get('category'),
                profile_data.get('generated_card')
            ))
            conn.commit()
            return True
    except Exception:
        return False
    
    def get_profile(self, user_id: int) -> Optional[Dict]:
    """Получение профиля пользователя"""
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM profiles WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    
    # Методы для работы с целями
    def create_goal(self, user_id: int, goal_text: str, goal_type: str, due_date: str = None) -> bool:
    """Создание новой цели"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO goals (user_id, goal_text, goal_type, due_date)
                VALUES (?, ?, ?, ?)
            ''', (user_id, goal_text, goal_type, due_date))
            conn.commit()
            return True
    except Exception:
        return False
    
    def get_user_goals(self, user_id: int, goal_type: str = None) -> List[Dict]:
    """Получение целей пользователя"""
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if goal_type:
            cursor.execute('SELECT * FROM goals WHERE user_id = ? AND goal_type = ? ORDER BY created_date DESC', 
                         (user_id, goal_type))
        else:
            cursor.execute('SELECT * FROM goals WHERE user_id = ? ORDER BY created_date DESC', (user_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def update_goal_status(self, goal_id: int, user_id: int, status: str) -> bool:
    """Обновление статуса цели"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if status == 'completed':
                cursor.execute('''
                    UPDATE goals 
                    SET status = ?, completed_date = CURRENT_DATE 
                    WHERE goal_id = ? AND user_id = ?
                ''', (status, goal_id, user_id))
            else:
                cursor.execute('''
                    UPDATE goals 
                    SET status = ?, completed_date = NULL 
                    WHERE goal_id = ? AND user_id = ?
                ''', (status, goal_id, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
    except Exception:
        return False
    
    # Методы для работы с рефералами
    def get_referral_stats(self, user_id: int) -> Dict:
    """Получение статистики рефералов"""
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.cursor()
        
        # Получаем количество рефералов
        cursor.execute('''
            SELECT COUNT(*) as referral_count, COALESCE(SUM(earnings), 0) as total_earnings
            FROM referrals 
            WHERE referrer_user_id = ?
        ''', (user_id,))
        
        stats = cursor.fetchone()
        
        # Получаем реферальный код пользователя
        cursor.execute('SELECT referral_code FROM users WHERE user_id = ?', (user_id,))
        referral_code = cursor.fetchone()
        
        return {
            'referral_count': stats[0] if stats else 0,
            'total_earnings': stats[1] if stats else 0.0,
            'referral_code': referral_code[0] if referral_code else None
        }
    
    def add_referral(self, referrer_user_id: int, referred_user_id: int) -> bool:
    """Добавление записи о реферале"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO referrals (referrer_user_id, referred_user_id, timestamp, earnings)
                VALUES (?, ?, ?, 0.0)
            ''', (referrer_user_id, referred_user_id, datetime.now()))
            return True
    except Exception as e:
        print(f"Error adding referral: {e}")
        return False

    # Методы для работы с привычками
    def create_habit(self, user_id: int, habit_name: str, habit_description: str = None, 
                habit_type: str = 'daily', target_frequency: int = 1, 
                reminder_time: str = None) -> bool:
    """Создание новой привычки"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO habits (user_id, habit_name, habit_description, habit_type, 
                                  target_frequency, reminder_time)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (user_id, habit_name, habit_description, habit_type, target_frequency, reminder_time))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error creating habit: {e}")
        return False
    
    def get_user_habits(self, user_id: int, active_only: bool = True) -> List[Dict]:
    """Получение привычек пользователя"""
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = 'SELECT * FROM habits WHERE user_id = ?'
        params = [user_id]
        
        if active_only:
            query += ' AND is_active = TRUE'
        
        query += ' ORDER BY created_date DESC'
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def log_habit_completion(self, habit_id: int, user_id: int, completed: bool = True, 
                       completion_date: str = None, notes: str = None) -> bool:
    """Логирование выполнения привычки"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO habit_logs 
                (habit_id, user_id, completion_date, completed, notes)
                VALUES (?, ?, COALESCE(?, CURRENT_DATE), ?, ?)
            ''', (habit_id, user_id, completion_date, completed, notes))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error logging habit completion: {e}")
        return False
    
    def get_habit_stats(self, user_id: int, habit_id: int, days: int = 30) -> Dict:
    """Получение статистики по привычке"""
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Получаем статистику за последние N дней
        cursor.execute('''
            SELECT 
                COUNT(*) as total_logs,
                SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed_count,
                MAX(completion_date) as last_completion
            FROM habit_logs 
            WHERE habit_id = ? AND user_id = ? 
            AND completion_date >= date('now', '-{} days')
        '''.format(days), (habit_id, user_id))
        
        stats = dict(cursor.fetchone())
        
        # Вычисляем процент выполнения
        if stats['total_logs'] > 0:
            stats['completion_rate'] = (stats['completed_count'] / stats['total_logs']) * 100
        else:
            stats['completion_rate'] = 0
        
        return stats
    
    def toggle_habit_status(self, habit_id: int, user_id: int) -> bool:
    """Переключение статуса активности привычки"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE habits 
                SET is_active = NOT is_active 
                WHERE habit_id = ? AND user_id = ?
            ''', (habit_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error toggling habit status: {e}")
        return False

    # Методы для работы с задачами органайзера
    def create_task(self, user_id: int, task_title: str, task_description: str = None,
               task_category: str = None, priority: str = 'medium', 
               due_date: str = None, parent_task_id: int = None) -> bool:
    """Создание новой задачи"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO tasks (user_id, task_title, task_description, task_category,
                                 priority, due_date, parent_task_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, task_title, task_description, task_category, 
                  priority, due_date, parent_task_id))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error creating task: {e}")
        return False
    
    def get_user_tasks(self, user_id: int, status: str = None, category: str = None) -> List[Dict]:
    """Получение задач пользователя"""
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM tasks WHERE user_id = ?'
        params = [user_id]
        
        if status:
            query += ' AND status = ?'
            params.append(status)
        
        if category:
            query += ' AND task_category = ?'
            params.append(category)
        
        query += ' ORDER BY priority DESC, due_date ASC, created_date DESC'
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def update_task_status(self, task_id: int, user_id: int, status: str) -> bool:
    """Обновление статуса задачи"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Если задача завершена, устанавливаем дату завершения
            if status == 'completed':
                cursor.execute('''
                    UPDATE tasks 
                    SET status = ?, completed_date = CURRENT_TIMESTAMP 
                    WHERE task_id = ? AND user_id = ?
                ''', (status, task_id, user_id))
            else:
                cursor.execute('''
                    UPDATE tasks 
                    SET status = ?, completed_date = NULL 
                    WHERE task_id = ? AND user_id = ?
                ''', (status, task_id, user_id))
            
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error updating task status: {e}")
        return False

    # Методы для работы с календарными событиями
    def create_calendar_event(self, user_id: int, event_title: str, start_datetime: str,
                         event_description: str = None, event_type: str = 'custom',
                         end_datetime: str = None, is_all_day: bool = False,
                         reminder_minutes: int = 15) -> bool:
    """Создание календарного события"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO calendar_events 
                (user_id, event_title, event_description, event_type, start_datetime,
                 end_datetime, is_all_day, reminder_minutes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, event_title, event_description, event_type, start_datetime,
                  end_datetime, is_all_day, reminder_minutes))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error creating calendar event: {e}")
        return False
    
    def get_user_events(self, user_id: int, start_date: str = None, end_date: str = None) -> List[Dict]:
    """Получение событий пользователя"""
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM calendar_events WHERE user_id = ?'
        params = [user_id]
        
        if start_date:
            query += ' AND date(start_datetime) >= ?'
            params.append(start_date)
        
        if end_date:
            query += ' AND date(start_datetime) <= ?'
            params.append(end_date)
        
        query += ' ORDER BY start_datetime ASC'
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def create_event(self, user_id: int, event_title: str, event_description: str = None,
                event_type: str = 'custom', start_datetime: str = None,
                reminder_minutes: int = None) -> bool:
    """Создание события (алиас для create_calendar_event)"""
    return self.create_calendar_event(
        user_id=user_id,
        event_title=event_title,
        event_description=event_description,
        event_type=event_type,
        start_datetime=start_datetime,
        reminder_minutes=reminder_minutes
    )
    
    def complete_event(self, event_id: int, user_id: int) -> bool:
    """Отметка события как выполненного"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE calendar_events 
                SET status = 'completed' 
                WHERE event_id = ? AND user_id = ?
            ''', (event_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error completing event: {e}")
        return False
    
    def delete_event(self, event_id: int, user_id: int) -> bool:
    """Удаление события"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM calendar_events 
                WHERE event_id = ? AND user_id = ?
            ''', (event_id, user_id))
            conn.commit()
            return cursor.rowcount > 0
    except Exception as e:
        print(f"Error deleting event: {e}")
        return False

    # Методы для работы с чек-листом матерманайда
    def get_mastermind_checklist(self, user_id: int, checklist_date: str = None) -> Optional[Dict]:
    """Получение чек-листа матерманайда на дату"""
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if not checklist_date:
            checklist_date = date.today().isoformat()
        
        cursor.execute('''
            SELECT * FROM mastermind_checklist 
            WHERE user_id = ? AND checklist_date = ?
        ''', (user_id, checklist_date))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def update_mastermind_checklist(self, user_id: int, checklist_data: Dict, 
                               checklist_date: str = None) -> bool:
    """Обновление чек-листа матерманайда"""
    try:
        if not checklist_date:
            checklist_date = date.today().isoformat()
        
        # Подсчитываем процент выполнения
        total_items = 10  # Количество пунктов в чек-листе
        completed_items = sum(1 for key, value in checklist_data.items() 
                            if key != 'notes' and value)
        completion_percentage = int((completed_items / total_items) * 100)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO mastermind_checklist 
                (user_id, checklist_date, morning_routine, goal_review, learning_session,
                 networking_activity, reflection_time, gratitude_practice, skill_development,
                 creative_thinking, physical_activity, mindfulness_practice, notes, completion_percentage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, checklist_date,
                checklist_data.get('morning_routine', False),
                checklist_data.get('goal_review', False),
                checklist_data.get('learning_session', False),
                checklist_data.get('networking_activity', False),
                checklist_data.get('reflection_time', False),
                checklist_data.get('gratitude_practice', False),
                checklist_data.get('skill_development', False),
                checklist_data.get('creative_thinking', False),
                checklist_data.get('physical_activity', False),
                checklist_data.get('mindfulness_practice', False),
                checklist_data.get('notes', ''),
                completion_percentage
            ))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error updating mastermind checklist: {e}")
        return False

    # Методы для работы с биохакинг метриками
    def add_biohacking_metric(self, user_id: int, metric_type: str, metric_name: str,
                         metric_value: float, metric_unit: str = None,
                         measurement_date: str = None, notes: str = None) -> bool:
    """Добавление биохакинг метрики"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO biohacking_metrics 
                (user_id, metric_type, metric_name, metric_value, metric_unit,
                 measurement_date, notes)
                VALUES (?, ?, ?, ?, ?, COALESCE(?, CURRENT_DATE), ?)
            ''', (user_id, metric_type, metric_name, metric_value, metric_unit,
                  measurement_date, notes))
            conn.commit()
            return True
    except Exception as e:
        print(f"Error adding biohacking metric: {e}")
        return False
    
    def get_biohacking_metrics(self, user_id: int, metric_type: str = None, 
                          days: int = 30) -> List[Dict]:
    """Получение биохакинг метрик"""
    with sqlite3.connect(self.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = '''
            SELECT * FROM biohacking_metrics 
            WHERE user_id = ? AND measurement_date >= date('now', '-{} days')
        '''.format(days)
        params = [user_id]
        
        if metric_type:
            query += ' AND metric_type = ?'
            params.append(metric_type)
        
        query += ' ORDER BY measurement_date DESC, timestamp DESC'
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def get_setting(self, key: str) -> str:
    """Получение настройки (заглушка для совместимости)"""
    # Возвращаем значения по умолчанию для известных настроек
    defaults = {
        'report_time': '21:00',
        'timezone': 'Europe/Moscow'
    }
    return defaults.get(key, '')
    
    def get_reminder_settings(self, user_id: int) -> dict:
        """Получение настроек напоминаний пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT reminder_interval, start_time, end_time, is_enabled
            FROM reminder_settings 
            WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        if result:
            return {
                'interval': result[0],
                'start_time': result[1],
                'end_time': result[2],
                'is_enabled': bool(result[3])
            }
        else:
            # Возвращаем настройки по умолчанию
            return {
                'interval': 300,  # 5 минут
                'start_time': '07:00',
                'end_time': '22:00',
                'is_enabled': True
            }

    def update_reminder_settings(self, user_id: int, interval: int = None, 
                                start_time: str = None, end_time: str = None, 
                                is_enabled: bool = None) -> bool:
        """Обновление настроек напоминаний"""
        try:
            cursor = self.conn.cursor()
            
            # Проверяем, существуют ли настройки для пользователя
            cursor.execute('SELECT user_id FROM reminder_settings WHERE user_id = ?', (user_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Обновляем существующие настройки
                updates = []
                params = []
                
                if interval is not None:
                    updates.append('reminder_interval = ?')
                    params.append(interval)
                if start_time is not None:
                    updates.append('start_time = ?')
                    params.append(start_time)
                if end_time is not None:
                    updates.append('end_time = ?')
                    params.append(end_time)
                if is_enabled is not None:
                    updates.append('is_enabled = ?')
                    params.append(is_enabled)
                
                if updates:
                    updates.append('updated_at = CURRENT_TIMESTAMP')
                    params.append(user_id)
                    
                    query = f'UPDATE reminder_settings SET {", ".join(updates)} WHERE user_id = ?'
                    cursor.execute(query, params)
            else:
                # Создаем новые настройки
                cursor.execute('''
                    INSERT INTO reminder_settings (user_id, reminder_interval, start_time, end_time, is_enabled)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    interval or 300,
                    start_time or '07:00',
                    end_time or '22:00',
                    is_enabled if is_enabled is not None else True
                ))
            
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating reminder settings: {e}")
            return False

    def create_reminder_settings_table(self):
        """Создание таблицы настроек напоминаний"""
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminder_settings (
                user_id INTEGER PRIMARY KEY,
                reminder_interval INTEGER DEFAULT 300,
                start_time TEXT DEFAULT '07:00',
                end_time TEXT DEFAULT '22:00',
                is_enabled BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        self.conn.commit()

    def set_setting(self, key: str, value: str) -> bool:
        """Установка настройки (заглушка для совместимости)"""
        return True


# Создаем глобальный экземпляр базы данных для обратной совместимости
db = Database()

# Добавляем методы для работы с настройками напоминаний
def create_reminder_settings_table():
    """Создание таблицы настроек напоминаний"""
    cursor = db.conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reminder_settings (
        user_id INTEGER PRIMARY KEY,
        reminder_interval INTEGER DEFAULT 300,  -- интервал в секундах (300 = 5 минут)
        start_time TEXT DEFAULT '07:00',  -- время начала напоминаний
        end_time TEXT DEFAULT '22:00',    -- время окончания напоминаний
        is_enabled BOOLEAN DEFAULT TRUE,  -- включены ли напоминания
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )
    ''')
    db.conn.commit()

def get_reminder_settings(user_id: int) -> dict:
    """Получение настроек напоминаний пользователя"""
    cursor = db.conn.cursor()
    cursor.execute('''
        SELECT reminder_interval, start_time, end_time, is_enabled
        FROM reminder_settings 
        WHERE user_id = ?
    ''', (user_id,))
    
    result = cursor.fetchone()
    if result:
        return {
            'interval': result[0],
            'start_time': result[1],
            'end_time': result[2],
            'is_enabled': bool(result[3])
        }
    else:
        # Возвращаем настройки по умолчанию
        return {
            'interval': 300,  # 5 минут
            'start_time': '07:00',
            'end_time': '22:00',
            'is_enabled': True
        }

    def update_reminder_settings(self, user_id: int, interval: int = None, 
                            start_time: str = None, end_time: str = None, 
                            is_enabled: bool = None) -> bool:
    """Обновление настроек напоминаний"""
    try:
        cursor = self.conn.cursor()
        
        # Проверяем, существуют ли настройки для пользователя
        cursor.execute('SELECT user_id FROM reminder_settings WHERE user_id = ?', (user_id,))
        exists = cursor.fetchone()
        
        if exists:
            # Обновляем существующие настройки
            updates = []
            params = []
            
            if interval is not None:
                updates.append('reminder_interval = ?')
                params.append(interval)
            if start_time is not None:
                updates.append('start_time = ?')
                params.append(start_time)
            if end_time is not None:
                updates.append('end_time = ?')
                params.append(end_time)
            if is_enabled is not None:
                updates.append('is_enabled = ?')
                params.append(is_enabled)
            
            if updates:
                updates.append('updated_at = CURRENT_TIMESTAMP')
                params.append(user_id)
                
                query = f'UPDATE reminder_settings SET {", ".join(updates)} WHERE user_id = ?'
                cursor.execute(query, params)
        else:
            # Создаем новые настройки
            cursor.execute('''
                INSERT INTO reminder_settings (user_id, reminder_interval, start_time, end_time, is_enabled)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_id,
                interval or 300,
                start_time or '07:00',
                end_time or '22:00',
                is_enabled if is_enabled is not None else True
            ))
        
        self.conn.commit()
        return True
    except Exception as e:
        print(f"Error updating reminder settings: {e}")
        return False

