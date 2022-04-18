"""
Работа с БД:
    Добавление пользователя
    Добавление истории
    Извлечение истории
    Добавление ID города поиска
    Добавление check-in
    Извлечение check-in
    Добавление check-out
    Добавление минимальной цены (только для bestdeal)
    Добавление максимальной цены (только для bestdeal)
    Добавление минимальной дистанции (только для bestdeal)
    Добавление максимальной дистанции (только для bestdeal)
    Извлечение минимальной дистанции (только для bestdeal)
    Извлечение максимальной дистанции (только для bestdeal)
    Извлечение полной информации
"""
import datetime
import traceback
from decouple import config
import psycopg2
import telebot.types
from loguru import logger
from psycopg2 import extras, errors

logger.add('debug.log', format='{time} {level} {message}',
           level='DEBUG', rotation='10 MB', compression='zip'
           )


def connect_database() -> psycopg2.connect:
    """
    Функция для подключения к БД.
    :return: Подключение к БД.
    """
    try:
        connect = psycopg2.connect(
            database=config('database'),
            user=config('user'),
            password=config('password'),
            host=config('host'),
            port=config('port')
        )
        return connect
    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())


def add_tables() -> None:
    """
    Функция для создания таблиц в БД, при наличии таблиц
    возвращает исключение, записывает его в logger и
    выдает соответствующее сообщение в консоль.
    :return:
    """
    try:
        connect = connect_database()
        cursor = connect.cursor()
        cursor.execute(
            "CREATE TABLE users(id INT PRIMARY KEY,first_name TEXT,last_name TEXT,"
            "user_name TEXT, check_in DATE, check_out DATE, destination_id INT,"
            "command TEXT, price_min INT,price_max INT, distance_min INT, distance_max INT);"
        )

        connect.commit()

    except psycopg2.errors.DuplicateTable:
        logger.info("Таблица users уже создана")
    else:
        logger.info('Таблица "users" успешно создана')

    try:
        connect = connect_database()
        cursor = connect.cursor()
        cursor.execute(
            "CREATE TABLE history(id INT, command TEXT, "
            "datetime TIMESTAMP, results JSON);"
        )
        connect.commit()
    except psycopg2.errors.DuplicateTable:
        logger.info("Таблица history уже создана")
    else:
        logger.info('Таблица "history" успешно создана')


def add_user(message: telebot.types.Message) -> None:
    """
    Функция добавления нового пользователя в БД.
    :param message: Сообщение с командой start.
    :return:
    """
    try:
        connect = connect_database()
        cursor = connect.cursor()
        user_id = str(message.from_user.id)
        first_name = str(message.from_user.first_name)
        last_name = str(message.from_user.last_name)
        user_name = str(message.from_user.username)
        cursor.execute("INSERT INTO users (id, first_name, last_name, user_name) "
                       "VALUES (%s, %s, %s, %s);", (user_id, first_name, last_name, user_name))
        connect.commit()
        connect.close()
    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())
    except errors.UniqueViolation as ex:
        logger.error(ex)
    else:
        logger.info('{id} - post.add_user - ok'.format(id=user_id))


def add_history(user_id: int, sortorder: str, date_time: datetime, history_data: str) -> None:
    """
    Функция добавления истории в БД.
    :param user_id: Id пользователя отправившего команду
    :param sortorder: Команда отправленная пользователям
    :param date_time: Дата и время. Объект datatime.
    :param history_data: Результаты отправленные пользователю в формате json.
    :return:
    """
    try:
        if sortorder == 'DISTANCE_FROM_LANDMARK':
            sortorder = 'Bestdeal'
        elif sortorder == 'PRICE':
            sortorder = 'Lowprice'
        elif sortorder == 'PRICE_HIGHEST_FIRST':
            sortorder = 'Highprice'
        connect = connect_database()
        cursor = connect.cursor()

        cursor.execute("INSERT INTO history (id, command, datetime, results) "
                       "VALUES (%s, %s, %s, %s);", (user_id, sortorder, date_time, history_data))
        connect.commit()
        connect.close()
    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id} - post.add_history - ok'.format(id=user_id))


def get_history(user_id: int) -> zip:
    """
    Функция извлечения истории для пользователя
    :param user_id: ID пользователя
    :return results: Zip объект включающий (команда, объект datetime) и json найденых отелей
    """
    try:
        connect = connect_database()
        cursor = connect.cursor(cursor_factory=extras.DictCursor)
        cursor.execute(
            "SELECT results FROM history WHERE id=%s "
            "AND results IS NOT NULL;", (user_id,)
                        )
        history_data = cursor.fetchall()
        cursor = connect.cursor()
        cursor.execute(
            "SELECT command, datetime FROM history WHERE id=%s "
            "AND results IS NOT NULL;", (user_id,)
                        )
        command_datetime = cursor.fetchall()
        connect.close()
        if len(command_datetime) and len(history_data):
            results = zip(command_datetime, history_data)
        else:
            results = None
    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id} - post.get_history - ok'.format(id=user_id))
        return results


def add_destination_id(message: telebot.types.CallbackQuery) -> None:
    """
    Функция добавления destination ID в БД.
    :param message: Callback data содержит префикс сокращенной команды и ID
    :return :
    """
    try:
        connect = connect_database()
        cursor = connect.cursor()
        command = 'PRICE'
        user_id = message.from_user.id

        if message.data.startswith('l'):
            command = 'PRICE'
        elif message.data.startswith('h'):
            command = 'PRICE_HIGHEST_FIRST'
        elif message.data.startswith('b'):
            command = 'DISTANCE_FROM_LANDMARK'
        destination_id = message.data[2:]
        cursor.execute(
            "UPDATE users SET destination_id=%s, command=%s WHERE id=%s;",
            (destination_id, command,  user_id)
                        )
        connect.commit()
        connect.close()

    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id} - post.add_destination - ok'.format(id=user_id))


