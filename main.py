import telebot
from telebot import types
import database_manager
import os
from dotenv import load_dotenv
from data_messages import messages
from bot_logic import profile_editing
import sqlite3


load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
bot = telebot.TeleBot(API_TOKEN)

if API_TOKEN is None:
    print("Ошибка: Токен API не найден.")
else:
    print("Токен API успешно загружен")


USER_DATA = {}  # Словарь для хранения данных пользователей

# Состояния
STATE_ASK_AGE = 1
STATE_ASK_CONSENT = 2
STATE_ENTER_NAME = 3
STATE_ENTER_GENDER = 4
STATE_ENTER_CITY = 5
STATE_DESCRIPTIONS = 6
STATE_CHOOSE_STATUS = 7
STATE_UPLOAD_PHOTO = 8
STATE_MAIN_SCREEN = 9
STATE_ABOUT_PROJECT = 10
STATE_CREATE_PROFILE = 11
STATE_PROFILE = 12
STATE_EDIT_PROFILE = 13
STATE_DELETE_PROFILE = 14
STATE_DELETE_PROFILE_CONFIRM = 15
STATE_WAITING_FOR_PROFILE_UPDATE = 16
STATUS_PROFILE_UPDATE_COMPLETE = 17
STATE_WAITING_FOR_DESCRIPTIONS_UPDATE = 18
STATUS_DESCRIPTIONS_UPDATE_COMPLETE = 19
STATE_WAITING_FOR_STATUS_UPDATE = 20
STATUS_UPDATE_COMPLETE = 21
STATE_WAITING_FOR_CITY_UPDATE = 22
STATE_CITY_UPDATE_COMPLETE = 23
STATE_WAITING_FOR_PHOTO_UPDATE = 24
STATE_PHOTO_UPDATE_COMPLETE = 25
STATE_WAITING_FOR_PHOTO = 26
STATE_SEARCHING = 27



# Функция для обновления состояния пользователя
def set_state(user_id, state):
    print(f"Setting state for user {user_id} to {state}")
    try:
        database_manager.update_user(user_id, state=state)
    except Exception as e:
        print(f"Error updating state: {e}")


# Функция для получения состояния пользователя
def get_state(user_id):
    state = database_manager.get_user_state(user_id)
    print(f"State for user {user_id} is {state}")
    return state


# Старт регистрации
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    user_data = database_manager.get_user(user_id)

    if user_data:
        set_state(user_id, STATE_MAIN_SCREEN)
        main_screen_data = messages["main_screen_message"]
        img_url = main_screen_data["image_url"]
        message_text = main_screen_data["text"]
        button_text_start_searching = main_screen_data["button_text_start_searching"]
        button_text_profile = main_screen_data["button_text_profile"]
        button_text_about = main_screen_data["button_text_about"]

        markup_main_buttons = types.InlineKeyboardMarkup()
        markup_main_buttons.row(
            types.InlineKeyboardButton(button_text_start_searching, callback_data="start_searching"))
        markup_main_buttons.add(types.InlineKeyboardButton(button_text_profile, callback_data='show_profile'),
                                types.InlineKeyboardButton(button_text_about, callback_data='about_project'))

        bot.send_photo(message.chat.id, img_url, caption=message_text, reply_markup=markup_main_buttons,
                       parse_mode="HTML")

    else:
        welcome_data = messages["welcome_message"]
        img_url = welcome_data["image_url"]
        message_text = welcome_data["text"]
        button_text = welcome_data["button_text"]

        markup = types.InlineKeyboardMarkup()
        reg_button = types.InlineKeyboardButton(button_text, callback_data='register')
        markup.add(reg_button)
        bot.send_photo(message.chat.id, img_url, caption=message_text, reply_markup=markup, parse_mode="HTML")


# Обработчик для кнопки регистрации
@bot.callback_query_handler(func=lambda call: call.data == 'register')
def age_request(call):
    user_id = call.from_user.id

    # Создаем пользователя с начальным состоянием в БД
    database_manager.add_user(user_id=user_id, state=STATE_ASK_AGE)
    set_state(user_id, STATE_ASK_AGE)

    age_request_text = messages["age_request_message"]["text"]
    bot.send_message(call.message.chat.id, age_request_text, parse_mode="HTML")


