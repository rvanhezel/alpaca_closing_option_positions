from twelvedata import TDClient
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType, TakeProfitRequest, StopLossRequest
import logging
import os
import time
import random
from src.configuration import Configuration
import os


class AlpacaAPI:
    __slots__ = ("client_api")

    def __init__(self) -> None:
        """
        Initialize AlpacaAPI instance without an active connection.
        """
        super().__init__()
        self.client_api = None

    def connect(self, config: Configuration) -> None:
        """
        Connect to the Alpaca API using the provided configuration.

        :param config: Configuration object containing API keys and settings.
        """
        try:
            self.client_api = TradingClient(
                api_key=os.environ.get('ALPACA_KEY', 'WRONG-KEY'),
                secret_key=os.environ.get('ALPACA_SECRET', 'WRONG-KEY'),
                paper=config.paper_trading,
            )
            logging.info("Successfully connected to Alpaca client.")
        except Exception as err:
            logging.error(f"Failed to connect to Alpaca API: {err}")
            raise
