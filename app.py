import os

import telebot
import requests
import datetime
import redis

from functools import lru_cache
from flask import Flask, request

day_name = {
    1: 'пн',
    2: 'вт',
    3: 'ср',
    4: 'чт',
    5: 'пт',
    6: 'сб',
    7: 'вс'
}

REDIS_ID_KEY = 'last_message_id_'


def reverse_date(date: str):
    return '.'.join(date.split('.')[::-1])


@lru_cache()
def get_rasp(group_id: int, date: str):
    url = f'https://ruz.spbstu.ru/api/v1/ruz/scheduler/{group_id}?date={date}'

    try:
        resp = requests.get(url, timeout=3).json()
    except Exception as e:
        print(e)
        return 'Ошибка при выполнении запроса получения расписания'

    if resp.get('error'):
        return resp.get('text')

    is_odd = resp['week']['is_odd']
    date_start = reverse_date(resp['week']['date_start'])
    date_end = reverse_date(resp['week']['date_end'])

    what_week = 'нечётная' if is_odd else 'чётная'
    header = f'Расписание</a> с <b>{date_start}</b> по <b>{date_end}</b> (<b>{what_week}</b> неделя)'

    text = f'<a href="https://ruz.spbstu.ru/faculty/95/groups/{group_id}?date={date}">{header}\n'
    for day in resp['days']:
        weekday_name = day_name[int(day['weekday'])]
        text += f"<b>{day['date'][-2:]}</b> (<b>{weekday_name}</b>):\n"
        for lesson in day['lessons']:
            additional_info = lesson['additional_info']
            subgroup = f", {additional_info[additional_info.rfind('п/г'):]}" if 'п/г' in additional_info else ''
            text += f"\t<i>{lesson['time_start']}-{lesson['time_end']}</i> ({lesson['typeObj']['abbr']}{subgroup})\t{lesson['subject_short']}\n"
        text += '\n'
    return text


def save_last_id(chat_id: int, message_id: int):
    rc.set(REDIS_ID_KEY + str(chat_id), message_id)


def get_last_id(chat_id: int):
    value = rc.get(REDIS_ID_KEY + str(chat_id))
    if not value:
        rc.set(REDIS_ID_KEY + str(chat_id), -1)
        return -1
    return int(value)


def handle_message(user_message: telebot.types.Message, command: str):
    chat_id = user_message.chat.id
    print(f'Message from {user_message.from_user.full_name} ({user_message.from_user.username}, id {chat_id})')
    to_send = 'err'

    if chat_id == 187479117:
        rasp_id = 34989
    else:
        rasp_id = 35499

    if command == 'rasp':
        to_send = get_rasp(rasp_id, str(datetime.date.today()))
    if command == 'nextrasp':
        to_send = get_rasp(rasp_id, str(datetime.date.today() + datetime.timedelta(days=7)))

    print(f'Message len: {len(to_send)}')

    last_id = get_last_id(chat_id)
    if last_id != -1:
        try:
            bot.delete_message(chat_id, last_id)
        except Exception:
            print('Can\'t delete old message')
    sent = bot.send_message(chat_id, to_send, parse_mode="HTML")
    save_last_id(chat_id, sent.message_id)
    try:
        bot.delete_message(chat_id, user_message.message_id)
    except Exception:
        print('Can\'t delete message (no adm priv)')


app = Flask(__name__)
token = os.getenv('API_KEY')
bot = telebot.TeleBot(token)
bot.set_my_commands([
    telebot.types.BotCommand("/rasp", "Расписание на неделю"),
    telebot.types.BotCommand("/nextrasp", "Расписание на следующую неделю")
])

r_host = os.getenv('REDIS_HOST')
r_port = os.getenv('REDIS_PORT')
r_pass = os.getenv('REDIS_PASS')
rc = redis.Redis(host=r_host, port=r_port, password=r_pass)


@bot.message_handler(commands=['rasp'])
def send_rasp(message: telebot.types.Message):
    handle_message(message, 'rasp')


@bot.message_handler(commands=['nextrasp'])
def send_rasp(message: telebot.types.Message):
    handle_message(message, 'nextrasp')


@app.route("/" + token, methods=['POST'])
def get_message():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200


@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook('https://rasp-10022-paid.herokuapp.com/' + token)
    return "!", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
