from __future__ import annotations

from typing import Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


SECTIONS: list[tuple[str, str]] = [
    ("foundation", "Фундамент"),
    ("walls", "Стены"),
    ("floors", "Перекрытия"),
    ("roof", "Кровля"),
    ("extras", "Доп. работы"),
]


def kb_admin_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Цены и коэффициенты", callback_data="admin:sections")],
            [InlineKeyboardButton(text="➕ Добавить пункт", callback_data="admin:add")],
            [InlineKeyboardButton(text="✏️ Изменить пункт", callback_data="admin:edit")],
            [InlineKeyboardButton(text="❌ Удалить пункт", callback_data="admin:delete")],
            [InlineKeyboardButton(text="📤 Экспорт конфигурации", callback_data="admin:export")],
            [InlineKeyboardButton(text="📥 Импорт конфигурации", callback_data="admin:import")],
        ]
    )


def kb_admin_sections() -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=title, callback_data=f"admin:section:{sec}")] for sec, title in SECTIONS]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_admin_items(section: str, items: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for it in sorted(items, key=lambda x: x.get("order", 0)):
        it_id = str(it.get("id"))
        title = str(it.get("title", it_id))
        enabled = bool(it.get("enabled", True))
        mark = "🟢" if enabled else "⚫️"
        rows.append([InlineKeyboardButton(text=f"{mark} {title}", callback_data=f"admin:item:{section}:{it_id}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:sections")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_admin_item_actions(section: str, item_id: str, enabled: bool) -> InlineKeyboardMarkup:
    toggle_text = "Выключить" if enabled else "Включить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"{toggle_text}", callback_data=f"admin:toggle:{section}:{item_id}")],
            [InlineKeyboardButton(text="Изменить название", callback_data=f"admin:field:{section}:{item_id}:title")],
            [InlineKeyboardButton(text="Изменить цену (₽/м²)", callback_data=f"admin:field:{section}:{item_id}:price")],
            [InlineKeyboardButton(text="Изменить порядок", callback_data=f"admin:field:{section}:{item_id}:order")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"admin:section:{section}")],
        ]
    )


def kb_admin_coef() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Коэф. площади кровли (roof_coef)", callback_data="admin:coef:roof_coef")],
            [InlineKeyboardButton(text="Лимиты площади (area_limits)", callback_data="admin:coef:area_limits")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:home")],
        ]
    )
