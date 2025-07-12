import os
import openai
import logging
from datetime import datetime
import random

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, ContentType
)
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Logging
logging.basicConfig(level=logging.INFO)

# Load environment
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
CREDS_PATH = os.getenv("GOOGLE_SHEETS_CREDS")

# OpenAI configuration
openai.api_key = OPENAI_API_KEY

# Telegram bot initialization
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Google Sheets initialization
gscope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_PATH, gscope)
client = gspread.authorize(creds)
main_sheet = client.open_by_key(SPREADSHEET_ID)

# Worksheets
onboard_ws = main_sheet.worksheet("Onboarding")
participants_ws = main_sheet.worksheet("Participants")
mentors_ws = main_sheet.worksheet("Mentors")
likes_ws = main_sheet.worksheet("MentorLikes")
tips_ws = main_sheet.worksheet("Tips")
tip_reactions_ws = main_sheet.worksheet("TipReactions")
referrals_ws = main_sheet.worksheet("Referrals")
journal_ws = main_sheet.worksheet("Journal")
quests_ws = main_sheet.worksheet("Quests")
quest_results_ws = main_sheet.worksheet("QuestResults")
support_ws = main_sheet.worksheet("SupportWheel")
audio_ws = main_sheet.worksheet("Audio")
events_ws = main_sheet.worksheet("Events")
categories_ws = main_sheet.worksheet("Categories")

# FSM States
class Onboarding(StatesGroup):
    step = State()
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

# Start command
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Send welcome images (replace with real media IDs or URLs)
    for img in ["img1.jpg", "img2.jpg", "img3.jpg", "img4.jpg"]:
        await bot.send_photo(message.chat.id, img)
    # Greet user
    full_name = message.from_user.full_name
    text = f"Здравствуй, {full_name}!\nХочешь заполнить визитку?"
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✅ Да", callback_data="vb_yes"),
        InlineKeyboardButton("❌ Нет", callback_data="vb_no")
    )
    await message.answer(text, reply_markup=kb)

@dp.callback_query(lambda c: c.data in ["vb_yes", "vb_no"] )
async def process_vb_choice(c: CallbackQuery, state: FSMContext):
    await c.answer()
    if c.data == "vb_no":
        await c.message.answer("Главное меню:", reply_markup=menu_kb)
    else:
        await c.message.answer("1/10. Как тебя зовут?")
        await state.update_data(step=1)
        await Onboarding.name.set()

# Helper to ask next question
async def ask_next(message: types.Message, state: FSMContext, next_state: State, prompt: str):
    data = await state.get_data()
    step = data.get("step", 0) + 1
    await state.update_data(step=step)
    await message.answer(f"{step}/10. {prompt}")
    await next_state.set()

# Onboarding handlers
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
async def process_why_net(message: types.Message, state: FSMContext):
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
    # Generate visit card via GPT
    prompt = "Сформируй визитку в Markdown по данным: " + str(data)
    resp = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role":"system","content":"Ты делаешь визитку."},
            {"role":"user","content":prompt}
        ]
    )
    card = resp.choices[0].message.content
    # Send card
    await message.answer(card, parse_mode="Markdown")
    # Save raw data
    participants_ws.append_row([
        message.from_user.id,
        message.from_user.username,
        data.get("name",""),
        data.get("surname",""),
        data.get("about",""),
        data.get("product",""),
        data.get("cases",""),
        data.get("why_net",""),
        data.get("values",""),
        data.get("goals",""),
        data.get("lifestyle",""),
        data.get("social",""),
        datetime.utcnow().isoformat()
    ])
    # Management buttons
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

# Mentor catalog
@dp.message(Command("mentors"))
async def cmd_mentors(message: types.Message):
    data = mentors_ws.get_all_records()
    if not data:
        return await message.answer("В каталоге пока нет наставников.")
    kb = InlineKeyboardMarkup(row_width=1)
    for r in data:
        kb.add(InlineKeyboardButton(f"{r['name']} ({r['category']})", callback_data=f"mentor:{r['mentor_id']}"))
    await message.answer("Выберите наставника:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("mentor:"))
async def process_mentor_choice(c: CallbackQuery):
    mid = int(c.data.split(":")[1])
    rec = next((r for r in mentors_ws.get_all_records() if r['mentor_id']==mid), None)
    if not rec:
        return await c.message.edit_text("Наставник не найден.")
    text = (f"👤 <b>{rec['name']}</b>\nКатегория: {rec['category']}\nОпыт: {rec['experience']}\n\n{rec['description']}")
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("👍 Нравится", callback_data=f"mentor_like:{mid}"),
        InlineKeyboardButton("💬 Отзыв", callback_data=f"mentor_review:{mid}")
    )
    kb.add(InlineKeyboardButton("Выбрать", callback_data=f"mentor_select:{mid}"))
    await c.message.edit_text(text, parse_mode="HTML", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("mentor_like:"))
