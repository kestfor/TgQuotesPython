import sql
from aiogram import types, F, Router
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import CallbackQuery

import utils
from sql import connection
from utils import (get_menu_inline_keyboard, get_inline_keyboard, get_quote,
                   quote_filter, name_filter, Queue)

router = Router()
users_quotes = {}
users_liked = {}


@router.callback_query(F.data == "forget_me")
async def callback_cmd_clear_data(callback: CallbackQuery):
    name = await sql.get_user_name(connection, callback.message.chat.id)
    if name is None:
        text = "Мы даже еще не познакомились"
        await callback.message.edit_text(text, reply_markup=get_menu_inline_keyboard().as_markup(resize_keyboard=True))
    else:
        text = "вы действительно хотите удалить ваши сохраненные данные? отменить это действие будет невозможно"
        builder = InlineKeyboardBuilder()
        builder.add(types.InlineKeyboardButton(text="Да", callback_data='delete_user'),
                    types.InlineKeyboardButton(text="Нет", callback_data='cancel_deleting_user'))
        await callback.message.edit_text(text, reply_markup=builder.as_markup(resize_keyboard=True))
        await callback.answer()


@router.callback_query(F.data == "delete_user")
async def callback_del_user(callback: types.CallbackQuery):
    await sql.del_user(connection, callback.from_user.id)
    await callback.message.edit_text("Было приятно иметь с вами дело",
                                     reply_markup=get_menu_inline_keyboard().as_markup())
    await callback.answer()


@router.callback_query(F.data == "cancel_deleting_user")
async def callback_cancel_deleting_user(callback: types.CallbackQuery):
    await callback.message.edit_text("Больше меня так не пугайте",
                                     reply_markup=get_menu_inline_keyboard().as_markup())
    await callback.answer()


async def handle_unknown_user(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Ввести имя", callback_data="set_name"))
    text = "мы еще не знакомы, но это можно исправить"
    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "info")
async def callback_cmd_info(callback: CallbackQuery):
    name = await sql.get_user_name(connection, callback.from_user.id)
    if name is None:
        await handle_unknown_user(callback)
    else:
        amount_liked = await sql.get_amount_liked(connection, callback.from_user.id)
        amount_added = await sql.get_amount_user_quotes(connection, callback.message.chat.id)
        text = (f"никнейм: {name}"
                f"\nпонравившихся цитат: {amount_liked}"
                f"\nдобавлено цитат: {amount_added}")
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text="изменить имя", callback_data="change_name"))
        if amount_added > 0:
            builder.row(types.InlineKeyboardButton(text="просмотреть свои цитаты", callback_data="get_next_user_quote"))
        if amount_liked:
            builder.row(types.InlineKeyboardButton(text="просмотреть понравившиеся",
                                                   callback_data="get_next_liked_quote"))
        builder.row(types.InlineKeyboardButton(text="вернуться на главную", callback_data="clear_comeback_to_menu"))
        await callback.message.edit_text(text, parse_mode="html", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "get_next_user_quote")