@bot.message_handler(func=lambda message: get_state(message.from_user.id) == STATE_ASK_AGE)
def age_input(message):
    user_id = message.from_user.id
    try:
        age = int(message.text)
        if age < 16:
            error_text = messages["age_input_message"]["error_text_age_under_16"]
            bot.send_message(message.chat.id, error_text)
            database_manager.delete_user(user_id)  # Удаление пользователя из БД
            set_state(user_id, None)
        else:
            # Добавляем возраст пользователя в БД
            database_manager.update_user(user_id, age=age)
            set_state(user_id, STATE_ASK_CONSENT)
            consent_text = messages["age_input_message"]["text_consent_messages"]
            button_yes = messages["age_input_message"]["button_text_yes"]
            button_no = messages["age_input_message"]["button_text_no"]

            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(button_yes,
                                                  callback_data="consent_yes"),
                       types.InlineKeyboardButton(button_no,
                                                  callback_data="consent_no"))
            bot.send_message(message.chat.id, consent_text, reply_markup=markup, parse_mode="HTML")
    except ValueError:
        error_text = messages["age_input_message"]["error_text_invalid_data_type"]
        bot.send_message(message.chat.id, error_text, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data == "consent_yes")
def consent_yes(call):
    user_id = call.from_user.id
    telegram_username = call.from_user.username
    database_manager.update_user(user_id, telegram_username=telegram_username)

    set_state(user_id, STATE_ENTER_NAME)
    text_yes = messages["consent_yes_message"]["text"]
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=text_yes, reply_markup=None)  # Удаляем клавиатуру


@bot.callback_query_handler(func=lambda call: call.data == "consent_no")
def consent_no(call):
    user_id = call.from_user.id
    database_manager.delete_user(user_id)  # Удаляем пользователя из БД
    set_state(user_id, None)

    text_no = messages["consent_no_message"]["text"]
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=text_no, reply_markup=None)


# Обработчик текстовых сообщений для регистрации
@bot.message_handler(func=lambda message: get_state(message.from_user.id) == STATE_ENTER_NAME)
def ask_gender(message):
    user_id = message.from_user.id
    name = message.text
    database_manager.update_user(user_id, name=name)
    set_state(user_id, STATE_ENTER_GENDER)

    text_message = messages["ask_gender_message"]["text"]
    button_male = messages["ask_gender_message"]["button_text_male"]
    button_female = messages["ask_gender_message"]["button_text_female"]

    markup_gender = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton(button_male, callback_data="gender_male"),
        types.InlineKeyboardButton(button_female, callback_data='gender_female'),
    ]
    for button in buttons:
        markup_gender.add(button)
    bot.send_message(message.chat.id, text_message, reply_markup=markup_gender, parse_mode="HTML")


def get_gender_text(callback_data):
    statuses = {
        "gender_male": "Мужчина",
        "gender_female": "Женщина",
    }
    return statuses.get(callback_data, "Неизвестный пол")


@bot.callback_query_handler(func=lambda call: call.data in ["gender_male", "gender_female"])
def ask_city(call):
    user_id = call.from_user.id
    gender_text = get_gender_text(call.data)
    database_manager.update_user(user_id, gender=gender_text)
    set_state(user_id, STATE_ENTER_CITY)

    message_text = messages["ask_city_message"]["text"]
    bot.answer_callback_query(call.id)  # подтверждение получения callback
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=message_text, reply_markup=None)


@bot.message_handler(func=lambda message: get_state(message.from_user.id) == STATE_ENTER_CITY)
def ask_descriptions(message):
    user_id = message.from_user.id
    city = message.text
    database_manager.update_user(user_id, city=city)
    set_state(message.from_user.id, STATE_DESCRIPTIONS)

    message_text = messages["ask_descriptions_message"]["text"]
    bot.send_message(message.chat.id, message_text, parse_mode="HTML")


