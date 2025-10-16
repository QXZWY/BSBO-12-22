import os
import aiohttp
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from telegram.ext import CommandHandler
from dotenv import load_dotenv

load_dotenv()

try:
    token = os.getenv('TOKEN')
    token_weather = os.getenv('TOKEN_WEATHER')
    if not token or not token_weather:
        raise EnvironmentError("Не найдены обязательные переменные окружения: TOKEN, TOKEN_WEATHER")
except Exception as e:
    print("Ошибка загрузки переменных окружения:", e)
    exit(1)

def get_user_info(update: Update):
    chat_id = update.effective_chat.id
    user = update.effective_user
    user_id = user.id
    message = update.effective_message
    timestamp = int(message.date.timestamp())
    first_name = user.first_name or ''
    last_name = user.last_name or ''
    full_name = f'{first_name} {last_name}'.strip()
    ava_str = f'{user.username or "no_username"}_{user_id}_{first_name[:2]}_{timestamp}'
    ava_url_cat = f'https://robohash.org/{ava_str}?set=set4'
    return {
        'chat_id': chat_id,
        'first_name': first_name,
        'full_name': full_name,
        'ava_url_cat': ava_url_cat,
        'user_id': user_id,
        'username': user.username,
        'timestamp': timestamp
    }

async def say_hi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = get_user_info(update)
    text = update.message.text
    
    if text == 'Сгенерируй аватар':
        try:
            await context.bot.send_photo(
                chat_id=user_info['chat_id'],
                photo=user_info['ava_url_cat']
            )
        except Exception as e:
            await context.bot.send_message(
                chat_id=user_info['chat_id'],
                text='Ошибка при отправке аватара'
            )
    elif text == 'Мой ID':
        await context.bot.send_message(
            chat_id=user_info['chat_id'],
            text=f"Ваш Telegram user ID: {user_info['user_id']}"
        )

    elif text == 'Погода сегодня':
        await request_location(update, context)
    elif text == 'Фото котика':
        await send_cat_photo(update, context)
    elif text.lower().startswith('рандом') or text.lower().startswith('случайн'):
        await send_random_digit(update, context, user_info)
    else:
        await context.bot.send_message(
            chat_id=user_info['chat_id'],
            text=f"{user_info['first_name']}, как твои дела?\n"
                 f"Твои данные:\n"
                 f"ID: {user_info['user_id']}\n"
                 f"Юзернейм: @{user_info['username']}"
        )

async def wake_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = get_user_info(update)
    button = ReplyKeyboardMarkup([
        ['Фото котика', 'Сгенерируй аватар'],
        ['Мой ID', 'Рандомное число'],
        ['Погода сегодня']
    ], resize_keyboard=True)
    await context.bot.send_message(
        chat_id=user_info['chat_id'],
        text=f'Привет {user_info["username"]}, спасибо, что присоединился!',
        reply_markup=button
    )

async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = get_user_info(update)
    await context.bot.send_message(
        chat_id=user_info['chat_id'],
        text=f"Ваш Telegram user ID: {user_info['user_id']}"
    )

async def request_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_info = get_user_info(update)
    location_keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton('Отправить координаты 📍', request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await context.bot.send_message(
        chat_id=user_info['chat_id'],
        text='Пожалуйста, поделитесь своей геолокацией:',
        reply_markup=location_keyboard
    )
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    location = update.message.location
    if location is None:
        await update.message.reply_text("Локация не получена, попробуйте снова отправить координаты.")
        return
    latitude = location.latitude
    longitude = location.longitude
    context.user_data['location'] = (latitude, longitude)
    try:
        weather_report = await get_weather(latitude, longitude)
    except Exception as e:
        weather_report = "Ошибка при получении данных о погоде."
    await update.message.reply_text(weather_report)
    main_menu = ReplyKeyboardMarkup(
        [
            ['Фото котика', 'Сгенерируй аватар'],
            ['Мой ID', 'Рандомное число'],
            ['Погода сегодня']
        ],
        resize_keyboard=True
    )
    await update.message.reply_text('😎', reply_markup=main_menu)

async def get_weather(lat: float, lon: float) -> str:
    url = f'https://api.openweathermap.org/data/2.5/weather?APPID={token_weather}&lang=ru&units=metric&lat={lat}&lon={lon}'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return 'Ошибка при получении данных о погоде'
                data = await resp.json()
    except Exception as e:
        return 'Ошибка соединения с сервером погоды.'
    
    try:
        city = data.get('name', 'Неизвестное место')
        weather = data['weather'][0]['description']
        temp = data['main']['temp']
        feels_like = data['main']['feels_like']
        wind_speed = data['wind']['speed']
        if wind_speed < 5:
            wind_recom = 'Ветра почти нет, погода хорошая, ветра почти нет'
        elif wind_speed < 10:
            wind_recom = 'На улице немного ветрено, оденьтесь чуть теплее'
        elif wind_speed < 20:
            wind_recom = 'Сейчас на улице очень сильный ветер, будьте осторожны, выходя из дома'
        else:
            wind_recom = 'Не лучшее время, на улицу лучше не выходить'

        return (
            f'Сейчас в {city} {weather}\n'
            f'🌡 Температура: {temp}°C (Ощущается как {feels_like}°C)\n'
            f'💨 Скорость ветра: {wind_speed} м/с\n'
            f'{wind_recom}\n'
        )
    except Exception as e:
        return "Ошибка разбора данных о погоде."

async def send_cat_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    breed_id = 'beng'
    url = f'https://api.thecatapi.com/v1/images/search?breed_ids={breed_id}'
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and 'url' in data[0]:
                        cat_url = data[0]['url']
                    elif data:
                        cat_url = data[0].get('url')
                    else:
                        cat_url = None
                else:
                    cat_url = None
    except Exception as e:
        cat_url = None

    if cat_url:
        await context.bot.send_photo(
            chat_id=chat_id,
            photo=cat_url,
            caption='Вот котик бенгальской породы😺:'
        )
    else:
        await context.bot.send_message(chat_id=chat_id, text='Не удалось получить фото котика нужной породы 🐱')
async def send_random_digit(update: Update, context: ContextTypes.DEFAULT_TYPE, user_info):
    url = "https://www.randomnumberapi.com/api/v1.0/random?min=1&max=100&count=1"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list) and data:
                        rand_num = data[0]
                        text = f"Ваше случайное число: {rand_num}"
                    else:
                        text = "Ошибка: API не вернул число!"
                else:
                    text = "Ошибка при получении случайного числа!"
    except Exception as e:
        text = "Ошибка соединения с сервисом случайных чисел!"
    await context.bot.send_message(chat_id=user_info['chat_id'], text=text)

application = ApplicationBuilder().token(token).build()
application.add_handler(CommandHandler('start', wake_up))
application.add_handler(CommandHandler('myID', my_id))
application.add_handler(MessageHandler(filters.TEXT, say_hi))
application.add_handler(MessageHandler(filters.LOCATION, handle_location))
application.run_polling()