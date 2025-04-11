from src.utilities.utils import quantity_buckets
import queue
import sys
from src.utilities.logger import Logger
import time
from datetime import datetime
import logging
from src.configuration import Configuration
from src.utilities.enums import Signal
import pandas as pd
import os
import shutil
from src.api.alpaca_api import AlpacaAPI    
from src.trading_session_manager import TradingSessionManager


class ExecutionOrchestrator:

    def __init__(self, cfg: Configuration):
        self.config = cfg
        self.api = AlpacaAPI()
        self.trading_session_manager = TradingSessionManager(
            cfg.timezone,
            cfg.trading_start_time,
            cfg.trading_end_time)
        
        self.market_data = pd.DataFrame()
        self._order_statuses = {}
        self._quote_data = queue.Queue()
        self._trade_data = queue.Queue()

        self.expiry_day = False


    def start(self):
        """Start the trading system"""
        try:
            self._save_config()
            logging.info("Starting trading system...")

            if self.config.paper_trading:
                logging.info("Paper trading mode enabled")
            else:
                logging.info("Live trading mode enabled")

            self.api.connect(self.config)

            try:
                self._trading_session_loop()

            except Exception as e:
                logging.error(f"Error in trading loop: {str(e)}")
                time.sleep(10)  

        except ConnectionError as e:
            logging.error(f"Failed to connect to Alpaca API: {str(e)}")

        except KeyboardInterrupt:
            logging.info("KeyboardInterrupt - Shutting down trading system...")

        except Exception as e:
            logging.error(f"Unexpected error within trading system: {str(e)}")

        finally:

            logging.info("Trading system shut down")
            
            
    def _trading_session_loop(self):
        """Main trading loop"""
        previous_day = pd.Timestamp.now(tz=self.config.timezone).date()

        while True:
            logging.info(f"Starting trading loop")

            now = pd.Timestamp.now(tz=self.config.timezone)
            if now.date() > previous_day:
                Logger(now.date()) # Create new log file for new day to avoid excessively large files
                previous_day = now.date()

            if self.trading_session_manager.is_trading_day(now) and self.trading_session_manager.is_trading_hours(now):

                self._trading_execution()

            else:

                logging.warning("Outside trading schedule. Waiting...")
                time.sleep(60)
            
    

    def _save_config(self):
        """Save configuration file to outputs for audit purposes"""
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%d%m%Y")
        filename = f"config_{timestamp}.cfg"
        filepath = os.path.join(output_dir, filename)
        
        shutil.copy2('run.cfg', filepath)
        logging.info(f"Configuration saved to {filepath}")

    def _save_market_data(self):
        """Save data to CSV file"""
        if not self.market_data.empty:
            logging.info("Saving market data to CSV file...")

            # Create output directory if it doesn't exist
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"market_data_{self.config.instrument_id}_{timestamp}.csv"
            filepath = os.path.join(output_dir, filename)
            
            self.market_data.to_csv(filepath, index=True)
            logging.info(f"Market data saved to {filepath}")

    async def _update_order_status(self, data):
        """Update order status"""
        logging.debug(f"Order update received from WS. Id: {data.order.id}. Status: {data.order.status}")
        self._order_statuses[data.order.id] = data

    async def _update_quote_data(self, data):
        """Update quote data from WS"""
        logging.debug(f"Quote data received from WS for {data.symbol} at {data.timestamp}")
        self._quote_data.put(data)

    async def _update_trade_data(self, data):
        """Update trade data from WS"""
        logging.debug(f"Trade data received from WS: {data}")
        self._trade_data.put(data)

    def _trading_execution(self):
        """Execute trading logic"""

        self.api.subscribe_trade_updates(self._update_order_status)
        self.api.subscribe_option_md_updates(
            self._update_quote_data, 
            self._update_trade_data, 
            [self.config.instrument_id]
            )

        time.sleep(3)   #Seems important to wait for the websocket to connect! 
                        #Not sure why this is needed over the pause in the api.connect()

        class NativePosition:
            def __init__(self, instrument_id: str, qty: int, avg_entry_price: float):
                self.instrument_id = instrument_id
                self.qty = qty
                self.avg_entry_price = avg_entry_price

        ## Place sample order & wait for response
        # order = self.api.place_market_order(
        #     self.config.instrument_id, 
        #     self.config.starting_position_quantity, 
        #     Signal.BUY)
        # self._wait_for_order_response(order.id, self.config.timeout)

        # Get position from API
        # native_position = self.api.get_open_position_by_id(self.config.instrument_id)
        native_position = NativePosition(self.config.instrument_id, self.config.starting_position_quantity, 10)

        if native_position is None:
            logging.error(f"No position found for {self.config.instrument_id}")
            return
        else:
            logging.debug(f"Position found for {self.config.instrument_id}: {native_position}")

        if int(native_position.qty) != self.config.starting_position_quantity:
            logging.error(f"Position quantity mismatch. Expected {self.config.starting_position_quantity}, got {native_position.qty}")
        else:
            logging.info(f"Position quantity matches. Expected {self.config.starting_position_quantity}, got {native_position.qty}")

        profit_target_levels = [float(native_position.avg_entry_price) * (1 + target) for target in self.config.profit_targets]
        logging.info(f"Profit target levels: {profit_target_levels}")

        sell_quantity_buckets = quantity_buckets(int(native_position.qty), self.config.sell_buckets, self.config.close_strategy)
        logging.info(f"Sell quantity buckets: {sell_quantity_buckets}")

        # Check expiry day
        now = pd.Timestamp.now(tz=self.config.timezone)
        expiry_date = self.api.get_option_contract_by_id(self.config.instrument_id).expiration_date
        if now.date() == expiry_date:
            logging.info(f"{self.config.instrument_id} is expiring today.")
            self.expiry_day = True
            
        # Handle existing positions_closed.csv
        closed_buckets = pd.DataFrame(columns = [
            "order_id",
            "symbol" 
            "order_status", 
            "bucket_qty", 
            "profit_target", 
            "fill_price", 
            "timestamp",
            "reason"])
        
        close_starting_idx = 0
        
        # Check if positions_closed.csv exists and load it
        positions_closed_path = os.path.join("output", "positions_closed.csv")
        if os.path.exists(positions_closed_path):

            loaded_buckets_closed = pd.read_csv(positions_closed_path)
            loaded_buckets_closed = loaded_buckets_closed[loaded_buckets_closed['symbol'] == self.config.instrument_id]

            logging.debug(f"Loaded existing positions_closed.csv with {len(loaded_buckets_closed)} records: {loaded_buckets_closed}")
            logging.debug(f"{len(loaded_buckets_closed)} positions have been closed with a total qty {sum(loaded_buckets_closed['bucket_qty'])} sold")

            close_starting_idx = len(loaded_buckets_closed)

            missing = [col for col in closed_buckets.columns if col not in loaded_buckets_closed.columns]
            if missing:
                logging.error(f"Missing columns in loaded positions_closed.csv: {missing}")
            else:
                closed_buckets = loaded_buckets_closed
        
        try:

            for idx, (cur_bucket_qty, cur_profit_target) in enumerate(zip(sell_quantity_buckets, profit_target_levels)):
                logging.debug(f"Current bucket quantity: {cur_bucket_qty}, Current profit target: {cur_profit_target}")

                if idx < close_starting_idx:
                    logging.info(f"Skipping bucket {idx} as it has already been closed")
                    continue

                if cur_bucket_qty > 0:

                    next_bucket = False

                    while not next_bucket:

                        # Handle tick data
                        if self.config.store_all_ticks:

                            latest_ticks = []
                            while not self._quote_data.empty():
                                latest_ticks.append(self._quote_data.get_nowait())

                            if not latest_ticks:
                                continue

                            latest_tick_df = self._parse_tick_data(latest_ticks)

                        else: 

                            latest_quote = None
                            while not self._quote_data.empty():
                                latest_quote = self._quote_data.get_nowait()

                            if not latest_quote:
                                continue

                            latest_tick_df = self._parse_tick_data(latest_quote)

                        self.market_data = pd.concat([self.market_data, latest_tick_df])
                        if self.market_data.shape[0] > 100:
                            self._save_market_data()

                        latest_quote = self.market_data.iloc[-1]

                        msg = f"Using quote: timestamp: {latest_quote.datetime}, bid_price: {latest_quote.bid_price}"
                        msg += f", ask_price: {latest_quote.ask_price}"
                        logging.debug(msg)

                        latest_option_bid_price = latest_quote.bid_price

                        # Selling logic
                        if latest_option_bid_price >= cur_profit_target:
                            
                            logging.debug(f"Latest option quote {latest_option_bid_price} >= {cur_profit_target}")
                            logging.debug(f"Closing position {native_position.symbol} with quantity {cur_bucket_qty}")

                            #close position
                            order = self.api.close_position_by_id(native_position.symbol, str(cur_bucket_qty))
                            self._wait_for_order_response(order.id, self.config.timeout)

                            order_status = self._order_statuses[order.id].order.status
                            logging.debug(f"Order {order.id} status: {order_status}")

                            if order_status == "filled":

                                next_bucket = True

                                closed_buckets.loc[idx] = [
                                    order.id, 
                                    native_position.symbol,
                                    self._order_statuses[order.id].order.status, 
                                    cur_bucket_qty, 
                                    cur_profit_target,
                                    self._order_statuses[order.id].order.filled_avg_price,
                                    pd.Timestamp.now(tz=self.config.timezone),
                                    "profit_target"]
                                closed_buckets.to_csv(os.path.join("output", "positions_closed.csv"), index=False)

                            else:

                                logging.warning(f"Order {order.id} status: {order_status}. Waiting 5 more seconds...")
                                time.sleep(5)

                                order_status = self._order_statuses[order.id].order.status
                                logging.debug(f"Order {order.id} status: {order_status}")

                                if order_status != "filled":

                                    raise Exception(f"Unhandled order status...")
                                    # Add more logic depending on the order status

                                else:

                                    next_bucket = True

                                    closed_buckets.loc[idx] = [
                                        order.id, 
                                        native_position.symbol,
                                        self._order_statuses[order.id].order.status, 
                                        cur_bucket_qty, 
                                        cur_profit_target,
                                        self._order_statuses[order.id].order.filled_avg_price,
                                        pd.Timestamp.now(tz=self.config.timezone),
                                        "profit_target"]
                                    closed_buckets.to_csv(os.path.join("output", "positions_closed.csv"), index=False)

                        else:

                            logging.debug(f"Latest option bid quote {latest_option_bid_price} < {cur_profit_target}")

                            if self.expiry_day:
                                
                                logging.info(f"Expiry day. Checking if we should close positions")
            
                                now = pd.Timestamp.now(tz=self.config.timezone)
                                expiry_sell_cutoff = self.trading_session_manager.trading_end - pd.Timedelta(minutes=self.config.expiry_sell_cutoff)

                                if now >= expiry_sell_cutoff:

                                    msg = f"Current time {now} >= expiry sell cutoff {expiry_sell_cutoff}."
                                    msg += f" Closing position {native_position.symbol} with quantity {cur_bucket_qty}"
                                    logging.info(msg)

                                    order = self.api.close_position_by_id(native_position.symbol, str(cur_bucket_qty))
                                    self._wait_for_order_response(order.id, self.config.timeout)

                                    next_bucket = True

                                    closed_buckets.loc[idx] = [
                                        order.id, 
                                        native_position.symbol,
                                        self._order_statuses[order.id].order.status, 
                                        cur_bucket_qty, 
                                        cur_profit_target,
                                        self._order_statuses[order.id].order.filled_avg_price,
                                        pd.Timestamp.now(tz=self.config.timezone),
                                        "expiry"]
                                    closed_buckets.to_csv(os.path.join("output", "positions_closed.csv"), index=False)

                            logging.debug(f"Looping again...")

        except Exception as e:

            logging.debug(f"Error: {e}")
            logging.debug(f"Closing all positions")

            self.api.close_all_positions()

        finally:
            logging.info("All positions closed. Terminating...")


    def _wait_for_order_response(self, order_id, timeout):
        cur_timeout = timeout
        while cur_timeout > 0:
            if order_id not in self._order_statuses:
                cur_timeout -= 1
                time.sleep(1)
            else:
                break

    def _parse_tick_data(self, latest_quote):
        latest_quote = latest_quote if isinstance(latest_quote, list) else [latest_quote]
        df = pd.DataFrame({
            'datetime': [pd.to_datetime(tick.timestamp, format='%Y%m%d %H:%M:%S %Z') for tick in latest_quote],
            'symbol': [tick.symbol for tick in latest_quote],
            'bid_price': [tick.bid_price for tick in latest_quote],
            'bid_size': [tick.bid_size for tick in latest_quote],
            'bid_exchange': [tick.bid_exchange for tick in latest_quote],
            'ask_price': [tick.ask_price for tick in latest_quote],
            'ask_size': [tick.ask_size for tick in latest_quote],
            'ask_exchange': [tick.ask_exchange for tick in latest_quote],
            'conditions': [tick.conditions for tick in latest_quote],
            'tape': [tick.tape for tick in latest_quote]
        })
        df.set_index('datetime', inplace=True)
        df.sort_index(ascending=True, inplace=True)
        df.index = df.index.tz_convert(self.config.timezone)
        return df

            
            
