import unittest
import pandas as pd
import numpy as np
import os
from src.strategys.take_profit_strategy import TakeProfitStrategy
from src.utilities.enums import Signal
from src.configuration import Configuration
from src.mkt_data.mkt_data_state import MktDataState
from datetime import datetime
import pytz


class Quote:
    def __init__(self, bid_price, ask_price=None, timestamp=None, symbol=None, bid_size=None, 
                 bid_exchange=None, ask_size=None, ask_exchange=None, conditions=None, tape=None):
        self.bid_price = bid_price
        self.ask_price = ask_price
        self.timestamp = timestamp or datetime.now(pytz.timezone("US/Eastern"))
        self.symbol = symbol
        self.bid_size = bid_size or 1
        self.bid_exchange = bid_exchange or "NYSE"
        self.ask_size = ask_size or 1
        self.ask_exchange = ask_exchange or "NYSE"
        self.conditions = conditions
        self.tape = tape


class TestTakeProfitStrategy(unittest.TestCase):
    def setUp(self):
        # Get the path to the test config file
        config_path = os.path.join(os.getcwd(), 
                                   "test", 
                                   "test_strategy", 
                                   "test_run.cfg")
        self.cfg = Configuration(config_path)
        self.strategy = TakeProfitStrategy()
        self.mkt_data = MktDataState(self.cfg)

    def _add_quote_to_market_data(self, quote):
        """Helper method to add a quote to market data"""
        self.mkt_data._quote_data.put(quote)
        self.mkt_data.update_state()

    def test_generate_sell_signal(self):
        """Test that a SELL signal is generated when price exceeds profit target"""
        # Create a quote with bid price above profit target
        quote = Quote(bid_price=1.2, ask_price=1.3)
        self._add_quote_to_market_data(quote)
        
        # Set profit target to 1.0
        strategy_args = {'profit_target': 1.0}
        
        signal = self.strategy.generate_signals(self.mkt_data, self.cfg, strategy_args)
        self.assertEqual(signal, Signal.SELL)

    def test_generate_hold_signal(self):
        """Test that a HOLD signal is generated when price is below profit target"""
        # Create a quote with bid price below profit target
        quote = Quote(bid_price=0.8, ask_price=0.9)
        self._add_quote_to_market_data(quote)
        
        # Set profit target to 1.0
        strategy_args = {'profit_target': 1.0}
        
        signal = self.strategy.generate_signals(self.mkt_data, self.cfg, strategy_args)
        self.assertEqual(signal, Signal.HOLD)

    def test_edge_case_exact_profit_target(self):
        """Test edge case where price exactly equals profit target"""
        # Create a quote with bid price exactly at profit target
        quote = Quote(bid_price=1.0, ask_price=1.1)
        self._add_quote_to_market_data(quote)
        
        # Set profit target to 1.0
        strategy_args = {'profit_target': 1.0}
        
        signal = self.strategy.generate_signals(self.mkt_data, self.cfg, strategy_args)
        self.assertEqual(signal, Signal.SELL)  # Should sell when price equals target

if __name__ == '__main__':
    unittest.main()
