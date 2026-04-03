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
VK_TOKEN = "vk1.a.WxSVX6N2XfB4UwcRrywyRRzHxvNv5QUQcW7haoNTjTMMV7k4jICqpKqC7k4P7r59017Expskp8sQOOwSr7ck64UvC_EYU5ocbiAzIbvlvshtMRBnDYzwaEAyHhBC8tBx392oErEpZ57ggLDsOjRQHER4yMfThmlliq5cBl1-EOUcmimedQf5FbekMqb97JfP39TpOc9TidzoogOIArUoow"
GROUP_ID = "vrv_radar"
ADMIN_ID = 1913014542

CHECK_INTERVAL = 30
POST_COUNT = 20

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
        "raketa_on": "❗ВНИМАНИЕ! В Самарской области ракетная опасность!\n\nПо возможности оставайтесь дома. Укройтесь в помещениях без окон со сплошными стенами. Не подходите к окнам. Если вы на улице или в транспорте, направляйтесь в ближайшее укрытие или безопасное место. Тел. 112.",
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

# ===== VK ПАРСЕР =====
async def vk_parser():
    url = f"https://api.vk.com/method/wall.get?domain=vrv_radar&count=2&access_token=vk1.a.WxSVX6N2XfB4UwcRrywyRRzHxvNv5QUQcW7haoNTjTMMV7k4jICqpKqC7k4P7r59017Expskp8sQOOwSr7ck64UvC_EYU5ocbiAzIbvlvshtMRBnDYzwaEAyHhBC8tBx392oErEpZ57ggLDsOjRQHER4yMfThmlliq5cBl1-EOUcmimedQf5FbekMqb97JfP39TpOc9TidzoogOIArUoow&v=5.131"

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(url) as resp:
                    data = await resp.json()

                    if "response" not in data:
                        print("❌ VK ошибка:", data)
                        await asyncio.sleep(10)
                        continue

                    posts = data["response"]["items"]

                    for post in posts:
                        post_id = str(post["id"])
                        text = post.get("text", "")

                        if post_id in sent_posts:
                            continue

                        print("\n--- НОВЫЙ ПОСТ ---")
                        print(text)

                        event = detect_event(text)
                        print("Определено событие:", event)

                        if event:
                            message = get_message(event)
                            await send_to_all(message)

                        sent_posts.add(post_id)

                    save_json(POSTS_FILE, sent_posts)

            except Exception as e:
                print("❌ Ошибка VK:", e)

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
