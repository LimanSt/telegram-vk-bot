import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton


# ===== НАСТРОЙКИ =====
TOKEN = "8728196428:AAFpFpgLoTPie4wKihFwBfcl0DYnR2eCMB4"
VK_TOKEN = "vk1.a.BGk6rqrdXdY52bfBqlanSkVvsz0rd8s7i9qomGimslc0hveX1lhlw6u32Pp80qSo-Hdh0g_IcZoPMJh-klTjmOqC5AFAdXWB_5UzW416wEU4jSntIFx-S6HsSaXg6sQ_6pB78BrC6HXHs0Vlda7mdnFDUSZSAL_yzvDx8ZDOhMOZ8ELuJa9BFyO7fpeRGC_baZArFky-iC7VZx9PrnJpqw"
OWNER_ID = -227681059  # ID группы ВК с минусом
ADMIN_ID = 1913014542


bot = Bot(token=TOKEN)
dp = Dispatcher()


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

# ===== ПОДПИСЧИКИ =====
subscribers = set()

# ===== События =====
EVENTS = {
    "bpla_on": "❗ВНИМАНИЕ! В Самарской области объявлена опасность атаки БПЛА!\n\nБудьте бдительны! Тел. 112.",
    "bpla_off": "✅ ВНИМАНИЕ! В Самарской области отбой опасности атаки БПЛА!",
    "raketa_on": "❗ВНИМАНИЕ! В Самарской области ракетная опасность!\n\nПо возможности оставайтесь дома. Укройтесь в помещениях без окон со сплошными стенами. Не подходите к окнам. Если вы на улице или в транспорте, направляйтесь в ближайшее укрытие или безопасное место. Тел. 112.",
    "raketa_off": "✅ ВНИМАНИЕ! В Самарской области отбой ракетной опасности!"
}

# ===== Отправка сообщений =====
async def send_to_all(text: str):
    if not subscribers:  # Проверка на отсутствие подписчиков
        print("👥 Нет подписчиков для отправки")
        return

    success_count = 0
    error_count = 0

    for user in subscribers:
        try:
            await bot.send_message(user, text)
            success_count += 1
        except Exception as e:
            print(f"❌ Ошибка отправки {user}: {e}")
            error_count += 1

    print(f"💬 Сообщение отправлено: {success_count} успешно, {error_count} ошибок")

# ===== Определение события по тексту =====
def detect_event(text: str):
    # Проверка на пустой текст
    if not text or not text.strip():
        return None

    text_lines = text.lower().splitlines()
    joined_text = " ".join(text_lines)

    # Обязательные условия для срабатывания:
    # 1. Должен быть регион «самарская область»
    # 2. Должна быть либо «опасность», либо «воздушная тревога»
    if "самарская область" in joined_text and ("опасность" in joined_text or "воздушная тревога" in joined_text):
        if "бпла" in joined_text:
            return "bpla_off" if "отбой" in joined_text else "bpla_on"
        if "ракетная" in joined_text:
            return "raketa_off" if "отбой" in joined_text else "raketa_on"
    return None

# ===== VK ПАРСЕР =====
async def vk_parser():
    last_processed_post_id = None  # ID последнего обработанного поста
    url = f"https://api.vk.com/method/wall.get?owner_id=-227681059&count=1&access_token=vk1.a.BGk6rqrdXdY52bfBqlanSkVvsz0rd8s7i9qomGimslc0hveX1lhlw6u32Pp80qSo-Hdh0g_IcZoPMJh-klTjmOqC5AFAdXWB_5UzW416wEU4jSntIFx-S6HsSaXg6sQ_6pB78BrC6HXHs0Vlda7mdnFDUSZSAL_yzvDx8ZDOhMOZ8ELuJa9BFyO7fpeRGC_baZArFky-iC7VZx9PrnJpqw&v=5.199"


    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(url) as resp:
                    data = await resp.json()
            posts = data.get("response", {}).get("items", [])

            if not posts:
                print("⏱ Новых постов нет за прошедшую минуту")
            else:
                post = posts[0]  # берём только последний пост
                post_id = post["id"]
                text = post.get("text", "")

                # Если это первый запуск, запоминаем ID последнего поста
                if last_processed_post_id is None:
                    last_processed_post_id = post_id
                    print(f"🚀 Бот запущен. Последний пост ID={last_processed_post_id} отмечен как обработанный")
                # Проверяем, новый ли это пост
                elif post_id != last_processed_post_id:
                    print(f"🔹 Новый пост {post_id}:\n{text}")
            # Проверяем событие
            event = detect_event(text)
            if event:
                print(f"✅ Обнаруден новый пост, пост опубликован: {event}")
                await send_to_all(EVENTS[event])
            else:
                print("❌ Обнаруден новый пост, после проверки он не опубликован")
            # Обновляем ID последнего обработанного поста
            last_processed_post_id = post_id

            except Exception as e:
                print(f"❌ Ошибка VK: {e}")

            await asyncio.sleep(60)  # проверка каждую минуту


# ===== ТЕЛЕГРАМ КОМАНДЫ =====
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    subscribers.add(user_id)
    print(f"🔔 Подписался пользователь: {user_id}")

    if user_id == ADMIN_ID:
        await message.answer("✅ Ты админ", reply_markup=keyboard)
    else:
        await message.answer("🔔 Ты подписан на оповещения")

@dp.message()
async def handle_buttons(message: Message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        return

    mapping = {
        "🚁 Объявлена опасность БПЛА": "bpla_on",
        "✅ Отбой опасности БПЛА": "bpla_off",
        "🚀 Объявлена ракетная опасность": "raketa_on",
        "✅ Отбой ракетной опасности": "raketa_off"
    }

    if message.text in mapping:
        await send_to_all(EVENTS[mapping[message.text]])

# ===== ЗАПУСК =====
async def main():
    print("🚀 БОТ ЗАПУЩЕН")
    asyncio.create_task(vk_parser())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
