import os
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command, CommandStart, Text
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from aiogram.utils.callback_data import CallbackData
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InputMediaPhoto



# Загрузка конфигурации из config.ini
import configparser
config = configparser.ConfigParser()
config.read("config.ini")

# __________________________Данные бота__________________________
token = config.get("Bot", "token")
admin_id = int(config.get("Bot", "admin_id"))
chat_link = config.get("Bot", "chat_link")

bot = Bot(token=token)
dp = Dispatcher(bot, storage=MemoryStorage())

# __________________________Вопросы__________________________
question_1 = " Первым делом раскажи откуда ты узнал о нашем проекте?"
question_2 = " Отлично, а был ли у тебя опыт в скаме? "
question_3 = " А сколько времени ты готов уделять работе в нашем проекте?"
# __________________________Отображение вопросов у админа__________________________
admin_question_1 = "откуда узнали"
admin_question_2 = "опыт"
admin_question_3 = "Сколько готов уделять времени"
# _________________________________________________________


# __________________________Действие при старте бота__________________________
async def on_startup(_):
    print("Бот успешно запущен")
# _________________________________________________________


# __________________________Действие с БД__________________________
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_file):
        self.connection = sqlite3.connect(db_file)
        self.cursor = self.connection.cursor()
        self.message_tracking = {}
        print("Ваша база данных успешно подключена")

    def add_user(self, ID, username):
        with self.connection:
            try:
                self.cursor.execute("INSERT INTO 'user' VALUES (?, ?, ?, ?, ?)", (ID, "null", "null", "null", username))
            except:
                pass

    def add_client(self, ID):
        with self.connection:
            try:
                self.cursor.execute("INSERT INTO 'client' VALUES (?)", (ID,))
            except:
                pass

    def update_user_data(self, ID, a1, a2, a3):
        with self.connection:
            self.cursor.execute("UPDATE 'user' SET answer1 = ?, answer2 = ?, answer3 = ? WHERE user_id = ?", (a1, a2, a3, ID))

    def get_user_data(self, ID):
        with self.connection:
            return self.cursor.execute("SELECT * FROM 'user' WHERE user_id = ?", (ID,)).fetchmany()[0]

    def delete_zayavka(self, ID):
        with self.connection:
            return self.cursor.execute("DELETE FROM 'user' WHERE user_id = ?", (ID,))

    def client_exists(self, ID):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM 'user' WHERE user_id = ?", (ID,)).fetchmany(1)
            if not bool(len(result)):
                return False
            else:
                return True

    def update_last_message_time(self, user_id):
        now = datetime.utcnow()
        self.message_tracking[user_id] = now

    def get_last_message_time(self, user_id):
        return self.message_tracking.get(user_id, datetime.utcnow() - timedelta(seconds=10))

    def get_message_count(self, user_id):
        return self.message_tracking.get(user_id, 0)

    def increment_message_count(self, user_id):
        current_count = self.get_message_count(user_id)
        self.message_tracking[user_id] = current_count + timedelta(seconds=1)
    
    def confirmed_user(self, user_id):
        with self.connection:
            result = self.cursor.execute("SELECT * FROM 'client' WHERE user_id = ?", (user_id,)).fetchmany(1)
            if not bool(len(result)):
                return False
            else:
                return True
# ________________________________________________________

# __________________________Кнопки__________________________
cb = CallbackData("fabnum", "action")

main_menu = InlineKeyboardMarkup(row_width=1)
main_menu.add(InlineKeyboardButton(text='🔰 Принять правила 🔰', callback_data=cb.new(action='start_answer')))

send_menu = InlineKeyboardMarkup(row_width=2)
send_menu.add(InlineKeyboardButton(text="Отправить заявку", callback_data=cb.new(action="send")),
              InlineKeyboardButton(text="Заполнить заново", callback_data=cb.new(action='application')))


def admin_menu(ID):
    menu = InlineKeyboardMarkup(row_width=2)
    menu.add(InlineKeyboardButton(text="Принять", callback_data=f"#y{str(ID)}"),
             InlineKeyboardButton(text="Отклонить", callback_data=f'#n{str(ID)}'))
    return menu