async def callback_get_user_quote(callback: CallbackQuery):
    if callback.from_user.id not in users_quotes:
        val = await sql.get_users_quotes_ids(
            connection, callback.from_user.id)
        users_quotes[callback.from_user.id] = Queue(values=val)
    quote_id = users_quotes[callback.from_user.id].get()
    builder = InlineKeyboardBuilder()
    if quote_id is None:
        text = "Больше цитат нет"
    else:
        builder.row(types.InlineKeyboardButton(text="следующая", callback_data="get_next_user_quote"))
        builder.row(types.InlineKeyboardButton(text="удалить", callback_data="del_quote"))
        data = await sql.get_quote(connection, "from_users", quote_id)
        text = utils.format_text(data, amount_keys=2)
    builder.row(types.InlineKeyboardButton(text="вернуться на главную", callback_data="clear_comeback_to_menu"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "get_next_liked_quote")
async def callback_get_liked_quote(callback: CallbackQuery):
    if callback.from_user.id not in users_liked:
        if await sql.get_amount_liked(connection, callback.from_user.id) == 0:
            builder = InlineKeyboardBuilder()
            builder.row(types.InlineKeyboardButton(text="вернуться на главную", callback_data="clear_comeback_to_menu"))
            await callback.message.edit_text("Больше цитат нет", reply_markup=builder.as_markup())
        ids = await sql.get_liked(connection, callback.from_user.id)
        ids = [(item[1], item[2]) for item in ids]
        users_liked[callback.from_user.id] = Queue(values=ids)
    builder = InlineKeyboardBuilder()
    if len(users_liked[callback.from_user.id]) > 0:
        quote_id, category_id = users_liked[callback.from_user.id].get()
    else:
        quote_id = None
    if quote_id is None:
        builder.row(types.InlineKeyboardButton(text="вернуться на главную", callback_data="clear_comeback_to_menu"))
        await callback.message.edit_text("Больше цитат нет", reply_markup=builder.as_markup())
    category = await sql.get_category_name(connection, "categories", category_id)
    amount_keys = 3 if category == 'books' else 2
    builder.row(types.InlineKeyboardButton(text="следующая", callback_data="get_next_liked_quote"))
    builder.row(types.InlineKeyboardButton(text="удалить", callback_data="unlike_quote"))
    builder.row(types.InlineKeyboardButton(text="вернуться на главную", callback_data="clear_comeback_to_menu"))
    data = await sql.get_quote(connection, category, quote_id)
    await callback.message.edit_text(utils.format_text(data, amount_keys=amount_keys), reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "unlike_quote")
async def callback_unlike_quote(callback: CallbackQuery):
    quote_id, category_id = users_liked[callback.from_user.id].last
    await sql.unlike_quote(connection, quote_id, category_id, callback.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="следующая", callback_data="get_next_liked_quote"))
    builder.row(types.InlineKeyboardButton(text="вернуться на главную", callback_data="clear_comeback_to_menu"))
    await callback.message.edit_text("Цитата удалена", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "clear_comeback_to_menu")
async def clear_queue(callback: CallbackQuery):
    if callback.from_user.id in users_quotes:
        users_quotes.pop(callback.from_user.id)
    if callback.from_user.id in users_liked:
        users_liked.pop(callback.from_user.id)
    if callback.from_user.id in utils.users_queue:
        utils.users_queue[callback.from_user.id] = None
    await sql.fix_id(connection, "from_users", "quote_id")
    await callback_menu(callback)


@router.callback_query(F.data == 'del_quote')
async def del_user_quote(callback: CallbackQuery):
    quote_id = users_quotes[callback.from_user.id].last
    await sql.del_quote(connection, "from_users", quote_id)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="следующая", callback_data="get_next_user_quote"))
    builder.row(types.InlineKeyboardButton(text="вернуться на главную", callback_data="clear_comeback_to_menu"))
    await callback.message.edit_text("Цитата удалена", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "clear_get_categories")
async def clear_categories(callback: CallbackQuery):
    if callback.from_user.id in utils.users_queue:
        utils.users_queue[callback.from_user.id] = None
    await callback_cmd_categories(callback)


@router.callback_query(F.data == "set_name")
async def cmd_set_name_callback(callback: CallbackQuery):
    await callback.message.edit_text("Выбери имя, которое по твоему мнению подходит тебе больше всего, и напиши eго")
    name_filter.change_state()
    await callback.answer()


@router.callback_query(F.data == 'add_quote')
async def callback_add_quote(callback: CallbackQuery):
    quote_filter.change_state()
    await callback.message.answer("Напиши свою цитату, ты будешь указан как автор")
    await callback.answer()


