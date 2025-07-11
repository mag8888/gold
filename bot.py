import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Загрузка настроек
load_dotenv()

# Инициализация бота
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# Подключение к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(os.getenv("GOOGLE_SHEETS_CREDS"), scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(os.getenv("SPREADSHEET_ID")).sheet1

# Команда /start
@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Бот работает! Отправь /add [текст] для записи в таблицу.")

# Команда /add
@dp.message(Command("add"))
async def add_data(message: types.Message):
    text = message.text.replace("/add", "").strip()
    sheet.append_row([message.from_user.username, text])
    await message.answer(f"Добавлено в таблицу: '{text}'")

if __name__ == "__main__":
    dp.run_polling(bot)