import telebot
import sqlite3
import traceback
import uuid
from time import sleep
from multiprocessing import Process, Manager

from telebot import types, apihelper
from utils import *
from config import *


class TeleBotModify(telebot.TeleBot):
    def set_mdict(self, mdict):
        self.mdict = mdict


apihelper.ENABLE_MIDDLEWARE = True
bot = TeleBotModify(f"{TG_TOKEN}", parse_mode='MarkdownV2', threaded=True, num_threads=1)

conn = sqlite3.connect('db.db', check_same_thread=False)
conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
cursor = conn.cursor()

manager = None

USER_INPUT_FLAGS = {}


@bot.middleware_handler(update_types=['message'])
def set_session(bot_instance, message):
    user_id = message.from_user.id
    user_data = get_user_or_none(user_id, cursor)
    if not user_data:
        create_user(user_id, message.chat.id, cursor, conn)
        user_data = get_user_or_none(user_id, cursor)
    message.user_data = user_data


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    if message.user_data['notifications_status']:
        itembtn1 = types.InlineKeyboardButton('Остановить рассылку', callback_data="stop_notifications")
    else:
        itembtn1 = types.InlineKeyboardButton('Включить рассылку', callback_data="start_notifications")
    markup.add(itembtn1)
    bot.reply_to(message,
                 "Здравствуйте\! 👋🏻\n\n💌 _Я могу присылать Вам последние новости, о которых Вам стоит знать\.\n\n📪 Вы "
                 "можете в любой момент включить/отключить рассылку, нажав на соответствующую кнопку на клавиатуре бота\._",
                 reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "stop_notifications")
def stop_notifiactions(call):
    user_id = call.from_user.id
    stop_user_notifications(user_id, cursor, conn)

    markup = types.InlineKeyboardMarkup(row_width=1)
    itembtn1 = types.InlineKeyboardButton('Включить рассылку', callback_data="start_notifications")
    markup.add(itembtn1)

    bot.reply_to(call.message,
                 "😔 Рассылка новостей преостановлена\.\n\n📪 _Если в будущем, Вы захотите включить рассылку, "
                 "то нажмите \"Включить рассылку\"\._", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "start_notifications")
