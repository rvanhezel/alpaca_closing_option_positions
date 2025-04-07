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
        self.strategy = self.config.get('Trading', 'strategy')
        self.paper_trading = self._check_paper_trading(self.config.getboolean('Trading', 'paper_trading'))

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
        
    def _check_paper_trading(self, paper_trading: bool):
        if paper_trading:
            return True
        else:
            raise ValueError("Paper trading must be enabled for testing")
