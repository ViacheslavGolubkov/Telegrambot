"""
Телеграм бот для получения отелей по запросу с сайта hotels.com
посредством request запросов на api dojo hotels.com
"""
import json
import re
import datetime
import random
import time
import traceback

import requests.exceptions
import telebot
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
from loguru import logger
from decouple import config
from telebot import types
from botrequests import bestdeal, api_requests, postgres_database

logger.add('debug.log', format='{time} {level} {message}',
           level='DEBUG', rotation='10 MB', compression='zip'
           )

bot = telebot.TeleBot(config('Token'))


@logger.catch
@bot.message_handler(commands=['start'])
def start_message(message: types.Message) -> None:
    """
    Функция обработчик команды start, добавляет пользователя в БД,
    отправляет приветственное сообщение.
    :param message:
    :return:
    """
    postgres_database.add_user(message)
    text_message = 'Привет, на данный момент я работаю исключительно с командами\n' \
                   r'/lowprice''\n'r'/highprice''\n'r'/bestdeal''\n'r'/history'
    bot.send_message(message.chat.id, text_message)


@logger.catch
@bot.message_handler(commands=['lowprice'])
def low_price(message: types.Message) -> None:
    """
    Функция обработчик команды lowprice, отправляет сообщение пользователю и
    переходит к следующему шагу.
    :param message: Команда от пользователя.
    :return:
    """
    bot.send_message(message.chat.id, 'Введите город в котором необходимо найти отели. Латиницей.')
    bot.register_next_step_handler(message, get_city, command='l')


@logger.catch
@bot.message_handler(commands=['highprice'])
def high_price(message: types.Message) -> None:
    """
    Функция обработчик команды highprice, отправляет сообщение пользователю и
    переходит к следующему шагу.
    :param message: Команда от пользователя.
    :return:
    """
    bot.send_message(message.chat.id, 'Введите город в котором необходимо найти отели. Латиницей.')
    bot.register_next_step_handler(message, get_city, command='h')


@logger.catch
@bot.message_handler(commands=['bestdeal'])
def best_deal(message: types.Message) -> None:
    """
    Функция обработчик команды bestdeal, отправляет сообщение пользователю и
    переходит к следующему шагу.
    :param message: Команда от пользователя.
    :return:
    """
    bot.send_message(message.chat.id, 'Введите город в котором необходимо найти отели. Латиницей.')
    bot.register_next_step_handler(message, get_city, command='b')


@logger.catch
@bot.message_handler(commands=['history'])
def history(message: types.Message) -> None:
    """
    Функция обработчик для команды history, делает запрос в БД,
    получает zip объект по которому проходится циклом и отправляет пользователю информацию.
    :param message: Сообщение команда "history"
    :return:
    """
    try:
        results = postgres_database.get_history(message.from_user.id)
        for info, result in results:
            keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
            hotels_name = []

            for hotel in result[0]:
                url = 'https://hotels.com/ho{id}'.format(id=hotel['id'])
                url_button = telebot.types.InlineKeyboardButton(text=hotel['name'], url=url)
                hotels_name.append(hotel['name'])
                keyboard.add(url_button)

            hotels_name = ", ".join(hotels_name)
            text_message = f"Command: {info[0]}\n" \
                           f"Date and Time: {info[1]}\n" \
                           f"Hotel name: {hotels_name}"
            bot.send_message(message.from_user.id, text_message, reply_markup=keyboard)
    except TypeError:
        logger.info('{id} - history - empty'.format(id=str(message.from_user.id)))
        bot.send_message(message.from_user.id, 'История пуста.')
    except IndexError:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id} - history - ok'.format(id=str(message.from_user.id)))


@logger.catch
@bot.message_handler(content_types=['text'])
def get_text_messages(message: types.Message) -> None:
    """
    Функция обработчик любого текстового сообщения, отправляет сообщение.
    :param message: Сообщение от пользователя.
    :return:
    """
    text_message = 'Привет, на данный момент я работаю исключительно с командами\n' \
                   r'/lowprice''\n'r'/highprice''\n'r'/bestdeal''\n'r'/history'
    bot.send_message(message.chat.id, text_message)


