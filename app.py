import os

import telebot
import requests
import datetime

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


def reverse_date(date: str):
    return '.'.join(date.split('.')[::-1])


def get_rasp(date):
    url = 'https://ruz.spbstu.ru/api/v1/ruz/scheduler/33858?date=' + date

    resp = requests.get(url).json()

    date_start = reverse_date(resp['week']['date_start'])
    date_end = reverse_date(resp['week']['date_end'])

    text = f'Расписание с {date_start} по {date_end}\n'
    for day in resp['days']:
        weekday_name = day_name[int(day['weekday'])]
        text += f"{day['date'][-2:]} ({weekday_name}):\n"
        for lesson in day['lessons']:
            text += f"\t{lesson['time_start']}-{lesson['time_end']} ({lesson['typeObj']['abbr']}) {lesson['subject_short']}\n"
    return text


app = Flask(__name__)
token = os.getenv('API_KEY')
bot = telebot.TeleBot(token)
bot.set_my_commands([
    telebot.types.BotCommand("/rasp", "Расписание на неделю"),
    telebot.types.BotCommand("/nextrasp", "Расписание на следующую неделю")
])


@bot.message_handler(commands=['rasp'])
def send_rasp(message: telebot.types.Message):
    bot.send_message(message.chat.id, get_rasp(str(datetime.date.today())))


@bot.message_handler(commands=['nextrasp'])
def send_rasp(message: telebot.types.Message):
    bot.send_message(message.chat.id, get_rasp(str(datetime.date.today() + datetime.timedelta(days=7))))


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
