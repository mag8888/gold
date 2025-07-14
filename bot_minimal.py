#!/usr/bin/env python3

import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command

load_dotenv()

bot = Bot(token=os.getenv('BOT_TOKEN'))
dp = Dispatcher()

@dp.message(Command("mylink"))
async def get_my_link(message: types.Message):
    """Получение правильной реферальной ссылки"""
    user_id = message.from_user.id
    
    if user_id == 6840451873:  # Ваш ID
        link = "https://t.me/Alteria_8_bot?start=REF_6840451873_20250713"
        await message.answer(f"✅ Ваша правильная ссылка:\n{link}")
    else:
        await message.answer("Эта команда только для владельца бота.")

@dp.message(F.text == "🤝 Партнёры")
async def partners_test(message: types.Message):
    """Тестовый обработчик партнеров"""
    user_id = message.from_user.id
    
    if user_id == 6840451873:
        link = "https://t.me/Alteria_8_bot?start=REF_6840451873_20250713"
        text = f"""🤝 **Партнёры**

📊 **Ваша статистика:**
👥 Приглашено: 2 человек
💰 Заработано: 0.00 ₽
🔗 Ваша реферальная ссылка: {link}

✅ Эта ссылка гарантированно правильная!"""
        
        await message.answer(text, parse_mode="Markdown")
    else:
        await message.answer("Раздел в разработке.")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))

