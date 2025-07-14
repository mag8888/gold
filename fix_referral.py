#!/usr/bin/env python3
"""
Скрипт для исправления реферальной ссылки
"""

import sqlite3

def fix_referral_code():
    """Исправление реферального кода"""
    print("🔧 Исправление реферального кода...")
    
    # Подключаемся к базе данных
    with sqlite3.connect('bot_database.db') as conn:
        cursor = conn.cursor()
        
        # Обновляем referral_code для пользователя
        user_id = 6840451873
        correct_code = "REF_6840451873_20250713"
        
        cursor.execute('''
            UPDATE users 
            SET referral_code = ? 
            WHERE user_id = ?
        ''', (correct_code, user_id))
        
        conn.commit()
        
        # Проверяем результат
        cursor.execute('SELECT referral_code FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        
        if result:
            print(f"✅ Referral code обновлен: {result[0]}")
            print(f"✅ Правильная ссылка: https://t.me/Alteria_8_bot?start={result[0]}")
        else:
            print("❌ Пользователь не найден")

if __name__ == "__main__":
    fix_referral_code()

