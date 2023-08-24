import json
import mysql.connector
from mysql.connector import Error
from mysql.connector import MySQLConnection, CMySQLConnection
import logging
from config_reader import config

logging.basicConfig(filename="logs.txt", level=logging.INFO, filemode="w")
last_quote_data = None

CONFIG = {
    'user': config.user.get_secret_value(),
    'password': config.password.get_secret_value(),
    'host': config.host.get_secret_value(),
    'database': config.database.get_secret_value(),
    'raise_on_warnings': config.raise_on_warnings
}

table = "categories"

create_users_table = f"""
CREATE TABLE IF NOT EXISTS users (
    chat_id INT,
    user_name TEXT,
    PRIMARY KEY (chat_id) 
) ENGINE = InnoDB
"""

create_likes_table = f'''
CREATE TABLE IF NOT EXISTS likes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    quote_id INT,
    category_id INT,
    chat_id INT,
    FOREIGN KEY (category_id) REFERENCES categories (id),
    FOREIGN KEY (chat_id) REFERENCES users (chat_id)
) ENGINE = InnoDB
'''

create_categories_table = f"""
CREATE TABLE IF NOT EXISTS categories (
  id INT AUTO_INCREMENT, 
  category VARCHAR(255) UNIQUE, 
  PRIMARY KEY (id)
) ENGINE = InnoDB
"""

create_movies_table = f"""
CREATE TABLE IF NOT EXISTS movies (
    quote_id INT AUTO_INCREMENT,
    category_id INT,
    quote TEXT,
    movie TEXT,
    PRIMARY KEY (quote_id),
    FOREIGN KEY (category_id) REFERENCES categories (id)
) ENGINE = InnoDB
"""

create_series_table = f"""
CREATE TABLE IF NOT EXISTS series (
    quote_id INT AUTO_INCREMENT,
    category_id INT,
    quote TEXT,
    series TEXT,
    info TEXT,
    PRIMARY KEY (quote_id),
    FOREIGN KEY (category_id) REFERENCES categories (id)
) ENGINE = InnoDB
"""

create_books_table = f"""
CREATE TABLE IF NOT EXISTS books (
    quote_id INT AUTO_INCREMENT,
    category_id INT,
    quote TEXT,
    author TEXT,
    book TEXT,
    PRIMARY KEY (quote_id),
    FOREIGN KEY (category_id) REFERENCES categories (id)
) ENGINE = InnoDB
"""

create_from_users_table = f"""
CREATE TABLE IF NOT EXISTS from_users (
    quote_id INT AUTO_INCREMENT,
    category_id INT,
    quote TEXT,
    author TEXT,
    chat_id INT,
    PRIMARY KEY (quote_id),
    FOREIGN KEY (chat_id) REFERENCES users (chat_id)
) ENGINE = InnoDB
"""


def create_connection(configuration) -> CMySQLConnection | MySQLConnection | None:
    connect = None
    try:
        connect = mysql.connector.connect(**configuration)
        logging.log(level=logging.INFO, msg="connected to MySQL")
    except Error as err:
        logging.log(level=logging.CRITICAL, msg=err)
    return connect


async def execute_query(connect: CMySQLConnection | MySQLConnection | None, query) -> None:
    try:
        cursor = connect.cursor()
        cursor.execute(query)
        connect.commit()
        logging.log(level=logging.INFO, msg="Query executed successfully")
    except Error as err:
        logging.log(level=logging.CRITICAL, msg=err)


async def get_category_name(connect, main_table, category_id):
    try:
        cursor = connect.cursor()
        query = f"SELECT category FROM {main_table} WHERE (id={category_id})"
        cursor.execute(query)
        res = cursor.fetchall()
        logging.log(logging.INFO, "successfully got category name")
        if len(res) > 0:
            return res[0][0]
        else:
            return None
    except Error as err:
        logging.critical(err)


async def get_category_id(connect, main_table, category) -> int | None:
    try:
        cursor = connect.cursor()
        query = f"SELECT id FROM {main_table} WHERE category='{category}'"
        cursor.execute(query)
        res = cursor.fetchall()
        logging.log(logging.INFO, "successfully got category id")
        if len(res) > 0:
            return res[0][0]
        else:
            return None
    except Error as err:
        logging.log(logging.CRITICAL, err)


