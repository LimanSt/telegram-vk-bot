import asyncio
import logging
import os

import aiohttp
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup
from dotenv import load_dotenv

# ===== ЗАГРУЗКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ =====
load_dotenv()

# ===== КОНФИГУРАЦИЯ =====
TOKEN: str = os.getenv("TOKEN", "")
VK_TOKEN: str = os.getenv("VK_TOKEN", "")
ADMIN_ID: int = int(os.getenv("ADMIN_ID", "0"))
GROUP_ID: str = os.getenv("GROUP_ID", "vrv_radar")
POLL_INTERVAL: int = int(os.getenv("POLL_INTERVAL", "60"))

VK_API_VERSION = "5.131"
VK_POST_COUNT = 5

# ===== ЛОГИРОВАНИЕ =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ===== ВАЛИДАЦИЯ КОНФИГУРАЦИИ =====
if not TOKEN:
    raise ValueError("Переменная окружения TOKEN не задана")
if not VK_TOKEN:
    raise ValueError("Переменная окружения VK_TOKEN не задана")
if not ADMIN_ID:
    raise ValueError("Переменная окружения ADMIN_ID не задана")

# ===== ИНИЦИАЛИЗАЦИЯ БОТА =====
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
    resize_keyboard=True,
)

# ===== СОСТОЯНИЕ =====
subscribers: set[int] = set()
sent_posts: set[int] = set()

# ===== СООБЩЕНИЯ =====
MESSAGES = {
    "drone_alert": (
        "❗ВНИМАНИЕ! В Самарской области объявлена опасность атаки БПЛА!\n\n"
        "Будьте бдительны! Тел. 112."
    ),
    "drone_clear": "✅ В Самарской области отбой опасности БПЛА.",
    "rocket_alert": (
        "❗ВНИМАНИЕ! В Самарской области ракетная опасность!\n\n"
        "По возможности оставайтесь дома. Укройтесь в помещениях без окон со "
        "сплошными стенами. Не подходите к окнам. Если вы на улице или в "
        "транспорте, направляйтесь в ближайшее укрытие или безопасное место. "
        "Тел. 112."
    ),
    "rocket_clear": "✅ В Самарской области отбой ракетной опасности.",
}


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def contains(text: str, words: list[str]) -> bool:
    """Проверяет, содержит ли текст все указанные слова (без учёта регистра)."""
    text = text.lower()
    return all(word in text for word in words)


def classify_post(text: str) -> str | None:
    """
    Определяет тип оповещения по тексту поста.

    Возвращает ключ из словаря MESSAGES или None, если пост не релевантен.
    """
    if contains(text, ["самарская", "бпла", "отбой"]):
        return "drone_clear"
    if contains(text, ["самарская", "бпла"]):
        return "drone_alert"
    if contains(text, ["самарская", "ракетная", "отбой"]):
        return "rocket_clear"
    if contains(text, ["самарская", "ракетная"]):
        return "rocket_alert"
    return None


# ===== РАССЫЛКА =====
async def send_to_all(text: str) -> None:
    """Отправляет сообщение всем подписчикам, логируя ошибки доставки."""
    logger.info("Рассылка сообщения %d подписчикам", len(subscribers))
    for user_id in list(subscribers):
        try:
            await bot.send_message(user_id, text)
        except Exception as e:
            logger.warning("Ошибка отправки пользователю %d: %s", user_id, e)


# ===== VK ПАРСЕР =====
async def vk_parser() -> None:
    """
    Фоновая задача: периодически опрашивает стену VK-группы и рассылает
    оповещения подписчикам при обнаружении новых релевантных постов.
    """
    url = (
        f"https://api.vk.com/method/wall.get"
        f"?domain={GROUP_ID}"
        f"&count={VK_POST_COUNT}"
        f"&access_token={VK_TOKEN}"
        f"&v={VK_API_VERSION}"
    )

    logger.info("VK-парсер запущен (группа: %s, интервал: %ds)", GROUP_ID, POLL_INTERVAL)

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

                    if "error" in data:
                        error = data["error"]
                        logger.error(
                            "VK API вернул ошибку %s: %s",
                            error.get("error_code"),
                            error.get("error_msg"),
                        )
                    else:
                        posts = data.get("response", {}).get("items", [])
                        for post in posts:
                            post_id: int = post["id"]
                            text: str = post.get("text", "")

                            if post_id in sent_posts:
                                continue

                            logger.debug("Проверяю пост #%d: %.80s", post_id, text)

                            alert_key = classify_post(text)
                            if alert_key:
                                logger.info(
                                    "Пост #%d соответствует типу '%s', запускаю рассылку",
                                    post_id,
                                    alert_key,
                                )
                                await send_to_all(MESSAGES[alert_key])

                            sent_posts.add(post_id)

            except aiohttp.ClientError as e:
                logger.error("Сетевая ошибка при запросе к VK: %s", e)
            except Exception as e:
                logger.exception("Неожиданная ошибка в VK-парсере: %s", e)

            await asyncio.sleep(POLL_INTERVAL)


# ===== ОБРАБОТЧИКИ КОМАНД =====
@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """Подписывает пользователя на оповещения и приветствует его."""
    user_id = message.from_user.id
    subscribers.add(user_id)
    logger.info("Новый подписчик: %d", user_id)

    if user_id == ADMIN_ID:
        await message.answer("✅ Ты админ", reply_markup=keyboard)
    else:
        await message.answer("🔔 Ты подписан на оповещения")


# ===== ОБРАБОТЧИК КНОПОК АДМИНИСТРАТОРА =====
@dp.message()
async def handle_admin_buttons(message: Message) -> None:
    """
    Обрабатывает нажатия кнопок ручного оповещения.
    Доступно только администратору.
    """
    user_id = message.from_user.id
    subscribers.add(user_id)

    if user_id != ADMIN_ID:
        return

    button_map: dict[str, str] = {
        "🚁 Объявлена опасность БПЛА": MESSAGES["drone_alert"],
        "✅ Отбой опасности БПЛА": MESSAGES["drone_clear"],
        "🚀 Объявлена ракетная опасность": MESSAGES["rocket_alert"],
        "✅ Отбой ракетной опасности": MESSAGES["rocket_clear"],
    }

    text = button_map.get(message.text)
    if text:
        logger.info("Администратор инициировал рассылку: %s", message.text)
        await send_to_all(text)


# ===== ЗАПУСК =====
async def main() -> None:
    """Точка входа: запускает VK-парсер и начинает polling Telegram."""
    logger.info("Бот запускается...")
    asyncio.create_task(vk_parser())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
