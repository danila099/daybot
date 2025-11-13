import telebot
from datetime import datetime, date
import sqlite3

bot = telebot.TeleBot('7940654185:AAHaqBhLa8vKIa9h52OsYGGJxYz9DVv7uT0')

conn = sqlite3.connect('birthdays.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS birthdays (
        user_id INTEGER PRIMARY KEY,
        birthday TEXT,
        created_at TEXT
    )''')
conn.commit()
conn.close()

def days_until_birthday(birthday_str):
    today = date.today()
    
    try:
        birthday = datetime.strptime(birthday_str, "%d.%m.%Y").date()
    except ValueError:
        return None, "Неверный формат даты. Используйте ДД.ММ.ГГГГ"
    next_birthday = date(today.year, birthday.month, birthday.day)
    if next_birthday < today:
        next_birthday = date(today.year + 1, birthday.month, birthday.day)
    days_left = (next_birthday - today).days
    return days_left, None

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Привет! Я бот, который поможет тебе запоминать дни рождения! \n Чтобы узнать команды напишите /help ')

@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id, 'Чтобы добавить деньрождение напишите /setbirthday \n Чтобы узнать сколько дней до своего дня рождения напишите /mybirthday')  

@bot.message_handler(commands=['setbirthday']) 
def set_birthday(message):
    bot.send_message(message.chat.id, "Введите вашу дату рождения в формате ДД.ММ.ГГГГ (например: 15.05.1990)")
    bot.register_next_step_handler(message, save_birthday)

def save_birthday(message):
    user_id = message.from_user.id
    birthday = message.text
    try:
        datetime.strptime(birthday, "%d.%m.%Y")
    except ValueError:
        bot.send_message(message.chat.id, "Неверный формат даты. Используйте ДД.ММ.ГГГГ")
        return
    conn = sqlite3.connect('birthdays.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO birthdays (user_id, birthday, created_at)
        VALUES (?, ?, ?)
    ''', (user_id, birthday, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, "Дата рождения успешно сохранена!")
     
@bot.message_handler(commands=['mybirthday'])
def check_birthday(message):
    user_id = message.from_user.id
    
    conn = sqlite3.connect('birthdays.db')
    cursor = conn.cursor()
    cursor.execute('''SELECT birthday FROM birthdays WHERE user_id = ?''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if not result:
        bot.send_message(message.chat.id, "У вас нет сохраненных дней рождения. Чтобы добавить день рождения напишите /setbirthday")
        return
    
    birthday_str = result[0]
    days_left, error = days_until_birthday(birthday_str)
    
    if error:
        bot.send_message(message.chat.id, f"❌ Ошибка: {error}")
        return
    
    if days_left == 0:
        bot.send_message(message.chat.id, f"Ваш день рождения сегодня! Поздравляем!")
    elif days_left == 1:
        bot.send_message(message.chat.id, f"До вашего дня рождения остался 1 день.")
    else:
        bot.send_message(message.chat.id, f"До вашего дня рождения осталось {days_left} дней.")
        
bot.polling()
