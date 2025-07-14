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
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    bio TEXT,
                    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE,
                    referral_code TEXT UNIQUE,
                    referred_by INTEGER,
                    FOREIGN KEY (referred_by) REFERENCES users (user_id)
                )
            ''')
            
            # Таблица привычек
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS habits (
                    habit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    habit_name TEXT NOT NULL,
                    habit_description TEXT,
                    target_frequency INTEGER DEFAULT 1,
                    frequency_type TEXT CHECK(frequency_type IN ('daily', 'weekly')) DEFAULT 'daily',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_date DATE DEFAULT CURRENT_DATE,
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
            
            # Таблица настроек напоминаний
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
            
            conn.commit()

    @property
    def conn(self):
        """Получение соединения с базой данных"""
        return sqlite3.connect(self.db_path)

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

    # Остальные методы из оригинального файла
    def add_user(self, user_id: int, username: str = None, first_name: str = None, 
                 last_name: str = None, referral_code: str = None, referred_by: int = None) -> bool:
        """Добавление нового пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO users (user_id, username, first_name, last_name, referral_code, referred_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, username, first_name, last_name, referral_code, referred_by))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            print(f"Error adding user: {e}")
            return False

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, first_name, last_name, bio, registration_date, 
                           is_active, referral_code, referred_by
                    FROM users WHERE user_id = ?
                ''', (user_id,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'user_id': result[0],
                        'username': result[1],
                        'first_name': result[2],
                        'last_name': result[3],
                        'bio': result[4],
                        'registration_date': result[5],
                        'is_active': result[6],
                        'referral_code': result[7],
                        'referred_by': result[8]
                    }
                return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None

    def get_referral_stats(self, user_id: int) -> Dict:
        """Получение статистики рефералов"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем реферальный код пользователя
                cursor.execute('SELECT referral_code FROM users WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                referral_code = result[0] if result else f"ref_{user_id}"
                
                # Считаем количество рефералов
                cursor.execute('''
                    SELECT COUNT(*), COALESCE(SUM(earnings), 0)
                    FROM referrals WHERE referrer_user_id = ?
                ''', (user_id,))
                
                count_result = cursor.fetchone()
                referral_count = count_result[0] if count_result else 0
                total_earnings = count_result[1] if count_result else 0.0
                
                return {
                    'referral_code': referral_code,
                    'referral_count': referral_count,
                    'total_earnings': total_earnings
                }
        except Exception as e:
            print(f"Error getting referral stats: {e}")
            return {
                'referral_code': f"ref_{user_id}",
                'referral_count': 0,
                'total_earnings': 0.0
            }

    def get_user_by_referral_code(self, referral_code: str) -> Optional[Dict]:
        """Получение пользователя по реферальному коду"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, username, first_name, last_name, referral_code 
                    FROM users WHERE referral_code = ?
                ''', (referral_code,))
                
                result = cursor.fetchone()
                if result:
                    return {
                        'user_id': result[0],
                        'username': result[1],
                        'first_name': result[2],
                        'last_name': result[3],
                        'referral_code': result[4]
                    }
                return None
        except Exception as e:
            print(f"Error getting user by referral code: {e}")
            return None

    def get_user_referrals(self, user_id: int) -> List[Dict]:
        """Получение списка рефералов пользователя с их данными"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        r.referral_id,
                        r.referred_user_id,
                        r.timestamp,
                        r.earnings,
                        u.username,
                        u.first_name,
                        u.last_name
                    FROM referrals r
                    JOIN users u ON r.referred_user_id = u.user_id
                    WHERE r.referrer_user_id = ?
                    ORDER BY r.timestamp DESC
                ''', (user_id,))
                
                results = cursor.fetchall()
                referrals = []
                
                for row in results:
                    referrals.append({
                        'referral_id': row[0],
                        'user_id': row[1],
                        'timestamp': row[2],
                        'earnings': row[3],
                        'username': row[4],
                        'first_name': row[5],
                        'last_name': row[6],
                        'bio': None  # Пока нет колонки bio
                    })
                
                return referrals
        except Exception as e:
            print(f"Error getting user referrals: {e}")
            return []

    def get_all_users_with_habits(self) -> List[int]:
        """Получение всех пользователей, у которых есть активные привычки"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT user_id 
                    FROM habits 
                    WHERE is_active = 1
                ''')
                
                results = cursor.fetchall()
                return [row[0] for row in results]
        except Exception as e:
            print(f"Error getting users with habits: {e}")
            return []

    def add_habit(self, user_id: int, habit_name: str, habit_description: str = None, 
                  target_frequency: int = 1, frequency_type: str = 'daily') -> bool:
        """Добавление новой привычки"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO habits (user_id, habit_name, habit_description, habit_type, target_frequency)
                    VALUES (?, ?, ?, ?, ?)
                ''', (user_id, habit_name, habit_description, frequency_type, target_frequency))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error adding habit: {e}")
            return False

    def get_user_habits(self, user_id: int, active_only: bool = True) -> List[Dict]:
        """Получение привычек пользователя"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT habit_id, habit_name, habit_description, habit_type, 
                           target_frequency, is_active, created_date
                    FROM habits WHERE user_id = ?
                '''
                params = [user_id]
                
                if active_only:
                    query += ' AND is_active = 1'
                
                cursor.execute(query, params)
                results = cursor.fetchall()
                
                habits = []
                for result in results:
                    habits.append({
                        'habit_id': result[0],
                        'habit_name': result[1],
                        'habit_description': result[2],
                        'habit_type': result[3],
                        'target_frequency': result[4],
                        'is_active': result[5],
                        'created_date': result[6],
                        'user_id': user_id
                    })
                
                return habits
        except Exception as e:
            print(f"Error getting user habits: {e}")
            return []

    def log_habit_completion(self, habit_id: int, user_id: int, completed: bool = True, notes: str = None) -> bool:
        """Логирование выполнения привычки"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO habit_logs (habit_id, user_id, completed, notes)
                    VALUES (?, ?, ?, ?)
                ''', (habit_id, user_id, completed, notes))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error logging habit completion: {e}")
            return False

    def get_habit_stats(self, user_id: int, habit_id: int, days: int = 30, end_date=None) -> Dict:
        """Получение статистики по привычке"""
        try:
            from datetime import date, timedelta
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Получаем информацию о привычке
                cursor.execute('''
                    SELECT target_frequency FROM habits 
                    WHERE habit_id = ? AND user_id = ?
                ''', (habit_id, user_id))
                
                habit_info = cursor.fetchone()
                if not habit_info:
                    return {'completion_rate': 0, 'completed_count': 0, 'today_count': 0, 'period_days': days}
                
                target_frequency = habit_info[0]
                
                # Определяем конечную дату
                if end_date is None:
                    end_date = date.today()
                elif isinstance(end_date, str):
                    end_date = date.fromisoformat(end_date)
                
                start_date = end_date - timedelta(days=days-1)
                
                # Получаем количество выполнений за указанный период
                cursor.execute('''
                    SELECT COUNT(*) FROM habit_logs 
                    WHERE habit_id = ? AND user_id = ? AND completed = 1 
                    AND completion_date >= ? AND completion_date <= ?
                ''', (habit_id, user_id, start_date.isoformat(), end_date.isoformat()))
                
                completed_count = cursor.fetchone()[0]
                
                # Получаем количество выполнений за конечную дату (сегодня или указанную)
                cursor.execute('''
                    SELECT COUNT(*) FROM habit_logs 
                    WHERE habit_id = ? AND user_id = ? AND completed = 1 
                    AND completion_date = ?
                ''', (habit_id, user_id, end_date.isoformat()))
                
                today_count = cursor.fetchone()[0]
                
                # Рассчитываем процент выполнения
                expected_total = target_frequency * days
                completion_rate = (completed_count / expected_total * 100) if expected_total > 0 else 0
                
                return {
                    'completion_rate': completion_rate,
                    'completed_count': completed_count,
                    'today_count': today_count,
                    'period_days': days
                }
        except Exception as e:
            print(f"Error getting habit stats: {e}")
            return {
                'completion_rate': 0,
                'completed_count': 0,
                'today_count': 0,
                'period_days': days
            }

    def create_user(self, user_id: int, first_name: str = None, last_name: str = None, 
                   username: str = None, referrer_id: int = None) -> bool:
        """Создание нового пользователя (алиас для add_user)"""
        import secrets
        import string
        
        # Генерируем реферальный код
        referral_code = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
        
        return self.add_user(user_id, username, first_name, last_name, referral_code, referrer_id)

    def get_profile(self, user_id: int) -> Optional[Dict]:
        """Получение профиля пользователя (алиас для get_user)"""
        return self.get_user(user_id)

    def create_habit(self, user_id: int, habit_name: str, habit_description: str = None, 
                    habit_type: str = 'daily', target_frequency: int = 1) -> bool:
        """Создание новой привычки (алиас для add_habit)"""
        return self.add_habit(
            user_id=user_id,
            habit_name=habit_name, 
            habit_description=habit_description,
            target_frequency=target_frequency,
            frequency_type=habit_type
        )

    def reset_daily_habits_counters(self, user_id: int) -> bool:
        """Сброс ежедневных счетчиков привычек для пользователя"""
        try:
            # В нашей системе счетчики не хранятся отдельно, 
            # а рассчитываются на основе habit_logs
            # Поэтому просто возвращаем True, так как новый день автоматически
            # означает новые записи в habit_logs
            return True
        except Exception as e:
            print(f"Error resetting daily habits counters for user {user_id}: {e}")
            return False

    def get_setting(self, key: str) -> str:
        """Получение настройки из базы данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT setting_value FROM settings WHERE setting_key = ?', (key,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Error getting setting {key}: {e}")
            return None

# Создаем глобальный экземпляр базы данных для обратной совместимости
db = Database()