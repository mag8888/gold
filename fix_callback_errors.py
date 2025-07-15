#!/usr/bin/env python3
"""
Скрипт для исправления всех callback.answer() в боте
Добавляет обработку ошибок для устаревших callback-запросов
"""

import re

def fix_callback_answers():
    """Исправляет все callback.answer() в bot.py"""
    
    # Читаем файл
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Паттерн для поиска await callback.answer()
    pattern = r'(\s+)await callback\.answer\(\)'
    
    # Замена на версию с обработкой ошибок
    replacement = r'''\1try:
\1    await callback.answer()
\1except Exception as e:
\1    # Игнорируем ошибки устаревших callback-запросов
\1    logger.warning(f"Callback answer error (ignored): {e}")'''
    
    # Выполняем замену
    new_content = re.sub(pattern, replacement, content)
    
    # Также исправляем случаи с параметрами
    pattern2 = r'(\s+)await callback\.answer\(([^)]+)\)'
    replacement2 = r'''\1try:
\1    await callback.answer(\2)
\1except Exception as e:
\1    # Игнорируем ошибки устаревших callback-запросов
\1    logger.warning(f"Callback answer error (ignored): {e}")'''
    
    new_content = re.sub(pattern2, replacement2, new_content)
    
    # Записываем обратно
    with open('bot.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✅ Все callback.answer() исправлены!")

if __name__ == "__main__":
    fix_callback_answers()