@bot.callback_query_handler(func=lambda c: c.data.startswith('q'))
def get_photo_answer(callback_query):
    """
        Функция обработчик inline кнопки получения фотографии,
        отправляет пользователю сообщение с вопросом о количестве требуемых фотографий
        и переходит к следующему шагу.
        :param callback_query: запрос обратного вызова с сообщением
    """
    bot.send_message(callback_query.from_user.id, 'Сколько фотографий требуется? (Max=10)')
    bot.register_next_step_handler_by_chat_id(callback_query.from_user.id,
                                              get_photo_number, hotel_id=callback_query.data[1:]
                                              )


@logger.catch
@bot.callback_query_handler(func=lambda c: c.data.startswith('b'))
def get_city_callback_bestdeal(callback_query):
    """
    Функция обработчик города следования для команды bestdeal, получает ответ пользователя,
    передает его в БД, переходит к следующему шагу.
    :param callback_query: запрос обратного вызова с сообщением
    """
    postgres_database.add_destination_id(callback_query)
    bot.send_message(callback_query.from_user.id, 'Введите минимальную стоимость в USD за ночь')
    bot.register_next_step_handler_by_chat_id(callback_query.from_user.id, get_price_min)


@logger.catch
@bot.callback_query_handler(func=lambda c: c.data.startswith('l') or c.data.startswith('h'))
def get_city_callback_low_and_high_price(callback_query: types.CallbackQuery):
    """
    Функция обработчик города следования для команд lowprice и hig  hprice,
    получает ответ пользователя, передает его в БД, переходит к следующему шагу.
    :param callback_query: запрос обратного вызова с сообщение
    """
    postgres_database.add_destination_id(callback_query)
    get_check_in(callback_query)


@logger.catch
def get_check_in(callback_query: [types.Message, types.CallbackQuery]):
    """
        Функция вызова даты въезда
        :param callback_query: запрос обратного вызова с сообщением
    """
    text = "Выберите дату заезда"
    bot.send_message(callback_query.from_user.id, text)
    date_today = datetime.date.today()
    calendar, step = DetailedTelegramCalendar(
        calendar_id=1, locale='ru', min_date=date_today
    ).build()
    bot.send_message(callback_query.from_user.id, f"Выберите {LSTEP[step]}", reply_markup=calendar)


