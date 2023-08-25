from aiogram import types, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.command import Command
from sql import db
from utils import (get_menu_inline_keyboard,
                   quote_filter, name_filter)

router = Router()


@router.message(Command("start"))
async def cmd_start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="ввести имя", callback_data="set_name"))
    builder.row(types.InlineKeyboardButton(text="продолжить без аутентификации", callback_data="clear_comeback_to_menu"))
    await message.answer("Привет, я бот с цитатами, ты можешь попросить меня прислать цитату определенной категории "
                         "или добавить свою собственную, попробуй!\n"
                         "Ты можешь ввести имя, для того чтобы добавлять свои цитаты или лайкать существующие,"
                         " либо продолжить без аутентификации, "
                         "вести имя или изменить его можно будет в любое время в разделе 'обо мне'\n"
                         "попасть в меню в любой момент можно командой '/menu'",
                         reply_markup=builder.as_markup(resize_keyboard=True))


@router.message(Command("menu"))
async def cmd_menu(message: types.Message):
    builder = get_menu_inline_keyboard()
    await message.answer("главное меню", reply_markup=builder.as_markup(resize_keyboard=True))


@router.message(quote_filter)
async def cmd_add_quote(message: types.Message):
    user_name = await db.get_user_name(message.chat.id)
    if user_name is None:
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="Ввести имя", callback_data="set_name"))
        await message.answer("Для того чтобы добавить цитату, нужно указать свое имя", reply_markup=builder.as_markup())
    else:
        data = {}
        category_id = await db.get_category_id("categories", "from_users")
        data["category_id"] = category_id
        data["quote"] = message.text
        data["author"] = await db.get_user_name(message.chat.id)
        data["chat_id"] = message.chat.id
        error = await db.add_quote("from_users", data)
        if error is None:
            amount_quotes = await db.get_amount_user_quotes(message.chat.id)
            await message.answer(f"Новая цитата добавлена, всего твоих цитат: "
                                 f"{amount_quotes}",
                                 reply_markup=get_menu_inline_keyboard().as_markup())
        else:
            await message.answer("Такая цитата уже существует", reply_markup=get_menu_inline_keyboard().as_markup())


@router.message(name_filter)
async def cmd_set_name(message: types.Message):
    user_name = message.text
    if user_name:
        old_name = await db.get_user_name(message.chat.id)
        if old_name == user_name:
            text = "Это и есть твое имя"
        elif old_name is not None:
            await db.update_user_name(message.chat.id, user_name)
            text = f"Решил поменять имя? почему бы и нет, теперь ты {user_name}"
        else:
            await db.add_user(message.chat.id, user_name)
            text = f"Теперь я тебя запомню, {user_name}"
        await message.answer(text, parse_mode="html", reply_markup=get_menu_inline_keyboard().as_markup())
