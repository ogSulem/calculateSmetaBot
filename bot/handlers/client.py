from __future__ import annotations

from typing import Any

from aiogram import F, Router
from aiogram.filters import CommandStart
import tempfile
from pathlib import Path

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message

from bot.db import get_config
from bot.excel import build_estimate_xlsx
from bot.fsm import CalcStates
from bot.keyboards import (
    kb_back_to_result,
    kb_back_to_start,
    kb_extras,
    kb_options,
    kb_result,
    kb_start,
)
from bot.settings import Settings
from bot.utils import fmt_lines, rub, safe_float

router = Router(name=__name__)


SECTION_ORDER: list[str] = ["foundation", "walls", "floors", "roof"]


async def _ui_edit_or_answer(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup=None,
) -> None:
    ui_message_id = (await state.get_data()).get("ui_message_id")
    if ui_message_id:
        await message.bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=int(ui_message_id),
            text=text,
            reply_markup=reply_markup,
        )
        return
    sent = await message.answer(text, reply_markup=reply_markup)
    await state.update_data(ui_message_id=sent.message_id)


async def _try_delete_user_message(message: Message) -> None:
    try:
        await message.delete()
    except TelegramBadRequest:
        return


def _drop_dependent(items: list[dict[str, Any]], from_section: str) -> list[dict[str, Any]]:
    if from_section not in SECTION_ORDER:
        return items
    idx = SECTION_ORDER.index(from_section)
    drop_sections = set(SECTION_ORDER[idx:]) | {"extras"}
    return [it for it in items if str(it.get("section")) not in drop_sections]


@router.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "Добро пожаловать в калькулятор строительной сметы.\n"
        "Рассчитайте предварительную стоимость дома за 2–3 минуты.",
        reply_markup=kb_start(),
    )


@router.callback_query(F.data == "calc:info")
async def how_it_works(callback: CallbackQuery) -> None:
    if callback.message is None:
        return
    await callback.message.edit_text(
        fmt_lines(
            [
                "Как работает расчёт:",
                "1) Вы вводите площадь дома.",
                "2) Выбираете материалы/работы по этапам.",
                "3) Бот считает стоимость по ценам за м² и коэффициентам.",
                "",
                "Расчёт является предварительным и не является публичной офертой.",
            ]
        ),
        reply_markup=kb_back_to_start(),
    )
    await callback.answer()


@router.callback_query(F.data == "result:contact")
async def contact(callback: CallbackQuery) -> None:
    if callback.message is None:
        return
    await callback.message.edit_text(
        "Напишите ваш номер телефона и город, и менеджер свяжется с вами в ближайшее время.",
        reply_markup=kb_back_to_result(),
    )
    await callback.answer()


