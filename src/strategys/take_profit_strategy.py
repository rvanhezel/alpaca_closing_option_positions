from src.strategys.abstract_strategy import AbstractStrategy
from src.configuration import Configuration
import pandas as pd
from src.utilities.enums import Signal


class TakeProfitStrategy(AbstractStrategy):
    """
    Abstract interface for trading strategies.

    Defines methods for processing market data and generating trade signals.
    """
    @staticmethod
    def generate_signals(historical_data: pd.DataFrame, cfg:Configuration) -> Signal:      
        """
        Generate a trade signal based on the provided market data.

        :param historical_data: Time series of historical data
        :param cfg: Configuration instance
        :return: Signal
        """
        pass