@router.callback_query(F.data == "get_categories")
async def callback_cmd_categories(callback: CallbackQuery):
    kb = [
        [
            types.InlineKeyboardButton(text="фильмы", callback_data='next_movies_quote'),
            types.InlineKeyboardButton(text="сериалы", callback_data="next_series_quote"),
        ],
        [
            types.InlineKeyboardButton(text="от пользователей", callback_data="next_from_users_quote"),
        ],
        [
            types.InlineKeyboardButton(text="игры", callback_data="next_games_quote"),
            types.InlineKeyboardButton(text="книги", callback_data="next_books_quote"),
        ],
        [
            types.InlineKeyboardButton(text="великих людей", callback_data="next_great_people_quote"),
        ],
        [
            types.InlineKeyboardButton(text="со смыслом", callback_data="next_with_meaning_quote"),
        ],
        [
            types.InlineKeyboardButton(text="вернуться на главную", callback_data="clear_comeback_to_menu"),
        ]
    ]
    keyboard = InlineKeyboardBuilder(kb)
    await callback.message.edit_text("Выберите категорию", reply_markup=keyboard.as_markup())
    await callback.answer()


async def next_quote(callback: CallbackQuery, category):
    amount_keys = 3 if category in ("books", "series") else 2
    quote = await get_quote(category, callback.from_user.id, amount_keys)
    if quote is not None:
        quote_data = sql.last_quote_data
        like_visible = not await sql.is_liked(connection, callback.from_user.id, quote_data)
        builder = get_inline_keyboard(f"next_{category}_quote", like_visible=like_visible)
        await callback.message.edit_text(quote,
                                         reply_markup=builder.as_markup())
    else:
        builder = InlineKeyboardBuilder()
        builder.row(types.InlineKeyboardButton(text='категории', callback_data="clear_get_categories"))
        builder.row(types.InlineKeyboardButton(text='вернуться на главную', callback_data="clear_comeback_to_menu"))
        await callback.message.edit_text("Похоже тут ничего нет(", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "next_great_people_quote")
async def callback_next_great_people_quote(callback: CallbackQuery):
    await next_quote(callback, "great_people")


@router.callback_query(F.data == "next_with_meaning_quote")
async def callback_next_great_people_quote(callback: CallbackQuery):
    await next_quote(callback, "with_meaning")


@router.callback_query(F.data == 'next_movies_quote')
async def callback_next_movie_quote(callback: types.CallbackQuery):
    await next_quote(callback, "movies")


@router.callback_query(F.data == 'next_books_quote')
async def callback_next_books_quote(callback: types.CallbackQuery):
    await next_quote(callback, "books")


@router.callback_query(F.data == 'next_series_quote')
async def callback_next_series_quote(callback: types.CallbackQuery):
    await next_quote(callback, "series")


@router.callback_query(F.data == 'next_from_users_quote')
async def callback_next_from_users_quote(callback: types.CallbackQuery):
    await next_quote(callback, "from_users")


@router.callback_query(F.data == 'next_games_quote')
async def callback_next_games_quote(callback: types.CallbackQuery):
    await next_quote(callback, "games")


@router.callback_query(F.data == "comeback_to_menu")
async def callback_menu(callback: CallbackQuery):
    builder = get_menu_inline_keyboard()
    await callback.message.edit_text(text="возвращаемся на главную",
                                     reply_markup=builder.as_markup(resize_keyboard=True))
    await callback.answer()


@router.callback_query(F.data == "change_name")
async def callback_change_name(callback: CallbackQuery):
    utils.name_filter = utils.SetNameFilter()
    name_filter.change_state()
    await callback.message.answer("Введи новое имя")
    await callback.answer()


@router.callback_query(F.data == "like_quote")
async def callback_like_quote(callback: CallbackQuery):
    data = utils.last_quote_data
    quote_id = data[0]
    category_id = data[1]
    await sql.like_quote(connection, quote_id, category_id, callback.from_user.id)
    category = await sql.get_category_name(connection, "categories", category_id)
    builder = get_inline_keyboard(f"next_{category}_quote", like_visible=False)
    amount_keys = 3 if category == 'books' else 2
    await callback.message.edit_text(utils.format_text(data, amount_keys), reply_markup=builder.as_markup())
    await callback.answer()
