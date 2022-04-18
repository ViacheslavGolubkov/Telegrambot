import main
import telebot
import re
import requests
from decouple import config
import json

bot = telebot.TeleBot(config('Token'))


def best_deal_request(chat_id, hotels_number, query):
    try:
        url = "https://hotels4.p.rapidapi.com/properties/list"
        hotels_list = list()
        rapid_api_key = str(config('rapid_api_key'))

        destination_id = str(query[0])
        check_in = str(query[1])
        check_out = str(query[2])
        sortorder = query[3]
        price_min = query[4]
        price_max = query[5]
        page_number = '1'
        page_size = hotels_number
        distance_min = round(float(query[6]) / 1, 609344498)
        distance_max = round(float(query[7]) / 1, 609344498)

        headers = {
            'x-rapidapi-host': "hotels4.p.rapidapi.com",
            'x-rapidapi-key': rapid_api_key
        }

        querystring = {
            "destinationId": destination_id, "pageNumber": page_number, "pageSize": page_size, "checkIn": check_in,
            "checkOut": check_out, "adults1": "1", "priceMin": price_min, "priceMax": price_max,
            "sortOrder": sortorder, "locale": "en_US", "currency": "USD"
        }

        while len(hotels_list) < hotels_number:
            try:
                response = requests.request("GET", url, headers=headers, params=querystring, timeout=50)
                json_data = json.loads(response.text)
                results = json_data['data']['body']['searchResults']['results']
                if not results:
                    bot.register_next_step_handler_by_chat_id(chat_id, main.request_mistake, user_id=chat_id)
                for i_hotel in results:
                    distance = re.findall(r'\d[,.]?\d', i_hotel['landmarks'][0]['distance'])[0].replace(',', '.')
                    if float(distance) > float(distance_max):
                        raise ValueError('Превышено максимальное расстояние от центра города')
                    elif float(distance) >= int(distance_min):
                        hotels_list.append(i_hotel)

                querystring['pageNumber'] = str(int(querystring.get('pageNumber')) + 1)

            except ValueError:
                break
    except requests.exceptions.Timeout:
        bot.send_message(chat_id, "Превышено максимальное ожидание от сервера. Попробуйте чуть позже")

    except Exception as ex:
        print(ex)

    else:
        main.logger.info(str(chat_id)," - best_deal_request - ok" )
        return results
