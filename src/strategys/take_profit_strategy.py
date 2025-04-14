from src.strategys.abstract_strategy import AbstractStrategy
from src.configuration import Configuration
import pandas as pd
from src.utilities.enums import Signal
from src.mkt_data.mkt_data_state import MktDataState
import logging


class TakeProfitStrategy(AbstractStrategy):
    """
    Abstract interface for trading strategies.

    Defines methods for processing market data and generating trade signals.
    """
    @staticmethod
    def generate_signals(mkt_data: MktDataState, cfg:Configuration, strategy_args: dict = None) -> Signal:      
        """
        Generate a trade signal based on the provided market data.

        :param mkt_data: MktDataState instance
        :param cfg: Configuration instance
        :param strategy_args: dict
        :return: Signal
        """
        latest_quote = mkt_data.latest_quote()
        latest_option_bid_price = latest_quote.bid_price
        cur_profit_target = strategy_args['profit_target']

        # Selling logic
        if latest_option_bid_price >= cur_profit_target:
            
            logging.info(f"Latest option quote {latest_option_bid_price} >= {cur_profit_target}")
            logging.info(f"SELL signal generated")

            return Signal.SELL
        else:
            return Signal.HOLD