@logger.catch
@bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id=1))
def calendar_1(callback_query: types.CallbackQuery) -> None:
    """
        Функция обработчик календаря, выводит клавиатуру с календарем и ожидает ответ,
        передает ответ в БД,
        и переходит к следующему шагу
        :param callback_query: запрос обратного вызова с сообщением
    """
    date = datetime.date.today()
    result, key, step = DetailedTelegramCalendar(
        calendar_id=1, locale='ru', min_date=date
    ).process(callback_query.data)
    if not result and key:
        bot.edit_message_text(f"Выберите {LSTEP[step]}",
                              callback_query.message.chat.id,
                              callback_query.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(f"Вы выбрали {result}",
                              callback_query.message.chat.id,
                              callback_query.message.message_id)
        postgres_database.add_check_in(chat_id=callback_query.message.chat.id, date=str(result))
        get_check_out(callback_query.message.chat.id)


@logger.catch
def get_check_out(chat_id: int) -> None:
    """
        Функция вызова даты выезда
        :param chat_id: ID чата
    """
    date_today = (datetime.datetime.strptime(postgres_database.get_check_in(chat_id=chat_id),
                                             "%Y-%m-%d") + datetime.timedelta(days=1)).date()
    text = "Выберите дату выезда"
    bot.send_message(chat_id, text)
    calendar, step = DetailedTelegramCalendar(
        calendar_id=2, locale='ru', min_date=date_today
    ).build()
    bot.send_message(chat_id, f"Выберите {LSTEP[step]}", reply_markup=calendar)


@logger.catch
@bot.callback_query_handler(func=DetailedTelegramCalendar.func(calendar_id=2))
def calendar_2(callback_query: types.CallbackQuery) -> None:
    """
        Функция обработчик календаря, выводит клавиатуру с календарем и ожидает ответ,
        передает ответ в БД,
        и переходит к следующему шагу
    :param callback_query: запрос обратного вызова с сообщением
    """
    date_today = (datetime.datetime.strptime(postgres_database.get_check_in(
        chat_id=callback_query.message.chat.id), "%Y-%m-%d") + datetime.timedelta(days=1)).date()

    result, key, step = DetailedTelegramCalendar(calendar_id=2, locale='ru',
                                                 min_date=date_today).process(callback_query.data)
    if not result and key:
        bot.edit_message_text(f"Выберите {LSTEP[step]}",
                              callback_query.message.chat.id,
                              callback_query.message.message_id,
                              reply_markup=key)
    elif result:
        bot.edit_message_text(f"Вы выбрали {result}",
                              callback_query.message.chat.id,
                              callback_query.message.message_id)
        postgres_database.add_check_out(chat_id=callback_query.from_user.id, date=str(result))
        send_message_how_much_results(callback_query.from_user.id)


@logger.catch
def send_message_how_much_results(user_id: int) -> None:
    """
    Функция для отправки сообщения-вопроса пользователю о количестве отелей для вывода.
    Отправляет сообщение и переходит к следующему шагу.
    :param user_id: Id пользователя (int)
    """
    text_message = 'Введите кол-во отелей, которые необходимо вывести в результате(max=10)'
    bot.send_message(user_id, text_message)
    bot.register_next_step_handler_by_chat_id(user_id, results_to_user,
                                              user_id=user_id)


@logger.catch
def get_city(message: types.Message, command: str) -> None:
    """
    Функция отправки inline кнопок уточняющих у пользователя необходимое ему местоположение.
    Получает город, отправляет в функцию api_request запрос полученный результат записывает
    в city_json_data, проходит циклом по city_json_data и отправляет пользователю
    возможные варианты, не более 10.
    :param message: Сообщение от пользователя должно содержать город поиска.
    :param command: Сокращенное обозначение команды от пользователя.
    :return:
    """
    try:
        if re.search(r'[а-яА-ЯёЁ]', message.text):
            raise TypeError
        bot.send_message(message.chat.id, "Работаю.")
        city_json_data = api_requests.get_request_search(message)
        buttons = {}
        pattern2 = r"<span class=\'highlighted\'>"
        pattern1 = r"</span>"

        for entities in city_json_data['suggestions'][0]['entities']:
            key = entities['caption']
            key = re.sub(pattern1, '', key)
            key = re.sub(pattern2, '', key)
            buttons[key] = entities['destinationId']

        keyboard = telebot.types.InlineKeyboardMarkup()

        for item, value in buttons.items():
            button = telebot.types.InlineKeyboardButton(
                text=str(item), callback_data='{} {}'.format(command, value))
            keyboard.add(button)
        text_messege = 'Найдено {} совпадений выберите более подходящий вариант.'.format(
            city_json_data['moresuggestions'])
        bot.send_message(message.chat.id, text_messege, reply_markup=keyboard)

    except TypeError:
        bot.send_message(
            message.from_user.id, 'Название города должно быть написано латиницей.\n'
                                  'Давайте попробуем еще раз.\n'
                                  'Введите город в котором необходимо найти отели.')
        bot.register_next_step_handler(message, get_city, command=command)
    else:
        logger.info('{id} - get_photo_answer - ok'.format(id=str(message.from_user.id)))


@logger.catch
@bot.message_handler(content_types=['text'])
def get_price_min(message: types.Message) -> None:
    """
        Функция для получения минимальной стоимости команды bestdeal,
        полученное значение отправляет в БД, и переходит к следующему шагу.
        Функция обрабатывает полученное значение на тип.
        :param message:
        :return:
        """
    try:
        float(message.text)
        postgres_database.add_price_min(message.from_user.id, message.text)
        bot.send_message(message.from_user.id, 'Введите максимальную стоимость в USD за ночь.')
        bot.register_next_step_handler_by_chat_id(
            message.from_user.id, get_price_max, price_min=message.text
        )
    except ValueError:
        bot.send_message(
            message.from_user.id, 'Минимальная цена должна быть числом.\n'
                                  'Давайте попробуем еще раз.\n'
                                  'Введите максимальную стоимость в USD за ночь.')
        bot.register_next_step_handler_by_chat_id(message.from_user.id, get_price_min)
    else:
        logger.info('{id} - get_price_min - ok'.format(id=str(message.from_user.id)))


@logger.catch
@bot.message_handler(content_types=['text'])
def get_price_max(message: types.Message, price_min: str) -> None:
    """
        Функция для получения минимальной стоимости команды bestdeal,
        полученное значение отправляет в БД, и переходит к следующему шагу.
        Функция обрабатывает полученное значение на тип.
        :param price_min: Минимальная цена, которую пользователь ввел на прошлом шагу.
        :param message:
        :return:
        """
    try:
        if float(message.text) < float(price_min):
            raise ImportError
        postgres_database.add_price_max(message.from_user.id, message.text)
        text_message = 'Введите минимальное удаление от центра. В километрах.'
        bot.send_message(message.from_user.id, text_message)
        bot.register_next_step_handler_by_chat_id(message.from_user.id, get_distance_min)
    except ImportError:
        bot.send_message(
            message.from_user.id, 'Максимальная цена не может быть меньше минимальной.\n'
                                  'Давайте попробуем еще раз.\n'
                                  'Введите максимальную стоимость в USD за ночь.')
        bot.register_next_step_handler_by_chat_id(
            message.from_user.id, get_price_max, price_min=price_min
        )
    except ValueError:
        bot.send_message(
            message.from_user.id, 'Максимальная цена должна быть числом.\n'
                                  'Давайте попробуем еще раз.\n'
                                  'Введите максимальную стоимость в USD за ночь.')
        bot.register_next_step_handler_by_chat_id(
            message.from_user.id, get_price_max, price_min=price_min
        )
    else:
        logger.info(str(message.from_user.id), ' - get_price_max - ok')


@logger.catch
@bot.message_handler(content_types=['text'])
def get_distance_min(message: types.Message) -> None:
    """
    Функция для получения минимальной дистанции команды bestdeal,
    полученное значение отправляет в БД, и переходит к следующему шагу.
    Функция обрабатывает полученное значение на тип.
    :param message:
    :return:
    """
    try:
        float(message.text)
        postgres_database.add_distance_min(
            message.from_user.id, message.text
        )
        text_message = 'Введите максимальное удаление от центра. В километрах.'
        bot.send_message(message.from_user.id, text_message)
        bot.register_next_step_handler_by_chat_id(
            message.from_user.id, get_distance_max, distance_min=message.text
        )
    except ValueError:
        bot.send_message(
            message.from_user.id, 'Минимальное удаление от центра должно быть числом.\n'
                                  'А число с точкой написано через "."\n'
                                  'Давайте попробуем еще раз.\n'
                                  'Введите минимальное удаление от центра. В километрах.')
        bot.register_next_step_handler_by_chat_id(message.from_user.id, get_distance_min)
    else:
        logger.info(str(message.from_user.id), ' - distance_min - ok')


@logger.catch
@bot.message_handler(content_types=['text'])
def get_distance_max(message: types.Message, distance_min: str) -> None:
    """
        Функция для получения минимальной дистанции команды bestdeal,
        полученное значение отправляет в БД, и переходит к следующему шагу.
        Функция обрабатывает полученное значение на тип.
        :param distance_min: Минимальная дистанция, которую пользователь ввел на прошлом шагу.
        :param message: Сообщение от пользователя.
        :return:
        """
    try:
        if float(message.text) < float(distance_min):
            raise ValueError

        postgres_database.add_distance_max(message.from_user.id, message.text)
        get_check_in(message)
    except ImportError:
        bot.send_message(message.from_user.id,
                         'Максимальная дистанция не может быть меньше минимальной.\n'
                         'Давайте попробуем еще раз.\n'
                         'Введите максимальное удаление от центра. В километрах.'
                         )
        bot.register_next_step_handler_by_chat_id(
            message.from_user.id, get_distance_max, distance_min=distance_min
        )
    except ValueError:
        bot.send_message(message.from_user.id,
                         'Максимальная дистанция должна быть числом.\n'
                         'А число с точкой написано через "."\n'
                         'Давайте попробуем еще раз.\n'
                         'Введите максимальное удаление от центра. В километрах.'
                         )
        bot.register_next_step_handler_by_chat_id(
            message.from_user.id, get_distance_max, distance_min=distance_min
        )
    else:
        logger.info(str(message.from_user.id), ' - distance_max - ok')


@logger.catch
@bot.message_handler(content_types=['text'])
def results_to_user(message: types.Message, user_id: int) -> None:
    """
    Функция отправки пользователю найденного результата.
    Делает запрос в БД для получения информации по поиску,
    потом отправляет эту информацию в функцию request'а,
    полученный результат записывается в переменную results, проходится циклом по results
    используя функцию send_media_result отправляет из пользователю,
    в конце отправляет пользователю сообщение об окончании работы.
    :param message: Количество результатов для показа пользователя
    :param user_id: ID пользователя
    :return:
    """
    try:
        bot.send_message(user_id, 'Делаю запрос. Это может занять несколько минут.')
        query = postgres_database.get_full_info(user_id)
        sortorder: str = query[3]
        results = None

        if int(message.text) > 10:
            hotels_number = 10
        else:
            hotels_number = int(message.text)

        if sortorder == "DISTANCE_FROM_LANDMARK":
            results = bestdeal.best_deal_request(user_id, hotels_number, query)
        elif sortorder in ('PRICE_HIGHEST_FIRST', 'PRICE'):
            results = api_requests.get_properties_list(user_id, hotels_number, query)

        date_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history_data = json.dumps(results)
        postgres_database.add_history(user_id, sortorder, date_time, history_data)
        for result in results:
            send_media_result(user_id, result)

    except TypeError:
        bot.send_message(user_id, "Похоже я ничего не нашел по вашему запросу.")
    else:
        bot.send_message(user_id, "Это всё что я смог найти для Вас.")
        logger.info(str(message.from_user.id), ' - results_to_user - ok\nSession Complete')


@logger.catch
def send_media_result(user_id, result):
    """
    Функция для отправки результатов пользователю, обрабатывает исключение KeyError.
    :param user_id: ID пользователя
    :param result: Объект с отелями
    """
    try:
        image = result['optimizedThumbUrls']['srpDesktop']
        hotel_id = result['id']
        hotel_name = result['name']
        star_rating = result['starRating']
        address = result['address']['streetAddress']
        price = result['ratePlan']['price']['current']
        total_price = re.sub(
            r'&nbsp;', ' ', result['ratePlan']['price']['fullyBundledPricePerStay']
        )

        message_text = f'Hotel ID: {hotel_id}\n' \
                       f'Name: {hotel_name}\n' \
                       f'Start rating: {star_rating}\n' \
                       f'Address: {address}\n' \
                       f'Price: {price} ' \
                       f'Total price: {total_price}'
        keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)

        url = 'https://hotels.com/ho{id}'.format(id=result['id'])
        url_button = telebot.types.InlineKeyboardButton(text="Перейти на Hotels.com", url=url)

        inline_button_1 = telebot.types.InlineKeyboardButton(
            text='Хочу фотографии!', callback_data='q{hotel_id}'.format(hotel_id=result['id'])
        )
        keyboard.add(inline_button_1, url_button)
        bot.send_photo(
            user_id, image, caption=message_text, parse_mode='HTML', reply_markup=keyboard
        )
    except KeyError:
        logger.error(result['id'])
        logger.error(traceback.format_exc())


