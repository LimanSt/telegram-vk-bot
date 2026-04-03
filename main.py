import asyncio
import aiohttp
import re
import json
import os
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

# ===== НАСТРОЙКИ =====
TOKEN = "8728196428:AAFpFpgLoTPie4wKihFwBfcl0DYnR2eCMB4"
GROUP_ID = "vrv_radar"  # пример публичной группы
ADMIN_ID = 1913014542

bot = Bot(token=TOKEN)
dp = Dispatcher()

SUBSCRIBERS_FILE = "subscribers.json"
POSTS_FILE = "posts.json"
CHECK_INTERVAL = 60  # проверка каждые 60 секунд

# ===== ЗАГРУЗКА / СОХРАНЕНИЕ =====
def load_json(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(list(data), f)

subscribers = load_json(SUBSCRIBERS_FILE)
sent_posts = load_json(POSTS_FILE)

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

# ===== НОРМАЛИЗАЦИЯ =====
def normalize(text):
    text = text.lower()
    text = text.replace("ё", "е")
    text = text.replace("\xa0", " ")
    text = text.replace("\n", " ")
    text = text.replace("\r", " ")
    text = re.sub(r"[^а-яa-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ===== ОПРЕДЕЛЕНИЕ СОБЫТИЙ =====
def detect_event(text):
    text_norm = normalize(text)

    is_samara = any(w in text_norm for w in ["самарск", "тольятти"])
    is_bpla = any(w in text_norm for w in ["бпла", "беспилот", "дрон", "коптер"])
    is_raketa = any(w in text_norm for w in ["ракет", "пво"])
    is_otboy = any(w in text_norm for w in ["отбой", "отмена"])
    is_opasnost = any(w in text_norm for w in ["опасност", "угроз"])

    print("\n=== ПРОВЕРКА ПОСТА ===")
    print("ОРИГИНАЛ:", repr(text))
    print("НОРМАЛ:", text_norm)
    print(f"SAMARA:{is_samara} | BPLA:{is_bpla} | RAKETA:{is_raketa} | OPASNOST:{is_opasnost} | OTBOY:{is_otboy}")

    if is_samara:
        if is_bpla and is_otboy:
            return "bpla_off"
        if is_bpla and is_opasnost:
            return "bpla_on"
        if is_raketa and is_otboy:
            return "raketa_off"
        if is_raketa and is_opasnost:
            return "raketa_on"

    return None

# ===== ТЕКСТЫ СОБЫТИЙ =====
def get_message(event):
    return {
        "bpla_on": "❗ВНИМАНИЕ! В Самарской области объявлена опасность атаки БПЛА!\n\nБудьте бдительны! Тел. 112.",
        "bpla_off": "✅ ВНИМАНИЕ! В Самарской области отбой опасности атаки БПЛА!",
        "raketa_on": "❗ВНИМАНИЕ! В Самарской области ракетная опасность!\n\nПо возможности оставайтесь дома. Укройтесь в помещениях без окон со сплошными стенами. Не подходите к окнам. Если вы на улице или в транспорте, направляйтесь в ближайшее укрытие или безопасное место. Тел. 112.",
        "raketa_off": "✅ ВНИМАНИЕ! В Самарской области отбой ракетной опасности!"
    }.get(event)

# ===== РАССЫЛКА =====
async def send_to_all(text):
    print("\n=== РАССЫЛКА ===")
    print(text)
    print("Подписчиков:", len(subscribers))
    for user in list(subscribers):
        try:
            await bot.send_message(user, text)
            print("✔ отправлено:", user)
        except Exception as e:
            print("❌ ошибка при отправке:", e)

# ===== ПАРСЕР VK =====
async def vk_parser():
    url = f"https://vk.com/vrv_radar?act=wall&offset=0&count=10"
    headers = {"User-Agent": "Mozilla/5.0"}

    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            try:
                async with session.get(url) as resp:
                    data = await resp.json()
                    posts = data.get("payload", [None, [None, []]])[1][0]

                    for post in posts:
                        post_id = str(post["id"])
                        text = post.get("text", "")

                        if post_id in sent_posts:
                            continue

                        print("\n==============================")
                        print("📩 НОВЫЙ ПОСТ:")
                        print(text)

                        event = detect_event(text)
                        if event:
                            print("✅ СОБЫТИЕ НАЙДЕНО:", event)
                            await send_to_all(get_message(event))
                        else:
                            print("❌ ПРОПУЩЕНО (не подошёл фильтр)")

                        sent_posts.add(post_id)

                    save_json(POSTS_FILE, sent_posts)

            except Exception as e:
                print("❌ ОШИБКА VK:", e)

            print("\n⏱ Проверка новых постов через 60 секунд...")
            await asyncio.sleep(CHECK_INTERVAL)

# ===== СТАРТ =====
@dp.message(Command("start"))
async def start(message: Message):
    subscribers.add(message.from_user.id)
    save_json(SUBSCRIBERS_FILE, subscribers)
    if message.from_user.id == ADMIN_ID:
        await message.answer("✅ Ты админ", reply_markup=keyboard)
    else:
        await message.answer("🔔 Ты подписан на оповещения")

@dp.message()
async def handle(message: Message):
    if message.from_user.id != ADMIN_ID:
        return

    mapping = {
        "🚁 Объявлена опасность БПЛА": "bpla_on",
        "✅ Отбой опасности БПЛА": "bpla_off",
        "🚀 Объявлена ракетная опасность": "raketa_on",
        "✅ Отбой ракетной опасности": "raketa_off"
    }

    if message.text in mapping:
        await send_to_all(get_message(mapping[message.text]))

# ===== ЗАПУСК =====
async def main():
    print("🚀 БОТ ЗАПУЩЕН")
    asyncio.create_task(vk_parser())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
