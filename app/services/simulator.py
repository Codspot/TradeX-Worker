import time
import random
from datetime import datetime
from threading import Thread
from app.services.tracker import RealTimeCandleTracker
from socket_server import emit_tick_to_clients

_simulators = {}

def start_simulation(symboltoken, exchangeType, interval_min, from_date, to_date):
    if symboltoken in _simulators:
        return  # already simulating

    tracker = RealTimeCandleTracker(symboltoken, exchangeType, interval_min)
    candles = tracker.fetch_historical_candles(from_date, to_date)
    if not candles:
        raise Exception("No historical data available")

    last_close = candles[-1][4] * 100  # in paise

    def run_simulation():
        ltp = last_close
        while symboltoken in _simulators:
            movement = random.randint(-50, 50)
            ltp += movement
            if ltp <= 0:
                ltp = last_close

            tick = {
                "ltp": ltp / 100,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "symboltoken": symboltoken
            }
            emit_tick_to_clients(tick)
            time.sleep(1)

    thread = Thread(target=run_simulation, daemon=True)
    _simulators[symboltoken] = thread
    thread.start()

def stop_simulation(symboltoken):
    _simulators.pop(symboltoken, None)
