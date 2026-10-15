

import os
import time
import requests

API_KEY = os.getenv("TD_API_KEY")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

DATA_URL = "https://api.twelvedata.com/time_series"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def send_message(message):
    response = requests.post(
        TELEGRAM_URL,
        json={"chat_id": CHAT_ID, "text": message},
        timeout=20
    )
    response.raise_for_status()


def ema(values, period):
    result = []
    alpha = 2 / (period + 1)

    for value in values:
        if not result:
            result.append(value)
        else:
            result.append(
                alpha * value + (1 - alpha) * result[-1]
            )

    return result


def get_signal():
    response = requests.get(
        DATA_URL,
        params={
            "symbol": "EUR/USD",
            "interval": "1min",
            "outputsize": 50,
            "apikey": API_KEY
        },
        timeout=20
    )
    response.raise_for_status()
    data = response.json()

    if "values" not in data:
        raise RuntimeError(data.get("message", "No candle data"))

    candles = sorted(
        data["values"],
        key=lambda candle: candle["datetime"]
    )

    # Ignore the newest candle because it may still be forming.
    candles = candles[:-1]

    if len(candles) < 25:
        raise RuntimeError("Not enough candle data")

    closes = [float(candle["close"]) for candle in candles]
    fast = ema(closes, 9)
    slow = ema(closes, 21)

    previous_fast, current_fast = fast[-2], fast[-1]
    previous_slow, current_slow = slow[-2], slow[-1]

    if previous_fast <= previous_slow and current_fast > current_slow:
        return "BUY", candles[-1]["datetime"]

    if previous_fast >= previous_slow and current_fast < current_slow:
        return "SELL", candles[-1]["datetime"]

    return "WAIT", candles[-1]["datetime"]


def main():
    if not API_KEY or not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError(
            "Configure TD_API_KEY, TELEGRAM_BOT_TOKEN "
            "and TELEGRAM_CHAT_ID first."
        )

    send_message(
        "Vamshi Demo Signals Bot is online ❤️\n"
        "EUR/USD | 1-minute candles\n"
        "Demo signals only; no trades are executed."
    )

    last_signal_candle = None

    while True:
        try:
            signal, candle_time = get_signal()

            if signal != "WAIT" and candle_time != last_signal_candle:
                send_message(
                    f"{signal} signal: EUR/USD\n"
                    f"Time: {candle_time}\n"
                    "Demo signal only. Confirm before any trade."
                )
                last_signal_candle = candle_time

            print(f"{candle_time}: {signal}")

        except Exception as error:
            print("Error:", error)

        time.sleep(120)


if __name__ == "__main__":
    main()