def add_check_in(chat_id: int, date: datetime) -> None:
    """
    Функция добавления check-in в БД.
    :param date: Дата check-in
    :param chat_id: ID пользователя
    :return :
    """
    try:
        connect = connect_database()
        cursor = connect.cursor()
        check_in = date
        cursor.execute(
            "UPDATE users SET check_in=%s WHERE id=%s;",
            (check_in, chat_id)
                       )
        connect.commit()
        connect.close()

    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id} - post.add_check-in - ok'.format(id=chat_id))


def get_check_in(chat_id: int) -> datetime:
    """
    Функция извлечения check-in для дальнейшего использования
    :param chat_id: ID пользователя
    :return date: Возвращает извлеченную из БД дату check-in
    """
    try:
        connect = connect_database()
        cursor = connect.cursor()
        select_query = "SELECT check_in FROM users WHERE id={chat_id};"
        cursor.execute(select_query.format(chat_id=chat_id))
        date = str(cursor.fetchall()[0][0])
        cursor.close()

    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id} - post.add_check-in - ok'.format(id=chat_id))
        return date


def add_check_out(chat_id: int, date: datetime) -> None:
    """
    Функция добавления check-out в БД.
    :param date: Дата check-out
    :param chat_id: ID пользователя
    :return :
    """
    try:
        connect = connect_database()
        cursor = connect.cursor()
        update_query = "UPDATE users SET check_out='{check_out}' WHERE id={chat_id};"
        cursor.execute(update_query.format(check_out=date, chat_id=chat_id))
        connect.commit()
        connect.close()

    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id} - post.add_check-out - ok'.format(id=chat_id))


def add_price_min(chat_id: int, price_min: str) -> None:
    """
    Функция добавления минимальной цены в БД.
    :param price_min: Минимальная цена
    :param chat_id: ID пользователя
    :return:
    """
    try:
        connect = connect_database()
        cursor = connect.cursor()
        update_query = "UPDATE users SET price_min='{price_min}' WHERE id={chat_id};"
        cursor.execute(update_query.format(price_min=price_min, chat_id=chat_id))
        connect.commit()
        connect.close()

    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id} - post.add_price_min - ok'.format(id=chat_id))


def add_price_max(chat_id: int, price_max: str) -> None:
    """
    Функция добавления максимальной цены в БД.
    :param price_max: Максимальная цена
    :param chat_id: ID пользователя
    :return:
    """
    try:
        connect = connect_database()
        cursor = connect.cursor()
        update_query = "UPDATE users SET price_max='{price_max}' WHERE id={chat_id};"
        cursor.execute(update_query.format(price_max=price_max, chat_id=chat_id))
        connect.commit()
        connect.close()

    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id} - post.add_price_max - ok'.format(id=chat_id))


def add_distance_min(chat_id: int, distance: str) -> None:
    """
    Функция добавления минимальной дистанции в БД.
    :param distance: Минимальная дистанция
    :param chat_id: ID пользователя
    :return:
    """
    try:
        connect = connect_database()
        cursor = connect.cursor()
        update_query = "UPDATE users SET distance_min='{distance}' WHERE id={chat_id};"
        cursor.execute(update_query.format(distance=distance, chat_id=chat_id))
        connect.commit()
        connect.close()

    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id} - post.add_distance_min - ok'.format(id=chat_id))


def add_distance_max(chat_id: int, distance: str) -> None:
    """
    Функция добавления максимальной дистанции в БД.
    :param distance: Максимальная дистанция
    :param chat_id: ID пользователя
    :return:
    """
    try:
        connect = connect_database()
        cursor = connect.cursor()
        update_query = "UPDATE users SET distance_max='{distance}' WHERE id={chat_id};"
        cursor.execute(update_query.format(distance=distance, chat_id=chat_id))
        connect.commit()
        connect.close()

    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id} - post.add_distance_max - ok'.format(id=chat_id))


def get_distance_min(chat_id: int) -> int:
    """
    Функция извлечения минимальной дистанции из БД.
    :param chat_id: ID пользователя
    :return:
    """
    try:
        connect = connect_database()
        cursor = connect.cursor()
        select_query = "SELECT distance_min FROM users WHERE id={id}"
        cursor.execute(select_query.format(id=chat_id))
        result = cursor.fetchall()[0]
        connect.close()

    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id} - post.get_distance_min - ok'.format(id=chat_id))
        return result


def get_distance_max(chat_id: int) -> int:
    """
    Функция извлечения максимальной дистанции из БД.
    :param chat_id: ID пользователя
    :return:
    """
    try:
        connect = connect_database()
        cursor = connect.cursor()
        select_query = "SELECT distance_max FROM users WHERE id={id}"
        cursor.execute(select_query.format(id=chat_id))
        result = cursor.fetchall()[0]
        connect.close()

    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id} - post.get_distance_max - ok'.format(id=chat_id))
        return result


def get_full_info(chat_id: int) -> list:
    """
    Функция извлечения полной информации из БД.
    :param chat_id: ID пользователя
    :return results: Список основных данных из БД необходимых для отправки запроса
    """
    try:
        connect = connect_database()
        cursor = connect.cursor()
        cursor.execute(
            "SELECT destination_id, check_in, check_out, command, "
            "price_min, price_max, distance_min,"
            "distance_max FROM users WHERE id=%s", (chat_id,)
                        )
        result = cursor.fetchall()[0]
        connect.close()

    except psycopg2.OperationalError:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id} - post.get_full_info - ok'.format(id=chat_id))
        return result
