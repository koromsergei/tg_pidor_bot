import os
import asyncio
import aiohttp
from typing import Optional, Dict, Any
from geopy.geocoders import Nominatim
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants as tg_const
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BOT_TOKEN = os.getenv("TG_TOKEN")

# ───────────────────────────────────────────────────────────────────────────────
# WMO-коды → человекочитаемые условия + эмодзи
# ───────────────────────────────────────────────────────────────────────────────
WMO_DESCR = {
    0: '☀️  Ясно', 1: '🌤️  Малооблачно', 2: '⛅  Переменная облачность', 3: '☁️  Пасмурно',
    45: '🌫️  Туман', 48: '🌫️  Изморозь', 51: '🌦️  Слабая морось', 53: '🌦️  Морось',
    55: '🌦️  Сильная морось', 56: '🌧️  Ледяной дождь', 57: '🌧️  Сильный ледяной дождь',
    61: '🌧️  Слабый дождь', 63: '🌧️  Дождь', 65: '🌧️  Ливень', 66: '🌨️  Снег с дождём',
    67: '🌨️  Ливень со снегом', 71: '❄️  Слабый снег', 73: '❄️  Снег', 75: '❄️  Сильный снег',
    77: '❄️  Снежная крупа', 80: '🌦️  Ливни', 81: '🌦️  Сильные ливни', 82: '🌦️  Очень сильные ливни',
    85: '🌨️  Снежные ливни', 86: '🌨️  Сильные снежные ливни', 95: '⛈️  Гроза',
    96: '⛈️  Гроза с градом', 99: '⛈️  Сильная гроза с градом'
}

