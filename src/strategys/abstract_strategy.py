from abc import ABC, abstractmethod
from src.mkt_data.mkt_data_state import MktDataState


class AbstractStrategy(ABC):
    """
    Abstract interface for trading strategies.

    Defines methods for processing market data and generating trade signals.
    """
    @staticmethod
    @abstractmethod
    def generate_signals(mkt_data: MktDataState, cfg, strategy_args: dict = None):        
        """
        Generate a trade signal based on the provided market data.

        :param mkt_data: MktDataState instance
        :param cfg: Configuration instance
        :return: Signal
        """
        pass