@bot.message_handler(func=lambda message: get_state(message.from_user.id) == STATE_DESCRIPTIONS)
def ask_status(message):
    user_id = message.from_user.id
    descriptions = message.text
    database_manager.update_user(user_id, descriptions=descriptions)
    set_state(message.from_user.id, STATE_CHOOSE_STATUS)

    ask_status_data = messages["ask_status_message"]
    message_text = ask_status_data["text"]
    button_status_1 = ask_status_data["button_text_status_1"]
    button_status_2 = ask_status_data["button_text_status_2"]
    button_status_3 = ask_status_data["button_text_status_3"]

    markup_status = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton(button_status_1, callback_data="status_find_friends"),
        types.InlineKeyboardButton(button_status_2, callback_data='status_find_love'),
        types.InlineKeyboardButton(button_status_3, callback_data='status_just_chat')
    ]
    for button in buttons:
        markup_status.add(button)
    bot.send_message(message.chat.id, message_text, reply_markup=markup_status, parse_mode="HTML")


def get_status_text(callback_data):
    statuses = {
        "status_find_friends": "Найти друзей",
        "status_find_love": "Найти вторую половинку",
        "status_just_chat": "Просто пообщаться",
    }
    # Получаем ключ статуса (например, 'find_friends') и возвращаем соответствующий текст
    return statuses.get(callback_data, "Неизвестный статус")


@bot.callback_query_handler(
    func=lambda call: call.data in ["status_find_friends", "status_find_love", "status_just_chat"])
def ask_photo(call):
    user_id = call.from_user.id
    status_text = get_status_text(call.data)
    database_manager.update_user(user_id, status=status_text)
    set_state(user_id, STATE_UPLOAD_PHOTO)

    message_text = messages["ask_photo_message"]["text"]
    bot.answer_callback_query(call.id)  # подтверждение получения callback
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text=message_text, reply_markup=None)


@bot.message_handler(content_types=['photo'],
                     func=lambda message: get_state(message.from_user.id) == STATE_UPLOAD_PHOTO)
def photo_and_final_register(message):
    user_id = message.from_user.id
    photo_id = message.photo[-1].file_id  # Получаем file_id самой большой версии фото
    database_manager.update_user(user_id, photo=photo_id)  # Обновляем профиль пользователя в базе данных с новым фото
    set_state(user_id, STATE_CREATE_PROFILE)

    photo_and_final_register_data = messages["photo_and_final_register_message"]
    img_url = photo_and_final_register_data["image_url"]
    message_text = photo_and_final_register_data["text"]
    button = photo_and_final_register_data["button_text"]
    markup = types.InlineKeyboardMarkup()
    reg_button = types.InlineKeyboardButton(button, callback_data='show_profile')
    markup.add(reg_button)
    bot.send_photo(message.chat.id, img_url, caption=message_text, reply_markup=markup, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data == "show_profile")
def show_profile(call):
    user_id = call.from_user.id
    user_data = database_manager.get_user(user_id)  # Получаем данные пользователя из базы данных
    set_state(user_id, STATE_PROFILE)

    if user_data:
        reply_markup = types.InlineKeyboardMarkup()
        reply_markup.row(types.InlineKeyboardButton("Ок, перейти в главное меню", callback_data="go_to_main_menu"))
        reply_markup.add(
            types.InlineKeyboardButton("Редактировать профиль", callback_data="edit_profile"),
            types.InlineKeyboardButton("Удалить профиль", callback_data="delete_profile")
        )

        bot.edit_message_media(
            media=types.InputMediaPhoto(
                user_data[6],
                caption=f"Ваша анкета:\nИмя: {user_data[1]}\nПол: {user_data[7]}\nГород: {user_data[2]}"
                        f"\nОписание: {user_data[4]}\nЦель общения: {user_data[5]}\nВозраст: {user_data[3]}"
            ),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=reply_markup

        )
    else:
        bot.send_message(call.message.chat.id, "Ошибка при получении данных профиля.")