def _wind_dir(deg: Optional[float]) -> str:
    if deg is None:
        return ''
    dirs = ['С','ССВ','СВ','ВСВ','В','ВЮВ','ЮВ','ЮЮВ','Ю','ЮЮЗ','ЮЗ','ЗЮЗ','З','ЗСЗ','СЗ','ССЗ']
    return dirs[int((deg + 11.25) % 360 // 22.5)]

# ───────────────────────────────────────────────────────────────────────────────
# Геокодирование через Nominatim
# ───────────────────────────────────────────────────────────────────────────────
async def get_city_coordinates(city: str) -> Optional[tuple[float, float, str]]:
    try:
        geo = Nominatim(user_agent='telegram_weather_bot', timeout=10)
        loc = geo.geocode(city, language='ru', exactly_one=True)
        if loc:
            return loc.latitude, loc.longitude, loc.address
    except Exception:
        pass
    return None

# ───────────────────────────────────────────────────────────────────────────────
# Запрос к Open-Meteo API
# ───────────────────────────────────────────────────────────────────────────────
async def fetch_openmeteo_weather(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    url = 'https://api.open-meteo.com/v1/forecast'
    params = {
        'latitude': lat,
        'longitude': lon,
        'current': 'temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,cloud_cover,wind_speed_10m,wind_direction_10m,weather_code',
        'daily': 'temperature_2m_max,temperature_2m_min,precipitation_sum',
        'timezone': 'auto',
        'forecast_days': 1
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception:
        pass
    return None

# ───────────────────────────────────────────────────────────────────────────────
# /getweather — подробный прогноз
# ───────────────────────────────────────────────────────────────────────────────
async def get_weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not context.args:
        await context.bot.send_message(
            chat_id, "❌ Укажите город: `/getweather Москва`", parse_mode='Markdown'
        )
        return
    city = " ".join(context.args)
    pending = await context.bot.send_message(
        chat_id, f"🔍 Ищу прогноз для *{city}*…", parse_mode='Markdown'
    )
    geo = await get_city_coordinates(city)
    if not geo:
        await pending.edit_text(f"❌ Город *{city}* не найден.", parse_mode='Markdown')
        return
    lat, lon, full = geo
    data = await fetch_openmeteo_weather(lat, lon)
    if not data:
        await pending.edit_text("⚠️ Не удалось получить данные от Open-Meteo.", parse_mode='Markdown')
        return

    cur = data['current']
    day = data['daily']
    descr   = WMO_DESCR.get(cur['weather_code'], f"🌤️ Код {cur['weather_code']}")
    t_now   = cur['temperature_2m']
    t_feels = cur['apparent_temperature']
    hum     = cur['relative_humidity_2m']
    cloud   = cur['cloud_cover']
    wind    = cur['wind_speed_10m']
    wdir    = _wind_dir(cur.get('wind_direction_10m'))
    prec    = cur['precipitation']
    t_max   = day['temperature_2m_max'][0]
    t_min   = day['temperature_2m_min'][0]
    prec_d  = day['precipitation_sum'][0]
    updated = datetime.now(timezone.utc).astimezone().strftime('%H:%M')

    msg = (
        f"📍 *{full.split(',')[0]}*\n"
        f"{descr}\n"
        f"🌡️ *{t_now:.1f}°C* (ощущается как {t_feels:.1f}°C)\n"
        f"🔺/🔻 {t_max:.1f}°/{t_min:.1f}°  ·  💧 {hum}%  ·  ☁️ {cloud}%\n"
        f"💨 {wind:.0f} км/ч {wdir}  ·  🌧️ сейчас {prec:.1f} мм/ч, за день {prec_d:.1f} мм\n"
        f"_Обновлено {updated}_"
    )
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh:{city}")]]
    )
    await pending.edit_text(msg, parse_mode='Markdown', reply_markup=kb)

# ───────────────────────────────────────────────────────────────────────────────
# Callback для обновления /getweather
# ───────────────────────────────────────────────────────────────────────────────
async def refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    city = q.data.split(":",1)[1]
    await q.edit_message_text(f"⏳ Обновляю прогноз для *{city}*…", parse_mode='Markdown')
    geo = await get_city_coordinates(city)
    if not geo:
        await q.edit_message_text(f"❌ Город *{city}* не найден.", parse_mode='Markdown')
        return
    lat, lon, full = geo
    data = await fetch_openmeteo_weather(lat, lon)
    if not data:
        await q.edit_message_text("⚠️ Ошибка Open-Meteo.", parse_mode='Markdown')
        return

    cur = data['current']; day = data['daily']
    descr = WMO_DESCR.get(cur['weather_code'], f"🌤️ Код {cur['weather_code']}")
    msg = (
        f"📍 *{full.split(',')[0]}*\n"
        f"{descr}\n"
        f"🌡️ *{cur['temperature_2m']:.1f}°C* (ощущается как {cur['apparent_temperature']:.1f}°C)\n"
        f"🔺/🔻 {day['temperature_2m_max'][0]:.1f}°/{day['temperature_2m_min'][0]:.1f}°\n"
        f"💧 {cur['relative_humidity_2m']}%  ·  ☁️ {cur['cloud_cover']}%\n"
        f"💨 {cur['wind_speed_10m']:.0f} км/ч {_wind_dir(cur.get('wind_direction_10m'))}\n"
        f"🌧️ {cur['precipitation']:.1f} мм/ч\n"
        f"_Обновлено {datetime.now(timezone.utc).astimezone().strftime('%H:%M')}_"
    )
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔄 Обновить", callback_data=f"refresh:{city}")]]
    )
    await q.edit_message_text(msg, parse_mode='Markdown', reply_markup=kb)

# ───────────────────────────────────────────────────────────────────────────────
# briefweather — краткий прогноз
# ───────────────────────────────────────────────────────────────────────────────
async def get_brief_weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    if not context.args:
        await context.bot.send_message(
            chat_id, "❌ Укажите город: `/briefweather Москва`", parse_mode='Markdown'
        )
        return
    city = " ".join(context.args)
    pending = await context.bot.send_message(chat_id, f"⚡ Получаю краткий прогноз для *{city}*…", parse_mode='Markdown')
    geo = await get_city_coordinates(city)
    if not geo:
        await pending.edit_text(f"❌ Город *{city}* не найден.", parse_mode='Markdown')
        return
    lat, lon, full = geo
    data = await fetch_openmeteo_weather(lat, lon)
    if not data:
        await pending.edit_text("⚠️ Ошибка Open-Meteo.", parse_mode='Markdown')
        return

    cur = data['current']
    temp = cur['temperature_2m']
    code = cur['weather_code']
    cloud = cur['cloud_cover']
    prec = cur['precipitation']
    emoji = WMO_DESCR.get(code, '🌤️').split()[0]
    cloud_desc = f"{cloud}%"
    precip_desc = f"{prec:.1f} мм/ч" if prec>0 else "без осадков"
    msg = (
        f"📍 *{full.split(',')[0]}*\n"
        f"🌡️ *{temp:.0f}°C* {emoji}\n"
        f"☁️ {cloud_desc}  ·  🌧️ {precip_desc}"
    )
    kb = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("📊 Подробно", callback_data=f"getweather:{city}"),
            InlineKeyboardButton("🔄", callback_data=f"brief_refresh:{city}")
        ]]
    )
    await pending.edit_text(msg, parse_mode='Markdown', reply_markup=kb)

