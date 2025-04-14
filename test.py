import time
from src.api.alpaca_api import AlpacaAPI
from dotenv import load_dotenv
from src.configuration import Configuration
from src.utilities.enums import *
from alpaca.trading.stream import TradingStream
import os
from alpaca.trading.requests import GetOrdersRequest, MarketOrderRequest
from alpaca.trading.enums import OrderSide, QueryOrderStatus
import asyncio
import threading



load_dotenv()
cfg = Configuration('run.cfg')

api = AlpacaAPI()
api.connect(cfg)

class Statuses:
    def __init__(self):
        self.statuses = {}

    async def update(self, data):
        print("XXXXXXXXXXXXXXXXXXX")
        print(f"Updating statuses: {data.order.status}")
        if data.order.id not in self.statuses:
            self.statuses[data.order.id] = []

        self.statuses[data.order.id].append(data)

    def print_statuses(self):
        print(f"Statuses: {self.statuses}")

statuses = Statuses()

trading_stream = TradingStream(api_key=os.environ.get('ALPACA_KEY', 'WRONG-KEY'),
                secret_key=os.environ.get('ALPACA_SECRET', 'WRONG-KEY'),
                paper=True,
            )

async def update_handler(data):
    # trade updates will arrive in our async handler
    print("XXXXXXXXXXXXXXXXXXX")
    print("Inside update handler")
    print(data.order.status)


# trading_stream.subscribe_trade_updates(update_handler)
# trading_stream.subscribe_trade_updates(statuses.update)

thread = threading.Thread(target=trading_stream.run, daemon=True)        # Here would run websocket and data processing in this thread.
thread.start()

time.sleep(3) #important to wait for the websocket to connect!

trading_stream.subscribe_trade_updates(statuses.update)

time.sleep(3) #important to wait for the websocket to connect!


print("Placing order")
order = api.place_market_order(symbol="GOOGL", qty=1, side=Signal.BUY)

time.sleep(3)

# statuses.print_statuses()

print("Cancelling order")
api.cancel_order_by_id(order.id)

time.sleep(3)

statuses.print_statuses()

b = 5