# _________________________________________________________
class SetLink(StatesGroup):
    waiting_for_link = State()

@dp.message_handler(Command("set_link"), user_id=admin_id)
async def set_link_command(message: types.Message):
    await bot.send_message(message.chat.id, "Отправьте мне новую ссылку для замены!")
    await SetLink.waiting_for_link.set()

@dp.message_handler(state=SetLink.waiting_for_link, user_id=admin_id)
async def set_link(message: types.Message, state: FSMContext, user_id: int):  # Добавьте аннотацию типа и передайте user_id из аргументов
    new_link = message.text
    global chat_link
    chat_link = new_link
    await bot.send_message(message.chat.id, "Ваша ссылка успешно заменена!")
    await state.finish()

# __________________________Подключаем БД__________________________
db = Database("data.db")
# _________________________________________________________


class get_answer(StatesGroup):
    answer1 = State()
    answer2 = State()
    answer3 = State()


# ____________________________________________________
# @dp.message_handlers(commands=["start"])
async def command_start(message: types.Message):  
    if message.from_user.username is not None:
        if db.confirmed_user(message.from_user.id):
            await bot.send_message(message.from_user.id, "Вы уже приняты ❗️")
        else:
            if db.client_exists(message.from_user.id):
                await bot.send_message(message.from_user.id, "Вы уже подавали заявку ❗️")
            else:
                # Путь к изображению
                image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image", "start.png")
                
                # Отправляем фото вместе с текстовым сообщением
                await bot.send_photo(
                    message.from_user.id,
                    InputFile(image_path),
                    caption=(
                        "👋 Привет, перед началом работы заполни небольшую анкету и ознакомься с правилами проекта:\n\n"
                        "🔸 правило бла бла\n"
                        "🔸 правило бла бла\n"
                        "🔸 правило бла бла\n"
                        "🔸 правило бла бла\n"
                        "🔸 правило бла бла\n"
                        "🔸 правило бла бла\n"
                        "🔸 правило бла бла\n"
                        "🔸 правило бла бла\n\n"
                        "⚡️ Если ты согласен с правилами проекта нажми на кнопку ниже"
                        "нажми на кнопку ниже"
                    ),
                    parse_mode=types.ParseMode.MARKDOWN,
                    reply_markup=main_menu
                )
    else:
        await bot.send_message(message.from_user.id, "У вас не установлен <b>username</b>(имя пользователя)\n\nУстановите его и напишите /start", parse_mode=types.ParseMode.HTML)
                

# @dp.callback_query_handlers(cb.filter(action=["send", "application"]), state="*")
async def send_state(call: types.CallbackQuery, callback_data: dict, state: FSMContext):
    action = callback_data["action"]
    current_state = await state.get_state()
    if current_state is None:
        return
    if action == "send":
        await bot.send_message(admin_id, f"Поступила новая заявка от @{str(db.get_user_data(call.from_user.id)[4])}\n"
                                         f"{admin_question_1}: <b>{str(db.get_user_data(call.from_user.id)[1])}</b>\n"
                                         f"{admin_question_2}: <b>{str(db.get_user_data(call.from_user.id)[2])}</b>\n"
                                         f"{admin_question_3}: <b>{str(db.get_user_data(call.from_user.id)[3])}</b>", parse_mode=types.ParseMode.HTML, reply_markup=admin_menu(call.from_user.id))
        await bot.edit_message_text(chat_id=call.from_user.id, message_id=call.message.message_id, text="""Отлично, твоя заявка отправлена на проверку ❗️ """)

        await state.finish()
    if action == "application":
        db.delete_zayavka(call.from_user.id)
        await state.finish()
        await command_start(call)
    await call.answer()


