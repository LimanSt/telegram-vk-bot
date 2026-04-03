import asyncio
import aiohttp
import re
import json
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

# ===== НАСТРОЙКИ =====
TOKEN = "ТВОЙ_TELEGRAM_TOKEN"
GROUP_URL = "https://vk.com/vrv_radar"
ADMIN_ID = 1913014542

CHECK_INTERVAL = 60  # проверка каждые 60 секунд

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== ФАЙЛЫ =====
SUBSCRIBERS_FILE = "subscribers.json"
POSTS_FILE = "posts.json"

# ===== КНОПКИ =====
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚁 Объявлена опасность БПЛА")],
        [KeyboardButton(text="✅ Отбой опасности БПЛА")],
        [KeyboardButton(text="🚀 Объявлена ракетная опасность")],
        [KeyboardButton(text="✅ Отбой ракетной опасности")],
    ],
    resize_keyboard=True
)

# ===== ЗАГРУЗКА / СОХРАНЕНИЕ =====
def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return default

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(list(data), f)

subscribers = load_json(SUBSCRIBERS_FILE, set())
sent_posts = load_json(POSTS_FILE, set())

# ===== НОРМАЛИЗАЦИЯ =====
def normalize(text):
    text = text.lower()
    text = text.replace("ё", "е")
    text = re.sub(r"[^а-яa-z0-9\s]", " ", text)
    return text

# ===== ОПРЕДЕЛЕНИЕ СОБЫТИЙ =====
def detect_event(text):
    text = normalize(text)

    is_samara = "самарск" in text
    is_bpla = any(w in text for w in ["бпла", "беспилот", "дрон"])
    is_raketa = any(w in text for w in ["ракет", "пво"])
    is_otboy = any(w in text for w in ["отбой", "отмена"])
    is_opasnost = any(w in text for w in ["опасност", "угроз"])

    if not is_samara:
        return None
    if is_bpla and is_otboy:
        return "bpla_off"
    if is_bpla and is_opasnost:
        return "bpla_on"
    if is_raketa and is_otboy:
        return "raketa_off"
    if is_raketa and is_opasnost:
        return "raketa_on"
    return None

# ===== СООБЩЕНИЯ =====
def get_message(event):
    messages = {
        "bpla_on": "❗ВНИМАНИЕ! В Самарской области объявлена опасность атаки БПЛА!\n\nБудьте бдительны! Тел. 112.",
        "bpla_off": "✅ В Самарской области отбой опасности БПЛА.",
        "raketa_on": "❗ВНИМАНИЕ! В Самарской области ракетная опасность!\n\nУкройтесь в безопасном месте. Тел. 112.",
        "raketa_off": "✅ В Самарской области отбой ракетной опасности.",
    }
    return messages.get(event)

# ===== РАССЫЛКА =====
async def send_to_all(text):
    print("\n=== РАССЫЛКА ===")
    print(text)
    print("Подписчиков:", len(subscribers))

    for user in list(subscribers):
        try:
            await bot.send_message(user, text)
            print("✔ Отправлено:", user)
        except Exception as e:
            print("❌ Ошибка:", user, e)
            subscribers.discard(user)

    save_json(SUBSCRIBERS_FILE, subscribers)

# ===== ПАРСЕР ПУБЛИЧНОЙ СТРАНИЦЫ =====
async def vk_parser():
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(GROUP_URL) as resp:
                    html = await resp.text()
                    # Простая регулярка для поиска постов
                    posts = re.findall(r'<div class="wall_text">(.*?)</div>', html, re.DOTALL)
                    for post_text in posts:
                        post_text = re.sub(r"<.*?>", "", post_text)  # удаляем HTML теги
                        post_id = str(hash(post_text))

                        if post_id in sent_posts:
                            continue

                        print("\n--- НОВЫЙ ПОСТ ---")
                        print(post_text)

                        event = detect_event(post_text)
                        print("Определено событие:", event)

                        if event:
                            message = get_message(event)
                            await send_to_all(message)

                        sent_posts.add(post_id)
                    save_json(POSTS_FILE, sent_posts)

            except Exception as e:
                print("❌ Ошибка парсинга VK:", e)

            await asyncio.sleep(CHECK_INTERVAL)

# ===== СТАРТ =====
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    subscribers.add(user_id)
    save_json(SUBSCRIBERS_FILE, subscribers)
    print("➕ Подписался:", user_id)

    if user_id == ADMIN_ID:
        await message.answer("✅ Ты админ", reply_markup=keyboard)
    else:
        await message.answer("🔔 Ты подписан на оповещения")

# ===== КНОПКИ =====
@dp.message()
async def handle(message: Message):
    user_id = message.from_user.id
    subscribers.add(user_id)
    save_json(SUBSCRIBERS_FILE, subscribers)

    if user_id != ADMIN_ID:
        return

    text = None
    if message.text == "🚁 Объявлена опасность БПЛА":
        text = get_message("bpla_on")
    elif message.text == "✅ Отбой опасности БПЛА":
        text = get_message("bpla_off")
    elif message.text == "🚀 Объявлена ракетная опасность":
        text = get_message("raketa_on")
    elif message.text == "✅ Отбой ракетной опасности":
        text = get_message("raketa_off")

    if text:
        await send_to_all(text)

# ===== ЗАПУСК =====
async def main():
    print("🚀 Бот запущен")
    asyncio.create_task(vk_parser())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
