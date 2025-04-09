from alpaca.data.live.option import OptionDataStream
from alpaca.data.historical.option import OptionHistoricalDataClient
from typing import Callable, List
import threading
import time
from typing import Union, Optional, Dict, Any
from uuid import UUID
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    GetOrdersRequest, 
    MarketOrderRequest, 
    GetOrderByIdRequest, 
    ClosePositionRequest, 
    GetOptionContractsRequest,
    LimitOrderRequest,
    StopOrderRequest,
    GetAssetsRequest
)
from alpaca.trading.enums import OrderSide, QueryOrderStatus, OrderType
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType, AssetClass
from alpaca.trading.models import OptionContract, OptionContractsResponse, Asset
import logging
import os
from src.configuration import Configuration
from src.utilities.enums import Signal
from dotenv import load_dotenv
from alpaca.trading.stream import TradingStream
from alpaca.trading.models import Order


class AlpacaAPI:
    """Wrapper class for the Alpaca API and websocket.
    
    Reference: https://alpaca.markets/sdks/python/api_reference/trading_api.html
    """
    __slots__ = (
        "trading_api", 
        "trading_stream", 
        "option_md_stream", 
        "option_md_api"
        )

    def __init__(self) -> None:
        """
        Initialize AlpacaAPI instance without an active connection.
        """
        # Configure logging to suppress Alpaca websocket & API messages
        logging.getLogger('websockets').setLevel(logging.WARNING)
        logging.getLogger('alpaca').setLevel(logging.WARNING)

        self.trading_api = None
        self.trading_stream = None
        self.option_md_stream = None
        self.option_md_api = None

    def connect(self, config: Configuration) -> None:
        self._connect_trading_api(config)
        self._connect_trading_websocket(config)
        self._connect_option_md_api(config)
        self._connect_option_md_websocket(config)

        time.sleep(3) #important to wait for the websockets to connect!

    def _connect_trading_api(self, config: Configuration) -> None:
        """
        Connect to the Alpaca API using the provided configuration.

        :param config: Configuration object containing API keys and settings.
        """
        try:
            self.trading_api = TradingClient(
                api_key=os.environ.get('ALPACA_KEY', 'WRONG-KEY'),
                secret_key=os.environ.get('ALPACA_SECRET', 'WRONG-KEY'),
                paper=config.paper_trading,
            )

            logging.info("Successfully connected to Alpaca trading client.")

        except Exception as err:
            logging.error(f"Failed to connect to Alpaca API: {err}")
            raise

    def _connect_trading_websocket(self, config: Configuration) -> None:
        """
        Connect to the Alpaca websocket.

        :param config: Configuration object containing API keys and settings.
        """
        try:
            self.trading_stream = TradingStream(
                api_key=os.environ.get('ALPACA_KEY', 'WRONG-KEY'),
                secret_key=os.environ.get('ALPACA_SECRET', 'WRONG-KEY'),
                paper=True,
            )

            thread = threading.Thread(target=self.trading_stream.run, daemon=True)
            thread.start()

            time.sleep(3) #important to wait for the websocket to connect!

            logging.info("Successfully connected to Alpaca trading websocket.")

        except Exception as err:
            logging.error(f"Failed to connect to Alpaca websocket: {err}")
            raise

    def _connect_option_md_websocket(self, config: Configuration) -> None:
        """
        Connect to the Alpaca option market data websocket.

        :param config: Configuration object containing API keys and settings.
        """
        try:
            self.option_md_stream = OptionDataStream(
                api_key=os.environ.get('ALPACA_KEY', 'WRONG-KEY'),
                secret_key=os.environ.get('ALPACA_SECRET', 'WRONG-KEY')
            )

            thread = threading.Thread(target=self.option_md_stream.run, daemon=True)
            thread.start()

            time.sleep(3) #important to wait for the websocket to connect!

            logging.info("Successfully connected to Alpaca option market data websocket.")

        except Exception as err:
            logging.error(f"Failed to connect to Alpaca option market data websocket: {err}")
            raise

    def _connect_option_md_api(self, config: Configuration) -> None:
        """
        Connect to the Alpaca option market data API.

        :param config: Configuration object containing API keys and settings.
        """
        try:
            self.option_md_api = OptionHistoricalDataClient(
                api_key=os.environ.get('ALPACA_KEY', 'WRONG-KEY'),
                secret_key=os.environ.get('ALPACA_SECRET', 'WRONG-KEY')
            )

            logging.info("Successfully connected to Alpaca option market data API.")

        except Exception as err:
            logging.error(f"Failed to connect to Alpaca option market data API: {err}")
            raise

    def subscribe_option_md_updates(self, update_handler: Callable, symbols: List[str]) -> None:
        logging.info(f"Subscribing to option market data streaming updates for {symbols}")
        self.option_md_stream.subscribe_quotes(update_handler, *symbols) 
        self.option_md_stream.subscribe_trades(update_handler, *symbols)

    def subscribe_trade_updates(self, update_handler: Callable) -> None:
        """
        Subscribe to trade updates from the Alpaca websocket.

        :param update_handler: Callable function that will be called with trade update data.
        """
        logging.info("Subscribing to trade updates from the Alpaca trading websocket.")
        self.trading_stream.subscribe_trade_updates(update_handler)

    def account_details(self) -> dict:
        return self.trading_api.get_account()
    
    def options_approved_level(self) -> int:
        return self.account_details().options_approved_level

    def options_trading_level(self) -> int:
        return self.account_details().options_trading_level

    def get_orders(self, signal: Signal = None, status: str = "all"):
        if not signal and not status:
            return self.trading_api.get_orders()
        
        if signal:
            signal = OrderSide.SELL if signal == Signal.SELL else OrderSide.BUY

        if status:
            if status == "open":
                status = QueryOrderStatus.OPEN
            elif status == "closed":
                status = QueryOrderStatus.CLOSED
            elif status == "all":
                status = QueryOrderStatus.ALL
            else:
                raise ValueError("Invalid status")

        request_params = GetOrdersRequest(
            status=status if status else None,
            side=signal if signal else None
        )

        return self.trading_api.get_orders(filter=request_params)
    
    def get_order_by_id(self, order_id: Union[UUID, str], _options: Optional[GetOrderByIdRequest] = None):
        return self.trading_api.get_order_by_id(order_id, _options)
    
    def place_market_order(self, symbol: str, qty: float, side: Signal, tif = TimeInForce.DAY) -> None:
        logging.info(f"Placing market order for {symbol} with quantity {qty} and side {side}")
        side = OrderSide.BUY if side == Signal.BUY else OrderSide.SELL

        market_order_data = MarketOrderRequest(
                            symbol=symbol,
                            qty=qty,
                            side=side,
                            time_in_force=tif
                            )

        return self.trading_api.submit_order(order_data=market_order_data)
    
    def cancel_all_orders(self) -> list:
        """Returns a list of cancelled orders"""
        return self.trading_api.cancel_orders()
    
    def cancel_order_by_id(self, order_id: Union[UUID, str]) -> None:
        return self.trading_api.cancel_order_by_id(order_id)

    def get_all_positions(self) -> list:
        """Returns a list of all positions"""
        return self.trading_api.get_all_positions()
    
    def get_open_position_by_id(self, symbol_or_asset_id: Union[UUID, str]):
        return self.trading_api.get_open_position(symbol_or_asset_id)

    def close_all_positions(self, cancel_orders: bool = True) -> list:
        """Returns a list of closed positions"""
        return self.trading_api.close_all_positions(cancel_orders=cancel_orders)
    
    # def close_position_by_id(self, symbol_or_asset_id: Union[UUID, str], close_options: Optional[ClosePositionRequest] = None):
    #     return self.client_api.close_position(symbol_or_asset_id, close_options)
    
    def close_position_by_id(self, symbol_or_asset_id: Union[UUID, str], qty: Optional[int] = None):
        if qty:
            close_options = ClosePositionRequest(qty=qty)
            return self.trading_api.close_position(symbol_or_asset_id, close_options)
        else:
            return self.trading_api.close_position(symbol_or_asset_id)
    
    def get_option_contract_by_id(self, symbol_or_id: Union[UUID, str]) -> Union[OptionContract, Dict[str, Any]]:
        return self.trading_api.get_option_contract(symbol_or_id)
    
    def get_all_assets(self, filter: Optional[GetAssetsRequest] = None) -> Union[List[Asset], Dict[str, Any]]:
        return self.trading_api.get_all_assets(filter)
    
    def get_us_options(self) -> List[Asset]:
        return self.get_all_assets(filter=GetAssetsRequest(asset_class=AssetClass.US_OPTION))
    
    def get_option_contracts(self, symbols: List[str], expiry= None):
        request = GetOptionContractsRequest(underlying_symbols=symbols, expiration_date=expiry)
        return self.trading_api.get_option_contracts(request)

    def close_websockets(self):
        logging.info("Stopping and closing websockets")
        self.trading_stream.stop()
        self.option_md_stream.stop()

