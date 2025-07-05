from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select, delete, update
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from aiogram.types import User as TelegramUser
from app.db.database import connect_database
from app.db.models import User, Message, Cloudpayment
from app.util.logger import logger


class UserDAO:
    def __init__(self):
        pass

    @staticmethod
    async def get_by_id(user_id: int | str) -> User | None:
        async with connect_database() as session:
            try:
                return await session.get(User, int(user_id))
            except (SQLAlchemyError, IntegrityError) as e:
                logger.error(f'Error during user retrieving: {e}')
                return None

    @staticmethod
    async def get_by_tg_id(user_tg_id: int | str) -> User | None:
        async with connect_database() as session:
            try:
                statement = select(User).where(User.tg_id == str(user_tg_id))
                result = await session.execute(statement)
                return result.scalars().first()
            except (SQLAlchemyError, IntegrityError) as e:
                logger.error(f'Error during user retrieving: {e}')
                return None

    @staticmethod
    async def get_by_username(username: str) -> User | None:
        async with connect_database() as session:
            try:
                if username.startswith('@'):
                    username = username[1:]
                statement = select(User).where(User.tg_username == username)
                result = await session.execute(statement)
                return result.scalars().first()
            except (SQLAlchemyError, IntegrityError) as e:
                logger.error(f'Error during user retrieving: {e}')
                return None

    @staticmethod
    async def get_all() -> list[User]:
        async with connect_database() as session:
            try:
                result = await session.execute(select(User))
                return list(result.scalars().all())
            except (SQLAlchemyError, IntegrityError) as e:
                logger.error(f'Error during users retrieving: {e}')
                return []
            
    @staticmethod
    async def upsert(tg_user: TelegramUser | None) -> User | None:
        async with connect_database() as session:
            if not tg_user:
                return None
            try:
                statement = insert(User).values(
                    tg_id=str(tg_user.id),
                    tg_username=tg_user.username,
                    tg_fullname=tg_user.full_name,
                ).on_conflict_do_update(
                    index_elements=['tg_id'],
                    set_={
                        "tg_username": tg_user.username,
                        "tg_fullname": tg_user.full_name,
                    }
                ).returning(User)

                result = await session.execute(statement)
                await session.commit()
                return result.scalars().first()
            except (SQLAlchemyError, IntegrityError) as e:
                await session.rollback()
                logger.error(f'Error during user upsert: {e}')
                return None
    
    @staticmethod
    async def delete(user_tg_id: str | int) -> bool:
        async with connect_database() as session:
            statement = delete(User).where(User.tg_id == str(user_tg_id))
            try:
                await session.execute(statement)
                await session.commit()
                return True
            except (SQLAlchemyError, IntegrityError) as e:
                await session.rollback()
                logger.error(f'Error during user deletion: {e}')
                return False
   
    @staticmethod
    async def count_messages(user_id: int) -> int | None:
        async with connect_database() as session:
            statement = select(Message).where(Message.user_id == user_id, ~Message.from_bot)
            try:
                result = await session.execute(statement)
                return len(result.scalars().all())
            except (SQLAlchemyError, IntegrityError) as e:
                logger.error(f'Error during message counting: {e}')
                return None


