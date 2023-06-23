import telebot
import requests
import sqlite3
import re
import datetime
import matplotlib.pyplot as plt
from io import BytesIO
from PIL import Image
import regexps
import pandas as pd
import os

#Finding database on machine
package_dir = os.path.abspath(os.path.dirname(__file__))
db_dir = os.path.join(package_dir, 'currency_data_base.db')

#Connecting to database
sqlite_connection = sqlite3.connect(db_dir, check_same_thread=False)
cursor = sqlite_connection.cursor()
print("Successfully Connected to SQLite")

#Bot settings
currency_bot = telebot.TeleBot('983193308:AAFwgr6uXQieZ7pP0WmimWFrL7n1qtMjFfI')
keyboard1 = telebot.types.ReplyKeyboardMarkup(True, True)
keyboard1.row('/start')


def inserting_data_into_database(dictionary):
    dict_list = [(currency, value) for currency, value in dictionary.items()]
    cursor.executemany('REPLACE INTO List_Currency VAlUES (?,?)', dict_list)
    sqlite_connection.commit()

def insert_time_to_database(time):
    sqlit_insert_with_param = """REPLACE INTO 'Time_stamp' ('insertion_time', 'id_time') VALUES (?, ?)"""
    key = 'old_time'
    data_tuple = (time, key)
    cursor.execute(sqlit_insert_with_param, data_tuple)
    sqlite_connection.commit()

def old_datetime_from_database():
    sqlite_query = """SELECT insertion_time FROM 'Time_stamp'"""
    cursor.execute(sqlite_query)
    time_stamp = pd.to_datetime(cursor.fetchall()[0][0])
    return time_stamp

def data_from_web():
    exchangeapi_data = requests.get('https://api.exchangeratesapi.io/latest?base=USD')
    if str(exchangeapi_data) == '<Response [200]>':
        exchange_dictionary = dict(exchangeapi_data.json()['rates'])
        exchange_list = 'This is your exhchange list:\n'
        for currency in exchange_dictionary:
            exchange_list = exchange_list + '\u2022 {0}: {1:.2f}\n'.format(currency, exchange_dictionary[currency])
        inserting_data_into_database(exchange_dictionary)
        return exchange_list
    else:
        return 'Something went wrong, try again later.'


def data_from_database():
    cursor.execute('SELECT * FROM List_Currency')
    rows = cursor.fetchall()
    exchange_list = 'This is your exchange list:\n'
    for row in rows:
        exchange_list = exchange_list + '\u2022 %s: %.2f\n'%(row)
    print (exchange_list)
    return exchange_list


def time_stamp_diff_in_seconds(newdate, olddate):
    timedelta = newdate - olddate
    return (timedelta.days * 24 * 3600 + timedelta.seconds) / 60


def graphs_coordinasts(message):
    groups_of_currencys = re.match(regexps.regexp_dictionary['history'], message)
    second_currency = groups_of_currencys.group(1)
    first_currency = groups_of_currencys.group(2)
    today = datetime.date.today()
    week_ago = (today - datetime.timedelta(days=7))
    histroy_json = requests.get('https://api.exchangeratesapi.io/history?start_at={}&end_at={}&base={}&symbols={}'.format(week_ago, today, second_currency, first_currency))
    values = dict(histroy_json.json()['rates'])
    x_list = sorted(values.keys())
    y_list = [dictionary[first_currency] for dictionary in [values[date] for date in x_list]]
    return x_list, y_list


def create_buffer_and_load_image(x_values, y_values):
    plt.plot(x_values, y_values)
    buffer = BytesIO()
    plt.savefig(buffer, format='jpeg')
    im = Image.open(buffer)
    im.save(buffer, 'jpeg')
    buffer.seek(0)
    return buffer

def clean_and_close_buffer(buf):
    buf.flush()
    buf.close()
    plt.clf()

time_stamp = datetime.datetime.now()
insert_time_to_database(time_stamp)

@currency_bot.message_handler(commands=['start'])
def start_message(message):

    help_information = ("Hi, I am an exchange bot.\n"
                        "Commands:\n/list - last exchanges rates\n"
                        "/lst -latest exchange rates\n"
                        "/exchange $amount_of_dollars to your_currency\n"
                        "/exchange amount_of_currency carrency_name to currency_name\n"
                        "For currency exchange\n"
                        "/history base_currency_name/currency_history_name 7 days\n"
                        "For graph history of desired currency\n"
                        "Examples:\n"
                        "/exchange $10 to CAD\n"
                        "/exchange 10 USD to CAD\n"
                        "/history USD/CAD for 7 days\n"
                        )
    currency_bot.send_message(message.chat.id, help_information, reply_markup=keyboard1)

@currency_bot.message_handler(content_types=['text'])
def send_text(message):

    if message.text.lower() == '/list' or message.text.lower() == '/lst' :
        new_time_request = datetime.datetime.now()
        old_time = old_datetime_from_database()
        diff = time_stamp_diff_in_seconds(new_time_request, old_time)
        if diff < 10:
            final_exchange_list = data_from_web()
        else:
            final_exchange_list = data_from_database()
        insert_time_to_database(new_time_request)
        currency_bot.send_message(message.chat.id, final_exchange_list)
        
    
    elif re.search(regexps.regexp_dictionary['first_exchange'], message.text) != None:
        elements = re.match(regexps.regexp_dictionary['first_exchange'], message.text)
        amount_of_currency = int(elements.group(1))
        name_of_currency = elements.group(2)
        requested_data = requests.get('https://api.exchangeratesapi.io/latest?base=USD')
        exchanged_value_of_currency = requested_data.json()['rates'][name_of_currency] * amount_of_currency
        string_result = 'Ex.: {:.2f} {}'.format(exchanged_value_of_currency, name_of_currency)
        currency_bot.send_message(message.chat.id, string_result)
    
    elif re.search(regexps.regexp_dictionary['second_exchange'], message.text) != None:
        elements = re.match(regexps.regexp_dictionary['second_exchange'], message.text)
        amount_of_currency = float(elements.group(1))
        from_name_of_currency = elements.group(2)
        to_name_of_currency = elements.group(3)
        requested_data = requests.get('https://api.exchangeratesapi.io/latest?base=USD')
        exchanged_value_of_currency = requested_data.json()['rates'][from_name_of_currency]
        exchanged_value_of_currency2 = requested_data.json()['rates'][to_name_of_currency]
        result = amount_of_currency / exchanged_value_of_currency * exchanged_value_of_currency2
        string_result = 'Ex.: {:.2f} {}'.format(result, to_name_of_currency)
        currency_bot.send_message(message.chat.id, string_result)

    elif re.search(regexps.regexp_dictionary['history'], message.text) != None:
        x_values, y_values = graphs_coordinasts(message.text)
        buf = create_buffer_and_load_image(x_values, y_values)
        currency_bot.send_photo(message.chat.id, photo=buf)
        clean_and_close_buffer(buf)
        
    else:
        currency_bot.send_message(message.chat.id, 'Please check entered data and try again')
        
currency_bot.polling()
