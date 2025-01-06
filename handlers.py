import logging
import random

from aiogram import Router, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command, StateFilter
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, \
    InlineKeyboardButton

import requests

from utils.utils import load_config
from utils.utils import validate_api_key, save_config
from keyboards.kb import del_kb, inline_choice_shop

router = Router()


@router.message(Command(commands=["start", "help"]))
async def help_for_user(message: Message):
    commands = (
        "/addshop - Добавить магазин\n"
        "/delshop - Удалить магазин\n"
        "/shops - Список магазинов\n"
        "/report - Получить отчет о продажах\n"
        "/help - Помощь"
    )
    await message.reply(f"Добро пожаловать, {message.from_user.first_name}!\n"
                        f"Вот доступные команды: \n{commands}")


class AddShopState(StatesGroup):
    api_key = State()


@router.message(Command("addshop"))
async def add_shop(message: Message, state: FSMContext):
    await state.set_state(AddShopState.api_key)
    await message.answer("Введите API ключ магазина:")


@router.message(AddShopState.api_key)
async def process_add_shop(message: Message, state: FSMContext):
    api_key = message.text
    response_validate_api_key = validate_api_key(api_key)
    headers = {"Authorization": f"Bearer {api_key}"}

    if response_validate_api_key["status_code"] in [401, 429, 500]:
        await message.answer(response_validate_api_key["message"])
    else:
        url_name_shop = ""  # production
        url_name_shop_dev = random.choice(["adidas", "nike", "li-ning"])
        try:
            #response = requests.get(url=url_name_shop, headers=headers)  # production
            response_dev = url_name_shop_dev
            result = {"api_key": api_key, "name_shop": response_dev}
            save = save_config(result)
            if not save:
                await message.reply("Магазин успешно добавлен в базу.")
            elif save == 409:
                await message.reply("Магазин уже был добавлен в базу")
        #except requests.RequestException as e:  # production
        except Exception as e:  # dev
            logging.error(f"Ошибка при проверке API ключа в процессе: {e}")
    await state.clear()


class DeleteShopState(StatesGroup):
    name_shop = State()


@router.message(Command("delshop"))
async def delete_shop(message: Message, state: FSMContext):
    config = load_config()
    if not config:
        await message.reply("У вас нет сохраненных магазинов.")
        return
    await state.set_state(DeleteShopState.name_shop)
    await message.answer("Введите название магазина, которую хотите удалить:")


@router.message(DeleteShopState.name_shop)
async def process_delete_first(message: Message, state: FSMContext):
    input_name_shop = message.text
    config = load_config()

    shop_found = next(
        (shop for shop in config if shop.get("name_shop") == input_name_shop),
        None)

    if not shop_found:
        await message.reply(f"Магазина с названием {input_name_shop} не найдено.")
        return

    del_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Да", callback_data=f"confirm_del_{input_name_shop}"),
             InlineKeyboardButton(text="Нет", callback_data="cancel_del")]
        ]
    )

    await message.reply(f"Вы подтверждаете удаление магазина?",
                        reply_markup=del_kb)
    await state.clear()


@router.callback_query(lambda c: c.data.startswith('confirm_del_') or c.data == "cancel_del")
async def process_delete_second(callback: CallbackQuery):
    config_list = load_config()

    if callback.data.startswith("confirm_del_"):
        shop_name = callback.data[len("confirm_del_"):]

        for shop in config_list:
            if shop.get("name_shop") == shop_name:
                config_list.remove(shop)
                await callback.answer("Удалено")

                await callback.message.answer(f"Магазин '{shop_name}' был удален из сохраненных.")
        save_config(config_list)

    elif callback.data == "cancel_del":
        await callback.answer("Отмена")
        await callback.message.answer("Удаление отменено.")
    else:
        await callback.answer("")
        await callback.message.answer("Принимается только: Да / Нет")


@router.message(Command("shops"))
async def get_shops(message: Message):
    config_list = load_config()
    print(config_list)
    if not config_list:
        await message.reply("У вас нет сохраненных магазинов.")
        return
    new_str = ""
    for shop in config_list:
        new_str += f"{shop["name_shop"]}\n"

    await message.answer(f"Список ваших магазинов: \n{new_str}")


