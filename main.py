import os
import logging
import asyncio

from aiogram import Bot, Dispatcher, executor, types, utils

import links
import database
from document_parser import DocumentsParser

API_TOKEN = os.environ.get("API_TOKEN")
logging.basicConfig(level=logging.INFO)


bot = Bot(token=API_TOKEN)
dispatcher = Dispatcher(bot)

database.cursor.execute("SELECT subject, url FROM statements")
statements = {i[0]: i[1] for i in database.cursor.fetchall()}

database.cursor.execute("SELECT subject, url FROM preliminary_protocols")
preliminary_protocols = {i[0]: i[1] for i in database.cursor.fetchall()}

database.cursor.execute("SELECT subject, url FROM final_protocols")
final_protocols = {i[0]: i[1] for i in database.cursor.fetchall()}

documents_parser = DocumentsParser(
    links.links, statements, preliminary_protocols, final_protocols)

special_phrases = [
    'Посмотреть ведомости', 'Посмотреть предварительные протоколы',
    'Посмотреть итоговые протоколы'
]

special_phrases_for_subscribing = [
    'Подписаться на уведомления о новых протоколах',
    'Отписаться от уведомлений о новых протоколах'
]


@dispatcher.message_handler(commands=['start'])
async def send_start_message(message: types.Message):
    user_id = message.from_user.id
    logging.info(
        f"Start command from {message.from_user.username}, id: {user_id}")

    database.cursor.execute(
        "SELECT count(*) FROM users WHERE telegram_id = %s", (user_id, )
    )
    is_user_use_bot_before = bool(database.cursor.fetchone()[0])

    if not is_user_use_bot_before:
        database.cursor.execute(
            "INSERT INTO users(telegram_id, is_subscribed_to_notifications) "
            "VALUES (%s, %s)", (user_id, False)
        )
        database.connection.commit()

    database.cursor.execute(
        "SELECT is_subscribed_to_notifications FROM users "
        "WHERE telegram_id = %s ", (user_id, )
    )
    is_subscribed_to_notifications = database.cursor.fetchone()[0]
    keyboard_markup = types.ReplyKeyboardMarkup(
        row_width=1, resize_keyboard=True
    )

    if not is_subscribed_to_notifications:
        buttons_text = (
            'Посмотреть ведомости',
            'Посмотреть предварительные протоколы',
            'Посмотреть итоговые протоколы',
            'Подписаться на уведомления о новых протоколах'
        )
    else:
        buttons_text = (
            'Посмотреть ведомости',
            'Посмотреть предварительные протоколы',
            'Посмотреть итоговые протоколы',
            'Отписаться от уведомлений о новых протоколах'
        )

    keyboard_markup.add(
        *(types.KeyboardButton(text) for text in buttons_text))
    await message.answer(
        'Привет!\nЭто скромный бот для ленивых! 🙃',
        reply_markup=keyboard_markup
    )


@dispatcher.message_handler(lambda message: message.text in special_phrases)
async def send_available_documents(message: types.Message):
    text = None
    available_documents = None
    if message.text == 'Посмотреть ведомости':
        available_documents = \
            documents_parser.get_documents(links.LINK_TO_STATEMENTS)
        text = 'ведомости'
        logging.info(
            f"check new statements|"
            f"{message.from_user.id}|"
            f"{message.from_user.username}"
        )
    elif message.text == 'Посмотреть предварительные протоколы':
        available_documents = \
            documents_parser.get_documents(links.LINK_TO_PRELIMINARY_PROTOCOLS)
        text = 'предварительные протоколы'
        logging.info(
            f"check new preliminary protocols|"
            f"{message.from_user.id}|"
            f"{message.from_user.username}"
        )
    elif message.text == 'Посмотреть итоговые протоколы':
        available_documents = \
            documents_parser.get_documents(links.LINK_TO_FINAL_PROTOCOLS)
        text = 'итоговые протоколы'
        logging.info(
            f"check new final_protocols|"
            f"{message.from_user.id}|"
            f"{message.from_user.username}"
        )
    await message.answer('\n'.join([
        f'Доступные на данный момент {text}:',
        *[utils.markdown.link(key, available_documents[key])
          for key in available_documents.keys()]
    ]), parse_mode='Markdown', disable_web_page_preview=True)


