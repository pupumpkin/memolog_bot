import io
import logging
import threading
import time
import schedule
import telebot
from datetime import datetime, timedelta
from config import TOKEN
from debug import clear_log_file, debugger, start_debug_mode, stop_debug_mode
from reddit_memes import get_random_meme_by_tag
from strings import *

bot = telebot.TeleBot(TOKEN)
users = set()  # Множество для хранения идентификаторов пользователей
user_times = {}  # Словарь для хранения времени отправки для каждого пользователя
user_sorting = {}  # Словарь для хранения сортировки мемов для каждого пользователя
meme_ratings = {}  # Словарь для хранения оценок мемов

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="../log_file.log",
    filemode="a",
)

sort_options = ["hot", "new", "top"]


@bot.message_handler(commands=['start'])
def send_start_message(message):
    if debugger.active:
        bot.send_message(message.chat.id, f"Log: Бот запущен")
    logging.info("Бот запущен")
    bot.send_message(message.chat.id, start_message)
    bot.send_message(message.chat.id, categories_sort_message)
    bot.send_message(message.chat.id, for_example_message)


@bot.message_handler(commands=['help'])
def help_handler(message):
    bot.reply_to(message, help_message)


@bot.message_handler(commands=['daily_memes_stop'])
def stop_daily_memes_mailing(message):
    users.discard(message.chat.id)  # Удаляем user_id при остановке
    user_times.pop(message.chat.id, None)  # Удаляем время отправки для пользователя
    user_sorting.pop(message.chat.id, None)  # Удаляем сортировку для пользователя
    bot.reply_to(message, stop_daily_memes_mailing_message)


@bot.message_handler(commands=['settings'])
def send_settings_message(message):
    user_id = message.chat.id
    current_time = user_times.get(user_id, "Не установлено")
    current_sorting = user_sorting.get(user_id, "Не установлено")

    settings_message = f"Текущие настройки:\nВремя отправки: {current_time}\nСортировка мемов: {current_sorting}"

    markup = telebot.types.InlineKeyboardMarkup()
    set_time_button = telebot.types.InlineKeyboardButton("Установить время", callback_data="set_time")
    set_sort_button = telebot.types.InlineKeyboardButton("Установить сортировку", callback_data="set_sort")
    markup.add(set_time_button, set_sort_button)

    bot.send_message(user_id, settings_message, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data in ["set_time", "set_sort"])
