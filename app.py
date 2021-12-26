import os

import telebot
import requests
import datetime
import redis

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


def get_rasp(date):
    url = 'https://ruz.spbstu.ru/api/v1/ruz/scheduler/33858?date=' + date

    resp = requests.get(url).json()

    date_start = reverse_date(resp['week']['date_start'])
    date_end = reverse_date(resp['week']['date_end'])

    text = f'<a href="https://ruz.spbstu.ru/faculty/95/groups/33858?date={date}">Расписание</a> с <b>{date_start}</b> по <b>{date_end}</b>\n'
    for day in resp['days']:
        weekday_name = day_name[int(day['weekday'])]
        text += f"<b>{day['date'][-2:]}</b> (<b>{weekday_name}</b>):\n"
        for lesson in day['lessons']:
            text += f"\t<i>{lesson['time_start']}-{lesson['time_end']}</i> ({lesson['typeObj']['abbr']})\t{lesson['subject_short']}\n"
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


def handle_message(user_message: telebot.types.Message, to_send):
    chat_id = user_message.chat.id
    last_id = get_last_id(chat_id)
    if last_id != -1:
        bot.delete_message(chat_id, last_id)
    sent = bot.send_message(chat_id, to_send, parse_mode="HTML")
    save_last_id(chat_id, sent.message_id)
    bot.delete_message(chat_id, user_message.message_id)


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
    handle_message(message, get_rasp(str(datetime.date.today())))


@bot.message_handler(commands=['nextrasp'])
def send_rasp(message: telebot.types.Message):
    handle_message(message, get_rasp(str(datetime.date.today() + datetime.timedelta(days=7))))


@app.route("/" + token, methods=['POST'])
def get_message():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "!", 200


@app.route("/")
def webhook():
    bot.remove_webhook()
    bot.set_webhook('https://rasp-10022.herokuapp.com/' + token)
    return "!", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