async def process_mentor_like(c: CallbackQuery):
    mid = int(c.data.split(":")[1])
    likes_ws.append_row([c.from_user.username, mid, 'like', datetime.utcnow().isoformat()])
    await c.answer("Спасибо за лайк!")

@dp.callback_query(lambda c: c.data.startswith("mentor_review:"))
async def process_mentor_review(c: CallbackQuery, state: FSMContext):
    mid = int(c.data.split(":")[1])
    await state.update_data(review_mid=mid)
    await c.message.answer("Напишите ваш отзыв о наставнике:")
    await state.set_state(Onboarding.about)  # reuse state

# Tips
@dp.message(Command("tips"))
async def cmd_tips(message: types.Message):
    recs = tips_ws.get_all_records()
    if not recs:
        return await message.answer("Советов нет.")
    tip = random.choice(recs)
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("💾 Сохранить", callback_data=f"tip_save:{tip['tip_id']}"),
        InlineKeyboardButton("➡️ Отправить", callback_data=f"tip_send:{tip['tip_id']}"),
        InlineKeyboardButton("❤️", callback_data=f"tip_like:{tip['tip_id']}")
    )
    await message.answer(f"💡 Совет #{tip['tip_id']}: {tip['text']}", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("tip_"))
async def process_tip_action(c: CallbackQuery, state: FSMContext):
    action, sid = c.data.split(":")
    tid = int(sid)
    tip_reactions_ws.append_row([c.from_user.username, tid, action, datetime.utcnow().isoformat()])
    if action == 'tip_send':
        await state.update_data(pending_tip=tid)
        await c.message.answer("Кому отправить? Напиши username без @:")
    else:
        await c.answer("Сохранено", show_alert=True)

@dp.message(lambda m: True)
async def handle_tip_send(message: types.Message, state: FSMContext):
    data = await state.get_data()
    if 'pending_tip' in data:
        rec = next(r for r in tips_ws.get_all_records() if r['tip_id']==data['pending_tip'])
        target = message.text.strip().lstrip('@')
        try:
            await bot.send_message(target, f"💡 Совет от @{message.from_user.username}: {rec['text']}")
            await message.answer("Отправлено!")
        except:
            await message.answer("Ошибка! Проверьте username.")
        await state.clear()

# Referral
@dp.message(Command("ref"))
async def cmd_ref(message: types.Message):
    link = f"https://t.me/{(await bot.get_me()).username}?start={message.from_user.id}"
    await message.answer(f"Твоя реф. ссылка:\n{link}")

@dp.message(Command("start"))
async def cmd_start_ref(message: types.Message):
    args = message.get_args()
    if args.isdigit():
        ref = int(args)
        if ref != message.from_user.id:
            referrals_ws.append_row([ref, message.from_user.id, datetime.utcnow().isoformat()])

@dp.message(Command("refstats"))
async def cmd_refstats(message: types.Message):
    rows = referrals_ws.get_all_records()
    mine = [r for r in rows if r['referrer_id']==message.from_user.id]
    await message.answer(f"Приглашено: {len(mine)}")

# Participants
@dp.message(Command("register"))
async def cmd_register(message: types.Message):
    await message.answer("Заполни визитку через /start, пожалуйста.")

@dp.message(Command("find"))
async def cmd_find(message: types.Message):
    args = message.get_args().lower()
    if '=' not in args:
        return await message.answer("Используй `/find ключ=значение`.")
    key,val = args.split('=',1)
    allp = participants_ws.get_all_records()
    res = [p for p in allp if val in str(p.get(key,'')).lower()]
    if not res:
        return await message.answer("Не найдено.")
    msg = '\n'.join(f"👤 {p['name']} (@{p['username']})" for p in res[:10])
    await message.answer(msg)

# Journal
@dp.message(Command("journal"))
async def cmd_journal(message: types.Message):
    await message.answer("Что сделал сегодня? (текст/медиа)")
    await state.set_state(Onboarding.about)

@dp.message(lambda m: m.text or m.photo)
async def process_journal(message: types.Message):
    text = message.text or ''
    media = ''
    if message.photo:
        media = (await message.photo[-1].get_file()).file_path
    journal_ws.append_row([
        message.from_user.id, message.from_user.username,
        datetime.utcnow().date().isoformat(), text, media,
        datetime.utcnow().isoformat()
    ])
    await message.answer("Запись сохранена!")

@dp.message(Command("streak"))
async def cmd_streak(message: types.Message):
    rows = journal_ws.get_all_records()
    mine = [r for r in rows if r['user_id']==message.from_user.id]
    dates = sorted({r['date'] for r in mine}, reverse=True)
    streak = 0
    today = datetime.utcnow().date()
    from datetime import timedelta
    for i in range(len(dates)):
        if dates[i] == (today - timedelta(days=i)).isoformat():
            streak += 1
        else:
            break
    await message.answer(f"Серия: {streak} дней")