def settings_callback_handler(call):
    if call.data == "set_time":
        bot.send_message(call.message.chat.id, set_time_message)
        bot.register_next_step_handler(call.message, set_time)
    elif call.data == "set_sort":
        user_id = call.message.chat.id
        markup = telebot.types.InlineKeyboardMarkup()
        for option in sort_options:
            markup.add(telebot.types.InlineKeyboardButton(option, callback_data=f"sort:{option}"))
        bot.send_message(user_id, "Выберите сортировку мемов:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("sort:"))
def sort_callback_handler(call):
    user_id = call.message.chat.id
    sort_option = call.data.split(":")[1]
    user_sorting[user_id] = sort_option
    bot.send_message(user_id, f"Сортировка мемов установлена на {sort_option}.")


@bot.message_handler(commands=['set_time'])
def set_time_handler(message):
    bot.send_message(message.chat.id, set_time_message)
    bot.register_next_step_handler(message, set_time)


def set_time(message):
    user_id = message.chat.id
    time_str = message.text.strip()
    try:
        # Проверка формата времени
        datetime.strptime(time_str, '%H:%M')
        now = datetime.now()
        today_time = datetime.combine(now.date(), datetime.strptime(time_str, '%H:%M').time())

        if today_time <= now:
            # Время уже прошло на сегодня, устанавливаем на следующий день
            tomorrow_time = today_time + timedelta(days=1)
            user_times[user_id] = tomorrow_time.strftime('%H:%M')
            bot.send_message(user_id,
                             f"Время отправки ежедневных мемов установлено на {tomorrow_time.strftime('%H:%M')} "
                             f"(следующий день).")
        else:
            user_times[user_id] = time_str
            bot.send_message(user_id, f"Время отправки ежедневных мемов установлено на {time_str}.")

        # Пересчитываем расписание отправки мемов
        schedule_recalculate()

    except ValueError:
        bot.send_message(user_id, incorrect_time_format)


def schedule_recalculate():
    # Очищаем текущее расписание
    schedule.clear()

    # Заново формируем расписание на основе установленных времен отправки мемов для каждого пользователя
    for user_id, time_str in user_times.items():
        schedule.every().day.at(time_str).do(send_daily_meme, user_id)


@bot.message_handler(commands=['debug'])
def debug(message):
    logging.debug(debug_message)
    logging.getLogger().setLevel(logging.DEBUG)
    bot.send_message(message.chat.id, debug_message)
    try:
        with open('../log_file.log', 'r') as file:
            logs = file.read()
    except FileNotFoundError:
        logging.error(log_error_message)
        bot.reply_to(message, log_error_message)

    bot.send_document(message.chat.id, io.BytesIO(logs.encode()))
    clear_log_file(message)


@bot.message_handler(commands=['debug_mode_on'])
def debug_mode_on(message):
    start_debug_mode(message)


@bot.message_handler(commands=['debug_mode_off'])
def debug_mode_off(message):
    stop_debug_mode(message)


@bot.message_handler(commands=['planned_meme'])
def planned_meme_handler(message):
    bot.send_message(message.chat.id, planned_meme_message)
    bot.register_next_step_handler(message, planned_meme)


def planned_meme(message):
    date = message.text
    try:
        true_date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        if true_date <= datetime.now():
            raise ValueError(past_date_error_message)

        schedule.every().day.at(true_date.strftime('%H:%M:%S')).do(send_planned_meme, message.chat.id).tag(
            message.chat.id, true_date.strftime('%Y-%m-%d'))

        bot.send_message(message.chat.id, f"Мем будет отправлен {true_date}.")
    except ValueError:
        bot.send_message(message.chat.id, planned_meme_error_message)


def send_planned_meme(chat_id):
    meme_type, meme_url, meme_title = get_random_meme_by_tag('memes', 'new')
    try:
        # Создаем кнопки для оценки
        markup = telebot.types.InlineKeyboardMarkup()
        like_button = telebot.types.InlineKeyboardButton("👍", callback_data=f"like:{meme_url}")
        dislike_button = telebot.types.InlineKeyboardButton("👎", callback_data=f"dislike:{meme_url}")
        markup.add(like_button, dislike_button)

        if meme_type == 'image':
            bot.send_photo(chat_id, meme_url, caption=meme_title, reply_markup=markup)
        elif meme_type == 'video':
            bot.send_video(chat_id, meme_url, caption=meme_title, reply_markup=markup)

        # Инициализация рейтингов мема
        if meme_url not in meme_ratings:
            meme_ratings[meme_url] = {'likes': 0, 'dislikes': 0}

        schedule.clear(chat_id)
    except Exception as e:
        logging.error(f"Ошибка при отправке запланированного мема пользователю {chat_id}: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('like:') or call.data.startswith('dislike:'))
def callback_inline(call):
    try:
        data_parts = call.data.split(':', 1)  # Разделить строку только по первому символу ':'
        if len(data_parts) != 2:
            raise ValueError("Некорректный формат данных обратного вызова")

        meme_url = data_parts[1]
        if call.data.startswith('like:'):
            meme_ratings[meme_url]['likes'] += 1
            bot.answer_callback_query(call.id, "Вы поставили лайк!")
        elif call.data.startswith('dislike:'):
            meme_ratings[meme_url]['dislikes'] += 1
            bot.answer_callback_query(call.id, "Вы поставили дизлайк!")

        # Обновление сообщения с количеством лайков и дизлайков
        likes = meme_ratings[meme_url]['likes']
        dislikes = meme_ratings[meme_url]['dislikes']
        new_caption = f"{call.message.caption.split('👍')[0]}👍 {likes} | 👎 {dislikes}"

        bot.edit_message_caption(caption=new_caption, chat_id=call.message.chat.id, message_id=call.message.message_id,
                                 reply_markup=call.message.reply_markup)

    except Exception as e:
        logging.error(f"Ошибка при обработке обратного вызова: {e}")
        logging.error(f"Строка обратного вызова: {call.data}")
        bot.answer_callback_query(call.id, f"Произошла ошибка: {e}")


@bot.message_handler(
    func=lambda message: message.text.startswith('/') and message.text not in ['/start', '/daily_memes_stop',
                                                                               '/debug', '/debug_mode_on',
                                                                               '/debug_mode_off', '/set_time',
                                                                               '/planned_meme', '/settings'])
def invalid_command(message):
    user_id = message.from_user.id
    bot.send_message(user_id, invalid_message)
    if debugger.active:
        bot.send_message(user_id, f"Пользователь {user_id} попытался использовать команду {message.text}.")
    logging.info(f"Пользователь {user_id} попытался использовать команду {message.text}.")


@bot.message_handler(content_types=['text'])
def send_meme(message):
    user_id = message.from_user.id
    if debugger.active:
        bot.send_message(user_id, f"Пользователь {user_id} использовал команду meme.")
    try:
        tag = message.text

        # Используем сортировку, установленную пользователем, если она есть
        sort = user_sorting.get(user_id, 'new')
        meme_type, meme_url, meme_title = get_random_meme_by_tag(tag, sort)

        # Создаем кнопки для оценки
        markup = telebot.types.InlineKeyboardMarkup()
        like_button = telebot.types.InlineKeyboardButton("👍", callback_data=f"like:{meme_url}")
        dislike_button = telebot.types.InlineKeyboardButton("👎", callback_data=f"dislike:{meme_url}")
        markup.add(like_button, dislike_button)

        if meme_type == 'image':
            bot.send_photo(message.chat.id, meme_url, caption=meme_title, reply_markup=markup)
        elif meme_type == 'video':
            bot.send_video(message.chat.id, meme_url, caption=meme_title, reply_markup=markup)

        # Инициализация рейтингов мема
        if meme_url not in meme_ratings:
            meme_ratings[meme_url] = {'likes': 0, 'dislikes': 0}

    except IndexError:
        bot.reply_to(message, invalid_parameters)
    except Exception as e:
        logging.error(f"Ошибка при отправке мема: {e}")
        bot.reply_to(message, f"{error_message}: {e}")


def send_daily_meme(user_id):
    try:
        sort = user_sorting.get(user_id, 'new')
        meme_type, meme_url, meme_title = get_random_meme_by_tag('memes', sort)

        # Создаем кнопки для оценки
        markup = telebot.types.InlineKeyboardMarkup()
        like_button = telebot.types.InlineKeyboardButton("👍", callback_data=f"like:{meme_url}")
        dislike_button = telebot.types.InlineKeyboardButton("👎", callback_data=f"dislike:{meme_url}")
        markup.add(like_button, dislike_button)

        if meme_type == 'image':
            bot.send_photo(user_id, meme_url, caption=meme_title, reply_markup=markup)
            bot.send_message(user_id, daily_mem_message)
        elif meme_type == 'video':
            bot.send_message(user_id, daily_mem_message)

        # Инициализация рейтингов мема
        if meme_url not in meme_ratings:
            meme_ratings[meme_url] = {'likes': 0, 'dislikes': 0}

    except Exception as e:
        logging.error(f"Ошибка при отправке ежедневного мема пользователю {user_id}: {e}")
        bot.send_message(user_id, f"Произошла ошибка при отправке мема: {e}")


def schedule_daily_meme():
    for user_id, time_str in user_times.items():
        schedule.every().day.at(time_str).do(send_daily_meme, user_id)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    threading.Thread(target=schedule_daily_meme, daemon=True).start()
    bot.infinity_polling()
