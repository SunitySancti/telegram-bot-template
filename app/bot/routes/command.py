import random
from aiogram import Router
from aiogram.types import Message as TelegramMessage
from aiogram.filters import CommandStart
from app.db.models import User
from app.bot.util import parse_deeplink_args


# ROUTER

command_router = Router()


# MAIN HANDLERS

@command_router.message(CommandStart())
async def start_handler(message: TelegramMessage, user: User):
    args = (message.text or ' ').split(' ', 1)[1]
    start_params = parse_deeplink_args(args or '')
    texts = [
        'Meh... I\'m stupid... but I work!',
        'Hi there!',
        'I don\'t understand what u are saying but you\'re cool ;)',
        'I am bot, and you?',
        'Are you alive? Prove me',
    ]
    await message.answer(random.choice(texts))
