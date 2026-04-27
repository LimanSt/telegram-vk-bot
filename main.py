import asyncio
import aiohttp
import json
import os
import time

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

# ===== НАСТРОЙКИ =====
TOKEN = "8728196428:AAFpFpgLoTPie4wKihFwBfcl0DYnR2X"
VK_TOKEN = "vk1.a.U_TIquBJERKH-gou93B93pn-ceKqu3h7DVcayhWImUOf8mFJfjG9_9hvN8-H77A4erRaD5X9hi0welhfzG7ZLQo9tnMxUFzfzQehI-VvKIBJaIM2-fPkfmpHEEnOPql_gjC7c04bqdV3UC4KCPIRmpNDZTVrPx7OfcOaTByAkzJTSCCYTM7Z7Yk7-MTDo4hiKyELKHfjZRoi1xq9KuNWUQ"

OWNER_ID = -227681059
ADMIN_ID = 1913014542

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== ЗАГРУЗКА ПОДПИСЧИКОВ =====
os.makedirs("/data", exist_ok=True)

try:
    with open("/data/subscribers.json", "r") as f:
        subscribers = set(json.load(f))
except:
    subscribers = set()

# ===== СОХРАНЕНИЕ =====
def save_subscribers():
    with open("/data/subscribers.json", "w") as f:
        json.dump(list(subscribers), f)

# ===== СОСТОЯНИЯ =====
waiting_for_broadcast = set()

# ===== КНОПКИ =====
keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🚁 Объявлена опасность БПЛА")],
        [KeyboardButton(text="✅ Отбой опасности БПЛА")],
        [KeyboardButton(text="🚀 Объявлена ракетная опасность")],
        [KeyboardButton(text="✅ Отбой ракетной опасности")],
        [KeyboardButton(text="✍️ Отправить своё сообщение")],
        [KeyboardButton(text="📊 Кол-во подписчиков")],
    ],
    resize_keyboard=True
)

# ===== СОБЫТИЯ =====
EVENTS = {
    "bpla_on": "❗ Граждане, ВНИМАНИЕ! Объявлена опасность БПЛА на территории Самарской области!/n/n❗ Будьте бдительны! Публикация фото и видео с БПЛА, а также последствия их применений ЗАПРЕЩЕНА! Не помогайте врагу./n❗ 112 — ЕДИНЫЙ НОМЕР ВЫЗОВА ЭКСТРЕННЫХ СЛУЖБ.",
    "bpla_off": "✅ Граждане, ВНИМАНИЕ! Снята опасность БПЛА на территории Самарской области!",
    "raketa_on": "‼️ Граждане, ВНИМАНИЕ! Объявлена РАКЕТНАЯ опасность на территории Самарской области!/n/n‼️ ЕСЛИ ВЫ НА УЛИЦЕ ИЛИ В ТРАНСПОРТЕ:/n•   сохраняйте спокойствие/n•   покиньте транспортное средство/n•   определите возле себя надёжное укрытие (подъезд дома, подземный переход или паркинг, метро)/n•   не оставайтесь на открытой местности/n•   при отсутствия надёжного укрытия выберите любое углубление, выступ или бетонные конструкции/n‼️ ЕСЛИ ВЫ В ЗДАНИИ:ЕСЛИ ВБЛИЗИ НЕТ ЗАЩИТНОГО СООРУЖЕНИЯ ГРАЖДАНСКОЙ ОБОРОНЫ, ПОДВАЛА ИЛИ ПАРКИНГА:/n•   держитесь подальше от окон•   зайдите в помещение с несущими стенами или помещение без окон (в квартире, как правило, ванная комната)•   сядьте на пол возле несущей стены и пригнитесь./nНЕ ПОЛЬЗУЙТЕСЬ ЛИФТОМ ВО ВРЕМЯ РАКЕТНОЙ ОПАСНОСТИ, ТАКЖЕ ЛИФТ НЕ ПОДХОДИТ ДЛЯ УКРЫТИЯ./n‼️ ПОСЛЕ ОКОНЧАНИЯ АТАКИ:/n•   не торопитесь выходить из защищённого места/n•   внимательно смотрите под ноги/n•   не поднимайте с земли незнакомые предметы, неразорвавшиеся боеприпасы и не прикасайтесь к ним./n‼️ 112 — ЕДИНЫЙ НОМЕР ВЫЗОВАЭКСТРЕННЫХ СЛУЖБ.",
    "raketa_off": "✅ Граждане, ВНИМАНИЕ! Снята РАКЕТНАЯ опасность на территории Самарской области!"
}

