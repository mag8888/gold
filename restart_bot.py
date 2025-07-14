#!/usr/bin/env python3

import os
import signal
import subprocess
import time
import psutil

def restart_bot():
    """Безопасный перезапуск бота"""
    print("🔄 Перезапуск бота...")
    
    # Находим процесс бота
    bot_process = None
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'bot.py' in ' '.join(proc.info['cmdline']):
                bot_process = proc
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    # Останавливаем старый процесс
    if bot_process:
        print(f"⏹️ Останавливаю процесс {bot_process.pid}")
        bot_process.terminate()
        
        # Ждем завершения
        try:
            bot_process.wait(timeout=5)
            print("✅ Процесс остановлен")
        except psutil.TimeoutExpired:
            print("⚠️ Принудительное завершение")
            bot_process.kill()
    
    # Запускаем новый процесс
    print("🚀 Запускаю новый процесс...")
    subprocess.Popen(['python3', 'bot.py'], 
                    stdout=subprocess.DEVNULL, 
                    stderr=subprocess.DEVNULL)
    
    time.sleep(2)
    
    # Проверяем запуск
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'bot.py' in ' '.join(proc.info['cmdline']):
                print(f"✅ Бот запущен! PID: {proc.pid}")
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    
    print("❌ Ошибка запуска бота")
    return False

if __name__ == "__main__":
    restart_bot()