@bot.callback_query_handler(func=lambda call: call.data == "edit_profile")
def edit_profile(call):
    set_state(call.from_user.id, STATE_EDIT_PROFILE)

    edit_profile_data = messages["profile_edit_message"]
    image_url = edit_profile_data["image_url"]
    message_text = edit_profile_data["text"]
    button_text_back = edit_profile_data["button_text_back"]
    button_text_edit_name = edit_profile_data["button_text_edit_name"]
    button_des = "Описание"
    button_status = "Статус"
    button_city = "Город"
    button_photo = "Фото"

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(button_text_edit_name, callback_data='edit_name'),
               types.InlineKeyboardButton(button_des, callback_data='edit_descriptions'),
               types.InlineKeyboardButton(button_status, callback_data='edit_status'),
               types.InlineKeyboardButton(button_city, callback_data='edit_city'),
               types.InlineKeyboardButton(button_photo, callback_data='edit_photo')
               )
    markup.row(types.InlineKeyboardButton(button_text_back, callback_data='show_profile'))

    bot.edit_message_media(
        media=types.InputMediaPhoto(image_url, caption=message_text, parse_mode="HTML"),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup

    )


@bot.callback_query_handler(func=lambda call: call.data == "edit_name")
def edit_name_callback(call):
    profile_editing.edit_name(call, bot, set_state, STATE_WAITING_FOR_PROFILE_UPDATE)


@bot.message_handler(func=lambda message: get_state(message.from_user.id) == STATE_WAITING_FOR_PROFILE_UPDATE)
def update_name_callback(message):
    profile_editing.update_name(message)
    profile_editing.send_profile_edit_message(message, bot, message.chat.id, set_state, STATE_EDIT_PROFILE)


@bot.callback_query_handler(func=lambda call: call.data == "edit_descriptions")
def edit_descriptions_callback(call):
    profile_editing.edit_descriptions(call, bot, set_state, STATE_WAITING_FOR_DESCRIPTIONS_UPDATE)


@bot.message_handler(func=lambda message: get_state(message.from_user.id) == STATE_WAITING_FOR_DESCRIPTIONS_UPDATE)
def update_descriptions_callback(message):
    profile_editing.update_descriptions(message)
    profile_editing.send_profile_edit_message(message, bot, message.chat.id, set_state, STATE_EDIT_PROFILE)


@bot.callback_query_handler(func=lambda call: call.data == "edit_status")
def edit_status_callback(call):
    profile_editing.edit_status(call, bot, set_state, STATE_WAITING_FOR_STATUS_UPDATE)


@bot.callback_query_handler(func=lambda call: call.data in ["status_find_friends_1", "status_find_love_2", "status_just_chat_3"])
def update_status_callback(call):
    bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)
    profile_editing.update_status_complete(call, bot, set_state, STATE_EDIT_PROFILE)


@bot.callback_query_handler(func=lambda call: call.data == "edit_city")
def edit_city_callback(call):
    profile_editing.edit_city(call, bot, set_state, STATE_WAITING_FOR_CITY_UPDATE)


@bot.message_handler(func=lambda message: get_state(message.from_user.id) == STATE_WAITING_FOR_CITY_UPDATE)
def update_city_callback(message):
    profile_editing.update_city(message)
    profile_editing.send_profile_edit_message(message, bot, message.chat.id, set_state, STATE_EDIT_PROFILE)


@bot.callback_query_handler(func=lambda call: call.data == "edit_photo")
def edit_photo_callback(call):
    profile_editing.edit_photo(call, bot, set_state, STATE_WAITING_FOR_PHOTO_UPDATE)


@bot.message_handler(content_types=['photo'],
                     func=lambda message: get_state(message.from_user.id) == STATE_WAITING_FOR_PHOTO_UPDATE)
def update_photo_callback(message):
    profile_editing.update_photo(message)
    profile_editing.send_profile_edit_message(message, bot, message.chat.id, set_state, STATE_EDIT_PROFILE)


