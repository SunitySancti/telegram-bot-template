from aiogram import Router
from aiogram.types import Message as TelegramMessage
from aiogram.filters import Command
from app.bot.middlewares import AdminAuthMiddleware
from app.bot.util import parse_user_to_details
from app.db.dao import DAO
from app.db.models import User
from app.payments.cp_requests import cp_cancel_subscription, cp_get_subscription_status, cp_get_user_subscriptions, cp_find_subscription


# ROUTER

admin_router = Router()
admin_router.message.middleware(AdminAuthMiddleware())


# USERS AND MESSAGES

@admin_router.message(Command('get_me'))
async def get_me_handler(message: TelegramMessage, user: User):
    return await message.answer(f'Inner ID: <code>{user.id}</code>\nTelegram ID: <code>{user.tg_id}</code>')


@admin_router.message(Command('user_details'))
async def user_details_handler(message: TelegramMessage, user: User):
    parts = message.text.strip().split(maxsplit=1) if message.text else ['','']
    if len(parts) == 1:
        return await message.answer('Usage example: <code>/user_details <Inner ID | Telegram ID | Username></code>')
    
    _, id_or_tgid_or_username = parts

    users = []

    if id_or_tgid_or_username.isdigit():
        user_by_id = await DAO.User.get_by_id(id_or_tgid_or_username)
        user_by_tg_id = await DAO.User.get_by_tg_id(id_or_tgid_or_username)
        if user_by_id:
            users.append(user_by_id)
        if user_by_tg_id:
            users.append(user_by_tg_id)

    user_by_username = await DAO.User.get_by_username(id_or_tgid_or_username)
    if user_by_username:
        users.append(user_by_username)

    if not users:
        return await message.answer('User not found')
    elif len(users) > 1:
        user_details = '\n\n'.join([parse_user_to_details(u) for u in users])
        return await message.answer(f'Found {len(users)} users:\n\n{user_details}')
    else:
        return await message.answer(parse_user_to_details(users[0]))


@admin_router.message(Command('delete_me'))
async def delete_me_handler(message: TelegramMessage):
    tg_id = str(message.from_user.id) if message.from_user else None
    if tg_id and await DAO.User.delete_user(tg_id):
        return await message.answer('Ваши данные удалены из базы')
    else:
        return await message.answer('Упс... что-то пошло не так')


# SUBSCRIPTIONS


@admin_router.message(Command('sub_for_user'))
async def user_subscriptions_info_getter(message: TelegramMessage):
    parts = message.text.strip().split(maxsplit=1) if message.text else ['','']
    if len(parts) == 1:
        return await message.answer('Usage example: <code>/sub_for_user <Inner ID></code>')
    
    _, user_id = parts
    subscriptions = await cp_get_user_subscriptions(user_id)
    sub_strings = [f'<code>{sub.get('Id')}</code>: <b>{sub.get('Status')}</b>' for sub in subscriptions]
    text = f'Найдено подписок: {len(sub_strings)}.\n{'\n'.join(sub_strings)}'
    return await message.answer(text)


@admin_router.message(Command('sub_details'))
async def request_subscription_details_handler(message: TelegramMessage):
    parts = message.text.strip().split(maxsplit=1) if message.text else ['','']
    if len(parts) == 1:
        return await message.answer('Usage example: <code>/sub_details sc_123456789</code>')
    
    _, sub_id = parts
    sub = await cp_find_subscription(sub_id)
    if not sub:
        return await message.answer('Subscription not found')
    else:
        return await message.answer('\n'.join([f'<b>{key}</b>: {str(value)}' for key, value in sub.items()]))


@admin_router.message(Command('sub_cancel'))
async def cancel_subscription_by_id_handler(message: TelegramMessage):
    parts = message.text.strip().split(maxsplit=1) if message.text else ['','']
    if len(parts) == 1:
        return await message.answer('Usage example: <code>/sub_cancel sc_123456789</code>')
    
    _, sub_id = parts
    status = await cp_get_subscription_status(sub_id)
    if not status:
        return await message.answer(f'Subscription had not been ever existed')
    else:
        await cp_cancel_subscription(sub_id)
        return await message.answer(f'Subscription was <b>{status}</b> and has been successfully cancelled')

