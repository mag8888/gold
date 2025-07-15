#!/usr/bin/env python3
"""
Безопасная обертка для callback.answer() 
Добавляет в начало bot.py функцию-обертку
"""

def add_safe_callback_wrapper():
    """Добавляет безопасную обертку для callback в bot.py"""
    
    # Читаем файл
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Функция-обертка
    wrapper_code = '''
async def safe_callback_answer(callback, text=None):
    """Безопасная обертка для callback.answer() с обработкой ошибок"""
    try:
        if text:
            await callback.answer(text)
        else:
            await callback.answer()
    except Exception as e:
        # Игнорируем ошибки устаревших callback-запросов
        logger.warning(f"Callback answer error (ignored): {e}")

'''
    
    # Ищем место после импортов для вставки функции
    import_end = content.find('# Константы')
    if import_end == -1:
        import_end = content.find('# Настройка логирования')
    
    if import_end != -1:
        # Вставляем функцию после импортов
        new_content = content[:import_end] + wrapper_code + content[import_end:]
        
        # Записываем обратно
        with open('bot.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print("✅ Безопасная обертка для callback добавлена!")
        print("📝 Теперь используйте: await safe_callback_answer(callback, 'текст')")
    else:
        print("❌ Не удалось найти место для вставки функции")

if __name__ == "__main__":
    add_safe_callback_wrapper()