async def add_category(connect, category: str):
    try:
        values = [(category, )]
        cursor = connect.cursor()
        query = f"INSERT INTO categories (category) VALUES (%s)"
        cursor.executemany(query, values)
        connect.commit()
        logging.log(logging.INFO, f"successfully added category: {category}")
    except Error as err:
        logging.log(level=logging.CRITICAL, msg=err)


async def add_quote(connect, table_name, data: dict):
    try:
        query = f"INSERT INTO {table_name}"
        keys = ""
        values = ""
        for key, value in data.items():
            keys += ' ' + str(key) + ','
            if type(value) is str:
                value = value.replace("'", "\\'")
                values += ' ' + f"'{value}'" + ','
            else:
                values += ' ' + str(value) + ','
        keys = '(' + keys[:-1] + ')'
        values = '(' + values[:-1] + ')'
        query += ' ' + keys + ' VALUES ' + values
        await execute_query(connect, query)
        logging.info(f"successfully added quote to {table_name}")
    except Error as err:
        logging.log(logging.CRITICAL, err)


async def fix_id(connect, table_name, id_name):
    try:
        cursor = connect.cursor()
        query = f"ALTER TABLE {table_name} DROP {id_name}"
        cursor.execute(query)
        query = f"ALTER TABLE {table_name} ADD {id_name} INT NOT NULL AUTO_INCREMENT FIRST, ADD PRIMARY KEY ({id_name})"
        cursor.execute(query)
        connect.commit()
        logging.info(f"successfully fixed id in {table_name}")
    except Error as err:
        logging.log(level=logging.CRITICAL, msg=err)


async def check_amount(connect, name) -> int:
    try:
        cursor = connect.cursor()
        query = f"SELECT COUNT(quote_id) FROM {name}"
        cursor.execute(query)
        res = cursor.fetchall()[0][0]
        logging.info(f"Successfully checked amount in {name}")
        return res
    except Error as err:
        logging.critical(err)


async def get_quote(connect, category, quote_id):
    try:
        cursor = connect.cursor()
        query = f"SELECT * from {category} WHERE quote_id = {quote_id}"
        cursor.execute(query)
        res = cursor.fetchall()
        logging.info(f"Successfully got quote {quote_id} from {category}")
        if len(res) > 0:
            global last_quote_data
            last_quote_data = res[0]
            return res[0]
    except Error as err:
        logging.critical(err)


async def get_users_quotes_ids(connect, chat_id) -> list | tuple:
    try:
        cursor = connect.cursor()
        query = f"SELECT quote_id FROM from_users WHERE chat_id = {chat_id}"
        cursor.execute(query)
        res = cursor.fetchall()
        logging.info(f"Successfully got quotes for chat_id {chat_id}")
        if len(res) > 0:
            res = [item[0] for item in res]
            return res
    except Error as err:
        logging.critical(err)


async def fill_table(connect: MySQLConnection | CMySQLConnection, name, main_table, keys, file_name):
    try:
        cursor = connect.cursor()
        if await check_amount(connect, name) > 0:
            raise Error(f"Error in filling table: '{name}', table must be empty")
        query = f"SELECT id FROM {main_table} WHERE category = '{name}'"
        cursor.execute(query)
        res = cursor.fetchall()
        category_id = res[0][0] if len(res) > 0 else None
        if category_id is not None:
            if "category_id" in keys:
                keys.remove("category_id")
            with open(file_name, "r", encoding="utf-8") as file:
                data = json.load(file)
                sql = f"INSERT INTO {name} (category_id,"
                for key in keys:
                    sql += " " + str(key) + ","
                sql = sql[:-1]
                sql += ") VALUES (%s," + len(keys) * " %s,"
                sql = sql[:-1] + ")"
                values = []
                for ind, quote_id in enumerate(data, start=0):
                    values.append([category_id, int(quote_id)])
                    for key in data[quote_id]:
                        values[ind].append(data[quote_id][key])
                cursor.executemany(sql, values)
                connect.commit()
                logging.log(msg="table was successfully filled", level=logging.INFO)
        else:
            raise Error("wrong category name")
    except Error as err:
        logging.log(level=logging.CRITICAL, msg=err)


