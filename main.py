import asyncio
import aiohttp
import json
import time

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

# ================== НАСТРОЙКИ ==================

TOKEN = "8728196428:AAFpFpgLoTPie4wKihFwBfcl0DYnR2eCMB4"

# ⚠️ VK токен вставляешь сюда вручную
VK_TOKEN = "c1c1fdb9c1c1fdb9c1c1fdb95dc2fe0705cc1c1c1c1fdb9a811af7728d3b4bad84ceef3"

OWNER_ID = -227681059
ADMIN_ID = 1913014542

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ================== ДАННЫЕ ==================

subscribers = set()
waiting_for_broadcast = set()

last_post_id = 0

# ================== КНОПКИ ==================

keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Подписчики")],
        [KeyboardButton(text="✍️ Сообщение")],
        [KeyboardButton(text="🚁 БПЛА тревога")],
        [KeyboardButton(text="🚀 Ракетная тревога")],
        [KeyboardButton(text="✅ Отбой опасности БПЛА")],
        [KeyboardButton(text="✅ Отбой ракетной опасности")],
    ],
    resize_keyboard=True
)

# ================== СОБЫТИЯ ==================

EVENTS = {
    "bpla_on": "❗ Граждане, ВНИМАНИЕ! Объявлена опасность БПЛА на территории Самарской области!\n\n❗ Будьте бдительны! Публикация фото и видео с БПЛА, а также последствия их применений ЗАПРЕЩЕНА! Не помогайте врагу.\n❗ 112 — ЕДИНЫЙ НОМЕР ВЫЗОВА ЭКСТРЕННЫХ СЛУЖБ.",
    "bpla_off": "✅ Граждане, ВНИМАНИЕ! Снята опасность БПЛА на территории Самарской области!",
    "raketa_on": "‼️ Граждане, ВНИМАНИЕ! Объявлена РАКЕТНАЯ опасность на территории Самарской области!\n\n‼️ ЕСЛИ ВЫ НА УЛИЦЕ ИЛИ В ТРАНСПОРТЕ:\n•   сохраняйте спокойствие\n•   покиньте транспортное средство\n•   определите возле себя надёжное укрытие (подъезд дома, подземный переход или паркинг, метро)\n•   не оставайтесь на открытой местности\n•   при отсутствия надёжного укрытия выберите любое углубление, выступ или бетонные конструкции\n‼️ ЕСЛИ ВЫ В ЗДАНИИ:ЕСЛИ ВБЛИЗИ НЕТ ЗАЩИТНОГО СООРУЖЕНИЯ ГРАЖДАНСКОЙ ОБОРОНЫ, ПОДВАЛА ИЛИ ПАРКИНГА:\n•   держитесь подальше от окон\n•   зайдите в помещение с несущими стенами или помещение без окон (в квартире, как правило, ванная комната)\n•   сядьте на пол возле несущей стены и пригнитесь.\nНЕ ПОЛЬЗУЙТЕСЬ ЛИФТОМ ВО ВРЕМЯ РАКЕТНОЙ ОПАСНОСТИ, ТАКЖЕ ЛИФТ НЕ ПОДХОДИТ ДЛЯ УКРЫТИЯ.\n‼️ ПОСЛЕ ОКОНЧАНИЯ АТАКИ:\n•   не торопитесь выходить из защищённого места\n•   внимательно смотрите под ноги\n•   не поднимайте с земли незнакомые предметы, неразорвавшиеся боеприпасы и не прикасайтесь к ним.\n‼️ 112 — ЕДИНЫЙ НОМЕР ВЫЗОВАЭКСТРЕННЫХ СЛУЖБ.",
    "raketa_off": "✅ Граждане, ВНИМАНИЕ! Снята РАКЕТНАЯ опасность на территории Самарской области!"
}

# ================== ЛОГИКА ==================

