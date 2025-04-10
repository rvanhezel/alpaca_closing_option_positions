import os
import time
import pandas as pd
from src.api.alpaca_api import AlpacaAPI
from src.utilities.logger import Logger
from src.configuration import Configuration
from dotenv import load_dotenv
from src.execution_orchestrator import ExecutionOrchestrator
from src.utilities.utils import quantity_buckets
import queue
from src.utilities.enums import Signal
import logging


if __name__ == "__main__":
    load_dotenv()

    Logger()
    cfg = Configuration('run.cfg')

    order_statuses = {}
    quote_data = queue.Queue()
    trade_data = queue.Queue()

    async def update_trade_data(data):
        """Update trade data from WS"""
        logging.debug(f"Trade data received from WS: {data}")
        trade_data.put(data)

    async def update_quote_data(data):
        """Update quote data from WS"""
        # logging.debug(f"Quote data {type(data)}")
        # logging.debug(f"Quote data received from WS for {data.symbol}: {data.timestamp}")
        # quote_data[data.symbol] = data
        quote_data.put(data)

    async def update_order_status(data):
        logging.debug(f"Updating order status: {data.order.status}")
        # if data.order.id not in order_statuses:
        #     order_statuses[data.order.id] = []
        order_statuses[data.order.id] = data

    api = AlpacaAPI()
    api.connect(cfg)

    api.subscribe_trade_updates(update_order_status)
    api.subscribe_option_md_updates(update_quote_data, update_trade_data, [cfg.instrument_id])

    time.sleep(3)   #Seems important to wait for the websocket to connect! Not sure why this is needed over the pause in the api.connect()

    # class NativePosition:
    #     def __init__(self, instrument_id: str, qty: int, avg_entry_price: float):
    #         self.instrument_id = instrument_id
    #         self.qty = qty
    #         self.avg_entry_price = avg_entry_price

    ## Place sample order
    order = api.place_market_order(cfg.instrument_id, cfg.starting_position_quantity, Signal.BUY)
    timeout = 10
    while timeout > 0:
        if order.id not in order_statuses:
            timeout -= 1
            time.sleep(1)
        else:
            break

    native_position = api.get_open_position_by_id(cfg.instrument_id)
    # native_position = NativePosition(cfg.instrument_id, 5, 100)
    if native_position is None:
        logging.debug(f"No position found for {cfg.instrument_id}")
    else:
        logging.debug(f"Position found for {cfg.instrument_id}: {native_position}")

    if int(native_position.qty) != cfg.starting_position_quantity:
        logging.debug(f"Position quantity mismatch. Expected {cfg.starting_position_quantity}, got {native_position.qty}")
    else:
        logging.debug(f"Position quantity matches. Expected at least {cfg.starting_position_quantity}, got {native_position.qty}")

    profit_target_levels = [float(native_position.avg_entry_price) * (1 + target) for target in cfg.profit_targets]
    logging.debug(f"Profit target levels: {profit_target_levels}")

    sell_quantity_buckets = quantity_buckets(int(native_position.qty), cfg.sell_buckets, cfg.close_strategy)
    logging.debug(f"Sell quantity buckets: {sell_quantity_buckets}")

    buckets_closed = pd.DataFrame(columns=["order_id", "order_status", "bucket_qty", "profit_target", "fill_price", "timestamp"])
    
    try:

        for idx, (cur_bucket_qty, cur_profit_target) in enumerate(zip(sell_quantity_buckets, profit_target_levels)):
            logging.debug(f"Current bucket quantity: {cur_bucket_qty}, Current profit target: {cur_profit_target}")

            if cur_bucket_qty > 0:

                next_bucket = False

                while not next_bucket:

                    # Get latest option quote from queue
                    # try:
                    #     data = quote_data.get(timeout=1)
                    # except queue.Empty:
                    #     logging.debug("No quote data received. Waiting...")
                    #     continue

                    latest_quote = None
                    while not quote_data.empty():
                        latest_quote = quote_data.get_nowait()

                    if not latest_quote:
                        # logging.debug("No quote data received...")
                        continue

                    logging.debug(f"Using quote: timestamp: {latest_quote.timestamp}, bid_price: {latest_quote.bid_price}, ask_price: {latest_quote.ask_price}")

                    latest_option_bid_price = latest_quote.bid_price

                    if latest_option_bid_price >= cur_profit_target:
                        
                        logging.debug(f"Latest option quote {latest_option_bid_price} >= {cur_profit_target}")
                        logging.debug(f"Closing position {native_position.symbol} with quantity {cur_bucket_qty}")

                        #close position
                        order = api.close_position_by_id(native_position.symbol, str(cur_bucket_qty))
                        order_statuses[order.id] = None

                        time.sleep(3)   # pause for order callback

                        logging.debug(f"Order {order.id} status: {order_statuses[order.id].order.status}")

                        next_bucket = True

                        buckets_closed.loc[idx] = [
                            order.id, 
                            order_statuses[order.id].order.status, 
                            cur_bucket_qty, 
                            cur_profit_target,
                            order_statuses[order.id].order.filled_avg_price,
                            pd.Timestamp.now(tz=cfg.timezone)]
                        buckets_closed.to_csv(os.path.join("output", "positions_closed.csv"), index=False)

                    else:

                        logging.debug(f"Latest option bid quote {latest_option_bid_price} < {cur_profit_target}")
                        logging.debug(f"Looping again...")

    except Exception as e:

        logging.debug(f"Error: {e}")
        logging.debug(f"Closing all positions")

        api.close_all_positions()

    finally:
        logging.info("All positions closed. Terminating...")