@bot.callback_query_handler(func=lambda call: call.data == "delete_profile")
def confirm_delete_profile(call):
    set_state(call.from_user.id, STATE_DELETE_PROFILE)

    confirm_delete_profile_data = messages["profile_delete_confirm_message"]
    image_url = confirm_delete_profile_data["image_url"]
    message_text = confirm_delete_profile_data["text"]
    button_text_confirm = confirm_delete_profile_data["button_text_confirm_delete"]
    button_text_cancel = confirm_delete_profile_data["button_text_cancel"]

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(button_text_confirm, callback_data="confirm_delete_profile"),
               types.InlineKeyboardButton(button_text_cancel, callback_data="show_profile"))

    bot.edit_message_media(
        media=types.InputMediaPhoto(image_url, caption=message_text, parse_mode="HTML"),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "confirm_delete_profile")
def delete_profile(call):
    database_manager.delete_user(call.from_user.id)
    set_state(call.from_user.id, STATE_DELETE_PROFILE_CONFIRM)

    delete_profile_data = messages["profile_deleted_message"]
    img_url = delete_profile_data["image_url"]
    message_text = delete_profile_data["text"]

    bot.edit_message_media(
        media=types.InputMediaPhoto(img_url, caption=message_text, parse_mode="HTML"),
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
    )

    set_state(call.from_user.id, None)


@bot.callback_query_handler(func=lambda call: call.data == 'go_to_main_menu')
def main_screen(call):
    print("1111")
    user_id = call.from_user.id
    notify_likes(user_id)
    set_state(call.from_user.id, STATE_MAIN_SCREEN)

    main_screen_data = messages["main_screen_message"]
    img_url = main_screen_data["image_url"]
    message_text = main_screen_data["text"]
    button_text_start_searching = main_screen_data["button_text_start_searching"]
    button_text_profile = main_screen_data["button_text_profile"]
    button_text_about = main_screen_data["button_text_about"]

    markup_main_buttons = types.InlineKeyboardMarkup()
    markup_main_buttons.row(types.InlineKeyboardButton(button_text_start_searching, callback_data="start_searching"))
    # С помощью метода .row() можно сделать одну большую кнопку

    markup_main_buttons.add(types.InlineKeyboardButton(button_text_profile, callback_data='show_profile'),
                            types.InlineKeyboardButton(button_text_about, callback_data='about_project'))
    # Метод .add() добавляет каждую кнопку в новый ряд, что позволяет сделать в одном ряду две маленькие кнопки

    bot.edit_message_media(media=types.InputMediaPhoto(img_url, caption=message_text, parse_mode="HTML"),
                           chat_id=call.message.chat.id,
                           message_id=call.message.message_id,
                           reply_markup=markup_main_buttons)


@bot.callback_query_handler(func=lambda call: call.data == 'about_project')
def about_project(call):
    print("Handling about_project callback...")
    set_state(call.from_user.id, STATE_ABOUT_PROJECT)

    about_project_data = messages["about_project_message"]
    img_url = about_project_data["image_url"]
    message_text = about_project_data["text"]
    button_text = about_project_data["button_text_back"]

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(button_text, callback_data='go_to_main_menu'))
    bot.edit_message_media(media=types.InputMediaPhoto(img_url, caption=message_text, parse_mode="HTML"),
                           chat_id=call.message.chat.id,
                           message_id=call.message.message_id,
                           reply_markup=markup)