# ───────────────────────────────────────────────────────────────────────────────
# Callback для краткого прогноза
# ───────────────────────────────────────────────────────────────────────────────
async def brief_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    city = q.data.split(":",1)[1]
    await q.edit_message_text(f"⚡ Обновляю краткий прогноз для *{city}*…", parse_mode='Markdown')
    geo = await get_city_coordinates(city)
    if not geo:
        await q.edit_message_text(f"❌ Город *{city}* не найден.", parse_mode='Markdown')
        return
    lat, lon, full = geo
    data = await fetch_openmeteo_weather(lat, lon)
    if not data:
        await q.edit_message_text("⚠️ Ошибка Open-Meteo.", parse_mode='Markdown')
        return

    cur = data['current']
    temp = cur['temperature_2m']
    code = cur['weather_code']
    cloud = cur['cloud_cover']
    prec = cur['precipitation']
    emoji = WMO_DESCR.get(code, '🌤️').split()[0]
    cloud_desc = f"{cloud}%"
    precip_desc = f"{prec:.1f} мм/ч" if prec>0 else "без осадков"
    msg = (
        f"📍 *{full.split(',')[0]}*\n"
        f"🌡️ *{temp:.0f}°C* {emoji}\n"
        f"☁️ {cloud_desc}  ·  🌧️ {precip_desc}"
    )
    kb = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("📊 Подробно", callback_data=f"getweather:{city}"),
            InlineKeyboardButton("🔄", callback_data=f"brief_refresh:{city}")
        ]]
    )
    await q.edit_message_text(msg, parse_mode='Markdown', reply_markup=kb)

# ───────────────────────────────────────────────────────────────────────────────
# Прочие команды
# ───────────────────────────────────────────────────────────────────────────────
async def say_hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(update.effective_chat.id, "Сосал?")

async def who_is_pidor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(update.effective_chat.id, "Кто пидар?")

async def pidar_stat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_message(update.effective_chat.id, "Пиадрская статистика")

async def say_custom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = " ".join(context.args) if context.args else "привет"
    await context.bot.send_message(update.effective_chat.id, text)

async def start_hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("👋 Скажи привет", callback_data="say_hello")]])
    await update.message.reply_text("Нажми кнопку, чтобы получить привет!", reply_markup=kb)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    await q.answer()
    if q.data == "say_hello":
        await context.bot.send_message(q.message.chat_id, "привет")

# ───────────────────────────────────────────────────────────────────────────────
def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("sayhello", say_hello))
    app.add_handler(CommandHandler("start_hello", start_hello))
    app.add_handler(CallbackQueryHandler(button_click, pattern="^say_hello$"))

    app.add_handler(CommandHandler("getweather", get_weather))
    app.add_handler(CallbackQueryHandler(refresh_callback, pattern="^refresh:"))

    app.add_handler(CommandHandler("briefweather", get_brief_weather))
    app.add_handler(CallbackQueryHandler(brief_refresh, pattern="^brief_refresh:"))

    app.add_handler(CommandHandler("whoispidor", who_is_pidor))
    app.add_handler(CommandHandler("pidarstat", pidar_stat))
    app.add_handler(CommandHandler("say", say_custom))

    app.run_polling()

if __name__ == "__main__":
    main()
