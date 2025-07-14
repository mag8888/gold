#!/bin/bash

# Скрипт развертывания AlteriA Club Telegram Bot

set -e

echo "🚀 Начинаем развертывание AlteriA Club Telegram Bot..."

# Проверка прав sudo
if [ "$EUID" -ne 0 ]; then
    echo "❌ Запустите скрипт с правами sudo: sudo ./deploy.sh"
    exit 1
fi

# Получаем имя пользователя, который запустил sudo
REAL_USER=${SUDO_USER:-$USER}
USER_HOME=$(eval echo ~$REAL_USER)
PROJECT_DIR="$USER_HOME/gold"

echo "📁 Рабочая директория: $PROJECT_DIR"
echo "👤 Пользователь: $REAL_USER"

# Проверка существования проекта
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Директория проекта не найдена: $PROJECT_DIR"
    exit 1
fi

cd "$PROJECT_DIR"

# Проверка файлов
echo "🔍 Проверка файлов проекта..."
required_files=("bot.py" "database.py" "requirements.txt" ".env")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "❌ Не найден файл: $file"
        exit 1
    fi
done

echo "✅ Все необходимые файлы найдены"

# Установка зависимостей Python
echo "📦 Проверка виртуального окружения..."
if [ ! -d "venv" ]; then
    echo "🔧 Создание виртуального окружения..."
    sudo -u $REAL_USER python3 -m venv venv
fi

echo "📦 Установка зависимостей..."
sudo -u $REAL_USER bash -c "source venv/bin/activate && pip install -r requirements.txt"

# Проверка импортов
echo "🧪 Тестирование импортов..."
sudo -u $REAL_USER bash -c "cd $PROJECT_DIR && source venv/bin/activate && python -c 'import bot; print(\"Импорты успешны\")'"

# Настройка systemd сервиса
echo "⚙️ Настройка systemd сервиса..."

# Создание unit файла с правильными путями
cat > /etc/systemd/system/telegram-bot.service << EOF
[Unit]
Description=AlteriA Club Telegram Bot
After=network.target

[Service]
Type=simple
User=$REAL_USER
WorkingDirectory=$PROJECT_DIR
EnvironmentFile=$PROJECT_DIR/.env
ExecStart=$PROJECT_DIR/venv/bin/python $PROJECT_DIR/bot.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd
echo "🔄 Перезагрузка systemd..."
systemctl daemon-reload

# Включение автозапуска
echo "🔧 Включение автозапуска..."
systemctl enable telegram-bot

# Остановка старого сервиса (если запущен)
if systemctl is-active --quiet telegram-bot; then
    echo "⏹️ Остановка старого сервиса..."
    systemctl stop telegram-bot
fi

# Запуск сервиса
echo "▶️ Запуск сервиса..."
systemctl start telegram-bot

# Проверка статуса
sleep 3
if systemctl is-active --quiet telegram-bot; then
    echo "✅ Сервис успешно запущен!"
    echo ""
    echo "📊 Статус сервиса:"
    systemctl status telegram-bot --no-pager -l
    echo ""
    echo "📝 Для просмотра логов используйте:"
    echo "   sudo journalctl -u telegram-bot -f"
    echo ""
    echo "🎉 Развертывание завершено успешно!"
else
    echo "❌ Ошибка запуска сервиса!"
    echo "📝 Проверьте логи:"
    echo "   sudo journalctl -u telegram-bot -n 20"
    exit 1
fi