def detect_event(text):
    t = text.lower()

    if "бпла" in t:
        return "bpla_off" if "отбой" in t else "bpla_on"

    if "ракет" in t:
        return "raketa_off" if "отбой" in t else "raketa_on"

    return None


async def send_to_all(text):
    for user in list(subscribers):
        try:
            await bot.send_message(user, text)
        except:
            pass


# ================== VK ПАРСЕР ==================

async def vk_parser():
    global last_post_id, VK_TOKEN

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                if not VK_TOKEN:
                    print("❌ VK_TOKEN не задан")
                    await asyncio.sleep(10)
                    continue

                url = "https://api.vk.com/method/wall.get"

                params = {
                    "owner_id": OWNER_ID,
                    "count": 5,
                    "access_token": VK_TOKEN,
                    "v": "5.199"
                }

                async with session.get(url, params=params) as resp:
                    data = await resp.json()

                if "response" not in data:
                    print("VK ошибка:", data)
                    await asyncio.sleep(5)
                    continue

                posts = data["response"]["items"]

                if last_post_id == 0 and posts:
                    last_post_id = posts[0]["id"]
                    continue

                for post in reversed(posts):
                    if post["id"] <= last_post_id:
                        continue

                    text = post.get("text", "")
                    print("НОВЫЙ ПОСТ:", text)

                    event = detect_event(text)
                    if event:
                        await send_to_all(EVENTS[event])

                    last_post_id = post["id"]

            except Exception as e:
                print("VK ERROR:", e)

            await asyncio.sleep(30)


# ================== TELEGRAM ==================

@dp.message(Command("start"))
async def start(message: Message):
    subscribers.add(message.from_user.id)

    if message.from_user.id == ADMIN_ID:
        await message.answer("🔔 Ты подписан и будешь получать экстренные оповещения!\n\n👑Админ-панель!\n\nВАЖНО!\nДанный бот не является ботом МЧС России. Бот создан для оперативного оповещения граждан Самарской области.\n\nУсловные обозначения, если увидите уведомление и чтобы не читать все сразу:\n❗— Опасность БПЛА\n‼️— Ракетная опасность\n✅ — Отбой ракетной опасности или опасности БПЛА\n📄 — Прочие оповещения", reply_markup=keyboard)
    else:
        await message.answer("🔔 Ты подписан и будешь получать экстренные оповещения!\nВАЖНО!\nДанный бот не является ботом МЧС России. Бот создан для оперативного оповещения граждан Самарской области.\n\nУсловные обозначения, если увидите уведомление и чтобы не чиать все сразу:\n❗— Опасность БПЛА\n‼️— Ракетная опасность\n✅ — Отбой ракетной опасности или опасности БПЛА\n📢 — Прочие оповещения")


@dp.message()
async def handler(message: Message):
    user_id = message.from_user.id
    text = message.text

    subscribers.add(user_id)

    # ❗ СНАЧАЛА админ команды
    if user_id == ADMIN_ID:

        if text == "📊 Подписчики":
            await message.answer(str(len(subscribers)))
            return

        if text == "✍️ Сообщение":
            waiting_for_broadcast.add(user_id)
            await message.answer("Введи текст:")
            return

        if user_id in waiting_for_broadcast:
            await send_to_all("📢 " + text)
            waiting_for_broadcast.remove(user_id)
            await message.answer("Отправлено")
            return

        if text == "🚁 БПЛА тревога":
            await send_to_all(EVENTS["bpla_on"])
            return

        if text == "🚀 Ракетная тревога":
            await send_to_all(EVENTS["raketa_on"])
            return

        if text == "✅ Отбой опасности БПЛА":
            await send_to_all(EVENTS["bpla_off"])
            return

        if text == "✅ Отбой ракетной опасности":
            await send_to_all(EVENTS["raketa_off"])
            return

# ================== ЗАПУСК ==================

async def main():
    print("🚀 БОТ ЗАПУЩЕН")

    asyncio.create_task(vk_parser())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
