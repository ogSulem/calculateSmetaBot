from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.admin_fsm import AdminStates
from bot.admin_keyboards import (
    SECTIONS,
    kb_admin_coef,
    kb_admin_item_actions,
    kb_admin_items,
    kb_admin_main,
    kb_admin_sections,
)
from bot.db import get_config, set_config
from bot.handlers._shared import is_admin
from bot.settings import Settings

router = Router(name=__name__)


@router.message(Command("admin"))
async def admin_entry(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return

    await state.clear()
    await message.answer("Админ-панель", reply_markup=kb_admin_main())


@router.callback_query(F.data == "admin:home")
async def admin_home(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    await state.clear()
    await callback.message.edit_text("Админ-панель", reply_markup=kb_admin_main())
    await callback.answer()


@router.callback_query(F.data == "admin:sections")
async def admin_sections(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    await state.set_state(AdminStates.choosing_section)
    await callback.message.edit_text("Разделы", reply_markup=kb_admin_sections())
    await callback.answer()


def _section_title(section: str) -> str:
    for sec, title in SECTIONS:
        if sec == section:
            return title
    return section


@router.callback_query(F.data.startswith("admin:section:"))
async def admin_section(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer()
        return

    section = parts[2]
    settings = Settings()
    config = await get_config(settings.db_path)
    items = list(config.get(section, []))
    await state.update_data(admin_section=section)
    await state.set_state(AdminStates.choosing_item)
    await callback.message.edit_text(
        f"{_section_title(section)}: пункты",
        reply_markup=kb_admin_items(section, items),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:item:"))
async def admin_item(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 4:
        await callback.answer()
        return

    section, item_id = parts[2], parts[3]
    settings = Settings()
    config = await get_config(settings.db_path)
    items = list(config.get(section, []))
    item = next((x for x in items if str(x.get("id")) == item_id), None)
    if item is None:
        await callback.answer("Не найдено")
        return

    await state.update_data(admin_section=section, admin_item_id=item_id)
    enabled = bool(item.get("enabled", True))
    await callback.message.edit_text(
        "\n".join(
            [
                f"Раздел: {_section_title(section)}",
                f"Пункт: {item.get('title', item_id)}",
                f"id: {item_id}",
                f"price: {item.get('price', 0)}",
                f"order: {item.get('order', 0)}",
                f"enabled: {enabled}",
            ]
        ),
        reply_markup=kb_admin_item_actions(section, item_id, enabled),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:toggle:"))
async def admin_toggle(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 4:
        await callback.answer()
        return
    section, item_id = parts[2], parts[3]

    settings = Settings()
    config = await get_config(settings.db_path)
    items = list(config.get(section, []))
    item = next((x for x in items if str(x.get("id")) == item_id), None)
    if item is None:
        await callback.answer("Не найдено")
        return

    item["enabled"] = not bool(item.get("enabled", True))
    config[section] = items
    await set_config(settings.db_path, config)

    enabled = bool(item.get("enabled", True))
    await callback.message.edit_text(
        "\n".join(
            [
                f"Раздел: {_section_title(section)}",
                f"Пункт: {item.get('title', item_id)}",
                f"id: {item_id}",
                f"price: {item.get('price', 0)}",
                f"order: {item.get('order', 0)}",
                f"enabled: {enabled}",
            ]
        ),
        reply_markup=kb_admin_item_actions(section, item_id, enabled),
    )
    await callback.answer("Сохранено")


@router.callback_query(F.data.startswith("admin:field:"))
async def admin_edit_field(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 5:
        await callback.answer()
        return
    section, item_id, field = parts[2], parts[3], parts[4]
    await state.update_data(
        admin_section=section,
        admin_item_id=item_id,
        admin_field=field,
        admin_coef_key=None,
    )
    await state.set_state(AdminStates.waiting_value)
    await callback.message.answer(f"Введите новое значение для {field}")
    await callback.answer()


@router.message(AdminStates.waiting_value)
async def admin_value_input(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return
    if message.text is None:
        await message.answer("Введите значение текстом")
        return

    st = await state.get_data()
    coef_key = st.get("admin_coef_key")
    section = str(st.get("admin_section", ""))
    item_id = str(st.get("admin_item_id", ""))
    field = str(st.get("admin_field", ""))
    value_raw = message.text.strip()

    settings = Settings()
    config = await get_config(settings.db_path)

    if coef_key:
        try:
            if coef_key == "roof_coef":
                config["roof_coef"] = float(value_raw.replace(",", "."))
            elif coef_key == "area_limits":
                parts = [x.strip() for x in value_raw.split(",")]
                if len(parts) != 2:
                    raise ValueError
                min_a = int(parts[0])
                max_a = int(parts[1])
                config["area_limits"] = {"min": min_a, "max": max_a}
            else:
                await message.answer("Неизвестный параметр")
                return
        except ValueError:
            await message.answer("Некорректный формат значения")
            return

        await set_config(settings.db_path, config)
        await state.clear()
        await message.answer("Сохранено", reply_markup=kb_admin_main())
        return

    items = list(config.get(section, []))
    item = next((x for x in items if str(x.get("id")) == item_id), None)
    if item is None:
        await message.answer("Не найдено")
        await state.clear()
        return

    try:
        if field in {"price", "order"}:
            item[field] = float(value_raw) if field == "price" else int(value_raw)
        else:
            item[field] = value_raw
    except ValueError:
        await message.answer("Некорректный формат значения")
        return

    config[section] = items
    await set_config(settings.db_path, config)
    await state.set_state(AdminStates.choosing_item)
    await message.answer("Сохранено")


@router.callback_query(F.data == "admin:export")
async def admin_export(callback: CallbackQuery) -> None:
    if callback.message is None:
        return
    settings = Settings()
    config = await get_config(settings.db_path)

    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "config.json"
        p.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        await callback.message.answer_document(
            document=FSInputFile(str(p), filename="config.json"),
            caption="Экспорт конфигурации",
        )
    await callback.answer()


@router.callback_query(F.data == "admin:import")
async def admin_import(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    await state.set_state(AdminStates.importing_config)
    await callback.message.answer("Пришлите JSON-файл конфигурации (config.json)")
    await callback.answer()


@router.message(AdminStates.importing_config)
async def admin_import_file(message: Message, state: FSMContext) -> None:
    if not is_admin(message):
        return
    if message.document is None:
        await message.answer("Пришлите файл JSON")
        return

    bot = message.bot
    file = await bot.get_file(message.document.file_id)
    content = await bot.download(file)
    raw = content.getvalue().decode("utf-8", errors="replace")

    try:
        cfg = json.loads(raw)
    except json.JSONDecodeError:
        await message.answer("Не смог прочитать JSON")
        return

    if not isinstance(cfg, dict):
        await message.answer("Конфигурация должна быть JSON-объектом")
        return

    settings = Settings()
    await set_config(settings.db_path, cfg)
    await state.clear()
    await message.answer("Импорт выполнен", reply_markup=kb_admin_main())


@router.callback_query(F.data == "admin:add")
async def admin_add(callback: CallbackQuery) -> None:
    await callback.answer("Добавление пункта: следующий шаг")


@router.callback_query(F.data == "admin:edit")
async def admin_edit(callback: CallbackQuery) -> None:
    if callback.message is None:
        return
    await callback.message.edit_text("Коэффициенты и лимиты", reply_markup=kb_admin_coef())
    await callback.answer()


@router.callback_query(F.data == "admin:delete")
async def admin_delete(callback: CallbackQuery) -> None:
    await callback.answer("Удаление пункта: следующий шаг")


@router.callback_query(F.data.startswith("admin:coef:"))
async def admin_coef_choose(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer()
        return
    key = parts[2]
    await state.update_data(
        admin_coef_key=key,
        admin_section=None,
        admin_item_id=None,
        admin_field=None,
    )
    await state.set_state(AdminStates.waiting_value)
    if key == "area_limits":
        await callback.message.answer("Введите min,max (например 20,1000)")
    else:
        await callback.message.answer("Введите значение (например 1.2)")
    await callback.answer()