@dispatcher.message_handler(
    lambda message: message.text in special_phrases_for_subscribing)
async def notifications(message: types.Message):
    message_text = None
    buttons_text = None
    keyboard_markup = types.ReplyKeyboardMarkup(row_width=1,
                                                resize_keyboard=True)

    if message.text == 'Подписаться на уведомления о новых протоколах':
        database.cursor.execute(
            "UPDATE users "
            "SET is_subscribed_to_notifications = True "
            "WHERE telegram_id = %s", (message.from_user.id, )
        )
        buttons_text = (
            'Посмотреть ведомости',
            'Посмотреть предварительные протоколы',
            'Посмотреть итоговые протоколы',
            'Отписаться от уведомлений о новых протоколах'
        )
        message_text = "С данного момента, вы подписаны на уведомления."
    elif message.text == 'Отписаться от уведомлений о новых протоколах':
        database.cursor.execute(
            "UPDATE users "
            "SET is_subscribed_to_notifications = False "
            "WHERE telegram_id = %s", (message.from_user.id, )
        )
        buttons_text = (
            'Посмотреть ведомости',
            'Посмотреть предварительные протоколы',
            'Посмотреть итоговые протоколы',
            'Подписаться на уведомления о новых протоколах'
        )
        message_text = "С данного момента, вы отписаны от уведомлений."

    keyboard_markup.add(*(types.KeyboardButton(text) for text in buttons_text))
    database.connection.commit()
    await message.answer(message_text, reply_markup=keyboard_markup)


@dispatcher.message_handler(commands=['appealsdocuments'])
async def send_available_appeals_documents(message: types.Message):
    available_documents = documents_parser.get_documents(
        links.LINK_TO_APPEALS_DOCUMENTS
    )
    await message.answer('\n'.join([
        f'Доступные на данный момент даты аппеляций:',
        *[utils.markdown.link(key, available_documents[key])
          for key in available_documents.keys()]
    ]), parse_mode='Markdown', disable_web_page_preview=True)


async def send_notifications():
    new_documents = documents_parser.check_for_new_documents()
    message_text = []

    if len(new_documents[0]) > 0:
        message_text.append("Новые ведомости: ")
        for key in new_documents[0].keys():
            message_text.append(
                utils.markdown.link(key, new_documents[0][key]))
        message_text.append('')

    if len(new_documents[1]) > 0:
        message_text.append("Новые предварительные протоколы: ")
        for key in new_documents[1].keys():
            message_text.append(
                utils.markdown.link(key, new_documents[1][key]))
        message_text.append('')

    if len(new_documents[2]) > 0:
        message_text.append("Новые итоговые протоколы: ")
        for key in new_documents[2].keys():
            message_text.append(
                utils.markdown.link(key, new_documents[2][key]))
        message_text.append('')

    database.cursor.execute(
        "SELECT telegram_id FROM users "
        "WHERE is_subscribed_to_notifications = TRUE"
    )
    users_ids = database.cursor.fetchall()

    if len(message_text) > 0:
        for user_id in users_ids:
            await bot.send_message(
                user_id[0], '\n'.join(message_text),
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
        logging.info(
            f"Send notifications to "
            f"{''.join(map(str, [user_id[0] for user_id in users_ids]))}"
        )

    when_to_call = loop.time() + delay
    loop.call_at(when_to_call, add_task)


def add_task():
    asyncio.ensure_future(send_notifications())


loop = asyncio.get_event_loop()
delay = 300

add_task()

executor.start_polling(dispatcher, skip_updates=True)

database.cursor.close()
database.connection.close()
