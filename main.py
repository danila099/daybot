import telebot
from datetime import datetime, date, timedelta
import sqlite3
import threading
import time
import schedule
import random

bot = telebot.TeleBot('Your_Bot_Token')

def init_db():
    conn = sqlite3.connect('birthdays.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS birthdays (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            birthday TEXT,
            created_at TEXT
        )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS group_settings (
            group_id INTEGER PRIMARY KEY,
            auto_congratulate INTEGER DEFAULT 1,
            daily_reminder INTEGER DEFAULT 0
        )''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS group_birthdays (
            group_id INTEGER,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            birthday TEXT,
            created_at TEXT,
            PRIMARY KEY (group_id, user_id)
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

def create_congratulation(name, age):
    congratulations = [
        f"🎉 С ДНЕМ РОЖДЕНИЯ, {name}! 🎂\nИсполняется {age} лет! Пусть все мечты сбываются! 🌟",
        f"🎂 {name}, ПОЗДРАВЛЯЕМ С ДНЕМ РОЖДЕНИЯ! 🎉\n{age} лет - отличный возраст! Желаем счастья! 🥳",
        f"🌟 {name}, С ДНЕМ РОЖДЕНИЯ! 🎂\nВ {age} лет жизнь только начинается! Ура! 🎊",
        f"🎁 Друзья! Сегодня у {name} ДЕНЬ РОЖДЕНИЯ! 🎉\nИсполняется {age} лет! Давайте поздравим! 🥂"
    ]
    return random.choice(congratulations)

def check_todays_birthdays():
    """Проверяет дни рождения на сегодня и отправляет поздравления"""
    conn = sqlite3.connect('birthdays.db', check_same_thread=False)
    cursor = conn.cursor()

    cursor.execute('SELECT user_id, username, first_name, birthday FROM birthdays')
    users = cursor.fetchall()
    
    for user_id, username, first_name, birthday_str in users:
        days_left, _ = days_until_birthday(birthday_str)
        if days_left == 0:
            name = f"@{username}" if username else first_name
            birthday_date = datetime.strptime(birthday_str, "%d.%m.%Y").date()
            age = date.today().year - birthday_date.year
            
            congratulation = create_congratulation(name, age)
            try:
                bot.send_message(user_id, congratulation)
                print(f"✅ Отправлено поздравление пользователю {name}")
            except Exception as e:
                print(f"❌ Ошибка отправки пользователю {user_id}: {e}")
    
    cursor.execute('SELECT DISTINCT group_id FROM group_settings WHERE auto_congratulate = 1')
    groups = cursor.fetchall()
    
    for (group_id,) in groups:
        cursor.execute('''
            SELECT username, first_name, birthday FROM group_birthdays WHERE group_id = ?
        ''', (group_id,))
        birthdays = cursor.fetchall()
        
        for username, first_name, birthday_str in birthdays:
            days_left, _ = days_until_birthday(birthday_str)
            if days_left == 0:
                name = f"@{username}" if username else first_name
                birthday_date = datetime.strptime(birthday_str, "%d.%m.%Y").date()
                age = date.today().year - birthday_date.year
                
                congratulation = create_congratulation(name, age)
                try:
                    bot.send_message(group_id, congratulation)
                    print(f"✅ Отправлено поздравление для {name} в группе {group_id}")
                except Exception as e:
                    print(f"❌ Ошибка отправки в группе {group_id}: {e}")
    
    conn.close()

def send_daily_reminders():
    """Отправляет ежедневные напоминания"""
    conn = sqlite3.connect('birthdays.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT group_id FROM group_settings WHERE daily_reminder = 1')
    groups = cursor.fetchall()
    
    for (group_id,) in groups:
        upcoming_birthdays = []
        cursor.execute('SELECT username, first_name, birthday FROM group_birthdays WHERE group_id = ?', (group_id,))
        birthdays = cursor.fetchall()
        
        for username, first_name, birthday_str in birthdays:
            days_left, _ = days_until_birthday(birthday_str)
            if 0 < days_left <= 7:
                upcoming_birthdays.append((username, first_name, birthday_str, days_left))
        
        if upcoming_birthdays:
            upcoming_birthdays.sort(key=lambda x: x[3])
            reminder_text = "📅 Ближайшие дни рождения в группе:\n\n"
            
            for username, first_name, birthday_str, days_left in upcoming_birthdays[:5]:
                name = f"@{username}" if username else first_name
                birthday_date = datetime.strptime(birthday_str, "%d.%m.%Y").date()
                age = date.today().year - birthday_date.year
                
                if days_left == 1:
                    reminder_text += f"🎁 {name} - ЗАВТРА! ({age} лет)\n"
                else:
                    reminder_text += f"🎁 {name} - через {days_left} дней ({age} лет)\n"
            
            try:
                bot.send_message(group_id, reminder_text)
            except Exception as e:
                print(f"❌ Ошибка отправки напоминания в группу {group_id}: {e}")
    
    conn.close()

def scheduler():
    schedule.every().day.at("09:00").do(check_todays_birthdays)
    schedule.every().day.at("10:00").do(send_daily_reminders)
    
    while True:
        schedule.run_pending()
        time.sleep(60)

def start_scheduler():
    scheduler_thread = threading.Thread(target=scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type in ['group', 'supergroup']:
        welcome_text = """
🎉 Я бот для отслеживания дней рождений в группе!

Команды в группе:
/setbirthday - Добавить свой день рождения
/listbirthdays - Все дни рождения в группе
/nextbirthday - Ближайший день рождения
/today - Кто сегодня празднует?
/autoon - Включить авто-поздравления
/autooff - Выключить авто-поздравления
/reminderson - Включить напоминания
/remindersoff - Выключить напоминания
        """
    else:
        welcome_text = """
👋 Привет! Я бот, который поможет тебе запоминать дни рождения!

Команды в ЛС:
/setbirthday - Добавить день рождения
/mybirthday - Узнать сколько дней до ДР

Команды в группе:
/setbirthday - Добавить свой ДР в группу
/listbirthdays - Список всех ДР в группе
/autoon - Включить авто-поздравления
        """
    bot.send_message(message.chat.id, welcome_text)

@bot.message_handler(commands=['help'])
def help(message):
    if message.chat.type in ['group', 'supergroup']:
        help_text = """
📋 Команды для группы:

/setbirthday - Добавить свой день рождения в группу
/listbirthdays - Показать все дни рождения в группе
/nextbirthday - Ближайший день рождения
/today - Кто сегодня празднует?
/mybirthday - Мой день рождения
/autoon - Включить авто-поздравления (09:00)
/autooff - Выключить авто-поздравления
/reminderson - Включить ежедневные напоминания
/remindersoff - Выключить напоминания
        """
    else:
        help_text = """
📋 Команды в личных сообщениях:

/setbirthday - Добавить свой день рождения
/mybirthday - Узнать сколько дней до дня рождения
        """
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['setbirthday'])
def set_birthday(message):
    if message.chat.type in ['group', 'supergroup']:
        bot.send_message(message.chat.id, "📅 Введите дату рождения в формате ДД.ММ.ГГГГ (например: 15.05.1990)")
        bot.register_next_step_handler(message, save_group_birthday)
    else:
        bot.send_message(message.chat.id, "📅 Введите вашу дату рождения в формате ДД.ММ.ГГГГ (например: 15.05.1990)")
        bot.register_next_step_handler(message, save_private_birthday)

def save_private_birthday(message):
    user_id = message.from_user.id
    user = message.from_user
    birthday_text = message.text.strip()
    
    try:
        datetime.strptime(birthday_text, "%d.%m.%Y")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат! Используйте ДД.ММ.ГГГГ")
        return
    
    conn = sqlite3.connect('birthdays.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO birthdays (user_id, username, first_name, birthday, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, user.username, user.first_name, birthday_text, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    days_left, _ = days_until_birthday(birthday_text)
    if days_left == 0:
        bot.send_message(message.chat.id, "🎉 С Днем Рождения! Дата успешно сохранена!")
    else:
        bot.send_message(message.chat.id, f"✅ Дата рождения сохранена! До ДР осталось {days_left} дней")

def save_group_birthday(message):
    user = message.from_user
    group_id = message.chat.id
    birthday_text = message.text.strip()
    
    try:
        datetime.strptime(birthday_text, "%d.%m.%Y")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат! Используйте ДД.ММ.ГГГГ")
        return
    
    conn = sqlite3.connect('birthdays.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO group_birthdays 
        (group_id, user_id, username, first_name, birthday, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (group_id, user.id, user.username, user.first_name, birthday_text, datetime.now().isoformat()))
    conn.commit()
    conn.close()
    
    name = f"@{user.username}" if user.username else user.first_name
    days_left, _ = days_until_birthday(birthday_text)
    
    if days_left == 0:
        response = f"🎉 {name}, с Днем Рождения! Дата добавлена в группу!"
    else:
        response = f"✅ {name} добавил(а) день рождения: {birthday_text}\nДо ДР осталось: {days_left} дней"
    
    bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['mybirthday'])
def check_birthday(message):
    user_id = message.from_user.id
    
    if message.chat.type in ['group', 'supergroup']:
        group_id = message.chat.id
        conn = sqlite3.connect('birthdays.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT birthday FROM group_birthdays WHERE group_id = ? AND user_id = ?', (group_id, user_id))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            bot.send_message(message.chat.id, "❌ У вас нет сохраненного дня рождения в этой группе. Используйте /setbirthday")
            return
    else:
        conn = sqlite3.connect('birthdays.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('SELECT birthday FROM birthdays WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            bot.send_message(message.chat.id, "❌ У вас нет сохраненного дня рождения. Используйте /setbirthday")
            return
    
    birthday_str = result[0]
    days_left, error = days_until_birthday(birthday_str)
    
    if error:
        bot.send_message(message.chat.id, f"❌ Ошибка: {error}")
        return
    
    birthday_date = datetime.strptime(birthday_str, "%d.%m.%Y").date()
    age = date.today().year - birthday_date.year
    
    if days_left == 0:
        bot.send_message(message.chat.id, f"🎉 С ДНЕМ РОЖДЕНИЯ! Сегодня вам исполняется {age} лет! 🎂")
    elif days_left == 1:
        bot.send_message(message.chat.id, f"📅 До вашего дня рождения остался 1 день! Исполнится {age} лет")
    else:
        bot.send_message(message.chat.id, f"📅 До вашего дня рождения осталось {days_left} дней. Исполнится {age} лет")

@bot.message_handler(commands=['listbirthdays'], chat_types=['group', 'supergroup'])
def list_birthdays(message):
    group_id = message.chat.id
    
    conn = sqlite3.connect('birthdays.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT username, first_name, birthday 
        FROM group_birthdays 
        WHERE group_id = ?
        ORDER BY substr(birthday, 4, 2) || substr(birthday, 1, 2)
    ''', (group_id,))
    birthdays = cursor.fetchall()
    conn.close()
    
    if not birthdays:
        bot.send_message(message.chat.id, "❌ В этой группе пока нет дней рождений")
        return
    
    text = "🎂 Дни рождения участников:\n\n"
    for username, first_name, birthday_str in birthdays:
        days_left, _ = days_until_birthday(birthday_str)
        name = f"@{username}" if username else first_name
        
        if days_left == 0:
            text += f"🎉 {name} - СЕГОДНЯ! 🎂\n"
        elif days_left == 1:
            text += f"🚀 {name} - ЗАВТРА! - {birthday_str}\n"
        elif days_left <= 7:
            text += f"⭐ {name} - через {days_left} дней - {birthday_str}\n"
        else:
            text += f"📅 {name} - {birthday_str} (через {days_left} дней)\n"
    
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['nextbirthday'], chat_types=['group', 'supergroup'])
def next_birthday(message):
    group_id = message.chat.id
    
    conn = sqlite3.connect('birthdays.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT username, first_name, birthday FROM group_birthdays WHERE group_id = ?', (group_id,))
    all_birthdays = cursor.fetchall()
    conn.close()
    
    if not all_birthdays:
        bot.send_message(message.chat.id, "❌ В этой группе пока нет дней рождений")
        return
    
    today = date.today()
    nearest = None
    min_days = 365
    
    for username, first_name, birthday_str in all_birthdays:
        days_left, _ = days_until_birthday(birthday_str)
        if days_left < min_days:
            min_days = days_left
            nearest = (username, first_name, birthday_str, days_left)
    
    if nearest:
        username, first_name, birthday_str, days_left = nearest
        name = f"@{username}" if username else first_name
        birthday_date = datetime.strptime(birthday_str, "%d.%m.%Y").date()
        age = today.year - birthday_date.year
        
        if days_left == 0:
            response = f"🎉 Ближайший день рождения СЕГОДНЯ у {name}! 🎂\nЕму(ей) исполняется {age} лет!"
        else:
            response = f"📅 Ближайший день рождения у {name} через {days_left} дней\n{birthday_str} - исполнится {age} лет"
        
        bot.send_message(message.chat.id, response)

@bot.message_handler(commands=['today'], chat_types=['group', 'supergroup'])
def today_birthdays(message):
    group_id = message.chat.id
    
    conn = sqlite3.connect('birthdays.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT username, first_name, birthday FROM group_birthdays WHERE group_id = ?', (group_id,))
    birthdays = cursor.fetchall()
    conn.close()
    
    today_celebrants = []
    for username, first_name, birthday_str in birthdays:
        days_left, _ = days_until_birthday(birthday_str)
        if days_left == 0:
            today_celebrants.append((username, first_name, birthday_str))
    
    if today_celebrants:
        text = "🎉 Сегодня празднуют День Рождения:\n\n"
        for username, first_name, birthday_str in today_celebrants:
            name = f"@{username}" if username else first_name
            birthday_date = datetime.strptime(birthday_str, "%d.%m.%Y").date()
            age = date.today().year - birthday_date.year
            text += f"🎂 {name} - {age} лет!\n"
        
        bot.send_message(message.chat.id, text)
    else:
        bot.send_message(message.chat.id, "❌ Сегодня в группе никто не празднует День Рождения")

@bot.message_handler(commands=['autoon'], chat_types=['group', 'supergroup'])
def auto_on(message):
    group_id = message.chat.id
    conn = sqlite3.connect('birthdays.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO group_settings (group_id, auto_congratulate) VALUES (?, 1)', (group_id,))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, "✅ Автоматические поздравления ВКЛЮЧЕНЫ! Бот будет поздравлять именинников в 09:00")

@bot.message_handler(commands=['autooff'], chat_types=['group', 'supergroup'])
def auto_off(message):
    group_id = message.chat.id
    conn = sqlite3.connect('birthdays.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO group_settings (group_id, auto_congratulate) VALUES (?, 0)', (group_id,))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, "❌ Автоматические поздравления ВЫКЛЮЧЕНЫ")

@bot.message_handler(commands=['reminderson'], chat_types=['group', 'supergroup'])
def reminders_on(message):
    group_id = message.chat.id
    conn = sqlite3.connect('birthdays.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO group_settings (group_id, daily_reminder) VALUES (?, 1)', (group_id,))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, "✅ Ежедневные напоминания ВКЛЮЧЕНЫ! Бот будет отправлять напоминания в 10:00")

@bot.message_handler(commands=['remindersoff'], chat_types=['group', 'supergroup'])
def reminders_off(message):
    group_id = message.chat.id
    conn = sqlite3.connect('birthdays.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO group_settings (group_id, daily_reminder) VALUES (?, 0)', (group_id,))
    conn.commit()
    conn.close()
    
    bot.send_message(message.chat.id, "❌ Ежедневные напоминания ВЫКЛЮЧЕНЫ")

if __name__ == "__main__":
    init_db()
    start_scheduler()
    print("🤖 Бот запущен с автоматическими функциями...")
    bot.polling(none_stop=True)