@logger.catch
@bot.message_handler(content_types=['text'])
def get_photo_number(message: types.Message, hotel_id: str) -> None:
    """
    Функция для отправки фотографий по определенному отелю пользователю,
    делает запрос в api_requests
    результат записывается в json_data, циклом проходит по json_data и
    отправляет полученный результат пользователю.
    :param message:
    :param hotel_id:
    :return:
    """
    try:
        to_send_message = []
        json_data = api_requests.get_photo(hotel_id)
        sub_pattern = r'{size}.jpg'
        for _ in range(int(message.text)):
            random_photo = random.randint(0, len(json_data['hotelImages']) - 1)
            suffix = '{}.jpg'.format(json_data['hotelImages'][random_photo]['sizes'][0]['suffix'])
            img_url = re.sub(sub_pattern, suffix, json_data['hotelImages'][random_photo]['baseUrl'])
            to_send_message.append(types.InputMediaPhoto(img_url))

        bot.send_media_group(message.from_user.id, to_send_message)
        keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
        inline_button_1 = telebot.types.InlineKeyboardButton(
            text='Еще фотографий!', callback_data='q{hotel_id}'.format(hotel_id=hotel_id))
        keyboard.add(inline_button_1)
        bot.send_message(message.from_user.id, 'Hotel Id: {hotel_id}'.format(hotel_id=hotel_id),
                         reply_markup=keyboard)
    except BaseException:
        logger.error(traceback.format_exc())
    else:
        logger.info('{id}- get_photo_number - ok'.format(id=str(message.from_user.id)))


@logger.catch
def request_mistake(user_id: str) -> None:
    """
    Функция для отправки сообщения, если по запросу ничего не найдено.
    :param user_id: ID пользователя.
    :return:
    """
    bot.send_message(user_id, 'К сожалению по вашему запросу ничего не найдено.')


if __name__ == '__main__':
    while True:
        try:
            logger.info("Start main.py")
            postgres_database.add_tables()
            bot.polling(none_stop=True, interval=5)
        except requests.exceptions.ReadTimeout as ex:
            logger.error(traceback.format_exc())
            logger.error(ex)
            time.sleep(1200)
