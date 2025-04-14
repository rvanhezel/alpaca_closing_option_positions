import pandas as pd
import queue
from src.configuration import Configuration
import logging
import os
from datetime import datetime


class MktDataState:

    def __init__(self, config: Configuration):
        self.config = config

        self._quote_data = queue.Queue()
        self._market_data = pd.DataFrame()

    @property
    def market_data(self):
        return self._market_data

    def update_state(self, latest_tick_df: pd.DataFrame):
        """Update market data state"""

        while True:
                
            # Handle tick data
            if self.config.store_all_ticks:

                latest_ticks = []
                while not self._quote_data.empty():
                    latest_ticks.append(self._quote_data.get_nowait())

                if not latest_ticks:
                    continue

                latest_tick_df = self._parse_tick_data(latest_ticks)
                break

            else: 

                latest_quote = None
                while not self._quote_data.empty():
                    latest_quote = self._quote_data.get_nowait()

                if not latest_quote:
                    continue

                latest_tick_df = self._parse_tick_data(latest_quote)
                break

        self._market_data = pd.concat([self._market_data, latest_tick_df])
        if self.config.save_market_data and self._market_data.shape[0] % 100 == 0:
            self._save_market_data()

    def _parse_tick_data(self, latest_quote):
        latest_quote = latest_quote if isinstance(latest_quote, list) else [latest_quote]
        df = pd.DataFrame({
            'datetime': [pd.to_datetime(tick.timestamp, format='%Y%m%d %H:%M:%S %Z') for tick in latest_quote],
            'symbol': [tick.symbol for tick in latest_quote],
            'bid_price': [tick.bid_price for tick in latest_quote],
            'bid_size': [tick.bid_size for tick in latest_quote],
            'bid_exchange': [tick.bid_exchange for tick in latest_quote],
            'ask_price': [tick.ask_price for tick in latest_quote],
            'ask_size': [tick.ask_size for tick in latest_quote],
            'ask_exchange': [tick.ask_exchange for tick in latest_quote],
            'conditions': [tick.conditions for tick in latest_quote],
            'tape': [tick.tape for tick in latest_quote]
        })
        df.set_index('datetime', inplace=True)
        df.sort_index(ascending=True, inplace=True)
        df.index = df.index.tz_convert(self.config.timezone)
        return df
    
    async def update_quote_data(self, data):
        """Update quote data from WS"""
        # logging.debug(f"Quote data received from WS for {data.symbol} at {data.timestamp}")
        self._quote_data.put(data)

    def latest_quote(self):
        return self._market_data.iloc[-1]
    
    def _save_market_data(self):
        """Save data to CSV file"""
        if not self._market_data.empty:
            logging.info("Saving market data to CSV file...")

            # Create output directory if it doesn't exist
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"market_data_{self.config.instrument_id}_{timestamp}.csv"
            filepath = os.path.join(output_dir, filename)
            
            self._market_data.to_csv(filepath, index=True)
            logging.info(f"Market data saved to {filepath}")
