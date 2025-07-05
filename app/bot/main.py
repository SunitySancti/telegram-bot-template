from aiogram import Dispatcher
from app.bot.routes.chat import chat_router
from app.bot.routes.admin import admin_router
from app.bot.routes.command import command_router
from app.bot.middlewares import ErrorMiddleware, LeaveNonPrivateChatMiddleware, AuthMiddleware, SimulateTypingMiddleware


dp = Dispatcher()

dp.update.middleware(ErrorMiddleware())
dp.update.middleware(LeaveNonPrivateChatMiddleware())
dp.message.middleware(AuthMiddleware())
dp.message.middleware(SimulateTypingMiddleware())

dp.include_router(command_router)
dp.include_router(admin_router)
dp.include_router(chat_router)
