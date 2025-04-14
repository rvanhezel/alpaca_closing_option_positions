import os
import configparser
import logging
from datetime import datetime
import pytz
from typing import List


class Configuration:
    """
    Configuration class for managing trading system settings.
    
    This class handles the loading and validation of configuration settings from a config file.
    It provides access to various trading parameters and performs sanity checks on the configuration.
    """

    def __init__(self, path_to_config: str) -> None:
        """
        Initialize the Configuration object with settings from a config file.

        Args:
            path_to_config (str): Path to the configuration file.

        Raises:
            ValueError: If the configuration is invalid or sanity checks fail.
        """
        self.config = configparser.ConfigParser()
        self.config.read(path_to_config)

        # Run section
        self.log_level = self._configure_log(self.config.get('Run', 'log_level'))
        logger = logging.getLogger()
        logger.setLevel(self.log_level)

        # Trading section
        self.trading_start_time = self.config.get('Trading', 'trading_start_time')
        self.trading_end_time = self.config.get('Trading', 'trading_end_time')
        self.eod_exit_time = self.config.get('Trading', 'eod_exit_time')
        self.timezone = self.config.get('Trading', 'timezone')
        self.close_strategy = self.config.get('Trading', 'close_strategy')
        self.profit_targets = [float(target.strip()) for target in self.config.get('Trading', 'profit_targets').split(',')]

        self.sell_buckets = int(self.config.get('Trading', 'sell_buckets'))
        self.paper_trading = self.config.getboolean('Trading', 'paper_trading')

        # Positions section
        self.instrument_id = self.config.get('Positions', 'instrument_id')
        self.starting_position_quantity = int(self.config.get('Positions', 'starting_position_quantity'))

        # Market Data section
        self.save_market_data = self.config.getboolean('Market_Data', 'save_market_data')
        self.store_all_ticks = self.config.getboolean('Market_Data', 'store_all_ticks')

        # Risk Management section
        self.expiry_sell_cutoff = int(self.config.get('Risk_Management', 'expiry_sell_cutoff'))

        # API section
        self.timeout = int(self.config.get('API', 'timeout'))

        self._perform_sanity_checks()

    def _configure_log(self, log_level: str) -> int:
        """
        Convert string log level to logging module level.

        Args:
            log_level (str): String representation of log level (Debug, Info, Warning, Error)

        Returns:
            int: Corresponding logging module level constant

        Raises:
            ValueError: If log_level is not recognized
        """
        if log_level == "Debug":
            return logging.DEBUG
        elif log_level == "Info":
            return logging.INFO
        elif log_level == "Warning":
            return logging.WARNING
        elif log_level == "Error":
            return logging.ERROR
        else:
            raise ValueError("Log level not recognized")
        
    def _confirm_paper_trading(self) -> bool:
        """
        Verify that paper trading is enabled.

        Returns:
            bool: True if paper trading is enabled

        Raises:
            ValueError: If paper trading is not enabled
        """
        if self.paper_trading:
            return True
        else:
            raise ValueError("Paper trading must be enabled for testing")
        
    def _perform_sanity_checks(self) -> None:
        """
        Perform all configuration sanity checks.

        Raises:
            ValueError: If any sanity check fails
        """
        self._confirm_sell_buckets()
        self._confirm_paper_trading()

    def _confirm_sell_buckets(self) -> None:
        """
        Verify that the number of sell buckets matches the number of profit targets.

        Raises:
            ValueError: If sell_buckets is not equal to len(profit_targets) + 1
        """
        if self.sell_buckets != len(self.profit_targets) + 1:
            msg = f"Sell buckets must be equal to the number of profit targets - 1."
            msg += f"The last bucket is used for runners."
            raise ValueError(msg)
        
        

        
    
