from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.utils import rub


def kb_start() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🧮 Рассчитать смету", callback_data="calc:start")],
            [InlineKeyboardButton(text="ℹ️ Как работает расчёт", callback_data="calc:info")],
        ]
    )


def kb_back_to_start() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ В начало", callback_data="calc:home")]]
    )


def kb_options(section: str, items: list[dict[str, Any]], *, area: float, roof_coef: float = 1.0) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for item in sorted([x for x in items if x.get("enabled", True)], key=lambda x: x.get("order", 0)):
        price = float(item.get("price", 0) or 0)
        eff_area = area * roof_coef if section == "roof" else area
        cost = eff_area * price
        rows.append([
            InlineKeyboardButton(
                text=f"{item.get('title', item.get('id'))} — {rub(cost)}",
                callback_data=f"pick:{section}:{item.get('id')}"
            )
        ])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="calc:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_extras(items: list[dict[str, Any]], selected: set[str], *, area: float) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for item in sorted([x for x in items if x.get("enabled", True)], key=lambda x: x.get("order", 0)):
        item_id = str(item.get("id"))
        title = str(item.get("title", item_id))
        price = float(item.get("price", 0) or 0)
        cost = area * price
        mark = "✅" if item_id in selected else "⬜️"
        rows.append([
            InlineKeyboardButton(text=f"{mark} {title} — {rub(cost)}", callback_data=f"toggle:extras:{item_id}")
        ])
    rows.append([InlineKeyboardButton(text="Готово", callback_data="extras:done")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="calc:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_result() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Скачать смету в Excel", callback_data="result:xlsx")],
            [InlineKeyboardButton(text="🔁 Посчитать заново", callback_data="calc:restart")],
            [InlineKeyboardButton(text="📞 Связаться с менеджером", callback_data="result:contact")],
        ]
    )


def kb_back_to_result() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад к результату", callback_data="result:back")]]
    )
