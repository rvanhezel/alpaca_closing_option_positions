import sys
from src.utilities.logger import Logger
import time
from datetime import datetime
import logging
from src.configuration import Configuration
from src.utilities.enums import Signal
from src.db.database import Database
import pandas as pd
import os
import shutil
from src.api.alpaca_api import AlpacaAPI    
from src.trading_session_manager import TradingSessionManager


class ExecutionOrchestrator:

    def __init__(self, cfg: Configuration):
        self.config = cfg
        self.api = AlpacaAPI()
        # self.db = Database(self.config.timezone)
        self.trading_session_manager = TradingSessionManager(
            cfg.timezone,
            cfg.trading_start_time,
            cfg.trading_end_time)
        
        self.market_data = pd.DataFrame()
        self._order_statuses = {}
        self._quote_data = {}

        
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


            # while True:

            try:
                self._trading_loop()

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
            
            
    def _trading_loop(self):
        """Main trading loop"""
        previous_day = pd.Timestamp.now(tz=self.config.timezone).date()
        loop_sleep_time = 30

        while True:
            logging.info(f"Starting trading loop")

            now = pd.Timestamp.now(tz=self.config.timezone)
            if now.date() > previous_day:
                Logger(now.date()) # Create new log file for new day to avoid excessively large files
                previous_day = now.date()

            if not self.trading_session_manager.is_trading_day(now):
                logging.warning("Not a trading day. Waiting...")
                time.sleep(60)
                continue
                
            if not self.trading_session_manager.is_trading_hours(now):
                logging.warning("Outside trading hours. Waiting...")
                self.portfolio_manager.clear_orders_statuses_positions()
                time.sleep(60)
                continue
            
            ## Subscribe to websocket updates
            self.api.subscribe_trade_updates(self._update_order_status)
            self.api.subscribe_option_md_updates(self._update_quote_data, [self.config.instrument_id])
            logging.info(f"Pausing for 10 seconds to observe streaming data")
            time.sleep(10)

            # Closing websockets
            logging.info(f"Closing option market data websocket")
            self.api.option_md_stream.stop()
            time.sleep(3)

            ## Place sample order
            order = self.api.place_market_order(self.config.instrument_id, 1, Signal.BUY)
            timeout = 10
            while timeout > 0:
                if order.id not in self._order_statuses:
                    timeout -= 1
                    time.sleep(1)
                else:
                    break

            # print(f"Order {order.id} status: {self._order_statuses[order.id].order.status}")


            # Checking positional data
            logging.info(f"Checking positional data")
            position = self.api.get_open_position_by_id(self.config.instrument_id)
            logging.info(f"Position: {position}")


            # Exiting all positions
            logging.info(f"Exiting position {position.symbol} with asset_id: {position.asset_id}")
            closing_order = self.api.close_position_by_id(position.asset_id)
            logging.info(f"Closing order id: {closing_order.id}")
            self._order_statuses[closing_order.id] = None

            time.sleep(3)   # pause for order callback

            #close system
            logging.warning(f"Closing application")
            sys.exit()

            logging.info(f"Trading loop complete. Sleeping for {loop_sleep_time} seconds...")
            time.sleep(loop_sleep_time)           
    

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
            filename = f"market_data_{self.config.ticker}_{timestamp}.csv"
            filepath = os.path.join(output_dir, filename)
            
            self.market_data.to_csv(filepath, index=True)
            logging.info(f"Market data saved to {filepath}")

    async def _update_order_status(self, data):
        """Update order status"""
        logging.debug(f"Order update received from WS. Id: {data.order.id}. Status: {data.order.status}")
        self._order_statuses[data.order.id] = data

    async def _update_quote_data(self, data):
        """Update quote data from WS"""
        logging.debug(f"Quote data received from WS for {data.symbol}: {data}")
        self._quote_data[data.symbol] = data

