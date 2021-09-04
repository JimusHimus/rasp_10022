import os

import telebot
import requests
import datetime

from flask import Flask, request


def reverse_date(date: str):
    return '.'.join(date.split('.')[::-1])


def get_rasp():
    date = str(datetime.date.today())
    url = 'https://ruz.spbstu.ru/api/v1/ruz/scheduler/33858?date=' + date

    resp = requests.get(url).json()

    date_start = reverse_date(resp['week']['date_start'])
    date_end = reverse_date(resp['week']['date_end'])

    text = f'Расписание с {date_start} по {date_end}\n'
    for week in resp['days']:
        text += week['date'][-2:] + ':\n'
        for lesson in week['lessons']:
            text += f"\t{lesson['time_start']}-{lesson['time_end']} {lesson['subject_short']}\n"
    return text


app = Flask(__name__)
token = os.getenv('API_KEY')
bot = telebot.TeleBot(token)


@bot.message_handler(commands=['start', 'help'])
def send_welcome(message: telebot.types.Message):
    bot.send_message(message.chat.id, get_rasp())


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
