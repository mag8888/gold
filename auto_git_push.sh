#!/bin/bash

# Автоматический push в Git каждый час
# Скрипт для резервного копирования изменений

cd /home/ubuntu/gold

# Логирование
LOG_FILE="/home/ubuntu/gold/git_auto_push.log"
echo "$(date): Starting auto push..." >> $LOG_FILE

# Проверяем есть ли изменения (включая untracked файлы)
if git diff --quiet && git diff --cached --quiet && [ -z "$(git ls-files --others --exclude-standard)" ]; then
    echo "$(date): No changes to commit" >> $LOG_FILE
    exit 0
fi

# Добавляем все измененные файлы (кроме исключенных в .gitignore)
git add .

# Создаем коммит с временной меткой
COMMIT_MSG="Auto backup: $(date '+%Y-%m-%d %H:%M:%S')

- Automatic hourly backup
- Database updates and logs
- Bot state preservation"

git commit -m "$COMMIT_MSG"

# Пушим в репозиторий
if git push origin main; then
    echo "$(date): Successfully pushed to Git" >> $LOG_FILE
else
    echo "$(date): Failed to push to Git" >> $LOG_FILE
    exit 1
fi

echo "$(date): Auto push completed" >> $LOG_FILE

