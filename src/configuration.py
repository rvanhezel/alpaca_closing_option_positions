import os
import configparser
import logging
from datetime import datetime
import pytz


class Configuration:

    def __init__(self, path_to_config: str):
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

        self._perform_sanity_checks()

    def _confirm_profit_targets(self):
        if sum(self.profit_targets) != 1:
            raise ValueError("Profit targets must sum to 1")

    def _configure_log(self, log_level: str):
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
        
    def _confirm_paper_trading(self):
        if self.paper_trading:
            return True
        else:
            raise ValueError("Paper trading must be enabled for testing")
        
    def _perform_sanity_checks(self):
        # self._confirm_profit_targets()
        self._confirm_sell_buckets()
        self._confirm_paper_trading()

    def _confirm_sell_buckets(self):
        if self.sell_buckets != len(self.profit_targets):
            raise ValueError("Sell buckets must be equal to the number of profit targets")
        
        

        
    