# @dp.callback_query_handler(text_contains="#")
async def access(call: types.CallbackQuery):
    temp = [call.data[1:2], call.data[2:]]
    username = f"@{str(db.get_user_data(temp[1])[4])}"  # Получаем имя пользователя

    if temp[0] == "y":
        db.add_client(temp[1])
        db.delete_zayavka(temp[1])
        await bot.edit_message_text(chat_id=admin_id, message_id=call.message.message_id, text="Вы приняли заявку ❗️ ")

        # Создаем объект InputFile для изображения
        image_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image", "confirm.png")
        image = InputFile(image_path)

        # Отправляем изображение вместе с текстом
        await bot.send_photo(
            temp[1],
            image,
            caption=(
                f'💠 Твоя заявка была одобрена, {username}, добро пожаловать в наш проект! 💠\n'
                '\n'
                f'🔆 Ссылка для вступления в чат: {chat_link}\n'
                '\n'
                '❗ <b>ВСЯ ИНФОРМАЦИЯ НАХОДИТСЯ В ЗАКРЕПЕ ❗</b>'
            ),
            parse_mode=types.ParseMode.HTML
        )
    elif temp[0] == "n":
        await bot.edit_message_text(chat_id=admin_id, message_id=call.message.message_id, text="Вы отклонили заявку ❗️")
        await bot.send_message(temp[1], f'Извините, {username}, вы нам не подходите ⚠️ ')

    await call.answer()

# @dp.callback_query_handlers(cb.filter(action=["start_answer"]))
async def start_state(call: types.CallbackQuery, callback_data: dict):  # Первый вопрос
    action = callback_data["action"]
    if action == "start_answer":
        db.add_user(call.from_user.id, call.from_user.username)
        await bot.send_message(call.from_user.id, f"Ответьте на несколько вопросов:\n1) <b>{question_1}</b>", parse_mode=types.ParseMode.HTML)
        await get_answer.answer1.set()


# @dp.message_handlers(state=get_answer.answer1)
async def answer1(message: types.Message, state: FSMContext):  # Второй вопрос
    async with state.proxy() as data:
        data["answer1"] = message.text
    await bot.send_message(message.from_user.id, f'2) <b>{question_2}</b>', parse_mode=types.ParseMode.HTML)
    await get_answer.next()


# @dp.message_handlers(state=get_answer.answer2)
async def answer2(message: types.Message, state: FSMContext):  # Третий вопрос
    async with state.proxy() as data:
        data["answer2"] = message.text
    await bot.send_message(message.from_user.id, f'3) <b>{question_3}</b>', parse_mode=types.ParseMode.HTML)
    await get_answer.next()


# @dp.message_handlers(state=get_answer.answer3)
async def answer3(message: types.Message, state: FSMContext):  # Отображение ответов на вопросы
    async with state.proxy() as data:
        data["answer3"] = message.text
    await bot.send_message(message.from_user.id, f'Ответы на наши вопросы:\n\n'
                                                 f'1) <b>{data["answer1"]}</b>\n'
                                                 f'2) <b>{data["answer2"]}</b>\n'
                                                 f'3) <b>{data["answer3"]}</b>', parse_mode=types.ParseMode.HTML, reply_markup=send_menu)
    db.update_user_data(message.from_user.id, data["answer1"], data["answer2"], data["answer3"])
# _________________________________________________________


# кнопка "Очистить БД" для администратора:
@dp.message_handler(state="*", commands=["clear_db"], user_id=admin_id)
async def cmd_clear_db(message: types.Message, state: FSMContext):
    db.connection.execute("DELETE FROM 'user'")
    db.connection.execute("DELETE FROM 'client'")
    db.connection.commit()
    await bot.send_message(message.chat.id, "База данных успешно очищена.")
# __________________________Обработка всех событий__________________________


def register_handlers_client(dp: Dispatcher):
    dp.register_message_handler(command_start, commands=["start"])
    dp.register_callback_query_handler(send_state, cb.filter(action=["send", "application"]), state="*")
    dp.register_callback_query_handler(access, text_contains="#")
    dp.register_callback_query_handler(start_state, cb.filter(action=["start_answer"]))
    dp.register_message_handler(answer1, state=get_answer.answer1)
    dp.register_message_handler(answer2, state=get_answer.answer2)
    dp.register_message_handler(answer3, state=get_answer.answer3)


# _________________________________________________________

register_handlers_client(dp)  # Запуск обработки событий

if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup)
