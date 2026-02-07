from __future__ import annotations

from typing import FrozenSet

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str
    admin_ids: str = ""
    db_path: str = "bot.db"

    def admin_id_set(self) -> FrozenSet[int]:
        raw = [x.strip() for x in self.admin_ids.split(",") if x.strip()]
        ids: set[int] = set()
        for item in raw:
            try:
                ids.add(int(item))
            except ValueError:
                continue
        return frozenset(ids)
