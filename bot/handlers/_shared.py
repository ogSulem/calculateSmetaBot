from __future__ import annotations

from aiogram.types import Message

from bot.settings import Settings


def is_admin(message: Message) -> bool:
    if message.from_user is None:
        return False
    settings = Settings()
    return message.from_user.id in settings.admin_id_set()
