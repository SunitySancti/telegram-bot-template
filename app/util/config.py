from pydantic_settings import BaseSettings
from typing import Optional


class Config(BaseSettings):
    DEV: bool = True
    LOG_BLOCK_WIDTH: int = 100

    TELEGRAM_BOT_HOST: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ADMIN_IDS: str = ''

    def is_admin(self, user_tg_id: str) -> bool:
        return user_tg_id in self.TELEGRAM_ADMIN_IDS.strip().split('_')

    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_NAME: str
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    @property
    def DB_URL(self) -> str:
        return f'postgresql+asyncpg://{self.POSTGRES_USERNAME}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_NAME}'

    CLOUDPAYMENTS_PUBLIC_ID: Optional[str] = None
    CLOUDPAYMENTS_API_SECRET: Optional[str] = None

    LAW_PRIVACY_POLICY_URL: Optional[str] = None
    LAW_PUBLIC_OFFER_URL: Optional[str] = None
    @property
    def DISCLAIMER(self):
        if self.LAW_PRIVACY_POLICY_URL and self.LAW_PUBLIC_OFFER_URL:
            return f'<i>Продолжая вы соглашаетесь с <a href="{self.LAW_PRIVACY_POLICY_URL}">Политикой конфинденциальности</a> и <a href="{self.LAW_PUBLIC_OFFER_URL}">Публичной офертой</a></i>'
        return ''

config = Config()