class MessageDAO:
    def __init__(self):
        pass

    @staticmethod
    async def save(content: str, user_id: int, user_tg_id: str, message_tg_id: int, from_bot: bool) -> bool:
        async with connect_database() as session:
            try:
                statement = insert(Message).values(
                    user_id=user_id,
                    user_tg_id=user_tg_id,
                    message_tg_id=message_tg_id,
                    content=content,
                    from_bot=from_bot
                ).on_conflict_do_nothing(
                    index_elements=['user_tg_id', 'message_tg_id']
                ).returning(Message.id)
                
                await session.execute(statement)
                await session.commit()
                return True
            except (SQLAlchemyError, IntegrityError) as e:
                logger.error(f'Error during message insertion: {e}')
                await session.rollback()
                return False
    
    @staticmethod
    async def get_last(user_id: int, limit: Optional[int] = None) -> list[Message]:
        async with connect_database() as session:
            try:
                statement = select(Message).where(Message.user_id == user_id).order_by(Message.created_at.desc())
                if limit:
                    statement = statement.limit(limit)
                result = await session.execute(statement)
                return list(result.scalars().all())
            except (SQLAlchemyError, IntegrityError) as e:
                logger.error(f'Error during messages retrieving: {e}')
                return []
    
    @staticmethod
    async def get_one(message_tg_id: int) -> Message | None:
        async with connect_database() as session:
            try:
                statement = select(Message).where(Message.message_tg_id == message_tg_id)
                result = await session.execute(statement)
                return result.scalars().first()
            except (SQLAlchemyError, IntegrityError) as e:
                logger.error(f'Error during message retrieving: {e}')
                return None
    
    @staticmethod
    async def delete_all_for_user(user_id: int) -> bool:
        async with connect_database() as session:
            statement = delete(Message).where(Message.user_id == user_id)
            try:
                await session.execute(statement)
                await session.commit()
                return True
            except (SQLAlchemyError, IntegrityError) as e:
                logger.error(f'Error during messages deletion: {e}')
                await session.rollback()
                return False
    
    @staticmethod
    async def delete_last_for_user(user_id: int) -> bool:
        async with connect_database() as session:
            try:
                statement = select(Message).where(Message.user_id == user_id).order_by(Message.created_at.desc()).limit(1)
                result = await session.execute(statement)
                last_message = result.scalar_one_or_none()
                if last_message:
                    await session.delete(last_message)
                    await session.commit()
                    return True
                return False
            except (SQLAlchemyError, IntegrityError) as e:
                logger.error(f'Error during message deletion: {e}')
                await session.rollback()
                return False


class PaymentDAO:
    def __init__(self):
        pass
    
    @staticmethod
    async def save(payload: dict) -> dict:
        async with connect_database() as session:
            account_id = payload.get('AccountId', '')
            user_id, user_tg_id = account_id.split('_')
            currency = payload.get('Currency', 'RUB')
            amount = payload.get('Amount', 0)
            status = payload.get('Status', 'Undefined')
            transaction_id = payload.get('TransactionId', '')
            invoice_id = payload.get('InvoiceId')
            auth_code = payload.get('AuthCode')
            card_id = payload.get('CardId')
            token = payload.get('Token')
            subscription_id = payload.get('SubscriptionId')

            statement = insert(Cloudpayment).values(
                user_id=int(user_id),
                user_tg_id=user_tg_id,
                currency=currency,
                amount=amount,
                status=status,
                transaction_id=transaction_id,
                invoice_id=invoice_id,
                auth_code=auth_code,
                card_id=card_id,
                token=token,
                subscription_id=subscription_id
            ).returning(Cloudpayment.id)

            try:
                await session.execute(statement)
                await session.commit()
        
            except SQLAlchemyError as e:
                await session.rollback()
                logger.error(f'Error during payment insertion: {e}')

    @staticmethod
    async def get_successful_ones_by_period(from_ts: Optional[int] = None, till_ts: Optional[int] = None) -> list[Cloudpayment]:
        async with connect_database() as session:
            filters = []
            if from_ts is not None:
                from_dt = datetime.fromtimestamp(from_ts, tz=timezone.utc)
                filters.append(Cloudpayment.created_at >= from_dt)
            if till_ts is not None:
                till_dt = datetime.fromtimestamp(till_ts, tz=timezone.utc)
                filters.append(Cloudpayment.created_at <= till_dt)
            
            statement = select(Cloudpayment).where(Cloudpayment.status == 'Success')
            if filters:
                statement = statement.where(*filters)
            result = await session.execute(statement)
            return list(result.scalars().all())


class DAO:
    User = UserDAO
    Message = MessageDAO
    Payment = PaymentDAO

