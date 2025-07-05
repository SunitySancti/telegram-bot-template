import random
import asyncio
import contextlib
import re
from aiogram.types import InputMediaPhoto, InputMediaVideo, Message as TelegramMessage
from aiogram.enums import ChatAction
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter
from app.db.dao import DAO
from app.db.models import User
from app.util.logger import logger
from app.bot.instance import bot


# UTILS

@contextlib.asynccontextmanager
async def simulate_typing(chat_id: int | str):
    async def simulate_typing_handler():
        try:
            while True:
                await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
                await asyncio.sleep(random.uniform(5.5, 8))
        except asyncio.CancelledError:
            pass

    typing_task = asyncio.create_task(simulate_typing_handler())
    try:
        yield
    finally:
        typing_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await typing_task


def convert_markdown_bold_to_html(text: str) -> str:
    first_iteration = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    return re.sub(r'\*(.+?)\*', r'<b>\1</b>', first_iteration)


async def answer_with_scribe(text: str, user: User, sent_photo_url: str | None):
    msg = await bot.send_message(user.tg_id, text)

    sent_text = text if sent_photo_url is None else f'{text}\n{sent_photo_url}'
    await DAO.Message.save(sent_text, user.id, user.tg_id, msg.message_id, True)


async def safe_send_mediagroup(user_tg_id: str, media: list[InputMediaPhoto | InputMediaVideo], fallback_message: str | None):
    # Telegram allows max 10 items per media group
    CHUNK_SIZE = 10
    if not media:
        return

    for i in range(0, len(media), CHUNK_SIZE):
        chunk = media[i:i+CHUNK_SIZE]
        try:
            await bot.send_media_group(user_tg_id, chunk)  # type: ignore
            
        except TelegramRetryAfter as e:
            logger.warning(f"[WAIT] Flood control due sending mediagroup: wait {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            return await safe_send_mediagroup(user_tg_id, media[i:], fallback_message)
        
        except TelegramNetworkError:
            logger.warning(f"[WARN] TelegramNetworkError due sending mediagroup to user: {user_tg_id} (tg_id)")
            if fallback_message:
                await bot.send_message(user_tg_id, fallback_message)
                logger.warning(f'Sent fallback message:\n{fallback_message}')
            return
        
        except Exception as e:
            logger.warning(f"[ERROR] Media sending error: {e}. Trying to send individually.")
            # Try to send each media item individually
            for item in chunk:
                try:
                    caption = item.caption if hasattr(item, 'caption') else None
                    if isinstance(item, InputMediaPhoto):
                        await bot.send_photo(user_tg_id, item.media, caption=caption)
                    elif isinstance(item, InputMediaVideo):
                        await bot.send_video(user_tg_id, item.media, caption=caption)
                except:
                    pass
            return


async def split_message_and_answer(message: TelegramMessage, text: str, max_length: int = 4000):
    messages = [text[i:i+max_length] for i in range(0, len(text), max_length)]
    for msg in messages:
        await message.answer(msg)


def parse_deeplink_args(args: str) -> dict[str, str]:
    if not args:
        return {}
    
    parts = args.split('_')
    result = {}

    for part in parts:
        if '-' not in part:
            continue
        key, value = part.split('-', 1)
        result[key] = value

    return result


def parse_user_to_details(user: User):
    return f'Inner ID: <code>{user.id}</code>\nTelegram ID: <code>{user.tg_id}</code>\nUsername: <code>@{user.tg_username}</code>\nFull name: <code>{user.tg_fullname}</code>'
    
