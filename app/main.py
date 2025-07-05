from contextlib import asynccontextmanager
from aiogram.types import Update, BotCommand
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.db.database import check_database
from app.bot.main import dp
from app.bot.instance import bot
from app.util.config import config
from app.util.logger import logger
from app.payments.cp_notifications import cloudpayments_router


TELEGRAM_WEBHOOK_PATH = '/telegram/webhook'
CLOUDPAYMENTS_WEBHOOK_PATH = '/cloudpayments/webhook'

@asynccontextmanager
async def lifespan(app: FastAPI):
    url = 'https://' + config.TELEGRAM_BOT_HOST + TELEGRAM_WEBHOOK_PATH
    await bot.set_webhook(
        url=url,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True
    )
    await bot.set_my_commands([
        BotCommand(command='start', description='Запустить бота'),
    ])
    logger.info('Telegram webhook set to ' + url)
    yield
    await bot.delete_webhook()

app = FastAPI(lifespan=lifespan)

app.mount('/static', StaticFiles(directory='/static'), name='static')

app.add_middleware(TrustedHostMiddleware, allowed_hosts=[config.TELEGRAM_BOT_HOST])

@app.middleware('http')
async def force_https_scheme(request: Request, call_next):
    request.scope['scheme'] = 'https'
    return await call_next(request)


# HANDLING EXCEPTIONS

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={'error': 'HTTP error', 'detail': exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={'error': 'Internal server error'}
    )

@app.get('/check_database')
async def check_database():
    return await check_database()


# WEBHOOKS

@app.post(TELEGRAM_WEBHOOK_PATH)
async def webhook(request: Request) -> None:
    update = Update.model_validate(await request.json(), context={'bot': bot})
    await dp.feed_update(bot, update)

app.include_router(cloudpayments_router, prefix=CLOUDPAYMENTS_WEBHOOK_PATH, tags=['cloudpayments'])