# Обработчик для кнопки "Начать поиск"
@bot.callback_query_handler(func=lambda call: call.data == 'start_searching')
def start_searching(call):
    user_id = call.from_user.id
    user_data = database_manager.get_next_profile(user_id)  # Получаем следующего пользователя из базы данных
    main_screen_data = messages["main_screen_message"]
    img_url = main_screen_data["image_url"]
    set_state(user_id, STATE_SEARCHING)

    if user_data:
        print(f"User data: {user_data[1]}")

        database_manager.mark_profile_as_viewed(user_id, user_data[0])

        reply_markup = types.InlineKeyboardMarkup()
        reply_markup.add(
            types.InlineKeyboardButton("Да", callback_data=f"like_{user_data[0]}"),
            types.InlineKeyboardButton("Нет", callback_data="next_profile")
        )
        reply_markup.row(types.InlineKeyboardButton("Все, хватит", callback_data="go_to_main_menu")
                         )

        bot.edit_message_media(
            media=types.InputMediaPhoto(user_data[6],
                                        caption=f"Хотите познакомится?\nИмя: {user_data[1]}\nПол: {user_data[7]}\nГород: {user_data[2]}"
                                                f"\nОписание: {user_data[4]}\nЦель общения: {user_data[5]}\nВозраст: {user_data[3]}"),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=reply_markup
        )
    else:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("Вернуться в главное меню", callback_data="go_to_main_menu"),
            types.InlineKeyboardButton("Просмотреть анкеты заново", callback_data="restart_searching")
        )
        bot.edit_message_media(media=types.InputMediaPhoto(img_url, caption="Нет доступных анкет"),
                               chat_id=call.message.chat.id,
                                message_id=call.message.message_id,
                                reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == 'next_profile')
def no_search_profile(call):
    start_searching(call)


# Обработчик для кнопки "Да"
@bot.callback_query_handler(func=lambda call: call.data.startswith('like_'))
def handle_like(call):
    user_id = call.from_user.id
    liked_user_id = int(call.data.split('_')[1])
    main_screen_data = messages["main_screen_message"]
    img_url = main_screen_data["image_url"]

    database_manager.add_like(user_id, liked_user_id)
    send_temporary_confirmation(user_id, "Ваш лайк успешно отправлен!")

    if check_mutual_like(user_id, liked_user_id):
        user_data = database_manager.get_user(user_id)
        liked_user_data = database_manager.get_user(liked_user_id)
        if user_data and liked_user_data:
            send_temporary_confirmation(user_id,
                                        f"Вы понравились друг другу! {liked_user_data[1]} лайкнул вас в ответ. "
                                        f"Начните общение: @{liked_user_data[9]}")
            send_temporary_confirmation(liked_user_id,
                                        f"Вы понравились друг другу! Вы лайкнули {user_data[1]} Начните общение: @{user_data[9]}")
            database_manager.remove_mutual_likes(user_id, liked_user_id)

    elif database_manager.get_user_state(liked_user_id) == STATE_MAIN_SCREEN:
        user_data = database_manager.get_user(user_id)
        if user_data:
            reply_markup = types.InlineKeyboardMarkup()
            reply_markup.add(
                types.InlineKeyboardButton("Лайкнуть в ответ", callback_data=f"accept_{user_id}_{liked_user_id}"))
            reply_markup.add(types.InlineKeyboardButton("Неинтересно", callback_data="decline_"))
            bot.send_photo(
                chat_id=liked_user_id,
                photo=user_data[6],
                caption=f"Вами заинтересовались!\nИмя: {user_data[1]}\nПол: {user_data[7]}\nГород: {user_data[2]}"
                        f"\nОписание: {user_data[4]}\nЦель общения: {user_data[5]}\nВозраст: {user_data[3]}",
                reply_markup=reply_markup
            )

    try:
        next_user_data = database_manager.get_next_profile(user_id)

        if next_user_data:
            reply_markup = types.InlineKeyboardMarkup()
            reply_markup.add(
                types.InlineKeyboardButton("Да", callback_data=f"like_{next_user_data[0]}"),
                types.InlineKeyboardButton("Нет", callback_data="next_profile")
            )
            reply_markup.row(types.InlineKeyboardButton("Все, хватит", callback_data="go_to_main_menu"))

            bot.edit_message_media(
                media=types.InputMediaPhoto(next_user_data[6],
                                            caption=f"Хотите познакомится?\nИмя: {next_user_data[1]}\nПол: {next_user_data[7]}\nГород: {next_user_data[2]}"
                                                    f"\nОписание: {next_user_data[4]}\nЦель общения: {next_user_data[5]}\nВозраст: {next_user_data[3]}"),
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                reply_markup=reply_markup
            )
        else:
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("Вернуться в главное меню", callback_data="go_to_main_menu"),
                types.InlineKeyboardButton("Просмотреть анкеты заново", callback_data="restart_searching")
            )
            bot.edit_message_media(media=types.InputMediaPhoto(img_url, caption="Нет доступных анкет"),
                                   chat_id=call.message.chat.id,
                                   message_id=call.message.message_id,
                                   reply_markup=markup)
    except Exception as e:
        print(f"Error: {e}")
        bot.send_message(user_id, "Произошла ошибка при поиске следующего профиля.")


