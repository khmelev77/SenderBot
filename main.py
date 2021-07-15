import telebot
import sqlite3
import traceback

from telebot import types, apihelper
from utils import *
from config import *


apihelper.ENABLE_MIDDLEWARE = True
bot = telebot.TeleBot(f"{TG_TOKEN}", parse_mode='MarkdownV2')

conn = sqlite3.connect('db.db', check_same_thread=False)
conn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
cursor = conn.cursor()

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
        markup = types.ReplyKeyboardMarkup(row_width=1)
        itembtn1 = types.KeyboardButton('Отмена')
        markup.add(itembtn1)

        bot.reply_to(message,
                     "*\(\!\)* Для создания рассылки отправьте мне сообщение, которое нужно разослать и я __сразу же его разошлю__\.\n\nИли нажмите \"Отмена\", чтобы вернуться назад\.", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text in ["/adm", "Отмена"])
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


@bot.message_handler(func=lambda message: USER_INPUT_FLAGS.get(message.from_user.id), content_types=['document', 'audio', 'photo', 'video', 'text'])
def send_notifications(message):
    users = get_all_users(cursor)

    markup = types.InlineKeyboardMarkup(row_width=1)
    itembtn1 = types.InlineKeyboardButton('Остановить рассылку', callback_data="stop_notifications")
    markup.add(itembtn1)

    if message.content_type == "text":
        for user in users:
            try:
                bot.send_message(user['chat_id'], text=message.text, reply_markup=markup)
            except:
                traceback.print_exc()
                continue

    elif message.content_type == "photo":
        for user in users:
            try:
                bot.send_photo(user['chat_id'], photo=message.photo[-1].file_id, caption=message.caption, reply_markup=markup)
            except:
                traceback.print_exc()
                continue

    elif message.content_type == "video":
        file_id_info = bot.get_file(message.video.file_id)
        downloaded_file = bot.download_file(file_id_info.file_path)
        for user in users:
            try:
                bot.send_video(user['chat_id'], data=downloaded_file, caption=message.caption, reply_markup=markup)
            except:
                traceback.print_exc()
                continue

    markup = types.ReplyKeyboardMarkup(row_width=1)
    itembtn1 = types.KeyboardButton('Создать рассылку')
    itembtn2 = types.KeyboardButton('Статистика')
    itembtn3 = types.KeyboardButton('Назад')
    markup.add(itembtn1, itembtn2, itembtn3)

    USER_INPUT_FLAGS[message.from_user.id] = False

    bot.send_message(message.chat.id,
                 "✅ Рассылка успешно окончена\!\n\nДобро пожаловать в *Панель Администратора*\! 👋🏻\n\n🖥 _Вы можете выбрать нужную опцию ниже или "
                 "вернуться обратно\._", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == f"{ADMIN_PASS}")
def admin_auth(message):
    user_id = message.from_user.id
    set_admin_status(user_id, cursor, conn)

    bot.reply_to(message,
                 "Вы авторизовались как администратор 👋🏻\n\n🖥 _Используйте команду */adm*, "
                 "чтобы открыть *Панель Администратора*\._ ")


@bot.message_handler(func=lambda message: message.text == "Статистика")
def admin_auth(message):
    if message.user_data['admin_status']:
        bot.reply_to(message,
                     get_bot_stats(cursor))


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



bot.polling(none_stop=True)
