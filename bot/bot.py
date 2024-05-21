import io
import logging
import telebot
from config import TOKEN
from debug import clear_log_file, debugger, start_debug_mode, stop_debug_mode
from reddit_memes import get_random_meme_by_tag
from strings import start_message, error_message, invalid_message, not_enough_parameters, \
    invalid_parameters, debug_message, log_error_message, categories_sort_message, time_sort_message, \
    for_example_message

bot = telebot.TeleBot(TOKEN)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    filename="../log_file.log",
    filemode="a",
)


@bot.message_handler(commands=['start'])
def send_start_message(message):
    if debugger.active:
        bot.send_message(message.chat.id, f"Log: Бот запущен")
    logging.info("Бот запущен")
    bot.send_message(message.chat.id, start_message)
    bot.send_message(message.chat.id, categories_sort_message)
    bot.send_message(message.chat.id, time_sort_message)
    bot.send_message(message.chat.id, for_example_message)


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


@bot.message_handler(commands=['meme'])
def send_meme(message):
    if debugger.active:
        bot.send_message(message.chat_id, f"Log: Пользователь {message.chat.id} использовал команду /meme.")
    logging.info(f"Пользователь {message.chat.id} использовал команду /meme.")
    try:
        # Получаем параметры из сообщения пользователя
        params = message.text.split(maxsplit=3)

        if len(params) < 2:
            raise IndexError(not_enough_parameters)

        tag = params[1]
        sort = params[2] if len(params) > 2 else 'hot'
        time_filter = params[3] if len(params) > 3 else 'all'

        meme_type, meme_url, meme_title = get_random_meme_by_tag(tag, sort, time_filter)

        # Отправляем мем в виде фотографии или видео с описанием
        if meme_type == 'image':
            bot.send_photo(message.chat.id, meme_url, caption=meme_title)
            logging.info(f"Пользователю {message.chat.id} отправлено фото с описанием {meme_title}.")
        elif meme_type == 'video':
            bot.send_video(message.chat.id, meme_url, caption=meme_title)
            logging.info(f"Пользователю {message.chat.id} отправлено видео с описанием {meme_title}.")
    except IndexError:
        bot.reply_to(message, invalid_parameters)
        logging.info(f"Пользователь {message.chat.id} неверно ввел параметры запроса.")
    except Exception as e:
        bot.reply_to(message, f"{error_message}: {e}")
        logging.info(f"Ошибка при отправке мема: {e}")


@bot.message_handler(func=lambda message: message.text[0] == '/' and message.text != 'start' or message.text != '/meme')
def invalid_command(message):
    bot.send_message(message.chat_id, invalid_message)
    if debugger.active:
        bot.send_message(message.chat_id,
                         f"Пользователь {message.chat.id} попытался использовать команду {message.text}.")
    logging.info(f"Пользователь {message.chat.id} использовал несуществующую команду {message.text}.")


if __name__ == '__main__':
    bot.polling(none_stop=True)
