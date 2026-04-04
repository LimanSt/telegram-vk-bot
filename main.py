import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

# ===== НАСТРОЙКИ =====
TOKEN = "8728196428:AAFpFpgLoTPie4wKihFwBfcl0DYnR2eCMB4"     # токен телеграм бота
VK_TOKEN = "vk1.a.BGk6rqrdXdY52bfBqlanSkVvsz0rd8s7i9qomGimslc0hveX1lhlw6u32Pp80qSo-Hdh0g_IcZoPMJh-klTjmOqC5AFAdXWB_5UzW416wEU4jSntIFx-S6HsSaXg6sQ_6pB78BrC6HXHs0Vlda7mdnFDUSZSAL_yzvDx8ZDOhMOZ8ELuJa9BFyO7fpeRGC_baZArFky-iC7VZx9PrnJpqw"     # рабочий токен VK
OWNER_ID = -227681059                # OWNER_ID группы VK (с минусом)
ADMIN_ID = 1913014542                 # Telegram ID администратора

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
sent_posts = set()

# ===== ФУНКЦИИ =====
def detect_event(text: str):
    """Определяет событие по тексту поста (учитывая многострочные сообщения)"""
    text_normalized = text.replace("\n", " ").lower()

    if "самарская область" in text_normalized:
        if "бпла" in text_normalized:
            return "bpla_off" if "отбой" in text_normalized else "bpla_on"
        if "ракетная" in text_normalized:
            return "raketa_off" if "отбой" in text_normalized else "raketa_on"
    return None

def get_message(event: str):
    """Возвращает готовый текст сообщения для подписчиков"""
    return {
        "bpla_on": "❗ВНИМАНИЕ! В Самарской области объявлена опасность атаки БПЛА!\n\nБудьте бдительны! Тел. 112.",
        "bpla_off": "✅ ВНИМАНИЕ! В Самарской области отбой опасности атаки БПЛА!",
        "raketa_on": "❗ВНИМАНИЕ! В Самарской области ракетная опасность!\n\nПо возможности оставайтесь дома. Укройтесь в помещениях без окон со сплошными стенами. Не подходите к окнам. Если вы на улице или в транспорте, направляйтесь в ближайшее укрытие или безопасное место. Тел. 112.",
        "raketa_off": "✅ ВНИМАНИЕ! В Самарской области отбой ракетной опасности!"
    }.get(event)

async def send_to_all(text: str):
    for user in subscribers:
        try:
            await bot.send_message(user, text)
        except Exception as e:
            print(f"❌ Ошибка отправки {user}: {e}")
    print(f"💬 Сообщение отправлено всем подписчикам: {text}")

# ===== VK ПАРСЕР =====
async def vk_parser():
    url = f"https://api.vk.com/method/wall.get?owner_id=-227681059&count=10&access_token=vk1.a.BGk6rqrdXdY52bfBqlanSkVvsz0rd8s7i9qomGimslc0hveX1lhlw6u32Pp80qSo-Hdh0g_IcZoPMJh-klTjmOqC5AFAdXWB_5UzW416wEU4jSntIFx-S6HsSaXg6sQ_6pB78BrC6HXHs0Vlda7mdnFDUSZSAL_yzvDx8ZDOhMOZ8ELuJa9BFyO7fpeRGC_baZArFky-iC7VZx9PrnJpqw&v=5.199"
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(url) as resp:
                    data = await resp.json()
                    posts = data.get("response", {}).get("items", [])

                    if not posts:
                        print("⏱ Проверка новых постов через 60 секунд... Нет новых постов.")
                    else:
                        new_posts_found = False
                        for post in posts:
                            post_id = post["id"]
                            text = post.get("text", "")
                            print(f"🔹 Проверка поста {post_id}:\n{text}")

                            if post_id in sent_posts:
                                continue

                            event = detect_event(text)
                            if event:
                                await send_to_all(get_message(event))
                                print(f"✅ Пост {post_id} обработан и опубликован: событие {event}")
                            else:
                                print(f"❌ Пост {post_id} не подходит под фильтр")

                            sent_posts.add(post_id)
                            new_posts_found = True

                        if not new_posts_found:
                            print("⏱ Проверка новых постов через 60 секунд... Новых постов нет подходящих.")

            except Exception as e:
                print(f"❌ Ошибка VK: {e}")

            await asyncio.sleep(60)

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
        await send_to_all(get_message(mapping[message.text]))

# ===== ЗАПУСК =====
async def main():
    print("🚀 БОТ ЗАПУЩЕН")
    asyncio.create_task(vk_parser())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
