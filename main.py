import numpy as np
import talib as ta
import requests
from telegram import Bot
import asyncio
import time

# Telegram Bot
telegram_token = '7040235627:AAGwfZKCy49S_SFinjMjXeNfOzgCCQtimfo'
chat_id = '1357096860'
bot = Bot(token=telegram_token)

# Храним последние цены закрытия для расчета индикаторов
close_prices = {}

# Асинхронная функция для отправки уведомления в Telegram
async def send_telegram_message(message):
    await bot.send_message(chat_id=chat_id, text=message)

# Функция для расчета индикаторов
def calculate_indicators(symbol):
    if symbol in close_prices and len(close_prices[symbol]) >= 100:  # Проверяем, что данных достаточно
        sma_100 = ta.SMA(np.array(close_prices[symbol]), timeperiod=100)
        sma_200 = ta.SMA(np.array(close_prices[symbol]), timeperiod=200)
        rsi = ta.RSI(np.array(close_prices[symbol]), timeperiod=14)

        close_price = close_prices[symbol][-1]  # Последняя цена закрытия

        return sma_100[-1], sma_200[-1], rsi[-1], close_price  # Возвращаем последние значения и цену закрытия
    return None, None, None, None

# Функция для получения списка тикеров с объемом торгов >= 40,000,000 USDT за последние 24 часа
def fetch_symbols_with_high_volume():
    url = "https://fapi.binance.com/fapi/v1/ticker/24hr"
    response = requests.get(url)
    tickers = response.json()
    filtered_symbols = [
        ticker['symbol'] for ticker in tickers 
        if ticker['symbol'].endswith('USDT') and float(ticker['quoteVolume']) >= 40000000
    ]
    
    if filtered_symbols:
        print(f"Отфильтрованные тикеры: {filtered_symbols}")  # Печатаем список тикеров
        print(f"Количество тикеров: {len(filtered_symbols)}")  # Печатаем количество тикеров
    else:
        print("Нет тикеров с объемом более 40 млн USDT.")
    
    return filtered_symbols

# Получаем исторические данные для тикера
def fetch_historical_data(symbol, interval='1h', limit=201):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {
        'symbol': symbol,
        'interval': interval,
        'limit': limit
    }
    response = requests.get(url, params=params)
    
    if response.status_code != 200:
        print(f"Ошибка получения данных для {symbol}: {response.status_code}")
        return []  # Возвращаем пустой список при ошибке

    klines = response.json()
    print(f"Загружены исторические данные для {symbol}: {len(klines)} свечей.")
    # Возвращаем только цены закрытия и пропускаем последнюю (текущую свечу)
    return [float(kline[4]) for kline in klines[:-1]]

# Проверка и логирование индикаторов для отфильтрованных тикеров
async def calculate_and_log_indicators(symbol):
    print("Расчет индикаторов для:", symbol)
    sma_100, sma_200, rsi, close_price = calculate_indicators(symbol)
    
    # Логируем индикаторы
    if sma_100 is not None and sma_200 is not None and rsi is not None:
        print(f"{symbol} - SMA100: {sma_100}, SMA200: {sma_200}, RSI: {rsi}, Close Price: {close_price}")
        
        # Проверяем условия
        if sma_100 < sma_200 and close_price < sma_100 and rsi < 30:
            valid_tickers.append(symbol)  # Добавляем тикер в список подходящих

# Основной процесс
async def main():
    await send_telegram_message("Тест: приложение запущено и работает.")  # Уведомление о запуске

    while True:
        print("Получаем тикеры с объемом > 40 млн USDT...")
        # Шаг 1: Получаем тикеры с объемом > 40 млн USDT
        filtered_tickers = fetch_symbols_with_high_volume()
        global valid_tickers
        valid_tickers = []  # Инициализация списка подходящих тикеров

        # Шаг 2: Для каждого тикера получаем исторические данные
        for ticker in filtered_tickers:
            close_prices[ticker] = fetch_historical_data(ticker)

            if len(close_prices[ticker]) < 100:  # Пропускаем тикеры с недостаточными данными
                print(f"Недостаточно исторических данных для {ticker}. Пропускаем.")
                continue

        # Шаг 3: Расчет индикаторов для отфильтрованных тикеров
        for ticker in filtered_tickers:
            await calculate_and_log_indicators(ticker)

        # Шаг 4: Отправляем сообщение о подходящих тикерах
        if valid_tickers:
            message = "Подходящие тикеры: " + ", ".join(valid_tickers)
        else:
            message = "Нет подходящих тикеров."
        
        await send_telegram_message(message)

        # Ожидаем, пока не откроется новая свеча
        while True:
            current_time = time.localtime()
            if current_time.tm_min == 0:  # Новый час
                print("Открытие новой часовой свечи. Запуск расчетов...")
                break  # Выходим из внутреннего цикла и начинаем заново
            await asyncio.sleep(60)  # Проверяем каждую минуту

if __name__ == '__main__':
    asyncio.run(main())  # Запускаем асинхронную функцию main
