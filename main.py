import re
import sys
import telebot
import sqlite3
from requests import ReadTimeout
from dotenv import load_dotenv
import os

load_dotenv()

API_TOKEN = os.getenv('API_TOKEN')
CHANNEL_ID = os.getenv('CHANNEL_ID')
GROUP_ID = int(os.getenv('GROUP_ID'))

bot = telebot.TeleBot(API_TOKEN)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Привет! 👋 Я — ваш помощник для технической поддержки. Чем могу помочь?")


@bot.message_handler(chat_types=['private'])
def handle_appeal(message):
    conn = sqlite3.connect('appeals.db')
    c = conn.cursor()
    c.execute('SELECT appeal_id FROM active_users WHERE chat_id = ?', (message.chat.id,))
    active_appeal = c.fetchone()

    if active_appeal is None:
        create_appeal(message, conn, c)
    else:
        appeal_id = active_appeal[0]
        c.execute('SELECT message_id FROM appeals WHERE appeal_id = ?', (appeal_id,))
        message_id = c.fetchone()[0]
        bot.send_message(GROUP_ID, message.text, reply_to_message_id=message_id)

    conn.close()


def create_appeal(message, conn, c):
    appeal_id = get_next_appeal_id(conn, c)
    client_id = message.from_user.id
    client_name = message.from_user.first_name
    client_message = message.text

    c.execute('''
        INSERT INTO appeals (appeal_id, client_id, client_name, client_message, manager_comments, closed, message_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (appeal_id, client_id, client_name, client_message, '', 0, None))
    conn.commit()
    appeal_text = f"Обращение #{appeal_id} от {client_name} ({client_id}): {client_message}"
    bot.send_message(CHANNEL_ID, appeal_text)

    c.execute('INSERT INTO active_users (chat_id, appeal_id) VALUES (?, ?)', (message.chat.id, appeal_id))
    conn.commit()
    bot.reply_to(message,
                 f"Ваш запрос успешно принят! Мы уже работаем над решением. Наш менеджер скоро с вами свяжется. 🛠️")


def get_next_appeal_id(conn, c):
    c.execute('SELECT MAX(appeal_id) FROM appeals')
    max_id = c.fetchone()[0]
    if max_id is None:
        return 1
    return max_id + 1


@bot.message_handler(content_types=['text'])
def handle_manager_comments(message):
    if message.reply_to_message:
        if message.reply_to_message.text.startswith("Обращение #"):
            appeal_id = int(message.reply_to_message.text.split(' ')[1].split('#')[1])
            conn = sqlite3.connect('appeals.db')
            c = conn.cursor()
            c.execute('SELECT * FROM appeals WHERE appeal_id = ?', (appeal_id,))
            appeal = c.fetchone()
            if appeal:
                if appeal[5] == 1:
                    return
                manager_comments = appeal[4]
                updated_comments = manager_comments + '\n' + message.text if manager_comments else message.text
                c.execute('UPDATE appeals SET manager_comments = ? WHERE appeal_id = ?', (updated_comments, appeal_id))
                conn.commit()
                client_id = appeal[1]
                if message.text == "/solved":
                    c.execute('UPDATE appeals SET closed = 1 WHERE appeal_id = ?', (appeal_id,))
                    c.execute('DELETE FROM active_users WHERE chat_id = ?', (client_id,))
                    conn.commit()
                    bot.send_message(message.chat.id, f"Обращение #{appeal_id} закрыто")
                    bot.send_message(client_id,
                                     f"Ваше обращение закрыто. Спасибо, что обратились! Если возникнут новые вопросы, не стесняйтесь написать нам снова. 😊")
                else:

                    bot.send_message(client_id, message.text)

            conn.close()

    which_message = process_message(message)
    if which_message is not None:
        conn = sqlite3.connect('appeals.db')
        c = conn.cursor()
        c.execute('UPDATE appeals SET message_id = ? WHERE client_id = ?', (which_message[0], which_message[1]))
        conn.commit()
        conn.close()


def process_message(message):
    if message.chat.id == GROUP_ID and message.from_user.first_name == 'Telegram':
        message_id = message.message_id
        user_id_match = re.search(r'\((\d+)\)', message.text)
        if user_id_match:
            user_id = int(user_id_match.group(1))
            return message_id, user_id

    return None


if __name__ == '__main__':
    try:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
    except (ConnectionError, ReadTimeout) as e:
        sys.stdout.flush()
        os.execv(sys.argv[0], sys.argv)
    else:
        bot.infinity_polling(timeout=10, long_polling_timeout=5)
