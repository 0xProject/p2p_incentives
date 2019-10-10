"""
This module defines Order and OrderInfo classes
"""

from typing import TYPE_CHECKING, Optional, Set
from data_types import (
    Category,
    Priority,
    OrderTypeName,
    SettleParameters,
    ConcaveParameters,
    CancelParameters,
    AgeBasedParameters,
)

if TYPE_CHECKING:
    from scenario import Scenario
    from node import Peer
    from engine import Engine


class Order:
    """
    Order class, each instance being an order in the mesh system.
    """

    def __init__(
        self,
        scenario: "Scenario",
        seq: int,
        birth_time: int,
        creator: Optional["Peer"],
        expiration: float = float("inf"),
        category: Category = None,
        order_type: OrderTypeName = "default",
        settlement: SettleParameters = ConcaveParameters(
            method="ConcaveParameters", sensitivity=1, max_prob=0
        ),
        cancellation: CancelParameters = AgeBasedParameters(
            method="AgeBasedParameters", sensitivity=1, max_prob=0
        ),
    ) -> None:

        self.scenario: "Scenario" = scenario  # Needed for function update_settled_status().
        self.seq: int = seq  # sequence number. Not in use now, reserved for possible future use
        self.birth_time: int = birth_time  # will be decided by system clock
        self.creator: Optional["Peer"] = creator  # the peer who creates this order
        # may refer to a trading pair label or something else
        self.category: Category = category
        self.order_type: OrderTypeName = order_type  # e.g., market making, NFT, ...

        # These are the order expiration, settlement and cancellation parameters.
        self.expiration: float = expiration  # maximum time for a peer to be valid
        self.settlement: SettleParameters = settlement
        self.cancellation: CancelParameters = cancellation

        # set of peers who put this order into their local storage.
        self.holders: Set["Peer"] = set()

        # set of peers who put this order into their pending table but not local storage.
        # in order words, these peers are hesitating whether to store the orders.
        self.hesitators: Set["Peer"] = set()

        self.is_expired: bool = False  # this order has not expired
        self.is_settled: bool = False  # this order instance has not been taken and settled
        self.is_canceled: bool = False  # will change to True when the order departs proactively.
        self.is_missing: bool = False  # will change to True if no holder nor hesitator.

        # will change to False if any of the above three attributes becomes True.
        self.is_valid: bool = True

    def update_expired_status(self, time_now) -> None:
        """Updates is_expired status for this order."""
        if time_now - self.birth_time >= self.expiration:
            self.is_expired = True

    def update_settled_status(self) -> None:
        """Updates is_settled value of this order."""
        self.scenario.update_order_settled_status(self)

    def update_canceled_status(self, time_now: float) -> None:
        """Updates is_canceled value of this order."""
        self.scenario.update_order_canceled_status(self, time_now)

    def update_missing_status(self) -> None:
        """Updates is_missing value of this order."""
        if not self.holders and not self.hesitators:
            self.is_missing = True

    def update_valid_status(self, time_now) -> None:
        """Updates is_valid value of this order."""
        self.update_expired_status(time_now)
        self.update_settled_status()
        self.update_canceled_status(time_now)
        self.update_missing_status()
        if self.is_expired or self.is_settled or self.is_canceled or self.is_missing:
            self.is_valid = False


class OrderInfo:
    """
    Orderinfo class. An instance of OrderInfo is an order instance from a peer's viewpoint.
    However, it contains extra information to an Order instance.
    Note, an Order instance can have multiple OrderInfo instances stored by different peers.
    It contains specific information about the novelty and property of the order.
    Such information is not included in Order.
    """

    def __init__(
        self,
        engine: "Engine",
        order: "Order",
        master: "Peer",
        arrival_time: int,
        priority: Priority = None,
        prev_owner: Optional["Peer"] = None,
        novelty: int = 0,
    ) -> None:

        # design choice. Needed for function orderinfo_set_priority()
        self.engine: "Engine" = engine
        # arrival time of this orderinfo to my pending table
        self.arrival_time: int = arrival_time
        # previous owner, None for a new order
        self.prev_owner: Optional["Peer"] = prev_owner
        # How many hops it has travelled. Default is 0.
        self.novelty: int = novelty

        # Note: there is no self.master or self.order. This is not a mistake.
        # These two input parameters are directly passed to
        # self.engine.set_priority_for_orderinfo() and they are not used anywhere else.

        # set up priority
        self.priority: Priority = priority
        self.engine.set_priority_for_orderinfo(
            orderinfo=self, order=order, master=master, priority=priority
        )

        # storage_decision is to record whether this peer decides to put this order into storage.
        # It seems redundant, but it will be useful in store_orders function.
        self.storage_decision: bool = False
