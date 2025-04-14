from src.api.api_utils import is_expiry_day, check_options_level
from src.utilities.utils import quantity_buckets
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
from typing import List, Optional


class ExecutionOrchestrator:
    """Orchestrates the execution of trading strategies and position management.
    
    This class manages the entire trading lifecycle including:
    - System initialization and configuration
    - Trading session management
    - Position entry and exit
    - Risk management and profit taking
    - End-of-day procedures
    """

    def __init__(self, cfg: Configuration) -> None:
        """Initialize the execution orchestrator.
        
        Args:
            cfg (Configuration): Configuration object containing trading parameters
        """
        self.config = cfg
        self.api = AlpacaAPI()
        self.trading_session_manager = TradingSessionManager(
            cfg.timezone,
            cfg.trading_start_time,
            cfg.trading_end_time)
        self.portfolio_manager = PortfolioManager(cfg, self.api)
        self.mkt_data_state = MktDataState(cfg)

        self.expiry_day = False

    def start(self) -> None:
        """Start the trading system and initialize all components.
        
        This method:
        - Saves the configuration for audit purposes
        - Initializes the API connection
        - Sets up market data subscriptions
        - Starts the main trading loop
        
        Raises:
            ConnectionError: If API connection fails
            Exception: For any other unexpected errors
        """
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
                            #Unclear why this is needed over the pause in the api.connect()

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
            
    def _trading_session_loop(self) -> None:
        """Main trading loop that manages the trading session.
        
        This method:
        - Checks if it's a valid trading day
        - Manages trading hours
        - Handles day transitions
        - Executes trading logic during valid sessions
        """
        previous_day = pd.Timestamp.now(tz=self.config.timezone).date()
        self.expiry_day = is_expiry_day(self.api, self.config.instrument_id, self.config.timezone)

        if self.expiry_day:
            logging.info(f"{self.config.instrument_id} is expiring today: {self.expiry_day}")

        if not check_options_level(self.api, 3):
            raise ValueError("Options trading level is too low. Requier level 3Exiting...")

        while True:
            logging.info(f"Starting trading loop")

            now = pd.Timestamp.now(tz=self.config.timezone)
            if now.date() > previous_day:
                Logger(now.date()) # Create new log file for new day to avoid excessively large files
                previous_day = now.date()

            if self.trading_session_manager.is_trading_day(now) and self.trading_session_manager.is_trading_hours(now):

                if self._trading_execution():
                    break

            else:

                logging.warning("Outside trading schedule. Waiting...")
                time.sleep(60)

    def _trading_execution(self) -> bool:
        """Execute the core trading logic.
        
        This method:
        - Places initial orders
        - Manages position entry
        - Implements profit-taking strategy
        - Handles position exits
        - Manages expiry day procedures
        
        Raises:
            ValueError: If position quantities don't match expectations
            Exception: For any other unexpected errors

        Returns:
            bool: True once all positions are closed
        """
        ## Place sample order & wait for response
        order = self.api.place_market_order(
            self.config.instrument_id, 
            self.config.starting_position_quantity, 
            Signal.BUY)
        self.portfolio_manager.wait_for_order_response(order.id, self.config.timeout)

        # Get position from API
        native_position = self.api.get_open_position_by_id(self.config.instrument_id)

        # Define profit targets and sell quantity buckets
        profit_target_levels = [float(native_position.avg_entry_price) * (1 + target) for target in self.config.profit_targets]
        logging.info(f"Profit target levels: {profit_target_levels}")

        original_sell_quantity_buckets = quantity_buckets(self.config.starting_position_quantity, 
                                                 self.config.sell_buckets, 
                                                 self.config.close_strategy)
        logging.info(f"Sell quantity buckets: {original_sell_quantity_buckets}")
        logging.info(f"The latest bucket with quantity {original_sell_quantity_buckets[-1]} will be used as runners.")
        logging.info(f"No take-profit constraint for these.")

        sell_quantity_buckets = original_sell_quantity_buckets[:-1]

        # Check existing position has enough quantity to sell
        if native_position is None:
            logging.error(f"No position found for {self.config.instrument_id}")
            return
        else:
            logging.info(f"Position found for {self.config.instrument_id}")
            logging.debug(f"{native_position}")

        required_qty = sum(original_sell_quantity_buckets[self.portfolio_manager.starting_idx:])
        if int(native_position.qty) < required_qty:
            logging.error(f"Position quantity mismatch. Expected at least {required_qty}, got {native_position.qty}")
            logging.error("Will not be able to close positions as requested.")

            raise ValueError("Position quantity mismatch. Please check.")
        else:
            logging.info(f"Position quantity sufficient. Expected {required_qty}, got {native_position.qty}")
     
  
        try:

            for idx, (cur_bucket_qty, cur_profit_target) in enumerate(zip(sell_quantity_buckets, profit_target_levels)):
                logging.info(f"Current bucket quantity: {cur_bucket_qty}, Current profit target: {cur_profit_target}")

                if idx < self.portfolio_manager.starting_idx:
                    logging.info(f"Skipping bucket {idx} as it has already been closed")
                    continue

                if cur_bucket_qty > 0:

                    loop_counter = 0
                    while True:

                        loop_counter += 1

                        if self.portfolio_manager.process_latest_order():
                            break

                        self.mkt_data_state.update_state()

                        # Log every 100 iterations for debugging
                        if loop_counter % 100 == 0:
                            latest_quote = self.mkt_data_state.latest_quote()

                            msg = f"Using quote: timestamp: {latest_quote.name}, bid_price: {latest_quote.bid_price}"
                            msg += f", target: {cur_profit_target}"
                            logging.info(msg)

                        signal = TakeProfitStrategy.generate_signals(self.mkt_data_state, self.config, {'profit_target': cur_profit_target})

                        # Selling logic
                        if signal == Signal.SELL and not self.portfolio_manager.latest_order_pending():
                        
                            logging.info(f"Closing position {native_position.symbol} with quantity {cur_bucket_qty}")

                            #close position
                            self.portfolio_manager.close_position_by_id(native_position.symbol, cur_bucket_qty, idx)

                            if self.portfolio_manager.process_latest_order():
                                break

                        if self.expiry_day:

                            now = pd.Timestamp.now(tz=self.config.timezone)
                            expiry_sell_cutoff = self.trading_session_manager.trading_end - pd.Timedelta(minutes=self.config.expiry_sell_cutoff)

                            if loop_counter % 100 == 0:
                                logging.info(f"Expiry day. Checking if we should close positions. Cutoff time: {expiry_sell_cutoff}")

                            if now >= expiry_sell_cutoff and not self.portfolio_manager.latest_order_pending():

                                msg = f"Current time {now} >= expiry cutoff {expiry_sell_cutoff}."
                                msg += f" Closing position {native_position.symbol} with quantity {cur_bucket_qty}"
                                logging.info(msg)
                            
                                self.portfolio_manager.close_position_by_id(native_position.symbol, cur_bucket_qty, idx)
                                
                                if self.portfolio_manager.process_latest_order():
                                    break

                else:
                    raise ValueError(f"Current bucket quantity is {cur_bucket_qty}. Exiting loop.")
                
            logging.info(f"All positions closed. Only runners left. Terminating...")
            return True

        except Exception as e:

            logging.debug(f"Error: {e}")
            logging.debug(f"Closing all positions")

            self.api.close_all_positions()

    def _save_config(self) -> None:
        """Save the current configuration to the output directory for audit purposes.
        
        The configuration is saved with a timestamp in the filename to maintain
        a history of configurations used for trading sessions.
        """
        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%d%m%Y")
        filename = f"config_{timestamp}.cfg"
        filepath = os.path.join(output_dir, filename)
        
        shutil.copy2('run.cfg', filepath)
        logging.info(f"Configuration saved to {filepath}")