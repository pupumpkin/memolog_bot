import logging
import telebot
from config import TOKEN

bot = telebot.TeleBot(TOKEN)


def clear_log_file(message):
    if logging.getLogger().isEnabledFor(logging.DEBUG):
        bot.send_message(message.chat.id, f"DEBUG LOG: Лог файл очищен")
    logging.info("Лог файл очищен")
    with open("../log_file.log", "w") as file:
        file.write("")


class DebugMode:
    def __init__(self):
        self.active = False


debugger = DebugMode()


def start_debug_mode(message):
    debugger.active = True
    bot.send_message(message.chat.id, "Режим отладки включен. Теперь вы получите статусы запросов и логи запросов.")


def stop_debug_mode(message):
    debugger.active = False
    bot.send_message(message.chat.id, "Режим отладки выключен.")