async def load_table(connect, table_name):
    try:
        cursor = connect.cursor()
        if cursor is not None:
            query_for_column_names = f"""
            select COLUMN_NAME FROM (select *
            from INFORMATION_SCHEMA.COLUMNS
            where TABLE_NAME='{table_name}') as tmp
            """
            cursor.execute(query_for_column_names)
            names = cursor.fetchall()
            names = [item[0] for item in names]
            query_for_data = F"SELECT * FROM {table_name}"
            cursor.execute(query_for_data)
            res = cursor.fetchall()
            data = {}
            for name in names:
                data[name] = []
            for i in range(len(res)):
                for ind, name in enumerate(names, start=0):
                    data[name].append(res[i][ind])
            logging.info(f"Successfully loaded table {table_name}")
            return data
    except Error as err:
        logging.critical(err)


async def get_amount_category_quotes(connect, category):
    try:
        query = f"SELECT COUNT(quote_id) FROM {category}"
        cursor = connect.cursor()
        cursor.execute(query)
        res = cursor.fetchall()
        logging.info(f"Successfully got amount quotes from {category}")
        if len(res) > 0:
            return res[0][0]
        else:
            return 0
    except Error as err:
        logging.critical(err)


async def get_amount_user_quotes(connect, chat_id):
    try:
        query = f"SELECT COUNT(quote) FROM from_users WHERE chat_id = {chat_id}"
        cursor = connect.cursor()
        cursor.execute(query)
        res = cursor.fetchall()
        logging.info(f"Successfully got amount users quotes")
        if len(res) > 0:
            return res[0][0]
        else:
            return 0
    except Error as err:
        logging.critical(err)


async def add_user(connect, chat_id, user_name):
    query = f"INSERT into users (chat_id, user_name) VALUES ({chat_id}, '{user_name}')"
    await execute_query(connect, query)


async def update_user_name(connect, chat_id, new_name):
    query = f"UPDATE users SET user_name = '{new_name}' WHERE chat_id = {chat_id}"
    await execute_query(connect, query)
    query = f"UPDATE from_users SET author = '{new_name}' WHERE chat_id = {chat_id}"
    await execute_query(connect, query)


async def del_user(connect, chat_id):
    query = f"UPDATE from_users SET author='anonymous', chat_id=1 WHERE chat_id={chat_id}"
    await execute_query(connect, query)
    query = f"DELETE FROM likes WHERE chat_id={chat_id}"
    await execute_query(connect, query)
    query = f"DELETE FROM users WHERE chat_id={chat_id}"
    await execute_query(connect, query)


async def del_quote(connect, category, quote_id):
    query = f"DELETE FROM {category} WHERE quote_id={quote_id}"
    await execute_query(connect, query)


async def get_user_name(connect, chat_id):
    try:
        cursor = connect.cursor()
        query = f"SELECT user_name FROM users WHERE chat_id={chat_id}"
        cursor.execute(query)
        res = cursor.fetchall()
        logging.info("Successfully got user name")
        if len(res) > 0:
            return res[0][0]
    except Error as err:
        logging.critical(err)


async def like_quote(connect, quote_id, category_id, chat_id):
    query = f"INSERT INTO likes (quote_id, category_id, chat_id) VALUES ({quote_id}, {category_id}, {chat_id})"
    await execute_query(connect, query)


async def unlike_quote(connect, quote_id, category_id, chat_id):
    query = f"DELETE FROM likes WHERE (quote_id={quote_id} AND category_id={category_id} AND chat_id={chat_id})"
    await execute_query(connect, query)


async def get_amount_liked(connect, chat_id):
    try:
        query = f"SELECT COUNT(quote_id) FROM likes WHERE (chat_id={chat_id})"
        cursor = connect.cursor()
        cursor.execute(query)
        res = cursor.fetchall()
        logging.info(f"Successfully got amount liked quotes chat_id {chat_id}")
        if len(res) > 0:
            return res[0][0]
        else:
            return 0
    except Error as err:
        logging.critical(err)


async def get_liked(connect, chat_id):
    try:
        query = f"SELECT * FROM likes WHERE (chat_id={chat_id})"
        cursor = connect.cursor()
        cursor.execute(query)
        res = cursor.fetchall()
        logging.info(f"Successfully got liked quotes chat_id {chat_id}")
        if len(res) > 0:
            return res
        else:
            return None
    except Error as err:
        logging.critical(err)


connection = create_connection(CONFIG)


if __name__ == "__main__":
    pass
