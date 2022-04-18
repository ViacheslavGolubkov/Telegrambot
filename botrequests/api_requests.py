"""
Основные реквесты api, включает, поиск города, команды lowprice, highprice, и поиск фотографий
"""
import json
import requests
import telebot.types
from decouple import config
from loguru import logger

logger.add('debug.log', format='{time} {level} {message}',
           level='DEBUG', rotation='10 MB', compression='zip'
           )

headers = {
    'x-rapidapi-host': "hotels4.p.rapidapi.com",
    'x-rapidapi-key': config('rapid_api_key')
}


def get_request_search(message: [telebot.types.Message]) -> dict:
    """
    Функция реквест-запрос получает список городов и ID, подходящих по запросу.
    Полученный json файл десериализуется и записывается в переменную
    results затем функция возвращает её.
    :param message: Сообщение от пользователя, содержит город для поиска.
    :return: Словарь с найденными городами.
    """

    # rapid_api_key = config('rapid_api_key')
    city = message.text.capitalize()
    url = "https://hotels4.p.rapidapi.com/locations/v2/search"

    querystring = {"query": city, "locale": "en_US", "currency": "USD"}

    response = requests.request("GET", url, headers=headers, params=querystring, timeout=50)
    json_data = json.loads(response.text)
    logger.info('{id} - get_request_search - ok'.format(id=str(message.from_user.id)))
    return json_data


def get_properties_list(chat_id: int, hotels_number: int, query: list) -> [None, dict]:
    """
    Функция реквест-запрос, получающая заданное количество отелей указанной сортировки.
    Полученный json файл десериализуется и записывается в переменную
    results затем функция возвращает её.
    :param query: Список необходимых для запроса переменных.
    :param chat_id: ID пользователя.
    :param hotels_number: Количество отелей, которые будут в results.
    :return: Словарь с найденными отелями.
    """
    url = "https://hotels4.p.rapidapi.com/properties/list"
    destination_id = str(query[0])
    check_in = str(query[1])
    check_out = str(query[2])
    sortorder = query[3]
    page_size = hotels_number

    querystring = {
        "destinationId": destination_id, "pageNumber": "1", "pageSize": page_size,
        "checkIn": check_in, "checkOut": check_out, "adults1": "1", "sortOrder": sortorder,
        "locale": "en_US", "currency": "USD"
    }

    response = requests.request("GET", url, headers=headers, params=querystring, timeout=50)
    json_data = json.loads(response.text)
    results = json_data['data']['body']['searchResults']['results']
    if not results:
        return None

    logger.info(str(chat_id), '{id} - get_properties_list - ok'.format(id=str(chat_id)))
    return results


def get_photo(hotel_id: str) -> dict:
    """
    Функция реквест-запрос, получающая фотографии отеля по ID. Возвращает dict.
    :param hotel_id: ID отеля.
    :return: Словарь с ссылками на фотографии.
    """
    url = "https://hotels4.p.rapidapi.com/properties/get-hotel-photos"
    querystring = {"id": hotel_id}

    response = requests.request("GET", url, headers=headers, params=querystring, timeout=50)
    json_data = json.loads(response.text)
    logger.info('Hotel {id} - get_photo - ok'.format(id=hotel_id))
    return json_data
