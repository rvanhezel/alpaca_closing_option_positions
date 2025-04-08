from typing import Callable
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
    StopOrderRequest
)
from alpaca.trading.enums import OrderSide, QueryOrderStatus, OrderType
from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce, OrderType
from alpaca.trading.models import OptionContract, OptionContractsResponse
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
    __slots__ = ("client_api", "trading_stream")

    def __init__(self) -> None:
        """
        Initialize AlpacaAPI instance without an active connection.
        """
        # Configure logging to suppress Alpaca websocket & API messages
        logging.getLogger('websockets').setLevel(logging.WARNING)
        logging.getLogger('alpaca').setLevel(logging.WARNING)

        self.client_api = None
        self.trading_stream = None

    def connect(self, config: Configuration) -> None:
        self._connect_api(config)
        self._connect_websocket(config)

    def _connect_api(self, config: Configuration) -> None:
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

    def _connect_websocket(self, config: Configuration) -> None:
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

            logging.info("Successfully connected to Alpaca websocket.")

        except Exception as err:
            logging.error(f"Failed to connect to Alpaca websocket: {err}")
            raise

    def subscribe_trade_updates(self, update_handler: Callable) -> None:
        """
        Subscribe to trade updates from the Alpaca websocket.

        :param update_handler: Callable function that will be called with trade update data.
        """
        self.trading_stream.subscribe_trade_updates(update_handler)

    def account_details(self) -> dict:
        return self.client_api.get_account()
    
    def options_approved_level(self) -> int:
        return self.account_details().options_approved_level

    def options_trading_level(self) -> int:
        return self.account_details().options_trading_level

    def get_orders(self, signal: Signal = None, status: str = "all"):
        if not signal and not status:
            return self.client_api.get_orders()
        
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

        return self.client_api.get_orders(filter=request_params)
    
    def get_order_by_id(self, order_id: Union[UUID, str], _options: Optional[GetOrderByIdRequest] = None):
        return self.client_api.get_order_by_id(order_id, _options)
    
    def place_market_order(self, symbol: str, qty: float, side: Signal, tif = TimeInForce.DAY) -> None:
        side = OrderSide.BUY if side == Signal.BUY else OrderSide.SELL

        market_order_data = MarketOrderRequest(
                            symbol=symbol,
                            qty=qty,
                            side=side,
                            time_in_force=tif
                            )

        return self.client_api.submit_order(order_data=market_order_data)
    
    def cancel_all_orders(self) -> list:
        """Returns a list of cancelled orders"""
        return self.client_api.cancel_orders()
    
    def cancel_order_by_id(self, order_id: Union[UUID, str]) -> None:
        return self.client_api.cancel_order_by_id(order_id)

    def get_all_positions(self) -> list:
        """Returns a list of all positions"""
        return self.client_api.get_all_positions()
    
    def get_open_position_by_id(self, symbol_or_asset_id: Union[UUID, str]):
        return self.client_api.get_open_position(symbol_or_asset_id)

    def close_all_positions(self, cancel_orders: bool = True) -> list:
        """Returns a list of closed positions"""
        return self.client_api.close_all_positions(cancel_orders=cancel_orders)
    
    def close_position_by_id(self, symbol_or_asset_id: Union[UUID, str], close_options: Optional[ClosePositionRequest] = None):
        return self.client_api.close_position(symbol_or_asset_id, close_options)
    
    def get_option_contracts(self, request: GetOptionContractsRequest) -> Union[OptionContractsResponse, Dict[str, Any]]:
        return self.client_api.get_option_contracts(request)
    
    def get_option_contract_by_id(self, symbol_or_id: Union[UUID, str]) -> Union[OptionContract, Dict[str, Any]]:
        return self.client_api.get_option_contract(symbol_or_id)

    def place_option_order(self, 
                          symbol: str, 
                          qty: int, 
                          side: Signal, 
                          expiry: str, 
                          strike: float, 
                          right: str,
                          order_type: OrderType = OrderType.MARKET,
                          limit_price: Optional[float] = None,
                          stop_price: Optional[float] = None,
                          tif: TimeInForce = TimeInForce.DAY) -> Order:
        """
        Place an option order.
        
        Args:
            symbol (str): The underlying symbol (e.g., 'AAPL')
            qty (int): Number of contracts
            side (Signal): BUY or SELL
            expiry (str): Expiration date in YYYY-MM-DD format
            strike (float): Strike price
            right (str): 'C' for call or 'P' for put
            order_type (OrderType): MARKET, LIMIT, or STOP
            limit_price (float, optional): Required for limit orders
            stop_price (float, optional): Required for stop orders
            tif (TimeInForce): Time in force for the order
            
        Returns:
            Order: The created order
        """
        side = OrderSide.BUY if side == Signal.BUY else OrderSide.SELL
        
        # Construct the option symbol
        option_symbol = f"{symbol}{expiry.replace('-', '')}{right}{int(strike*1000):08d}"
        
        # Create the appropriate order request based on order type
        if order_type == OrderType.MARKET:

            order_data = MarketOrderRequest(
                symbol=option_symbol,
                qty=qty,
                side=side,
                time_in_force=tif
            )
        elif order_type == OrderType.LIMIT:

            if limit_price is None:
                raise ValueError("limit_price is required for limit orders")
            
            order_data = LimitOrderRequest(
                symbol=option_symbol,
                qty=qty,
                side=side,
                time_in_force=tif,
                limit_price=limit_price
            )

        elif order_type == OrderType.STOP:

            if stop_price is None:
                raise ValueError("stop_price is required for stop orders")
            
            order_data = StopOrderRequest(
                symbol=option_symbol,
                qty=qty,
                side=side,
                time_in_force=tif,
                stop_price=stop_price
            )
        else:
            raise ValueError(f"Unsupported order type: {order_type}")
        
        return self.client_api.submit_order(order_data=order_data)




