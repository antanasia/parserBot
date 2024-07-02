import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import pymongo

client = pymongo.MongoClient("mongodb+srv://anastasia:SHSA7isDC3TzUygt@cluster1.0etffhg.mongodb.net/")
db = client['Bot_DB']
buy_collection = db['Buy_Collection']
rent_collection = db['Rent_Collection']
feedback_collection = db['Feedback_Collection']

TOKEN = '6730026589:AAEQ1RzAsfGrRa5mlrR4V0-jFnpDdX1RSv0'
bot = telebot.TeleBot(TOKEN)

districts_list = ["р-н Ауэзовский", "р-н Бостандыкский", "р-н Алмалинский", "р-н Алатауский", "р-н Медеуский",
                  "р-н Наурызбайский"]

user_errors_min_price = {}
user_errors_max_price = {}
user_errors_min_rent = {}
user_errors_max_rent = {}


def save_to_mongodb(message, data, operation_type):
    try:
        if operation_type == 'buy':
            buy_collection.insert_one(data)
        elif operation_type == 'rent':
            rent_collection.insert_one(data)
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")


def get_district_from_element(element):
    district_link = element.find('a', class_='non-click')
    if district_link:
        return district_link.text.strip()
    return None


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    markup.row_width = 2
    markup.add(
        types.InlineKeyboardButton("Старт", callback_data="start"),
        types.InlineKeyboardButton("Покупка", callback_data="purchase"),
        types.InlineKeyboardButton("Аренда", callback_data="rent"),
        types.InlineKeyboardButton("О компании", callback_data="about_company"),
        types.InlineKeyboardButton("Контакты", callback_data="contacts"),
        types.InlineKeyboardButton("Помощь", callback_data="help")
    )
    bot.send_message(
        message.chat.id,
        "Привет! Я бот, помогающий искать недвижимость на сайте etagi.com. Пожалуйста, выберите запрос:",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    if call.data == "purchase":
        buy_start(call.message)
    elif call.data == "rent":
        rent_start(call.message)
    elif call.data == "about_company":
        bot.send_message(call.message.chat.id, "О нашей компании: ...")
    elif call.data == "contacts":
        bot.send_message(call.message.chat.id, "Наши контакты: ...")
    elif call.data == "help":
        help_command(call.message)
    elif call.data == "start":
        send_welcome(call.message)


@bot.message_handler(func=lambda message: message.text.lower() == 'помощь')
def help_command(message):
    bot.send_message(
        message.chat.id,
        "Список доступных команд:\n/start - Начать заново\nПокупка - Поиск недвижимости для покупки\nАренда - Поиск недвижимости для аренды\nО компании - Информация о компании\nКонтакты - Наши контакты"
    )


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if message.text.lower() == 'покупка':
        buy_start(message)
    elif message.text.lower() == 'аренда':
        rent_start(message)


@bot.message_handler(commands=['buy'])
def buy_start(message):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        url = 'https://almaty.etagi.com/realty/'

        districts = districts_list

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(*[types.KeyboardButton(district) for district in districts])

        bot.send_message(message.chat.id, "Выберите район:", reply_markup=markup)
        bot.register_next_step_handler(message, process_user_selected_district_buy, headers, url)
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")


@bot.message_handler(commands=['rent'])
def rent_start(message):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        url = 'https://almaty.etagi.com/realty_rent/'

        districts = districts_list

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(*[types.KeyboardButton(district) for district in districts])

        bot.send_message(message.chat.id, "Выберите район:", reply_markup=markup)
        bot.register_next_step_handler(message, process_user_selected_district_rent, headers, url)
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")


# Покупка

def process_user_selected_district_buy(message, headers, url):
    try:
        selected_district = message.text
        bot.send_message(message.chat.id, "Введите минимальную цену в ₸:")
        bot.register_next_step_handler(message, process_user_min_price_input_buy, headers, url, selected_district)
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")


def process_user_min_price_input_buy(message, headers, url, selected_district):
    try:
        min_price = int(message.text.strip())
        bot.send_message(message.chat.id, "Введите максимальную цену в ₸:")
        bot.register_next_step_handler(message, process_user_max_price_input_buy, headers, url, selected_district,
                                       min_price)
    except ValueError:
        user_id = message.from_user.id
        if user_id in user_errors_min_price:
            user_errors_min_price[user_id] += 1
        else:
            user_errors_min_price[user_id] = 1

        if user_errors_min_price[user_id] == 1:
            bot.send_message(message.chat.id, "Некорректный формат. Введите число.")
        elif user_errors_min_price[user_id] == 2:
            bot.send_message(message.chat.id, "Неверный формат. Попробуйте 1000000")
        elif user_errors_min_price[user_id] >= 3:
            bot.send_message(message.chat.id, "Неверный формат. Попробуйте 1000000")
            user_errors_min_price[user_id] = 0

        bot.register_next_step_handler(message, process_user_min_price_input_buy, headers, url, selected_district)


def process_user_max_price_input_buy(message, headers, url, selected_district, min_price):
    try:
        max_price = int(message.text.strip())
        bot.send_message(message.chat.id, f"Ищем квартиры в диапазоне:\n"
                                          f"Цена: от {min_price} ₸ до {max_price} ₸\n"
                                          f"Район: {selected_district}")

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            apartment_links = soup.select('a.templates-object-card__slider')

            results = []
            for link in apartment_links:
                price_text = link.find_next('span', class_='eypL8 uwvkD').text
                price = int(price_text.replace(' ', '').replace('₸', ''))

                apartment_district = get_district_from_element(link.find_next('div', class_='_mbOx'))

                if min_price <= price <= max_price and selected_district.lower() in apartment_district.lower():
                    card_title = link.find_next('div', {'class': 'NKtNJ', 'displayname': 'cardTitle'})
                    if card_title:
                        details = card_title.get_text(separator=' ', strip=True)
                        results.append({'url': link['href'], 'price': price_text, 'details': details})

            if results:
                formatted_links = '\n'.join(
                    [f"https://almaty.etagi.com{entry['url']} - Цена: {entry['price']}\n{entry['details']}" for entry in results])
                bot.send_message(message.chat.id, f"Ссылки на квартиры:\n{formatted_links}")

                data = {
                    "user_id": message.from_user.id,
                    "type": "buy",
                    "district": selected_district,
                    "min_price": min_price,
                    "max_price": max_price,
                    "details": [entry['details'] for entry in results],
                    "links": [f"https://almaty.etagi.com{entry['url']}" for entry in results]
                }
                save_to_mongodb(message, data, 'buy')
                ask_feedback(message)
            else:
                bot.send_message(message.chat.id, f"Не найдено квартир в заданных ценовом диапазонах.")
                ask_feedback(message)

        else:
            bot.send_message(message.chat.id, f"Не удалось получить данные с сайта. Код ответа: {response.status_code}")
    except ValueError:
        user_id = message.from_user.id
        if user_id in user_errors_max_price:
            user_errors_max_price[user_id] += 1
        else:
            user_errors_max_price[user_id] = 1

        if user_errors_max_price[user_id] == 1:
            bot.send_message(message.chat.id, "Некорректный формат. Введите число.")
        elif user_errors_max_price[user_id] == 2:
            bot.send_message(message.chat.id, "Неверный формат. Попробуйте 1000000")
        elif user_errors_max_price[user_id] >= 3:
            bot.send_message(message.chat.id, "Неверный формат. Попробуйте 1000000")
            user_errors_max_price[user_id] = 0

        bot.register_next_step_handler(message, process_user_max_price_input_buy, headers, url, selected_district,
                                       min_price)


# Аренда

def process_user_selected_district_rent(message, headers, url):
    try:
        selected_district = message.text
        bot.send_message(message.chat.id, "Введите минимальную арендную плату в ₸:")
        bot.register_next_step_handler(message, process_user_min_rent_input, headers, url, selected_district)
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка: {str(e)}")


def process_user_min_rent_input(message, headers, url, selected_district):
    try:
        min_rent = int(message.text.strip())
        bot.send_message(message.chat.id, "Введите максимальную арендную плату в ₸:")
        bot.register_next_step_handler(message, process_user_max_rent_input, headers, url, selected_district, min_rent)
    except ValueError:
        user_id = message.from_user.id
        if user_id in user_errors_min_rent:
            user_errors_min_rent[user_id] += 1
        else:
            user_errors_min_rent[user_id] = 1

        if user_errors_min_rent[user_id] == 1:
            bot.send_message(message.chat.id, "Некорректный формат. Введите число.")
        elif user_errors_min_rent[user_id] == 2:
            bot.send_message(message.chat.id, "Неверный формат. Попробуйте 1000000")
        elif user_errors_min_rent[user_id] >= 3:
            bot.send_message(message.chat.id, "Неверный формат. Попробуйте 1000000")
            user_errors_min_rent[user_id] = 0

        bot.register_next_step_handler(message, process_user_min_rent_input, headers, url, selected_district)


def process_user_max_rent_input(message, headers, url, selected_district, min_rent):
    try:
        max_rent = int(message.text.strip())
        bot.send_message(message.chat.id, f"Ищем квартиры в диапазоне:\n"
                                          f"Арендная плата: от {min_rent} ₸ до {max_rent} ₸\n"
                                          f"Район: {selected_district}")

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            apartment_links = soup.select('a.templates-object-card__slider')

            results = []
            for link in apartment_links:
                rent_text = link.find_next('span', class_='eypL8 uwvkD').text
                rent = int(rent_text.replace(' ', '').replace('₸', ''))

                apartment_district = get_district_from_element(link.find_next('div', class_='_mbOx'))

                if min_rent <= rent <= max_rent and selected_district.lower() in apartment_district.lower():
                    card_title = link.find_next('div', {'class': 'NKtNJ', 'displayname': 'cardTitle'})
                    if card_title:
                        details = card_title.get_text(separator=' ', strip=True)
                        results.append({'url': link['href'], 'rent': rent_text, 'details': details})

            if results:
                formatted_links = '\n'.join(
                    [f"https://almaty.etagi.com{entry['url']} - Арендная плата: {entry['rent']}\n{entry['details']}" for entry in results])
                bot.send_message(message.chat.id, f"Ссылки на квартиры:\n{formatted_links}")
                data = {
                    "user_id": message.from_user.id,
                    "type": "rent",
                    "district": selected_district,
                    "min_rent": min_rent,
                    "max_rent": max_rent,
                    "details": [entry['details'] for entry in results],
                    "links": [f"https://almaty.etagi.com{entry['url']}" for entry in results]
                }
                save_to_mongodb(message, data, 'rent')
                ask_feedback(message)
            else:
                bot.send_message(message.chat.id, f"Не найдено квартир в заданных ценовом диапазонах.")
                ask_feedback(message)
        else:
            bot.send_message(message.chat.id, f"Не удалось получить данные с сайта. Код ответа: {response.status_code}")

    except ValueError:
        user_id = message.from_user.id
        if user_id in user_errors_max_rent:
            user_errors_max_rent[user_id] += 1
        else:
            user_errors_max_rent[user_id] = 1

        if user_errors_max_rent[user_id] == 1:
            bot.send_message(message.chat.id, "Некорректный формат. Введите число.")
        elif user_errors_max_rent[user_id] == 2:
            bot.send_message(message.chat.id, "Неверный формат. Попробуйте 1000000")
        elif user_errors_max_rent[user_id] >= 3:
            bot.send_message(message.chat.id, "Неверный формат. Попробуйте 1000000")
            user_errors_max_rent[user_id] = 0

        bot.register_next_step_handler(message, process_user_max_rent_input, headers, url, selected_district, min_rent)


def save_feedback_to_db(user_id, feedback_type, comment):
    feedback_collection.insert_one({
        "user_id": user_id,
        "feedback_type": feedback_type,
        "comment": comment
    })


def ask_feedback(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Хорошо'), types.KeyboardButton('Плохо'), types.KeyboardButton('Нейтрально'))
    bot.send_message(message.chat.id, "Как ваш опыт? Оставьте отзыв:", reply_markup=markup)
    bot.register_next_step_handler(message, process_feedback)


def process_feedback(message):
    user_id = message.from_user.id
    text = message.text.lower()

    if text == 'хорошо':
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('Старт'))
        bot.send_message(message.chat.id, f"Спасибо за ваш отзыв!", reply_markup=markup)
        save_feedback_to_db(user_id, "Хорошо", "")
        bot.register_next_step_handler(message, handle_start)

    elif text == 'плохо':
        bot.send_message(message.chat.id, f"Пожалуйста, оставьте комментарий о том, что мы можем улучшить.")
        bot.register_next_step_handler(message, process_comment, user_id, "Плохо")

    elif text == 'нейтрально':
        bot.send_message(message.chat.id, f"Пожалуйста, предложите, что мы можем улучшить.")
        bot.register_next_step_handler(message, process_comment, user_id, "Нейтрально")

    else:
        bot.send_message(message.chat.id, f"Пожалуйста, выберите один из вариантов: Хорошо, Плохо, Нейтрально.")
        bot.register_next_step_handler(message, process_feedback)


def process_comment(message, user_id, feedback_type):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Старт'))
    comment = message.text
    bot.send_message(message.chat.id, f"Спасибо за ваш отзыв!", reply_markup=markup)
    save_feedback_to_db(user_id, feedback_type, comment)
    bot.register_next_step_handler(message, handle_start)


def handle_start(message):
    send_welcome(message)


@bot.message_handler(func=lambda message: message.text.lower() == 'старт')
def start_over(message):
    handle_start(message)


if __name__ == "__main__":
    bot.polling(none_stop=True)