def start_notifiactions(call):
    user_id = call.from_user.id
    start_user_notifications(user_id, cursor, conn)

    markup = types.InlineKeyboardMarkup(row_width=1)
    itembtn1 = types.InlineKeyboardButton('Остановить рассылку', callback_data="stop_notifications")
    markup.add(itembtn1)

    bot.reply_to(call.message,
                 "☺️Рассылка новостей включена\.\n\n📫 _Если в будущем, Вы захотите выключить рассылку, то нажмите "
                 "\"Остановить рассылку\"\._", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Создать рассылку")
def start_mailing(message):
    if message.user_data['admin_status']:
        user_id = message.from_user.id
        USER_INPUT_FLAGS[user_id] = True

        markup = types.ReplyKeyboardRemove()

        bot.reply_to(message,
                     "*\(\!\)* Для создания рассылки отправьте мне сообщение, которое нужно разослать и я __сразу же его разошлю__\.",
                     reply_markup=markup)

        markup = types.InlineKeyboardMarkup(row_width=1)
        itembtn1 = types.InlineKeyboardButton('Отмена', callback_data="cancel")
        markup.add(itembtn1)

        bot.send_message(message.chat.id, "Или нажмите \"Отмена\", чтобы вернуться назад\.", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "cancel")
def cancel(call):
    user_id = call.from_user.id
    user_data = get_user_or_none(user_id, cursor)
    if user_data and user_data['admin_status']:
        USER_INPUT_FLAGS[user_id] = False
        markup = types.ReplyKeyboardMarkup(row_width=1)
        itembtn1 = types.KeyboardButton('Создать рассылку')
        itembtn2 = types.KeyboardButton('Статистика')
        markup.add(itembtn1, itembtn2)

        bot.reply_to(call.message,
                         "Добро пожаловать в *Панель Администратора*\! 👋🏻\n\n🖥 _Вы можете выбрать нужную опцию "
                         "ниже или "
                         "вернуться обратно\._", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "/adm")
def admin_panel(message):
    if message.user_data['admin_status']:
        user_id = message.from_user.id
        USER_INPUT_FLAGS[user_id] = False
        markup = types.ReplyKeyboardMarkup(row_width=1)
        itembtn1 = types.KeyboardButton('Создать рассылку')
        itembtn2 = types.KeyboardButton('Статистика')
        markup.add(itembtn1, itembtn2)

        bot.reply_to(message,
                     "Добро пожаловать в *Панель Администратора*\! 👋🏻\n\n🖥 _Вы можете выбрать нужную опцию ниже или "
                     "вернуться обратно\._", reply_markup=markup)


def mailer(messages_to_send_queue):
    markup = types.InlineKeyboardMarkup(row_width=1)
    itembtn1 = types.InlineKeyboardButton('Остановить рассылку', callback_data="stop_notifications")
    markup.add(itembtn1)

    while True:
        sleep(3)
        markup = types.InlineKeyboardMarkup(row_width=1)
        itembtn1 = types.InlineKeyboardButton('Остановить рассылку', callback_data="stop_notifications")
        markup.add(itembtn1)
        for mq_key in messages_to_send_queue.keys():
            users = get_all_users(cursor)
            for user in users:
                if user['admin_status']:
                    adm_markup = types.ReplyKeyboardMarkup(row_width=2)
                    itembtn1 = types.KeyboardButton('Создать рассылку')
                    itembtn2 = types.KeyboardButton('Статистика')
                    adm_markup.add(itembtn1, itembtn2)

                    bot.send_message(user['chat_id'],
                                     "✅ Рассылка успешно запущена\!\n\nПеред Вами *Панель Администратора*\! 👋🏻\n\n🖥 _Вы можете выбрать нужную опцию ниже или "
                                     "вернуться обратно\._", reply_markup=adm_markup)

            content = messages_to_send_queue[mq_key]['content']
            content_type = messages_to_send_queue[mq_key]['content_type']
            if content_type == "text":
                for user in users:
                    if user['notifications_status']:
                        try:
                            bot.send_message(user['chat_id'], text=escape_markdown(content[0]), reply_markup=markup)
                        except:
                            traceback.print_exc()
                            continue
            elif content_type == 'multimedia':
                for user in users:
                    if user['notifications_status']:
                        try:
                            bot.send_media_group(user['chat_id'], media=content)
                            # bot.send_message(user['chat_id'], text="📫 Вы всегда можете остановить рассылку!",
                            #                  reply_markup=markup, parse_mode="Markdown")
                        except:
                            traceback.print_exc()
                            continue
            del (messages_to_send_queue[mq_key])


@bot.message_handler(func=lambda message: message.text == "Статистика")
def admin_auth(message):
    if message.user_data['admin_status']:
        bot.reply_to(message,
                     get_bot_stats(cursor))


@bot.message_handler(func=lambda message: USER_INPUT_FLAGS.get(message.from_user.id),
                     content_types=['document', 'audio', 'photo', 'video', 'text'])
def send_notifications(message):
    users = get_all_users(cursor)
    markup = types.InlineKeyboardMarkup(row_width=1)
    itembtn1 = types.InlineKeyboardButton('Остановить рассылку', callback_data="stop_notifications")
    markup.add(itembtn1)

    if not message.media_group_id:
        message.media_group_id = message.id

    if message.content_type == "text":
        mdict_set_or_add_el(message.media_group_id, message.text, "text")

    elif message.content_type == "photo":
        mdict_set_or_add_el(message.media_group_id,
                            types.InputMediaPhoto(message.photo[-1].file_id, caption=escape_markdown(message.caption)),
                            "multimedia")

    elif message.content_type == "video":
        mdict_set_or_add_el(message.media_group_id,
                            types.InputMediaVideo(message.video.file_id, caption=escape_markdown(message.caption)),
                            "multimedia")
        # file_id_info = bot.get_file(message.video.file_id)
        # downloaded_file = bot.download_file(file_id_info.file_path)

    USER_INPUT_FLAGS[message.from_user.id] = False


def mdict_set_or_add_el(key, value, content_type):
    if bot.mdict.get(key):
        mdict_by_key_copy = bot.mdict[key].copy()
        mdict_by_key_copy['content'].append(value)
        bot.mdict[key] = mdict_by_key_copy
    else:
        bot.mdict[key] = {'content_type': content_type, 'content': [value]}


@bot.message_handler(func=lambda message: message.text == f"{ADMIN_PASS}")
def admin_auth(message):
    user_id = message.from_user.id
    set_admin_status(user_id, cursor, conn)

    bot.reply_to(message,
                 "Вы авторизовались как администратор 👋🏻\n\n🖥 _Используйте команду */adm*, "
                 "чтобы открыть *Панель Администратора*\._ ")


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    markup = types.InlineKeyboardMarkup()
    if message.user_data['notifications_status']:
        itembtn1 = types.InlineKeyboardButton('Остановить рассылку', callback_data="stop_notifications")
    else:
        itembtn1 = types.InlineKeyboardButton('Включить рассылку', callback_data="start_notifications")
    markup.add(itembtn1)
    bot.reply_to(message,
                 "Здравствуйте\! 👋🏻\n\n💌 _Я могу присылать Вам последние новости, о которых Вам стоит знать\.\n\n📪 Вы "
                 "можете в любой момент включить/отключить рассылку, нажав на соответствующую кнопку на клавиатуре бота\._",
                 reply_markup=markup)


if __name__ == '__main__':
    manager = Manager()
    messages_to_send_queue = manager.dict()
    Process(target=mailer, args=(messages_to_send_queue,)).start()
    bot.set_mdict(messages_to_send_queue)
    bot.polling(none_stop=True)
