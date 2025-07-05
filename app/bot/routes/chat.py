import random
from aiogram import Router, F
from aiogram.types import Message as TelegramMessage, CallbackQuery
from app.bot.middlewares import ScribeInboundMiddleware
from app.db.models import User


# ROUTER

chat_router = Router()
chat_router.message.middleware(ScribeInboundMiddleware())


# MAIN CHAT HANDLER

@chat_router.message(~F.text.startswith('/'))
async def chat_handler(message: TelegramMessage, user: User):
    texts = [
        'Meh... I\'m stupid... but I work!',
        'Hi there!',
        'I don\'t understand what u are saying but you\'re cool ;)',
        'I am bot, and you?',
        'Are you alive? Prove me',
    ]
    await message.answer(random.choice(texts))


# CALLBACK HANDLERS

@chat_router.callback_query(F.data.startswith('test/'))
async def test_callback_query(callback: CallbackQuery):
    parts = callback.data.split('/') if callback.data else ['','','','']
    # do something

