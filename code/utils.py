import random
import sql
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sql import db


class Queue:
    def __init__(self, values: list | tuple):
        self.last = None
        if values is not None and len(values) > 0:
            self._queue = values
            self.last = self._queue[0]
            random.shuffle(self._queue)
        else:
            self._queue = []

    def get(self):
        if len(self._queue) > 0:
            val = self._queue[0]
            self.last = val
            self._queue = self._queue[1:]
            return val
        else:
            return None

    def __len__(self):
        return len(self._queue)


users_queue = {}


class SetNameFilter:

    def __init__(self):
        self._state = None

    def change_state(self):
        self._state = "set_name"

    def __call__(self, message: types.Message):
        if self._state == "set_name":
            self._state = None
            return True
        else:
            return False


class AddQuoteFilter:

    def __init__(self):
        self._state = None

    def change_state(self):
        self._state = "add_quote"

    def __call__(self, message: types.Message):
        if self._state == 'add_quote':
            self._state = None
            return True
        else:
            return False


name_filter = SetNameFilter()
quote_filter = AddQuoteFilter()
last_quote_data = None


def format_text(data, amount_keys=None):
    if amount_keys is None or amount_keys > len(data) - 2:
        amount_keys = len(data) - 2
    text = ""
    for i in range(2, 2 + amount_keys):
        if data[i] is not None:
            text += str(data[i]) + '\n\n'
    return text.strip()


def get_menu_inline_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text='категории', callback_data="clear_get_categories"))
    builder.row(types.InlineKeyboardButton(text='обо мне', callback_data="info"),
                types.InlineKeyboardButton(text='забыть меня', callback_data="forget_me"))
    builder.row(types.InlineKeyboardButton(text='добавить свою цитату', callback_data="add_quote"))
    return builder


def get_inline_keyboard(data: str, like_visible=True):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="следующая", callback_data=data))
    if like_visible:
        builder.row(types.InlineKeyboardButton(text="❤️", callback_data="like_quote"))
    builder.row(types.InlineKeyboardButton(text='категории', callback_data="clear_get_categories"))
    builder.row(types.InlineKeyboardButton(text='вернуться на главную', callback_data="clear_comeback_to_menu"))
    return builder


# def get_quote(category: str, id_range: list | tuple, amount_keys=None) -> str:
#     data = sql.get_quote(connection, category, random.randint(id_range[0], id_range[-1]))
#     return format_text(data, amount_keys)

async def get_quote(category: str, chat_id: int, amount_keys=None) -> str | None:
    category_id = await db.get_category_id(category)
    if chat_id not in users_queue or users_queue[chat_id] is None or category_id not in users_queue[chat_id]:
        start = 1
        end = await db.get_amount_category_quotes(category)
        users_queue[chat_id] = {category_id: Queue(list(range(start, end+1)))}
    quote_id = users_queue[chat_id][category_id].get()
    if quote_id is None:
        return None
    data = await db.get_quote(category, quote_id)
    global last_quote_data
    last_quote_data = sql.last_quote_data
    return format_text(data, amount_keys)


if __name__ == "__main__":
    pass
