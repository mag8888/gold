# AlteriA Bot

Telegram бот для управления привычками и целями с реферальной системой.

## Функции

### 🎯 Управление привычками
- Создание и отслеживание ежедневных привычек
- Система напоминаний с настраиваемыми интервалами
- Статистика выполнения с процентами
- Ежедневные отчеты в 00:00

### 🤝 Реферальная система
- Персональные реферальные ссылки
- Отслеживание приглашенных пользователей
- Статистика заработка
- Просмотр списка рефералов

### 📊 Аналитика
- Детальная статистика по привычкам
- Процент выполнения за период
- Ежедневные отчеты с мотивационными сообщениями

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd gold
```

2. Создайте виртуальное окружение:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Настройте конфигурацию:
```bash
cp config.py.example config.py
# Отредактируйте config.py с вашими настройками
```

5. Запустите бота:
```bash
python3 bot.py
```

## Структура проекта

- `bot.py` - Основной файл бота
- `database.py` - Работа с базой данных SQLite
- `scheduler.py` - Планировщик задач и отчетов
- `reminder_system.py` - Система напоминаний
- `google_sheets.py` - Интеграция с Google Sheets

## Конфигурация

Создайте файл `config.py` на основе `config.py.example`:

```python
BOT_TOKEN = "your_bot_token"
CORRECT_BOT_USERNAME = "your_bot_username"
```

## Особенности

### Ежедневные отчеты
Бот автоматически отправляет отчеты в 00:00 с информацией о выполнении привычек:
- Список всех привычек с отметками выполнения
- Процент выполнения за день
- Мотивационные сообщения

### Система напоминаний
- Настраиваемые интервалы (5 минут, 20 минут, 1 час)
- Рабочие часы (например, с 7:00 до 22:00)
- Автоматическая остановка при выполнении всех привычек

### База данных
Использует SQLite с таблицами:
- `users` - пользователи
- `habits` - привычки
- `habit_logs` - логи выполнения
- `referrals` - реферальная система
- `settings` - настройки системы

## Разработка

Для разработки используйте тестовые файлы:
- `test_*.py` - различные тесты функционала
- `debug_*.py` - отладочные скрипты

## Лицензия

MIT License

