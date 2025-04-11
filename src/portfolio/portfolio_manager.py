import copy
from src.portfolio.position import Position
import pandas as pd
from typing import List, Dict, Optional
import os
from src.portfolio.position import Position
import queue
from src.configuration import Configuration
import logging
import time
from src.utilities.utils import trading_day_start_time_ts


class PortfolioManager:

    def __init__(self, config: Configuration, api):
        self.config = config
        self.api = api

        self.orders = [] # (order, order idx, handled) - handled is a boolean to check if the order has been processed to csv
        self._order_statuses = {}
        self._trade_data = queue.Queue()

        self.closed_buckets = pd.DataFrame(columns = [
            "order_id",
            "symbol", 
            "order_status", 
            "bucket_qty", 
            "fill_price", 
            "timestamp",
            "reason"])
        self._starting_idx = 0

    @property
    def starting_idx(self):
        return self._starting_idx
    
    def close_position_by_id(self, symbol, qty, idx):
        order = self.api.close_position_by_id(symbol, str(qty))

        self.orders.append((order, idx, False))
        self.wait_for_order_response(order.id, self.config.timeout)

    def process_latest_order(self):
        """Process the latest order"""
        if not self.orders:
            return False
        
        placed_order, order_idx, handled = self.orders[-1]
        order = self._order_statuses[placed_order.id].order

        if order.status == "filled" and not handled:

            logging.debug(f"PtfMgr: Adding filled order {order.id} at idx {order_idx} to csv")

            self.closed_buckets.loc[order_idx] = [
                order.id, 
                order.symbol,
                order.status, 
                order.qty,
                order.filled_avg_price,
                pd.Timestamp.now(tz=self.config.timezone),
                "profit_target"]
            
            self.closed_buckets.to_csv(os.path.join("output", "positions_closed.csv"), index=False)
            self.orders[-1] = (order, order_idx, True)

            return True
        
        elif order.status == "cancelled" and not handled:

            logging.debug(f"PtfMgr: Adding cancelled order {order.id} at idx {order_idx} to csv")

            self.closed_buckets.loc[order_idx] = [
            order.id, 
            order.symbol,
            order.status, 
            order.qty, 
            order.filled_avg_price,
            pd.Timestamp.now(tz=self.config.timezone),
            "profit_target"]
        
            self.closed_buckets.to_csv(os.path.join("output", "positions_closed.csv"), index=False)
            self.orders[-1] = (order, order_idx, True)

            return False #If an order is cancelled, we need to reprocess the bucket
        
        else:
            
            return False
    
    def latest_order_pending(self):
        if not self.orders:
            return False
        
        order_id = self.orders[-1][0].id
        order_status = self._order_statuses[order_id].order.status

        if (order_status != 'filled' and
            order_status != 'cancelled'):

                    return True
                
        return False

    def populate_from_csv(self):
        logging.info("PortfolioManager: Populating orders from csv.")
        
        # Check if positions_closed.csv exists and load it
        positions_closed_path = os.path.join("output", "positions_closed.csv")
        if os.path.exists(positions_closed_path):

            loaded_buckets_closed = pd.read_csv(positions_closed_path)

            query = (loaded_buckets_closed['symbol'] == self.config.instrument_id) & \
                    (loaded_buckets_closed['order_status'] == 'filled')
            loaded_buckets_closed = loaded_buckets_closed[query]

            logging.debug(f"Loaded existing positions_closed.csv with {len(loaded_buckets_closed)} records: {loaded_buckets_closed}")
            logging.debug(f"{len(loaded_buckets_closed)} positions have been closed with a total qty {sum(loaded_buckets_closed['bucket_qty'])} sold")

            self._starting_idx = len(loaded_buckets_closed)

            missing = [col for col in self.closed_buckets.columns if col not in loaded_buckets_closed.columns]
            if missing:
                logging.error(f"Missing columns in loaded positions_closed.csv: {missing}")
            else:
                self.closed_buckets = loaded_buckets_closed

    async def update_order_status(self, data):
        """Update order status"""
        # logging.debug(f"Order update received from WS. Id: {data.order.id}. Status: {data.order.status}")
        self._order_statuses[data.order.id] = data

    async def update_trade_data(self, data):
        """Update trade data from WS"""
        # logging.debug(f"Trade data received from WS: {data}")
        self._trade_data.put(data)

    def wait_for_order_response(self, order_id, timeout):
        cur_timeout = timeout
        while cur_timeout > 0:
            if order_id not in self._order_statuses:
                cur_timeout -= 1
                time.sleep(1)
            else:
                break
        
