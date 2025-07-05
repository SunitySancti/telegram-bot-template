import asyncio
from typing import Callable, Awaitable, Any, TypedDict
from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import Message as TelegramMessage, Update, ChatMemberUpdated
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter, TelegramNetworkError
from app.db.dao import DAO
from app.db.models import User
from app.util.logger import logger
from app.util.config import config
from app.bot.util import simulate_typing
from app.bot.instance import bot


class MiddlewareData(TypedDict):
    user: User


# BOT MIDDLEWARES

class ErrorMiddleware(BaseMiddleware):
    async def __call__(self, handler, event: Update, data: dict[str, Any]):
        try:
            return await handler(event, data)

        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            return await handler(event, data)

        except (TelegramBadRequest, TelegramForbiddenError) as e:
            return

        except TelegramNetworkError as e:
            await asyncio.sleep(1)
            return await handler(event, data)

        except Exception as e:
            logger.exception(f'UNHANDLED ERROR: {e}, {event.event_type}')


class LeaveNonPrivateChatMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, ChatMemberUpdated):
            if event.chat.type != ChatType.PRIVATE:
                await bot.leave_chat(event.chat.id)
                return
        return await handler(event, data)


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramMessage, dict[str, Any]], Awaitable[Any]],
        message: TelegramMessage,
        data: dict[str, Any]
    ) -> Any:
        if user := await DAO.User.upsert(message.from_user):
            data['user'] = user
            return await handler(message, data)


class SimulateTypingMiddleware(BaseMiddleware):
    async def __call__(self, handler, message: TelegramMessage, data: dict[str, Any]):
        async with simulate_typing(message.chat.id):
            return await handler(message, data)


# ROUTE MIDDLEWARES

class AdminAuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramMessage, dict[str, Any]], Awaitable[Any]],
        message: TelegramMessage,
        data: dict[str, Any]
    ) -> Any:
        user = data['user']
        if isinstance(user, User) and config.is_admin(user.tg_id):
            return await handler(message, data)


class ScribeInboundMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramMessage, dict[str, Any]], Awaitable[Any]],
        message: TelegramMessage,
        data: MiddlewareData
    ) -> Any:
        user = data['user']
        if isinstance(user, User) and isinstance(message, TelegramMessage):
            inserted = await DAO.Message.save(message.text or '', user.id, user.tg_id, message.message_id, False)
            if not inserted:
                return None
        
        return await handler(message, data)