def check_mutual_like(user_id, liked_user_id):
    return database_manager.has_like(user_id, liked_user_id) and database_manager.has_like(liked_user_id, user_id)


def notify_likes(user_id):
    likers = database_manager.get_likers(user_id)
    for liker_id in likers:
        liker_data = database_manager.get_user(liker_id)

        reply_markup = types.InlineKeyboardMarkup()
        reply_markup.add(types.InlineKeyboardButton("Лайкнуть в ответ", callback_data=f"accept_{user_id}_{liker_id}"))
        reply_markup.add(types.InlineKeyboardButton("Неинтересно", callback_data="decline_"))

        bot.send_photo(
            chat_id=user_id,
            photo=liker_data[6],
            caption=f"Вами заинтересовались!\nИмя: {liker_data[1]}\nПол: {liker_data[7]}\nГород: {liker_data[2]}"
                    f"\nОписание: {liker_data[4]}\nЦель общения: {liker_data[5]}\nВозраст: {liker_data[3]}",
            reply_markup=reply_markup
        )



@bot.callback_query_handler(func=lambda call: call.data.startswith('accept_'))
def handle_accept(call):
    # Разделение callback_data для получения ID пользователя и ID лайкнутого пользователя
    _, user_id, liked_user_id = call.data.split('_')
    user_id = int(user_id)
    liked_user_id = int(liked_user_id)

    # Получаем данные обоих пользователей
    user_data = database_manager.get_user(user_id)
    liked_user_data = database_manager.get_user(liked_user_id)

    if user_data and liked_user_data:
        send_temporary_confirmation(user_id,
                                    f"Вы понравились друг другу! {liked_user_data[1]} лайкнул вас в ответ. Начните общение: @{liked_user_data[9]}")
        send_temporary_confirmation(liked_user_id,
                                    f"Вы понравились друг другу! Вы лайкнули {user_data[1]} Начните общение: @{user_data[9]}")

        database_manager.remove_mutual_likes(user_id, liked_user_id)
        bot.delete_message(chat_id=call.message.chat.id, message_id=call.message.message_id)


@bot.callback_query_handler(func=lambda call: call.data == 'restart_searching')
def restart_searching(call):
    user_id = call.from_user.id
    database_manager.reset_viewed_profiles(user_id)
    start_searching(call)


def send_temporary_confirmation(user_id, message_text):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("ОК", callback_data='decline_'))
    bot.send_message(user_id, message_text, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('decline_'))
def handle_decline(call):
    # Удаляем сообщение с предложением
    bot.delete_message(call.message.chat.id, call.message.message_id)


if __name__ == '__main__':
    database_manager.create_table()
    print("Бот запущен")
    bot.polling(none_stop=True)

# Подключение к базе данных
conn = sqlite3.connect('profiles.db')
cursor = conn.cursor()


# функция для фильтрации анкет в соответствии с заданными критериями (пол пользователя)
def filter_profiles(STATE_PROFILE):
    conn = sqlite3.connect('users_database.db')
    cursor = conn.cursor() 

    cursor.execute('SELECT * FROM users_database WHERE gender != ? AND status = ?'), (STATE_PROFILE)
    filtered_profiles = cursor.fetchall()

    conn.close()

    return filtered_profiles

#  функцию фильтрации для выбора соответствующих анкет.

filtered_profiles = filter_profiles(STATE_PROFILE)

for profile in filtered_profiles:
    print(profile)
