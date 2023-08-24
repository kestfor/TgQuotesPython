import sql
from aiogram import types, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.command import Command
from sql import connection
from utils import (get_menu_inline_keyboard,
                   quote_filter, name_filter)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = get_menu_inline_keyboard()
    await message.answer("Привет, я бот с цитатами, ты можешь попросить меня прислать цитату определенной категории "
                         "или добавить свою собственную, попробуй!",
                         reply_markup=builder.as_markup(resize_keyboard=True))


@router.message(Command("menu"))
async def cmd_menu(message: types.Message):
    builder = get_menu_inline_keyboard()
    await message.answer("главное меню", reply_markup=builder.as_markup(resize_keyboard=True))


@router.message(quote_filter)
async def cmd_add_quote(message: types.Message):
    user_name = await sql.get_user_name(connection, message.chat.id)
    if user_name is None:
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="Ввести имя", callback_data="set_name"))
        await message.answer("Для того чтобы добавить цитату, нужно указать свое имя", reply_markup=builder.as_markup())
    else:
        data = {}
        category_id = await sql.get_category_id(connection, "categories", "from_users")
        data["category_id"] = category_id
        data["quote"] = message.text
        data["author"] = await sql.get_user_name(connection, message.chat.id)
        data["chat_id"] = message.chat.id
        await sql.add_quote(connection, "from_users", data)
        amount_quotes = await sql.get_amount_user_quotes(connection, message.chat.id)
        await message.answer(f"Новая цитата добавлена, всего твоих цитат: "
                             f"{amount_quotes}",
                             reply_markup=get_menu_inline_keyboard().as_markup())


@router.message(name_filter)
async def cmd_set_name(message: types.Message):
    user_name = message.text
    if user_name:
        old_name = await sql.get_user_name(connection, message.chat.id)
        if old_name == user_name:
            text = "Это и есть твое имя"
        elif old_name is not None:
            await sql.update_user_name(connection, message.chat.id, user_name)
            text = f"Решил поменять имя? почему бы и нет, теперь ты {user_name}"
        else:
            await sql.add_user(connection, message.chat.id, user_name)
            text = f"Теперь я тебя запомню, {user_name}"
        await message.answer(text, parse_mode="html", reply_markup=get_menu_inline_keyboard().as_markup())