# Quest
@dp.message(Command("quest"))
async def cmd_quest(message: types.Message):
    q = random.choice(quests_ws.get_all_records())
    kb = InlineKeyboardMarkup().add(
        InlineKeyboardButton("Выполнил ✅", callback_data=f"quest_done:{q['quest_id']}")
    )
    await message.answer(f"🎯 {q['text']}\nНаграда: {q['reward']}", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("quest_done:"))
async def handle_quest_done(c: CallbackQuery):
    qid = int(c.data.split(':')[1])
    quest_results_ws.append_row([c.from_user.id, qid, True, datetime.utcnow().isoformat()])
    await c.answer("Квест засчитан! 🎉")

# Support wheel
@dp.message(Command("support"))
async def cmd_support(message: types.Message):
    parts = participants_ws.get_all_records()
    others = [p for p in parts if p['user_id']!=message.from_user.id]
    o = random.choice(others)
    tip = random.choice(["Делай шаги", "Будь настойчив", "Веруй в себя"])
    support_ws.append_row([message.from_user.username, o['username'], tip, datetime.utcnow().isoformat()])
    await message.answer(f"🎡 Поддержка: @{o['username']} — «{tip}»")

# Audio
class AudioUpload(StatesGroup):
    waiting = State()

@dp.message(Command("audio_send"))
async def cmd_audio_send(message: types.Message, state: FSMContext):
    args = message.get_args().strip()
    if not args.isdigit(): return await message.answer("/audio_send <mentor_id>")
    await state.update_data(mid=int(args))
    await message.answer("Пришли голосовое (.ogg)")
    await AudioUpload.waiting.set()

@dp.message(AudioUpload.waiting, content_types=ContentType.VOICE)
async def process_audio(message: types.Message, state: FSMContext):
    data = await state.get_data()
    audio_ws.append_row([data['mid'], message.voice.file_id, message.caption or '', datetime.utcnow().isoformat()])
    await message.answer("Аудио сохранено!")
    await state.clear()

@dp.message(Command("audios"))
async def cmd_audios(message: types.Message):
    args = message.get_args().strip()
    if not args.isdigit(): return await message.answer("/audios <mentor_id>")
    recs = [r for r in audio_ws.get_all_records() if r['mentor_id']==int(args)]
    if not recs: return await message.answer("Аудио нет.")
    for r in recs:
        await message.answer_voice(r['file_id'], caption=r['caption'])

# Events
@dp.message(Command("events"))
async def cmd_events(message: types.Message):
    now = datetime.utcnow()
    evs = []
    for r in events_ws.get_all_records():
        dt = datetime.fromisoformat(r['datetime'])
        if dt>now: evs.append((dt, r))
    if not evs: return await message.answer("Событий нет.")
    evs = sorted(evs, key=lambda x: x[0])[:5]
    text = "📆 Ближайшие события:\n"
    for dt,r in evs:
        text += f"• {r['title']} — {dt:%Y-%m-%d %H:%M}\n{r['description']}\n{r['link']}\n\n"
    await message.answer(text)

# Card management
@dp.callback_query(lambda c: c.data=="save_card")
async def handle_save_card(c: CallbackQuery):
    await c.answer()
    kb = InlineKeyboardMarkup(row_width=3)
    kb.add(
        InlineKeyboardButton("👤 Коуч", callback_data="cat:Коуч"),
        InlineKeyboardButton("⚡ Энергопрактик", callback_data="cat:Энергопрактик"),
        InlineKeyboardButton("🧠 Психолог", callback_data="cat:Психолог")
    )
    await c.message.answer("Выбери категорию:", reply_markup=kb)

@dp.callback_query(lambda c: c.data.startswith("cat:"))
async def handle_cat(c: CallbackQuery):
    cat = c.data.split(':',1)[1]
    categories_ws.append_row([c.from_user.id, c.from_user.username, cat, datetime.utcnow().isoformat()])
    await c.answer(f"Категория {cat} сохранена!")
    await c.message.answer("Главное меню:", reply_markup=menu_kb)

@dp.callback_query(lambda c: c.data in ["regen_card","edit_card","menu"] )
async def handle_misc(c: CallbackQuery):
    await c.answer()
    if c.data=="regen_card":
        await c.message.answer("Перегенерация в разработке.")
    elif c.data=="edit_card":
        await c.message.answer("Редактирование в разработке.")
    await c.message.answer("Главное меню:", reply_markup=menu_kb)

# Fallback to menu
@dp.message()
async def fallback_menu(message: types.Message):
    await message.answer("Главное меню:", reply_markup=menu_kb)

if __name__ == "__main__":
    dp.run_polling(bot)
