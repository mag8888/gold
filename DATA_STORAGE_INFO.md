# Информация о хранении данных бота AlteriA

## 📍 Расположение данных

**Основная директория:** `/home/ubuntu/gold/`

### 🗄️ База данных SQLite
**Файл:** `bot_database.db` (48 KB)
**Путь:** `/home/ubuntu/gold/bot_database.db`

## 📊 Структура базы данных

### 1. **USERS** (1 запись)
Основная информация о пользователях:
- `user_id` - ID пользователя Telegram
- `first_name`, `last_name`, `username` - Личные данные
- `status` - Статус пользователя
- `join_date` - Дата регистрации
- `onboarding_completed` - Завершен ли онбординг
- `referrer_id`, `referral_code` - Реферальная система

### 2. **PROFILES** (0 записей)
Профили пользователей (визитки):
- `user_id` - Связь с пользователем
- `bio` - О себе
- `product_info` - Информация о продукте
- `case_studies` - Кейсы
- `networking_motive` - Мотивация для нетворкинга
- `life_values` - Жизненные ценности
- `lifestyle` - Образ жизни
- `social_link` - Социальные сети
- `category` - Категория
- `generated_card` - Сгенерированная визитка

### 3. **GOALS** (1 запись)
Цели пользователей:
- `goal_id` - ID цели
- `user_id` - Пользователь
- `goal_text` - Текст цели
- `goal_type` - Тип (daily/monthly)
- `status` - Статус выполнения
- `progress_data` - Данные прогресса
- `created_date`, `due_date`, `completed_date` - Даты

### 4. **REFERRALS** (0 записей)
Реферальная система:
- `referral_id` - ID реферала
- `referrer_user_id` - Кто пригласил
- `referred_user_id` - Кого пригласили
- `timestamp` - Время
- `earnings` - Заработок

### 5. **SETTINGS** (4 записи)
Настройки бота:
- `setting_key` - Ключ настройки
- `setting_value` - Значение
- `updated_at` - Время обновления

### 6. **PARTNER_CATEGORIES** (3 записи)
Категории партнеров:
- `category_id` - ID категории
- `category_name` - Название
- `category_emoji` - Эмодзи
- `is_active` - Активна ли

## 📁 Другие файлы данных

### Конфигурация
- **`.env`** - Переменные окружения (токены, ключи)
- **`order-arctur-c958d1d51d7e.json`** - Google Sheets credentials

### Логи
- **Systemd логи:** `sudo journalctl -u telegram-bot`
- **Путь к логам:** `/var/log/journal/`

### Кэш Python
- **`__pycache__/`** - Скомпилированные Python файлы

## 🔧 Управление данными

### Просмотр данных
```bash
# Подключение к базе
cd /home/ubuntu/gold
sqlite3 bot_database.db

# Просмотр пользователей
SELECT * FROM users;

# Просмотр целей
SELECT * FROM goals;
```

### Резервное копирование
```bash
# Создание бэкапа
cp /home/ubuntu/gold/bot_database.db /home/ubuntu/backup_$(date +%Y%m%d_%H%M%S).db

# Архив всего проекта
tar -czf /home/ubuntu/alteria_backup_$(date +%Y%m%d_%H%M%S).tar.gz /home/ubuntu/gold/
```

### Очистка данных
```bash
# Очистка таблицы (осторожно!)
sqlite3 /home/ubuntu/gold/bot_database.db "DELETE FROM goals;"

# Полная очистка базы
rm /home/ubuntu/gold/bot_database.db
# База пересоздастся при следующем запуске бота
```

## 📈 Мониторинг

### Размер базы данных
```bash
du -h /home/ubuntu/gold/bot_database.db
```

### Количество записей
```bash
cd /home/ubuntu/gold
python -c "
import sqlite3
conn = sqlite3.connect('bot_database.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM users')
print(f'Пользователей: {cursor.fetchone()[0]}')
cursor.execute('SELECT COUNT(*) FROM goals')
print(f'Целей: {cursor.fetchone()[0]}')
conn.close()
"
```

## 🔒 Безопасность

### Права доступа
```bash
# Текущие права
ls -la /home/ubuntu/gold/bot_database.db
# -rw-r--r-- 1 ubuntu ubuntu

# Ограничение доступа (рекомендуется)
chmod 600 /home/ubuntu/gold/bot_database.db
```

### Шифрование
- База данных SQLite не зашифрована
- Для продакшена рекомендуется использовать SQLCipher
- Или перейти на PostgreSQL с шифрованием

## 📍 Итого

**Все данные бота хранятся в:**
- 🗄️ **SQLite база:** `/home/ubuntu/gold/bot_database.db` (48 KB)
- ⚙️ **Конфигурация:** `/home/ubuntu/gold/.env`
- 📝 **Логи:** `journalctl -u telegram-bot`

**Текущее состояние:**
- ✅ 1 пользователь зарегистрирован
- ✅ 1 цель создана
- ✅ 4 настройки сохранены
- ✅ 3 категории партнеров настроены

---

**Обновлено:** 13 июля 2025

