import telebot
import json
import os
from datetime import datetime
from telebot import types

# Загрузка конфигурации

TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)
USERS_FILE = "users.json"

# Файлы для скачивания
FILES = {
    1: "file1.zip",
    2: "file2.zip",
    3: "file3.zip"
}

# Загрузка и сохранение пользователей
def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2, ensure_ascii=False)
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2, ensure_ascii=False)
        return {}

def save_users():
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)

users = load_users()

# Добавляем админа, если его нет
admin_id_str = str(ADMIN_ID)
if admin_id_str not in users:
    users[admin_id_str] = {
        "username": "admin",
        "access_level": 3,
        "registered": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    save_users()

def get_access_level(user_id):
    user_id = str(user_id)
    if user_id == admin_id_str:
        return 3
    return users.get(user_id, {}).get("access_level", 0)

def get_keyboard(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    level = get_access_level(user_id)
    if str(user_id) == admin_id_str:
        markup.add("📋 Список пользователей", "👤 Личный кабинет")
    if level >= 1:
        markup.add("📥 Скачать 1")
    if level >= 2:
        markup.add("📥 Скачать 2")
    if level >= 3:
        markup.add("📥 Скачать 3")
    markup.add("👤 Личный кабинет")
    return markup

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = str(message.from_user.id)
    if user_id in users:
        bot.send_message(user_id, f"👋 Добро пожаловать, {users[user_id]['username']}!", reply_markup=get_keyboard(user_id))
    else:
        msg = bot.send_message(user_id, "👋 Привет! Введите юзернейм (мин. 3 символа):")
        bot.register_next_step_handler(msg, register_user)

def register_user(message):
    user_id = str(message.from_user.id)
    username = message.text.strip()

    if len(username) < 3:
        msg = bot.send_message(user_id, "❗ Минимум 3 символа. Попробуйте снова:")
        bot.register_next_step_handler(msg, register_user)
        return

    if any(u["username"].lower() == username.lower() for u in users.values()):
        msg = bot.send_message(user_id, "⚠ Такой юзернейм уже существует. Введите другой:")
        bot.register_next_step_handler(msg, register_user)
        return

    users[user_id] = {
        "username": username,
        "access_level": 0,
        "registered": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    save_users()
    bot.send_message(user_id, f"✅ Регистрация завершена, <b>{username}</b>. Ожидайте доступа от администратора.", parse_mode="HTML", reply_markup=get_keyboard(user_id))

@bot.message_handler(commands=['profile'])
@bot.message_handler(func=lambda m: m.text == "👤 Личный кабинет")
def show_profile(message):
    user_id = str(message.from_user.id)
    if user_id in users:
        user = users[user_id]
        level = get_access_level(user_id)
        text = (
            f"👤 <b>Профиль</b>\n"
            f"🔸 Юзернейм: <b>{user['username']}</b>\n"
            f"🆔 ID: <code>{user_id}</code>\n"
            f"📅 Регистрация: {user['registered']}\n"
            f"🔐 Уровень доступа: <b>{level}</b>"
        )
    else:
        text = "⚠ Вы не зарегистрированы. Напишите /start"
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(commands=['allow'])
def allow_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        _, uid, level = message.text.strip().split()
        level = int(level)
        if uid in users:
            users[uid]["access_level"] = level
            save_users()
            bot.send_message(message.chat.id, f"✅ Доступ {level} выдан: {users[uid]['username']} ({uid})")
        else:
            bot.send_message(message.chat.id, "❗ Пользователь не найден.")
    except:
        bot.send_message(message.chat.id, "❗ Используйте: /allow <user_id> <level>")

@bot.message_handler(commands=['deny'])
def deny_user(message):
    if message.from_user.id != ADMIN_ID:
        return
    try:
        _, uid = message.text.strip().split()
        if uid in users:
            users[uid]["access_level"] = 0
            save_users()
            bot.send_message(message.chat.id, f"🚫 Доступ отключён для: {users[uid]['username']} ({uid})")
        else:
            bot.send_message(message.chat.id, "❗ Пользователь не найден.")
    except:
        bot.send_message(message.chat.id, "❗ Используйте: /deny <user_id>")

@bot.message_handler(func=lambda m: m.text == "📋 Список пользователей")
def list_users(message):
    if str(message.from_user.id) != str(ADMIN_ID):
        return
    if not users:
        bot.send_message(message.chat.id, "❗ Нет пользователей.")
        return
    text = "📑 <b>Список пользователей:</b>\n"
    for uid, data in users.items():
        level = data.get("access_level", 0)
        text += f"{uid} — {data['username']} — Уровень: {level} — {data['registered']}\n"
    bot.send_message(message.chat.id, text, parse_mode="HTML")

@bot.message_handler(func=lambda m: m.text.startswith("📥 Скачать"))
def send_file(message):
    user_id = str(message.from_user.id)
    level = get_access_level(user_id)
    text = message.text.strip()

    if "1" in text and level >= 1:
        path = FILES[1]
    elif "2" in text and level >= 2:
        path = FILES[2]
    elif "3" in text and level >= 3:
        path = FILES[3]
    else:
        bot.send_message(message.chat.id, "⛔️ У вас нет доступа к этому файлу.")
        return

    if os.path.exists(path):
        with open(path, "rb") as f:
            bot.send_document(message.chat.id, f)
    else:
        bot.send_message(message.chat.id, f"❌ Файл {path} не найден.")

print("✅ Бот запущен.")
bot.polling(none_stop=True)
