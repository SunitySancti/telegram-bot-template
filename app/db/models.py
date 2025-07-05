from typing import Optional
from datetime import datetime
from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, Boolean, Index, UniqueConstraint, text, func
from sqlalchemy.orm import declarative_base, declared_attr, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs


DeclarativeBase = declarative_base()


class Base(AsyncAttrs, DeclarativeBase):
    __abstract__ = True  # to prevent creation of separate table for the model Base

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        server_onupdate=func.now()
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:
        return cls.__name__.lower() + 's'


class Message(Base):
    __table_args__ = (
        Index('idx_user_id_created_at', 'user_id', text('created_at DESC')),
        UniqueConstraint('user_id', 'message_tg_id', name='unique_user_message'),
    )
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False)
    user_tg_id: Mapped[str] = mapped_column(ForeignKey('users.tg_id', ondelete='CASCADE'), index=True, nullable=False)
    user = relationship('User', back_populates='messages')

    message_tg_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    from_bot: Mapped[bool] = mapped_column(Boolean, nullable=False)


class User(Base):
    tg_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    tg_username: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tg_fullname: Mapped[str] = mapped_column(String, nullable=False)
    
    rub_spent: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default='0')

    cloudpayments = relationship('Cloudpayment', back_populates='user')
    messages = relationship('Message', back_populates='user', cascade='all, delete-orphan')


class Cloudpayment(Base):
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), index=True, nullable=True)
    user_tg_id: Mapped[str] = mapped_column(String, nullable=False, server_default='')
    user = relationship('User', back_populates='cloudpayments')
    
    # service: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)

    transaction_id: Mapped[str] = mapped_column(String, nullable=False)
    invoice_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    auth_code: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    card_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    token: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    subscription_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
