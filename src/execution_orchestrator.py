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
from src.portfolio.portfolio_manager import PortfolioManager
from src.mkt_data.mkt_data_state import MktDataState
from src.strategys.take_profit_strategy import TakeProfitStrategy


class ExecutionOrchestrator:

    def __init__(self, cfg: Configuration):
        self.config = cfg
        self.api = AlpacaAPI()
        self.trading_session_manager = TradingSessionManager(
            cfg.timezone,
            cfg.trading_start_time,
            cfg.trading_end_time)
        self.portfolio_manager = PortfolioManager(cfg, self.api)
        self.mkt_data_state = MktDataState(cfg)

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

            self.portfolio_manager.populate_from_csv()

            self.api.connect(self.config)
            self.api.subscribe_trade_updates(self.portfolio_manager.update_order_status)
            self.api.subscribe_option_md_updates(
                self.mkt_data_state.update_quote_data, 
                self.portfolio_manager.update_trade_data, 
                [self.config.instrument_id]
                )

            time.sleep(3)   #Seems important to wait for the websocket to connect! 
                            #Not sure why this is needed over the pause in the api.connect()

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

    def _trading_execution(self):
        """Execute trading logic"""

        ## Place sample order & wait for response
        order = self.api.place_market_order(
            self.config.instrument_id, 
            self.config.starting_position_quantity, 
            Signal.BUY)
        self.portfolio_manager.wait_for_order_response(order.id, self.config.timeout)

        # Get position from API
        native_position = self.api.get_open_position_by_id(self.config.instrument_id)

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

        sell_quantity_buckets = quantity_buckets(self.config.starting_position_quantity, 
                                                 self.config.sell_buckets, 
                                                 self.config.close_strategy)
        logging.info(f"Sell quantity buckets: {sell_quantity_buckets}")

        # Check expiry day
        now = pd.Timestamp.now(tz=self.config.timezone)
        expiry_date = self.api.get_option_contract_by_id(native_position.symbol).expiration_date
        if now.date() == expiry_date:
            logging.info(f"{native_position.symbol} is expiring today.")
            self.expiry_day = True
            

        try:

            for idx, (cur_bucket_qty, cur_profit_target) in enumerate(zip(sell_quantity_buckets, profit_target_levels)):
                logging.debug(f"Current bucket quantity: {cur_bucket_qty}, Current profit target: {cur_profit_target}")

                if idx < self.portfolio_manager.starting_idx:
                    logging.info(f"Skipping bucket {idx} as it has already been closed")
                    continue

                if cur_bucket_qty > 0:

                    loop_counter = 0
                    while True:

                        if self.portfolio_manager.process_latest_order():
                            break

                        self.mkt_data_state.update_state()
                        loop_counter += 1

                        if loop_counter % 1000 == 0:
                            latest_quote = self.mkt_data_state.latest_quote()

                            msg = f"Using quote: timestamp: {latest_quote.name}, bid_price: {latest_quote.bid_price}"
                            msg += f", target: {cur_profit_target}"
                            logging.debug(msg)

                        signal = TakeProfitStrategy.generate_signals(self.mkt_data_state, self.config, {'profit_target': cur_profit_target})

                        # Selling logic
                        if signal == Signal.SELL and not self.portfolio_manager.latest_order_pending():
                        
                            logging.debug(f"Closing position {native_position.symbol} with quantity {cur_bucket_qty}")

                            #close position
                            self.portfolio_manager.close_position_by_id(native_position.symbol, cur_bucket_qty, idx)

                            if self.portfolio_manager.process_latest_order():
                                break

                        if self.expiry_day:

                            now = pd.Timestamp.now(tz=self.config.timezone)
                            expiry_sell_cutoff = self.trading_session_manager.trading_end - pd.Timedelta(minutes=self.config.expiry_sell_cutoff)
                            logging.info(f"Expiry day. Checking if we should close positions. Cutoff time: {expiry_sell_cutoff}")

                            if now >= expiry_sell_cutoff and not self.portfolio_manager.latest_order_pending():

                                msg = f"Current time {now} >= expiry cutoff {expiry_sell_cutoff}."
                                msg += f" Closing position {native_position.symbol} with quantity {cur_bucket_qty}"
                                logging.info(msg)
                            
                                self.portfolio_manager.close_position_by_id(native_position.symbol, cur_bucket_qty, idx)
                                
                                if self.portfolio_manager.process_latest_order():
                                    break

                            logging.debug(f"Looping again...")

                else:
                    raise ValueError(f"Current bucket quantity is {cur_bucket_qty}. Exiting loop.")

        except Exception as e:

            logging.debug(f"Error: {e}")
            logging.debug(f"Closing all positions")

            self.api.close_all_positions()

        finally:

            logging.info("All positions closed. Terminating...")

            