@router.callback_query(F.data == "result:back")
async def result_back(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    data = await state.get_data()
    text = data.get("result_text")
    if not text:
        await callback.answer("Нет результата")
        return
    await callback.message.edit_text(str(text), reply_markup=kb_result())
    await callback.answer()


@router.callback_query(F.data == "result:xlsx")
async def download_xlsx(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    data = await state.get_data()
    area = float(data.get("area", 0))
    items = list(data.get("items", []))
    total = float(data.get("total", 0))
    price_per_m2 = float(data.get("price_per_m2", 0))

    if area <= 0 or not items:
        await callback.answer("Сначала сделайте расчёт")
        return

    with tempfile.TemporaryDirectory() as tmp:
        file_path = Path(tmp) / "estimate.xlsx"
        build_estimate_xlsx(
            path=file_path,
            area=area,
            items=items,
            total=total,
            price_per_m2=price_per_m2,
        )

        await callback.message.answer_document(
            document=FSInputFile(str(file_path), filename="smeta.xlsx"),
            caption="Смета в Excel",
        )

    await callback.answer()


@router.callback_query(F.data.in_({"calc:home", "calc:restart"}))
async def go_home(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    if callback.message is None:
        return
    await state.update_data(ui_message_id=callback.message.message_id)
    await callback.message.edit_text(
        "Добро пожаловать в калькулятор строительной сметы.\n"
        "Рассчитайте предварительную стоимость дома за 2–3 минуты.",
        reply_markup=kb_start(),
    )
    await callback.answer()


@router.callback_query(F.data == "calc:start")
async def calc_start(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CalcStates.awaiting_area)
    if callback.message is None:
        return
    await state.update_data(ui_message_id=callback.message.message_id)
    await callback.message.edit_text("Введите площадь дома в м² (только число)")
    await callback.answer()


@router.message(CalcStates.awaiting_area)
async def area_input(message: Message, state: FSMContext) -> None:
    if message.text is None:
        await _ui_edit_or_answer(message, state, "Введите площадь числом.")
        return

    area = safe_float(message.text)
    if area is None:
        await _ui_edit_or_answer(message, state, "Не понял площадь. Введите число, например 120")
        return

    settings = Settings()
    config = await get_config(settings.db_path)
    limits = config.get("area_limits", {})
    min_a = float(limits.get("min", 20))
    max_a = float(limits.get("max", 1000))

    if area < min_a or area > max_a:
        await _ui_edit_or_answer(message, state, f"Площадь должна быть от {int(min_a)} до {int(max_a)} м²")
        return

    await state.update_data(area=float(area), items=[], extras=set())
    await state.set_state(CalcStates.choosing_foundation)

    foundations = config.get("foundation", [])
    await _ui_edit_or_answer(
        message,
        state,
        "Выберите тип фундамента",
        reply_markup=kb_options("foundation", foundations, area=float(area)),
    )

    await _try_delete_user_message(message)


@router.message(
    CalcStates.choosing_foundation,
    CalcStates.choosing_walls,
    CalcStates.choosing_floors,
    CalcStates.choosing_roof,
    CalcStates.choosing_extras,
)
async def unexpected_text_during_buttons(message: Message, state: FSMContext) -> None:
    await _try_delete_user_message(message)
    await _ui_edit_or_answer(
        message,
        state,
        "Пожалуйста, выберите вариант кнопкой ниже.",
    )


@router.message(CalcStates.showing_result)
async def unexpected_text_on_result(message: Message, state: FSMContext) -> None:
    await _try_delete_user_message(message)
    data = await state.get_data()
    text = data.get("result_text")
    if text:
        await _ui_edit_or_answer(message, state, str(text), reply_markup=kb_result())
    else:
        await _ui_edit_or_answer(message, state, "Нажмите «Посчитать заново» чтобы начать", reply_markup=kb_result())


@router.callback_query(F.data == "calc:back")
async def go_back(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    current = await state.get_state()
    if callback.message is None:
        return

    settings = Settings()
    config = await get_config(settings.db_path)
    area = float(data.get("area", 0))
    roof_coef = float(config.get("roof_coef", 1.0))
    if current == CalcStates.choosing_walls.state:
        await state.set_state(CalcStates.choosing_foundation)
        await callback.message.edit_text(
            "Выберите тип фундамента",
            reply_markup=kb_options("foundation", config.get("foundation", []), area=area),
        )
    elif current == CalcStates.choosing_floors.state:
        await state.set_state(CalcStates.choosing_walls)
        await callback.message.edit_text(
            "Выберите тип стен",
            reply_markup=kb_options("walls", config.get("walls", []), area=area),
        )
    elif current == CalcStates.choosing_roof.state:
        await state.set_state(CalcStates.choosing_floors)
        await callback.message.edit_text(
            "Выберите тип перекрытий",
            reply_markup=kb_options("floors", config.get("floors", []), area=area),
        )
    elif current == CalcStates.choosing_extras.state:
        await state.set_state(CalcStates.choosing_roof)
        await callback.message.edit_text(
            "Выберите тип кровли",
            reply_markup=kb_options("roof", config.get("roof", []), area=area, roof_coef=roof_coef),
        )
    else:
        await state.clear()
        await callback.message.edit_text(
            "Добро пожаловать в калькулятор строительной сметы.\n"
            "Рассчитайте предварительную стоимость дома за 2–3 минуты.",
            reply_markup=kb_start(),
        )

    await callback.answer()


def _find_item(items: list[dict[str, Any]], item_id: str) -> dict[str, Any] | None:
    for it in items:
        if str(it.get("id")) == item_id and it.get("enabled", True):
            return it
    return None


@router.callback_query(F.data.startswith("pick:"))
async def pick_option(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer()
        return

    section, item_id = parts[1], parts[2]
    settings = Settings()
    config = await get_config(settings.db_path)
    data = await state.get_data()
    area = float(data.get("area", 0))

    section_items = config.get(section, [])
    item = _find_item(section_items, item_id)
    if item is None:
        await callback.answer("Пункт недоступен")
        return

    items = list(data.get("items", []))
    roof_coef = float(config.get("roof_coef", 1.0))

    items = _drop_dependent(items, section)
    await state.update_data(items=items, extras=set())

    item_area = area * roof_coef if section == "roof" else area

    items.append(
        {
            "section": section,
            "id": item_id,
            "title": item.get("title", item_id),
            "area": item_area,
            "price": float(item.get("price", 0)),
        }
    )
    await state.update_data(items=items)

    cost = item_area * float(item.get("price", 0))

    if section == "foundation":
        await state.set_state(CalcStates.choosing_walls)
        await callback.message.edit_text(
            fmt_lines([f"Фундамент: {item.get('title')} — {rub(cost)}", "", "Выберите тип стен"]),
            reply_markup=kb_options("walls", config.get("walls", []), area=area),
        )
    elif section == "walls":
        await state.set_state(CalcStates.choosing_floors)
        await callback.message.edit_text(
            fmt_lines([f"Стены: {item.get('title')} — {rub(cost)}", "", "Выберите тип перекрытий"]),
            reply_markup=kb_options("floors", config.get("floors", []), area=area),
        )
    elif section == "floors":
        await state.set_state(CalcStates.choosing_roof)
        await callback.message.edit_text(
            fmt_lines([f"Перекрытия: {item.get('title')} — {rub(cost)}", "", "Выберите тип кровли"]),
            reply_markup=kb_options("roof", config.get("roof", []), area=area, roof_coef=roof_coef),
        )
    elif section == "roof":
        await state.set_state(CalcStates.choosing_extras)
        selected: set[str] = set(data.get("extras", set()))
        await callback.message.edit_text(
            fmt_lines([f"Кровля: {item.get('title')} — {rub(cost)}", "", "Дополнительные работы:"]),
            reply_markup=kb_extras(config.get("extras", []), selected, area=area),
        )
    else:
        await callback.message.edit_text("Ок")

    await callback.answer()


@router.callback_query(F.data.startswith("toggle:extras:"))
async def toggle_extra(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    parts = (callback.data or "").split(":")
    if len(parts) != 3:
        await callback.answer()
        return

    extra_id = parts[2]
    data = await state.get_data()
    selected = set(data.get("extras", set()))
    if extra_id in selected:
        selected.remove(extra_id)
    else:
        selected.add(extra_id)
    await state.update_data(extras=selected)

    settings = Settings()
    config = await get_config(settings.db_path)
    area = float(data.get("area", 0))
    await callback.message.edit_reply_markup(reply_markup=kb_extras(config.get("extras", []), selected, area=area))
    await callback.answer()


@router.callback_query(F.data == "extras:done")
async def extras_done(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    data = await state.get_data()
    settings = Settings()
    config = await get_config(settings.db_path)

    area = float(data.get("area", 0))
    selected = set(data.get("extras", set()))

    items: list[dict[str, Any]] = list(data.get("items", []))

    for extra in config.get("extras", []):
        if not extra.get("enabled", True):
            continue
        extra_id = str(extra.get("id"))
        if extra_id not in selected:
            continue
        items.append(
            {
                "section": "extras",
                "id": extra_id,
                "title": extra.get("title", extra_id),
                "area": area,
                "price": float(extra.get("price", 0)),
            }
        )

    total = 0.0
    for it in items:
        it_area = float(it.get("area", 0))
        total += it_area * float(it.get("price", 0))

    price_per_m2 = total / area if area > 0 else 0.0
    await state.set_state(CalcStates.showing_result)
    result_text = fmt_lines(
        [
            f"Площадь: {int(area)} м²",
            f"Итого: {rub(total)}",
            f"Цена за м²: {rub(price_per_m2)}",
            "",
            "Расчёт является предварительным и не является публичной офертой.",
        ]
    )
    await state.update_data(items=items, total=total, price_per_m2=price_per_m2, result_text=result_text)

    await callback.message.edit_text(result_text, reply_markup=kb_result())
    await callback.answer()
