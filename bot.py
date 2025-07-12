import os
import openai
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

logging.basicConfig(level=logging.INFO)

# Load env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_PATH = os.getenv("GOOGLE_SHEETS_CREDS")

# OpenAI
openai.api_key = OPENAI_API_KEY

# Telegram bot init
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Google Sheets init
gscope = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_PATH, gscope)
client = gspread.authorize(creds)
main_sheet = client.open_by_key(SPREADSHEET_ID)

# Worksheets
onboard_ws = main_sheet.worksheet("Onboarding")
participants_ws = main_sheet.worksheet("Participants")

# FSM States
class Onboarding(StatesGroup):
    step = State()  # track progress
    name = State()
    surname = State()
    about = State()
    product = State()
    cases = State()
    why_net = State()
    values = State()
    goals = State()
    lifestyle = State()
    social = State()

# Main menu keyboard
menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("📁 Меню"), KeyboardButton("🤝 Партнеры")],
        [KeyboardButton("🎯 Мои цели")],
        [KeyboardButton("🆔 Визитка"), KeyboardButton("🎓 Обучение")],
        [KeyboardButton("🌐 Нетворкинг")]
    ], resize_keyboard=True
)

# Start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # send 4 images (IDs or URLs)
    for img in ["img1.jpg","img2.jpg","img3.jpg","img4.jpg"]:
        await bot.send_photo(message.chat.id, img)
    # greet
    full_name = message.from_user.full_name
    text = f"Здравствуй, {full_name}!\nХочешь заполнить визитку?"
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Да", callback_data="vb_yes"),
        InlineKeyboardButton("❌ Нет", callback_data="vb_no")
    )
    await message.answer(text, reply_markup=kb)

@dp.callback_query(lambda c: c.data in ["vb_yes","vb_no"])
async def process_vb_choice(c: CallbackQuery, state: FSMContext):
    await c.answer()
    if c.data == "vb_no":
        await c.message.answer("Главное меню:", reply_markup=menu_kb)
    else:
        # start onboarding
        await c.message.answer(f"1/10. Как тебя зовут?")
        await state.update_data(step=1)
        await Onboarding.name.set()

# Onboarding handlers with progress
async def ask_next(message: types.Message, state: FSMContext, next_state: State, prompt: str):
    data = await state.get_data()
    step = data.get("step", 0)
    step += 1
    await state.update_data(step=step)
    await message.answer(f"{step}/10. {prompt}")
    await next_state.set()

@dp.message(Onboarding.name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await ask_next(message, state, Onboarding.surname, "Введи фамилию:")

@dp.message(Onboarding.surname)
async def process_surname(message: types.Message, state: FSMContext):
    await state.update_data(surname=message.text)
    await ask_next(message, state, Onboarding.about, "Расскажи о себе, чем занимаешься:")

@dp.message(Onboarding.about)
async def process_about(message: types.Message, state: FSMContext):
    await state.update_data(about=message.text)
    await ask_next(message, state, Onboarding.product, "Есть ли у тебя свой продукт? Если да, какой:")

@dp.message(Onboarding.product)
async def process_product(message: types.Message, state: FSMContext):
    await state.update_data(product=message.text)
    await ask_next(message, state, Onboarding.cases, "Опиши свои лучшие кейсы:")

@dp.message(Onboarding.cases)
async def process_cases(message: types.Message, state: FSMContext):
    await state.update_data(cases=message.text)
    await ask_next(message, state, Onboarding.why_net, "Зачем тебе нетворкинг?:")

@dp.message(Onboarding.why_net)
async def process_why(message: types.Message, state: FSMContext):
    await state.update_data(why_net=message.text)
    await ask_next(message, state, Onboarding.values, "Топ-3 твоих жизненных ценностей:")

@dp.message(Onboarding.values)
async def process_values(message: types.Message, state: FSMContext):
    await state.update_data(values=message.text)
    await ask_next(message, state, Onboarding.goals, "Какие цели на ближайший год?")

@dp.message(Onboarding.goals)
async def process_goals(message: types.Message, state: FSMContext):
    await state.update_data(goals=message.text)
    await ask_next(message, state, Onboarding.lifestyle, "Какой образ жизни ведёшь? (спорт, йога...)")

@dp.message(Onboarding.lifestyle)
async def process_lifestyle(message: types.Message, state: FSMContext):
    await state.update_data(lifestyle=message.text)
    await ask_next(message, state, Onboarding.social, "Ссылка на Instagram (или соцсеть):")

@dp.message(Onboarding.social)
async def process_social(message: types.Message, state: FSMContext):
    await state.update_data(social=message.text)
    data = await state.get_data()
    # call GPT for card generation
    prompt = ("Сформируй визитку в Markdown по данным: " + str(data))
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role":"system","content":"Ты делаешь визитку."},
                  {"role":"user","content":prompt}]
    )
    card = resp.choices[0].message.content
    await message.answer(card, parse_mode="Markdown")
    # save raw data
    participants_ws.append_row([message.from_user.id, message.from_user.username] + 
                                [data[k] for k in ["name","surname","about","product","cases","why_net","values","goals","lifestyle","social"]] +
                                [datetime.utcnow().isoformat()])
    # show management buttons
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💾 Сохранить", callback_data="save_card"),
        InlineKeyboardButton("🔄 Перегенерировать", callback_data="regen_card")
    )
    kb.add(
        InlineKeyboardButton("✏️ Изменить", callback_data="edit_card"),
        InlineKeyboardButton("🔙 Меню", callback_data="menu")
    )
    await message.answer("Что дальше?", reply_markup=kb)
    await state.clear()

# Worksheets for categories/history (ensure these sheets exist)
categories_ws = main_sheet.worksheet("Categories")

# Callback handlers for card management
@dp.callback_query(lambda c: c.data == "save_card")
async def handle_save_card(c: CallbackQuery):
    await c.answer()
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("👤 Коуч", callback_data="cat:Коуч"),
        InlineKeyboardButton("⚡ Энергопрактик", callback_data="cat:Энергопрактик"),
        InlineKeyboardButton("🧠 Психолог", callback_data="cat:Психолог")
    )
    await c.message.answer("Выбери категорию для своей визитки (можно несколько):", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("cat:"))
async def handle_category_select(c: CallbackQuery):
    await c.answer()
    category = c.data.split(':',1)[1]
    user = c.from_user
    # save category selection
    categories_ws.append_row([
        user.id,
        user.username,
        category,
        datetime.utcnow().isoformat()
    ])
    await c.message.answer(f"Категория '{category}' сохранена!")
    await c.message.answer("Главное меню:", reply_markup=menu_kb)

@dp.callback_query(lambda c: c.data == "regen_card")
async def handle_regen_card(c: CallbackQuery):
    await c.answer()
    await c.message.answer("⚙️ Функция перегенерации визитки в разработке.")
    await c.message.answer("Главное меню:", reply_markup=menu_kb)

@dp.callback_query(lambda c: c.data == "edit_card")
async def handle_edit_card(c: CallbackQuery):
    await c.answer()
    await c.message.answer("✏️ Редактирование описания визитки в разработке.")
    await c.message.answer("Главное меню:", reply_markup=menu_kb)

@dp.callback_query(lambda c: c.data == "menu")
async def handle_menu(c: CallbackQuery):
    await c.answer()
    await c.message.answer("Главное меню:", reply_markup=menu_kb)


if __name__ == "__main__":
    dp.run_polling(bot)
```