class Form(StatesGroup):
    waiting_for_shop = State()
    waiting_for_date = State()

@router.message(Command("report"))
async def report(message: Message, state: FSMContext):
    config_list = load_config()

    if len(config_list) == 1:
        await message.answer("Пожалуйста, укажите дату в формате year-month-day:")
        await state.set_state(Form.waiting_for_date)
        await state.update_data(shop_name=config_list[0]["name_shop"])
    elif len(config_list) > 1:
        await message.answer("Выберите магазин:", reply_markup=await inline_choice_shop())
        await state.set_state(Form.waiting_for_shop)


@router.callback_query(StateFilter(Form.waiting_for_shop))
async def shop_selected(callback_query: CallbackQuery, state: FSMContext):
    print("work shop_selected")
    shop_name = callback_query.data
    config_list = load_config()
    selected_shop = next((shop for shop in config_list if shop["name_shop"] == shop_name), None)  # dict object

    if selected_shop:
        await state.update_data(shop_name=shop_name)
        await state.set_state(Form.waiting_for_date)
        await callback_query.message.answer("Теперь, пожалуйста, укажите дату в формате year-month-day:")


@router.message(StateFilter(Form.waiting_for_date))
async def handle_date(message: Message, state: FSMContext):
    selected_shop = (await state.get_data()).get("shop_name")
    url = "https://statistics-api.wildberries.ru/api/v1/supplier/sales"
    try:
        date = message.text
        year, month, day = map(int, date.split("-"))
        if year > 0 and 1 <= month <= 12 and 1 <= day <= 31:
            config_list = load_config()
            shop = next((shop for shop in config_list if shop["name_shop"] == selected_shop), None)
            if shop:
                api_key = shop["api_key"]
                url += f"?dateFrom={date}"
                try:
                    response = requests.get(url, headers={"Authorization": f"Bearer {api_key}"})
                    response.raise_for_status()
                    sales_data = response.json()

                    total_sales = 0
                    total_commission = 0
                    total_discounts = 0
                    total_acquiring_fee = 0
                    total_logistics_cost = 0
                    total_storage_cost = 0
                    total_units_sold = 0

                    for sale in sales_data:
                        total_sales += sale.get('forPay', 0)
                        total_commission += sale.get('commissionPercent',
                                                     0) / 100 * sale.get(
                            'priceWithDisc', 0)
                        total_discounts += sale.get('totalPrice',
                                                    0) - sale.get(
                            'priceWithDisc', 0)
                        total_acquiring_fee += sale.get('acquiringPercent',
                                                        0) / 100 * sale.get(
                            'priceWithDisc', 0)
                        total_logistics_cost += sale.get('deliveryCost', 0)
                        total_storage_cost += sale.get('storageCost', 0)
                        total_units_sold += sale.get('quantity', 1)

                    average_sale_price = total_sales / total_units_sold if total_units_sold > 0 else 0

                    report_ = (
                        f"__Отчёт по продажам__\n\n"
                        f"__Общая сумма продаж:__ {total_sales:.2f} сом.\n"
                        f"__Комиссия Wildberries:__ {total_commission:.2f} сом.\n"
                        f"__Скидки Wildberries:__ {total_discounts:.2f} сом.\n"
                        f"__Комиссия эквайринга:__ {total_acquiring_fee:.2f} сом.\n"
                        f"__Стоимость логистики:__ {total_logistics_cost:.2f} сом.\n"
                        f"__Стоимость хранения:__ {total_storage_cost:.2f} сом.\n"
                        f"__Количество проданных единиц:__ {total_units_sold} шт.\n"
                        f"__Средняя цена продажи:__ {average_sale_price:.2f} сом.\n"
                    )

                    await message.answer(report_, parse_mode="Markdown")
                except requests.RequestException as e:
                    print(e)
            else:
                await message.answer("Ошибка, магазин не найден.")
        else:
            await message.answer("Неверный формат даты, попробуйте еще раз.")
    except ValueError:
        await message.answer("Неверный формат даты, попробуйте еще раз.")

