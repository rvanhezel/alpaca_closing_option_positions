from typing import Optional
import pandas as pd
from .instrument import Instrument


class Order:
    def __init__(self,
                 order_id: int,
                 instrument: Instrument,
                 action: str,
                 order_type: str,
                 quantity: int,
                 parent_id: Optional[int] = None,
                 transmit: bool = True):
        """Initialize an Order
        
        Args:
            order_id (int): Unique identifier for the order
            instrument (Instrument): The instrument to trade
            action (str): BUY or SELL
            order_type (str): Type of order (e.g. 'MKT')
            quantity (int): Number of contracts/shares
            parent_id (int, optional): ID of parent order for OCO/bracket orders
            transmit (bool): Whether to transmit the order immediately
        """
        self.order_id = order_id
        self.instrument = instrument
        self.action = action
        self.order_type = order_type
        self.quantity = quantity
        self.parent_id = parent_id
        self.transmit = transmit
        self.created_at = pd.Timestamp.now()

    @classmethod
    def from_dict(cls, data: dict) -> 'Order':
        """Create an Order instance from a dictionary
        
        Args:
            data (dict): Dictionary containing order data
            
        Returns:
            Order: New Order instance
        """
        return cls(
            order_id=data.get('order_id'),
            instrument=Instrument.from_dict(data.get('instrument', {})),
            action=data.get('action'),
            order_type=data.get('order_type'),
            quantity=data.get('quantity'),
            parent_id=data.get('parent_id'),
            transmit=data.get('transmit', True)
        )

    def to_dict(self) -> dict:
        """Convert the Order to a dictionary
        
        Returns:
            dict: Dictionary representation of the Order
        """
        return {
            'order_id': self.order_id,
            'instrument': self.instrument.to_dict(),
            'action': self.action,
            'order_type': self.order_type,
            'quantity': self.quantity,
            'parent_id': self.parent_id,
            'transmit': self.transmit,
            'created_at': self.created_at.isoformat()
        }

    def __str__(self) -> str:
        """String representation of the Order
        
        Returns:
            str: Formatted string showing order details
        """
        parent_str = f" (Parent: {self.parent_id})" if self.parent_id else ""
        return f"{self.action} {self.quantity} {self.instrument} {self.order_type}{parent_str}"


class LimitOrder(Order):
    def __init__(self,
                 order_id: int,
                 instrument: Instrument,
                 action: str,
                 quantity: int,
                 limit_price: float,
                 parent_id: Optional[int] = None,
                 transmit: bool = True):
        """Initialize a Limit Order
        
        Args:
            order_id (int): Unique identifier for the order
            instrument (Instrument): The instrument to trade
            action (str): BUY or SELL
            quantity (int): Number of contracts/shares
            limit_price (float): Limit price for the order
            parent_id (int, optional): ID of parent order for OCO/bracket orders
            transmit (bool): Whether to transmit the order immediately
        """
        super().__init__(order_id, instrument, action, 'LMT', quantity, parent_id, transmit)
        self.limit_price = limit_price

    @classmethod
    def from_dict(cls, data: dict) -> 'LimitOrder':
        """Create a LimitOrder instance from a dictionary
        
        Args:
            data (dict): Dictionary containing order data
            
        Returns:
            LimitOrder: New LimitOrder instance
        """
        return cls(
            order_id=data.get('order_id'),
            instrument=Instrument.from_dict(data.get('instrument', {})),
            action=data.get('action'),
            quantity=data.get('quantity'),
            limit_price=data.get('limit_price'),
            parent_id=data.get('parent_id'),
            transmit=data.get('transmit', True)
        )

    def to_dict(self) -> dict:
        """Convert the LimitOrder to a dictionary
        
        Returns:
            dict: Dictionary representation of the LimitOrder
        """
        data = super().to_dict()
        data['limit_price'] = self.limit_price
        return data

    def __str__(self) -> str:
        """String representation of the LimitOrder
        
        Returns:
            str: Formatted string showing order details
        """
        base_str = super().__str__()
        return f"{base_str} @ {self.limit_price}"


class StopOrder(Order):
    def __init__(self,
                 order_id: int,
                 instrument: Instrument,
                 action: str,
                 quantity: int,
                 stop_price: float,
                 parent_id: Optional[int] = None,
                 transmit: bool = True):
        """Initialize a Stop Order
        
        Args:
            order_id (int): Unique identifier for the order
            instrument (Instrument): The instrument to trade
            action (str): BUY or SELL
            quantity (int): Number of contracts/shares
            stop_price (float): Stop price for the order
            parent_id (int, optional): ID of parent order for OCO/bracket orders
            transmit (bool): Whether to transmit the order immediately
        """
        super().__init__(order_id, instrument, action, 'STP', quantity, parent_id, transmit)
        self.stop_price = stop_price

    @classmethod
    def from_dict(cls, data: dict) -> 'StopOrder':
        """Create a StopOrder instance from a dictionary
        
        Args:
            data (dict): Dictionary containing order data
            
        Returns:
            StopOrder: New StopOrder instance
        """
        return cls(
            order_id=data.get('order_id'),
            instrument=Instrument.from_dict(data.get('instrument', {})),
            action=data.get('action'),
            quantity=data.get('quantity'),
            stop_price=data.get('stop_price'),
            parent_id=data.get('parent_id'),
            transmit=data.get('transmit', True)
        )

    def to_dict(self) -> dict:
        """Convert the StopOrder to a dictionary
        
        Returns:
            dict: Dictionary representation of the StopOrder
        """
        data = super().to_dict()
        data['stop_price'] = self.stop_price
        return data

    def __str__(self) -> str:
        """String representation of the StopOrder
        
        Returns:
            str: Formatted string showing order details
        """
        base_str = super().__str__()
        return f"{base_str} @ {self.stop_price} stop"


class BracketOrder:
    def __init__(self,
                 entry_order: LimitOrder,
                 take_profit: LimitOrder,
                 stop_loss: StopOrder):
        """Initialize a Bracket Order
        
        Args:
            entry_order (LimitOrder): The entry limit order
            take_profit (LimitOrder): The take profit limit order
            stop_loss (StopOrder): The stop loss order
        """
        self.entry_order = entry_order
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        
        # Link the orders together
        self.entry_order.parent_id = None
        self.take_profit.parent_id = self.entry_order.order_id
        self.stop_loss.parent_id = self.entry_order.order_id

    @classmethod
    def from_dict(cls, data: dict) -> 'BracketOrder':
        """Create a BracketOrder instance from a dictionary
        
        Args:
            data (dict): Dictionary containing bracket order data
            
        Returns:
            BracketOrder: New BracketOrder instance
        """
        return cls(
            entry_order=LimitOrder.from_dict(data.get('entry_order', {})),
            take_profit=LimitOrder.from_dict(data.get('take_profit', {})),
            stop_loss=StopOrder.from_dict(data.get('stop_loss', {}))
        )

    def to_dict(self) -> dict:
        """Convert the BracketOrder to a dictionary
        
        Returns:
            dict: Dictionary representation of the BracketOrder
        """
        return {
            'entry_order': self.entry_order.to_dict(),
            'take_profit': self.take_profit.to_dict(),
            'stop_loss': self.stop_loss.to_dict()
        }

    def __str__(self) -> str:
        """String representation of the BracketOrder
        
        Returns:
            str: Formatted string showing bracket order details
        """
        return (f"Bracket Order:\n"
                f"Entry: {self.entry_order}\n"
                f"Take Profit: {self.take_profit}\n"
                f"Stop Loss: {self.stop_loss}") 