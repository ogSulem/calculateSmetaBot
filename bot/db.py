from __future__ import annotations

import json
from typing import Any

import aiosqlite


DEFAULT_CONFIG: dict[str, Any] = {
    "area_limits": {"min": 20, "max": 1000},
    "roof_coef": 1.2,
    "foundation": [
        {"id": "pile", "title": "Свайный", "price": 1000, "enabled": True, "order": 10},
        {"id": "strip", "title": "Ленточный", "price": 1800, "enabled": True, "order": 20},
        {"id": "slab", "title": "Плита", "price": 2500, "enabled": True, "order": 30},
    ],
    "walls": [
        {"id": "aerated", "title": "Газобетон", "price": 3500, "enabled": True, "order": 10},
        {"id": "brick", "title": "Кирпич", "price": 5200, "enabled": True, "order": 20},
        {"id": "frame", "title": "Каркас", "price": 3000, "enabled": True, "order": 30},
    ],
    "floors": [
        {"id": "wood", "title": "Деревянные", "price": 1500, "enabled": True, "order": 10},
        {"id": "rc", "title": "Ж/б плиты", "price": 2400, "enabled": True, "order": 20},
    ],
    "roof": [
        {"id": "metal", "title": "Металлочерепица", "price": 1600, "enabled": True, "order": 10},
        {"id": "soft", "title": "Мягкая кровля", "price": 2100, "enabled": True, "order": 20},
    ],
    "extras": [
        {"id": "electric", "title": "Электрика", "price": 900, "enabled": True, "order": 10},
        {"id": "water", "title": "Водоснабжение", "price": 700, "enabled": True, "order": 20},
        {"id": "sewer", "title": "Канализация", "price": 650, "enabled": True, "order": 30},
        {"id": "heating", "title": "Отопление", "price": 1100, "enabled": True, "order": 40},
        {"id": "windows", "title": "Окна и двери", "price": 1300, "enabled": True, "order": 50},
        {"id": "rough", "title": "Черновая отделка", "price": 2000, "enabled": True, "order": 60},
    ],
}


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )
        await db.commit()

        cur = await db.execute("SELECT value_json FROM config WHERE key = ?", ("app_config",))
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO config(key, value_json) VALUES(?, ?)",
                ("app_config", json.dumps(DEFAULT_CONFIG, ensure_ascii=False)),
            )
            await db.commit()


async def get_config(db_path: str) -> dict[str, Any]:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute("SELECT value_json FROM config WHERE key = ?", ("app_config",))
        row = await cur.fetchone()
        if row is None:
            return DEFAULT_CONFIG
        try:
            return json.loads(row[0])
        except json.JSONDecodeError:
            return DEFAULT_CONFIG


async def set_config(db_path: str, config: dict[str, Any]) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE config SET value_json = ?, updated_at = datetime('now') WHERE key = ?",
            (json.dumps(config, ensure_ascii=False), "app_config"),
        )
        await db.commit()
