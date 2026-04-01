import asyncio
import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command

# ===== НАСТРОЙКИ =====
TOKEN = "8728196428:AAFpFpgLoTPie4wKihFwBfcl0DYnR2eCMB4"
VK_TOKEN = "vk1.a.WxSVX6N2XfB4UwcRrywyRRzHxvNv5QUQcW7haoNTjTMMV7k4jICqpKqC7k4P7r59017Expskp8sQOOwSr7ck64UvC_EYU5ocbiAzIbvlvshtMRBnDYzwaEAyHhBC8tBx392oErEpZ57ggLDsOjRQHER4yMfThmlliq5cBl1-EOUcmimedQf5FbekMqb97JfP39TpOc9TidzoogOIArUoow"
GROUP_ID = "vrv_radar"
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
sent_posts = set()

# ===== ПРОВЕРКА СЛОВ =====
def contains(text, words):
    text = text.lower()
    return all(word in text for word in words)

# ===== РАССЫЛКА =====
async def send_to_all(text):
    for user in subscribers:
        try:
            await bot.send_message(user, text)
        except Exception as e:
            print(f"Ошибка отправки {user}: {e}")

# ===== VK ПАРСЕР =====
async def vk_parser():
    url = f"https://api.vk.com/method/wall.get?domain=vrv_radar&count=2&access_token=vk1.a.WxSVX6N2XfB4UwcRrywyRRzHxvNv5QUQcW7haoNTjTMMV7k4jICqpKqC7k4P7r59017Expskp8sQOOwSr7ck64UvC_EYU5ocbiAzIbvlvshtMRBnDYzwaEAyHhBC8tBx392oErEpZ57ggLDsOjRQHER4yMfThmlliq5cBl1-EOUcmimedQf5FbekMqb97JfP39TpOc9TidzoogOIArUoow&v=5.131"

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(url) as resp:
                    data = await resp.json()
                    posts = data.get("response", {}).get("items", [])

                    for post in posts:
                        post_id = post["id"]
                        text = post.get("text", "")

                        if post_id in sent_posts:
                            continue

                        print("Проверяю пост:", text)

                        # ===== ФИЛЬТР =====
                        if contains(text, ["самарская", "бпла", "отбой"]):
                            await send_to_all("✅ В Самарской области отбой опасности БПЛА.")

                        elif contains(text, ["самарская", "бпла"]):
                            await send_to_all("❗ВНИМАНИЕ! В Самарской области объявлена опасность атаки БПЛА!\n\nБудьте бдительны! Тел. 112.")

                        elif contains(text, ["самарская", "ракетная", "отбой"]):
                            await send_to_all("✅ В Самарской области отбой ракетной опасности.")

                        elif contains(text, ["самарская", "ракетная"]):
                            await send_to_all("❗ВНИМАНИЕ! В Самарской области ракетная опасность!\n\nПо возможности оставайтесь дома. Укройтесь в помещениях без окон со сплошными стенами. Не подходите к окнам. Если вы на улице или в транспорте, направляйтесь в ближайшее укрытие или безопасное место. Тел. 112.")

                        sent_posts.add(post_id)

            except Exception as e:
                print("Ошибка VK:", e)

            await asyncio.sleep(60)  # проверка каждые 60 сек

# ===== СТАРТ =====
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    subscribers.add(user_id)

    print("Подписался:", user_id)

    if user_id == ADMIN_ID:
        await message.answer("✅ Ты админ", reply_markup=keyboard)
    else:
        await message.answer("🔔 Ты подписан на оповещения")

# ===== КНОПКИ =====
@dp.message()
async def handle(message: Message):
    user_id = message.from_user.id
    subscribers.add(user_id)

    if user_id != ADMIN_ID:
        return

    text = None

    if message.text == "🚁 Объявлена опасность БПЛА":
        text = "❗ВНИМАНИЕ! В Самарской области объявлена опасность атаки БПЛА!\n\nБудьте бдительны! Тел. 112."

    elif message.text == "✅ Отбой опасности БПЛА":
        text = "✅ В Самарской области отбой опасности БПЛА."

    elif message.text == "🚀 Объявлена ракетная опасность":
        text = "❗ВНИМАНИЕ! В Самарской области ракетная опасность!\n\nПо возможности оставайтесь дома. Укройтесь в помещениях без окон со сплошными стенами. Не подходите к окнам. Если вы на улице или в транспорте, направляйтесь в ближайшее укрытие или безопасное место. Тел. 112."

    elif message.text == "✅ Отбой ракетной опасности":
        text = "✅ В Самарской области отбой ракетной опасности."

    if text:
        await send_to_all(text)

# ===== ЗАПУСК =====
async def main():
    print("Бот запущен...")
    asyncio.create_task(vk_parser())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())