# ===== ОТПРАВКА =====
async def send_to_all(text):
    for user in subscribers:
        try:
            await bot.send_message(user, text)
        except Exception as e:
            print("Ошибка:", e)

# ===== ДЕТЕКТ =====
def detect_event(text):
    t = text.lower()

    if "самар" in t:
        if "бпла" in t:
            return "bpla_off" if "отбой" in t else "bpla_on"
        if "ракет" in t:
            return "raketa_off" if "отбой" in t else "raketa_on"

    return None

# ===== VK ПАРСЕР =====
last_post_id = 0

async def vk_parser():
    global last_post_id

    url = f"https://api.vk.com/method/wall.get?owner_id=-227681059&count=5&access_token=vk1.a.U_TIquBJERKH-gou93B93pn-ceKqu3h7DVcayhWImUOf8mFJfjG9_9hvN8-H77A4erRaD5X9hi0welhfzG7ZLQo9tnMxUFzfzQehI-VvKIBJaIM2-fPkfmpHEEnOPql_gjC7c04bqdV3UC4KCPIRmpNDZTVrPx7OfcOaTByAkzJTSCCYTM7Z7Yk7-MTDo4hiKyELKHfjZRoi1xq9KuNWUQ&v=5.199"

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(url + f"&t={int(time.time())}") as resp:
                    data = await resp.json()

                if "response" not in data:
                    print("VK ошибка:", data)
                    await asyncio.sleep(5)
                    continue

                posts = data["response"]["items"]

                if last_post_id == 0 and posts:
                    last_post_id = posts[0]["id"]
                    print("Инициализация:", last_post_id)
                    continue

                for post in reversed(posts):
                    post_id = post["id"]

                    if post_id <= last_post_id:
                        continue

                    text = post.get("text", "")
                    print("НОВЫЙ ПОСТ:", text)

                    event = detect_event(text)
                    if event:
                        await send_to_all(EVENTS[event])

                    last_post_id = post_id

            except Exception as e:
                print("Ошибка VK:", e)

            await asyncio.sleep(30)

# ===== TELEGRAM =====
@dp.message(Command("start"))
async def start(message: Message):
    user_id = message.from_user.id
    subscribers.add(user_id)
    save_subscribers()

    if user_id == ADMIN_ID:
        await message.answer("✅ Ты админ", reply_markup=keyboard)
    else:
        await message.answer("🔔 Ты подписан и будешь получать экстренные оповещения!\nВАЖНО!\nДанный бот не является ботом МЧС России. Бот создан для оперативного оповещения граждан Самарской области.\n\nУсловные обозначения, если увидите уведомление и чтобы не чиать все сразу:\n❗— Опасность БПЛА\n‼️— Ракетная опасность\n✅ — Отбой ракетной опасности или опасности БПЛА\n📄 — Прочие оповещения")

@dp.message()
async def handle(message: Message):
    user_id = message.from_user.id
    subscribers.add(user_id)
    save_subscribers()

    # только админ
    if user_id != ADMIN_ID:
        return

    # ===== ВВОД СООБЩЕНИЯ =====
    if user_id in waiting_for_broadcast:
        await send_to_all(f"📢 {message.text}")
        waiting_for_broadcast.remove(user_id)
        await message.answer("✅ Отправлено")
        return

    # ===== КНОПКИ =====
    if message.text == "✍️ Отправить своё сообщение":
        waiting_for_broadcast.add(user_id)
        await message.answer("Напиши текст:")
        return

    if message.text == "📊 Кол-во подписчиков":
        await message.answer(f"👥 Подписчиков: {len(subscribers)}")
        return

    mapping = {
        "🚁 Объявлена опасность БПЛА": "bpla_on",
        "✅ Отбой опасности БПЛА": "bpla_off",
        "🚀 Объявлена ракетная опасность": "raketa_on",
        "✅ Отбой ракетной опасности": "raketa_off",
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
